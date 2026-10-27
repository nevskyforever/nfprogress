import { decodeBase64Url, encodeBase64Url } from '@/api/base64url'
import type { AuthoritativeAccountBinding } from '@/auth/accountBinding'
import type { AuthoritativeKeyContextLease, RuntimeKeyContext } from '@/auth/keyContext'
import type { NormalUserAuthRuntime } from '@/auth/userAuth'
import { validatePortableDocument, validateTiptap, DocumentCodecError, type PortableDocument } from '@/cloud/documentCodec'
import { canonical, timestamp } from '@/cloud/projectMetadataCodec'
import { canonicalizeSyncTimestamp } from '@/cloud/syncTimestamp'
import { decryptObjectBytes, encryptObjectBytes, type AccountMasterKey } from '@/crypto'
import type { TiptapDocument } from '@/types/documents'
import { assertLocalSourceInTransaction, type BrowserLocalAuthorityRuntime, type LocalSourceToken } from './localAuthority'
import { localCanonicalBytes, localExact, localId, localSafe, validateLocalEnvelope, type LocalEnvelope } from './localAuthorityRecords'
import type { BrowserLocalStagesRuntime, LocalStage } from './localStages'
import { BrowserPersistenceError } from './persistence'
import { snapshotBrowserSyncScope, type BrowserSyncScope, type BrowserSyncTransaction } from './syncDurability'

/** One main manuscript for a project or one of its stages. No cloud writer. */
export interface LocalDocument {
  id: string
  project_id: string
  stage_id: string | null
  title: string
  content: TiptapDocument
  revision: number
  created_at: string
}

interface DocumentRow {
  record_version: 1
  account_id: string
  device_id: string
  project_id: string
  scope_key: string
  document_id: string
  revision: number
  envelope: LocalEnvelope
}

interface DocumentPayload {
  local_format: 1
  kind: 'document'
  account_id: string
  device_id: string
  project_id: string
  scope_key: string
  document_id: string
  revision: number
  document: PortableDocument
}

const MAX_DOCUMENT_BYTES = 8 * 1024 * 1024 - 20
const emptyContent: TiptapDocument = { type: 'doc', content: [{ type: 'paragraph' }] }
const fail = (code: 'closed' | 'corrupt_record' | 'invalid_local_source' | 'missing_local_source' | 'stale_source' | 'unsupported_local_source' | 'source_limit'): never => { throw new BrowserPersistenceError(code) }
const keyFor = (stageId: string | null) => stageId === null ? 'project' : `stage:${stageId}`
const rowKey = (scope: BrowserSyncScope, projectId: string, stageId: string | null) => [scope.accountId, projectId, keyFor(stageId)]
const now = () => canonicalizeSyncTimestamp(new Date().toISOString())

function validateContent(content: unknown): TiptapDocument {
  try { validateTiptap(content) }
  catch (error) {
    if (error instanceof DocumentCodecError && error.code === 'document_resource_limit') fail('source_limit')
    fail('invalid_local_source')
  }
  return structuredClone(content as TiptapDocument)
}

function validateRow(value: unknown, scope: BrowserSyncScope, projectId: string, stageId: string | null): DocumentRow {
  if (!localExact(value, ['record_version', 'account_id', 'device_id', 'project_id', 'scope_key', 'document_id', 'revision', 'envelope'])) fail('corrupt_record')
  const row = value as unknown as DocumentRow
  localId(row.document_id)
  if (row.record_version !== 1 || row.account_id !== scope.accountId || row.device_id !== scope.deviceId || row.project_id !== projectId
    || row.scope_key !== keyFor(stageId) || !localSafe(row.revision, 1)) fail('corrupt_record')
  const envelope = validateLocalEnvelope(row.envelope)
  const ciphertext = decodeBase64Url(envelope.ciphertext)
  try { if (ciphertext.length > MAX_DOCUMENT_BYTES + 16) fail('source_limit') }
  finally { ciphertext.fill(0) }
  return { ...row, envelope }
}

export class BrowserLocalDocuments {
  constructor(private readonly transaction: BrowserSyncTransaction) {}

  bind(auth: NormalUserAuthRuntime, bindings: AuthoritativeAccountBinding, keys: RuntimeKeyContext,
    source: BrowserLocalAuthorityRuntime, stages: BrowserLocalStagesRuntime): BrowserLocalDocumentsRuntime {
    return new BrowserLocalDocumentsRuntime(this.transaction, auth, bindings, keys, source, stages)
  }
}

export class BrowserLocalDocumentsRuntime {
  constructor(private readonly transaction: BrowserSyncTransaction, private readonly auth: NormalUserAuthRuntime,
    private readonly bindings: AuthoritativeAccountBinding, private readonly keys: RuntimeKeyContext,
    private readonly source: BrowserLocalAuthorityRuntime, private readonly stages: BrowserLocalStagesRuntime) {}

  private async guard(scope: BrowserSyncScope): Promise<{ lease: AuthoritativeKeyContextLease; current: () => boolean }> {
    const { context } = await this.bindings.ensureForCurrentUser(scope.accountId)
    const lease = this.keys.leaseForAccount(scope.accountId)
    const current = () => this.auth.isCurrent(context) && !!lease?.isCurrent()
    if (!lease || context.userId !== scope.canonicalUserId || lease.localAccountId !== scope.accountId
      || lease.canonicalUserId !== context.userId || lease.authEpoch !== context.authEpoch || !current()) fail('closed')
    return { lease: lease!, current }
  }

  private async owner(scope: BrowserSyncScope, projectId: string, stageId: string | null): Promise<{ token: LocalSourceToken; stage: LocalStage | null }> {
    const snapshot = await this.source.readSnapshot(scope, projectId)
    const project = await this.source.withDecryptedSnapshot(scope, snapshot.token, async value => value.project)
    if (project.status === 'завершен') fail('unsupported_local_source')
    const stage = stageId === null ? null : (await this.stages.list(scope, projectId)).find(item => item.id === stageId)
    if (stageId !== null && !stage) fail('missing_local_source')
    if (stage?.status === 'завершен') fail('unsupported_local_source')
    return { token: snapshot.token, stage: stage ?? null }
  }

  private readRow(scope: BrowserSyncScope, projectId: string, stageId: string | null): Promise<DocumentRow | null> {
    return this.transaction(scope, ['localDocuments'], 'readonly', (tx, result, abort) => {
      const request = tx.objectStore('localDocuments').get(rowKey(scope, projectId, stageId))
      request.onsuccess = () => { try { result(request.result ? validateRow(request.result, scope, projectId, stageId) : null) } catch (error) { abort(error) } }
    })
  }

  private async openRow(scope: BrowserSyncScope, row: DocumentRow, stageId: string | null, amk: AccountMasterKey): Promise<LocalDocument> {
    let nonce: Uint8Array | undefined, ciphertext: Uint8Array | undefined, bytes: Uint8Array | undefined
    try {
      nonce = decodeBase64Url(row.envelope.nonce)
      ciphertext = decodeBase64Url(row.envelope.ciphertext)
      bytes = await decryptObjectBytes(amk, { userId: scope.canonicalUserId, projectId: row.project_id,
        entityId: `${row.scope_key}/${row.document_id}`, entityType: 'document' },
      { crypto_version: 1, aad_version: 1, nonce, ciphertext })
      if (bytes.length > MAX_DOCUMENT_BYTES) fail('corrupt_record')
      const raw = new TextDecoder('utf-8', { fatal: true }).decode(bytes)
      const value: unknown = JSON.parse(raw)
      if (canonical(value) !== raw || !localExact(value, ['local_format', 'kind', 'account_id', 'device_id', 'project_id', 'scope_key', 'document_id', 'revision', 'document'])) fail('corrupt_record')
      const payload = value as unknown as DocumentPayload
      if (payload.local_format !== 1 || payload.kind !== 'document' || payload.account_id !== scope.accountId
        || payload.device_id !== scope.deviceId || payload.project_id !== row.project_id || payload.scope_key !== row.scope_key
        || payload.document_id !== row.document_id || payload.revision !== row.revision) fail('corrupt_record')
      validatePortableDocument(payload.document)
      const createdAt = payload.document.created_at
      if (payload.document.id !== row.document_id || payload.document.project_id !== row.project_id || payload.document.stage_id !== stageId
        || typeof createdAt !== 'string' || !timestamp(createdAt)) fail('corrupt_record')
      return { id: row.document_id, project_id: row.project_id, stage_id: stageId, title: payload.document.title,
        content: structuredClone(payload.document.content_json) as TiptapDocument, revision: row.revision, created_at: createdAt as string }
    } catch { return fail('corrupt_record') }
    finally { bytes?.fill(0); nonce?.fill(0); ciphertext?.fill(0) }
  }

  private async seal(scope: BrowserSyncScope, document: LocalDocument, amk: AccountMasterKey): Promise<DocumentRow> {
    const scopeKey = keyFor(document.stage_id)
    const portable: PortableDocument = { id: document.id, project_id: document.project_id, stage_id: document.stage_id,
      title: document.title, content_json: document.content, content_format: 'tiptap-json/v1', created_at: document.created_at, extensions: {} }
    validatePortableDocument(portable)
    const payload: DocumentPayload = { local_format: 1, kind: 'document', account_id: scope.accountId, device_id: scope.deviceId,
      project_id: document.project_id, scope_key: scopeKey, document_id: document.id, revision: document.revision, document: portable }
    const bytes = localCanonicalBytes(payload)
    if (bytes.length > MAX_DOCUMENT_BYTES) { bytes.fill(0); fail('source_limit') }
    let nonce: Uint8Array | undefined, ciphertext: Uint8Array | undefined
    try {
      const encrypted = await encryptObjectBytes(amk, { userId: scope.canonicalUserId, projectId: document.project_id,
        entityId: `${scopeKey}/${document.id}`, entityType: 'document' }, bytes)
      nonce = encrypted.nonce; ciphertext = encrypted.ciphertext
      return { record_version: 1, account_id: scope.accountId, device_id: scope.deviceId, project_id: document.project_id,
        scope_key: scopeKey, document_id: document.id, revision: document.revision,
        envelope: { crypto_version: 1, aad_version: 1, nonce: encodeBase64Url(nonce), ciphertext: encodeBase64Url(ciphertext) } }
    } finally { bytes.fill(0); nonce?.fill(0); ciphertext?.fill(0) }
  }

  /** The owner, binding, stage and revision are all checked in the committing transaction. */
  private write(scope: BrowserSyncScope, projectId: string, stageId: string | null, token: LocalSourceToken,
    stage: LocalStage | null, previous: DocumentRow | null, next: DocumentRow, current: () => boolean): Promise<void> {
    if (!current()) fail('closed')
    return this.transaction<void>(scope, ['localProjects', 'localNotes', 'localStages', 'localDocuments', 'projectBindings'], 'readwrite', (tx, result, abort) => {
      assertLocalSourceInTransaction(tx, scope, token, () => {
        const document = tx.objectStore('localDocuments').get(rowKey(scope, projectId, stageId))
        const binding = tx.objectStore('projectBindings').get([scope.accountId, projectId])
        const stageRow = stageId === null ? null : tx.objectStore('localStages').get([scope.accountId, projectId, stageId])
        let received = 0
        const total = stageRow ? 3 : 2
        const finish = () => { if (++received !== total) return; try {
          if (!current()) fail('closed')
          if (binding.result) fail('unsupported_local_source')
          if (stageRow && (!stageRow.result || stageRow.result.revision !== stage?.revision)) fail('stale_source')
          const stored = document.result ? validateRow(document.result, scope, projectId, stageId) : null
          if (previous ? !stored || stored.document_id !== previous.document_id || stored.revision !== previous.revision
            || canonical(stored) !== canonical(previous) : !!stored) fail('stale_source')
          const request = tx.objectStore('localDocuments')[previous ? 'put' : 'add'](next)
          request.onsuccess = () => { if (!current()) abort(new BrowserPersistenceError('closed')) }
          result(undefined)
        } catch (error) { abort(error) } }
        document.onsuccess = finish; binding.onsuccess = finish
        if (stageRow) stageRow.onsuccess = finish
      }, abort)
    })
  }

  async read(scope: BrowserSyncScope, projectId: string, stageId: string | null): Promise<LocalDocument | null> {
    scope = snapshotBrowserSyncScope(scope); localId(projectId); if (stageId !== null) localId(stageId)
    const owner = await this.owner(scope, projectId, stageId), guard = await this.guard(scope)
    const row = await this.readRow(scope, projectId, stageId)
    const document = row ? await guard.lease.use(amk => this.openRow(scope, row, stageId, amk)) : null
    await this.source.assertSnapshot(scope, owner.token)
    if (!guard.current()) fail('closed')
    return document
  }

  async open(scope: BrowserSyncScope, projectId: string, stageId: string | null): Promise<LocalDocument> {
    scope = snapshotBrowserSyncScope(scope); localId(projectId); if (stageId !== null) localId(stageId)
    const existing = await this.read(scope, projectId, stageId)
    if (existing) return existing
    const owner = await this.owner(scope, projectId, stageId), guard = await this.guard(scope)
    const document: LocalDocument = { id: crypto.randomUUID(), project_id: projectId, stage_id: stageId,
      title: stageId === null ? 'Текст проекта' : 'Текст этапа', content: structuredClone(emptyContent), revision: 1, created_at: now() }
    const row = await guard.lease.use(amk => this.seal(scope, document, amk))
    await this.write(scope, projectId, stageId, owner.token, owner.stage, null, row, guard.current)
    return document
  }

  async save(scope: BrowserSyncScope, projectId: string, stageId: string | null, expectedRevision: number,
    content: TiptapDocument): Promise<LocalDocument> {
    scope = snapshotBrowserSyncScope(scope); localId(projectId); if (stageId !== null) localId(stageId)
    if (!localSafe(expectedRevision, 1) || expectedRevision === Number.MAX_SAFE_INTEGER) fail('stale_source')
    const validated = validateContent(content)
    const owner = await this.owner(scope, projectId, stageId), guard = await this.guard(scope)
    const row = await this.readRow(scope, projectId, stageId)
    if (!row) throw new BrowserPersistenceError('missing_local_source')
    if (row.revision !== expectedRevision) fail('stale_source')
    const prior = await guard.lease.use(amk => this.openRow(scope, row, stageId, amk))
    const next = { ...prior, content: validated, revision: expectedRevision + 1 }
    const sealed = await guard.lease.use(amk => this.seal(scope, next, amk))
    await this.write(scope, projectId, stageId, owner.token, owner.stage, row, sealed, guard.current)
    return next
  }
}
