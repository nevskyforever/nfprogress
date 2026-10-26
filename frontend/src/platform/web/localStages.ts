import { decodeBase64Url, encodeBase64Url } from '@/api/base64url'
import type { AuthoritativeAccountBinding } from '@/auth/accountBinding'
import type { AuthoritativeKeyContextLease, RuntimeKeyContext } from '@/auth/keyContext'
import type { NormalUserAuthRuntime } from '@/auth/userAuth'
import { decryptObjectBytes, encryptObjectBytes, type AccountMasterKey } from '@/crypto'
import { canonical, timestamp } from '@/cloud/projectMetadataCodec'
import { canonicalizeSyncTimestamp } from '@/cloud/syncTimestamp'
import { MAX_STAGE_BYTES, STAGE_FIELDS, type StagePortable } from '@/cloud/stageCodec'
import { BrowserPersistenceError } from './persistence'
import { assertLocalSourceInTransaction, type BrowserLocalAuthorityRuntime, type LocalSourceToken } from './localAuthority'
import { localCanonicalBytes, localExact, localId, localSafe, validateLocalEnvelope, type LocalEnvelope } from './localAuthorityRecords'
import { snapshotBrowserSyncScope, type BrowserSyncScope, type BrowserSyncTransaction } from './syncDurability'

export interface LocalStage extends StagePortable {
  id: string
  project_id: string
  sort_order: number
  updated_at: string
  revision: number
}

interface StageRow {
  record_version: 1
  account_id: string
  device_id: string
  project_id: string
  stage_id: string
  revision: number
  envelope: LocalEnvelope
}

interface StagePayload {
  local_format: 1
  kind: 'stage'
  account_id: string
  device_id: string
  project_id: string
  stage_id: string
  revision: number
  sort_order: number
  updated_at: string
  stage: StagePortable
}

const fail = (code: 'invalid_local_source' | 'corrupt_record' | 'closed' | 'stale_source' | 'conflicting_record' | 'missing_local_source' | 'unsupported_local_source' | 'source_limit'): never => { throw new BrowserPersistenceError(code) }
const same = (left: unknown, right: unknown) => canonical(left) === canonical(right)
const range = (scope: BrowserSyncScope, projectId: string) => IDBKeyRange.bound([scope.accountId, projectId], [scope.accountId, projectId, []])
const order = (left: LocalStage, right: LocalStage) => left.sort_order - right.sort_order || left.id.localeCompare(right.id)
const now = () => canonicalizeSyncTimestamp(new Date().toISOString())

function validatePortable(value: unknown): StagePortable {
  if (!localExact(value, [...STAGE_FIELDS])) fail('corrupt_record')
  const stage = value as unknown as StagePortable
  if (typeof stage.name !== 'string' || !stage.name.trim() || new TextEncoder().encode(stage.name).length > 512 || stage.unit !== 'symbols' && stage.unit !== 'A4' && stage.unit !== 'author_list' && stage.unit !== 'ficbook_pages'
    || !['активен', 'в архиве', 'завершен'].includes(stage.status) || !['manual', 'sync', 'app'].includes(stage.work_method)
    || typeof stage.infinite !== 'boolean' || !(stage.goal === null || Number.isFinite(stage.goal) && stage.goal >= 0)
    || !localSafe(stage.personal_goal) || typeof stage.auto_freeze !== 'boolean' || typeof stage.streak_enabled !== 'boolean'
    || !(stage.deadline === null || typeof stage.deadline === 'string' && stage.deadline.length <= 32)
    || !(stage.created_at === null || timestamp(stage.created_at)) || !(stage.completed_at === null || timestamp(stage.completed_at))) fail('corrupt_record')
  return structuredClone(stage)
}

function validateRow(value: unknown, scope: BrowserSyncScope, projectId: string): StageRow {
  if (!localExact(value, ['record_version', 'account_id', 'device_id', 'project_id', 'stage_id', 'revision', 'envelope'])) fail('corrupt_record')
  const row = value as unknown as StageRow
  localId(row.stage_id)
  if (row.record_version !== 1 || row.account_id !== scope.accountId || row.device_id !== scope.deviceId || row.project_id !== projectId || !localSafe(row.revision, 1)) fail('corrupt_record')
  const envelope = validateLocalEnvelope(row.envelope)
  const ciphertext = decodeBase64Url(envelope.ciphertext)
  try { if (ciphertext.length > MAX_STAGE_BYTES + 16) fail('source_limit') } finally { ciphertext.fill(0) }
  return { ...row, envelope }
}

/** Local-only Stage authority. C21 imported Stage proofs and event heads are untouched. */
export class BrowserLocalStages {
  constructor(private readonly transaction: BrowserSyncTransaction) {}

  bind(auth: NormalUserAuthRuntime, bindings: AuthoritativeAccountBinding, keys: RuntimeKeyContext, source: BrowserLocalAuthorityRuntime): BrowserLocalStagesRuntime {
    return new BrowserLocalStagesRuntime(this.transaction, auth, bindings, keys, source)
  }
}

export class BrowserLocalStagesRuntime {
  constructor(private readonly transaction: BrowserSyncTransaction, private readonly auth: NormalUserAuthRuntime, private readonly bindings: AuthoritativeAccountBinding, private readonly keys: RuntimeKeyContext, private readonly source: BrowserLocalAuthorityRuntime) {}

  private async guard(scope: BrowserSyncScope): Promise<{ lease: AuthoritativeKeyContextLease; current: () => boolean }> {
    const { context } = await this.bindings.ensureForCurrentUser(scope.accountId)
    const lease = this.keys.leaseForAccount(scope.accountId)
    const current = () => this.auth.isCurrent(context) && !!lease?.isCurrent()
    if (!lease || context.userId !== scope.canonicalUserId || lease.localAccountId !== scope.accountId || lease.canonicalUserId !== context.userId || lease.authEpoch !== context.authEpoch || !current()) return fail('closed')
    return { lease, current }
  }

  private readRows(scope: BrowserSyncScope, projectId: string): Promise<StageRow[]> {
    return this.transaction(scope, ['localStages'], 'readonly', (tx, result, abort) => {
      const request = tx.objectStore('localStages').getAll(range(scope, projectId))
      request.onsuccess = () => { try { result(request.result.map(row => validateRow(row, scope, projectId))) } catch (error) { abort(error) } }
    })
  }

  private async open(scope: BrowserSyncScope, row: StageRow, amk: AccountMasterKey): Promise<LocalStage> {
    let nonce: Uint8Array | undefined, ciphertext: Uint8Array | undefined, bytes: Uint8Array | undefined
    try {
      nonce = decodeBase64Url(row.envelope.nonce)
      ciphertext = decodeBase64Url(row.envelope.ciphertext)
      bytes = await decryptObjectBytes(amk, { userId: scope.canonicalUserId, projectId: row.project_id, entityId: row.stage_id, entityType: 'stage' }, { crypto_version: 1, aad_version: 1, nonce, ciphertext })
      if (bytes.length > MAX_STAGE_BYTES) fail('corrupt_record')
      const raw = new TextDecoder('utf-8', { fatal: true }).decode(bytes)
      const value: unknown = JSON.parse(raw)
      if (canonical(value) !== raw || !localExact(value, ['local_format', 'kind', 'account_id', 'device_id', 'project_id', 'stage_id', 'revision', 'sort_order', 'updated_at', 'stage'])) fail('corrupt_record')
      const payload = value as unknown as StagePayload
      if (payload.local_format !== 1 || payload.kind !== 'stage' || payload.account_id !== scope.accountId || payload.device_id !== scope.deviceId || payload.project_id !== row.project_id || payload.stage_id !== row.stage_id || payload.revision !== row.revision || !localSafe(payload.sort_order) || !timestamp(payload.updated_at)) fail('corrupt_record')
      return { ...validatePortable(payload.stage), id: row.stage_id, project_id: row.project_id, sort_order: payload.sort_order, updated_at: payload.updated_at, revision: row.revision }
    } catch { return fail('corrupt_record') }
    finally { bytes?.fill(0); nonce?.fill(0); ciphertext?.fill(0) }
  }

  private async seal(scope: BrowserSyncScope, stage: LocalStage, amk: AccountMasterKey): Promise<StageRow> {
    const { id, project_id, sort_order, updated_at, revision, ...portable } = stage
    const payload: StagePayload = { local_format: 1, kind: 'stage', account_id: scope.accountId, device_id: scope.deviceId, project_id, stage_id: id, revision, sort_order, updated_at, stage: validatePortable(portable) }
    const bytes = localCanonicalBytes(payload)
    if (bytes.length > MAX_STAGE_BYTES) { bytes.fill(0); fail('source_limit') }
    let nonce: Uint8Array | undefined, ciphertext: Uint8Array | undefined
    try {
      const result = await encryptObjectBytes(amk, { userId: scope.canonicalUserId, projectId: project_id, entityId: id, entityType: 'stage' }, bytes)
      nonce = result.nonce; ciphertext = result.ciphertext
      return { record_version: 1, account_id: scope.accountId, device_id: scope.deviceId, project_id, stage_id: id, revision, envelope: { crypto_version: 1, aad_version: 1, nonce: encodeBase64Url(nonce), ciphertext: encodeBase64Url(ciphertext) } }
    } finally { bytes.fill(0); nonce?.fill(0); ciphertext?.fill(0) }
  }

  private async snapshot(scope: BrowserSyncScope, projectId: string, editable = false): Promise<LocalSourceToken> {
    const source = await this.source.readSnapshot(scope, projectId)
    const project = await this.source.withDecryptedSnapshot(scope, source.token, async value => value.project)
    if (editable && project.status === 'завершен') fail('unsupported_local_source')
    return source.token
  }

  async list(scope: BrowserSyncScope, projectId: string): Promise<LocalStage[]> {
    scope = snapshotBrowserSyncScope(scope); localId(projectId)
    const token = await this.snapshot(scope, projectId), guard = await this.guard(scope)
    const rows = await this.readRows(scope, projectId)
    if (rows.length > 4096) fail('source_limit')
    const stages = await guard.lease.use(amk => Promise.all(rows.map(row => this.open(scope, row, amk))))
    const project = await this.source.withDecryptedSnapshot(scope, token, async value => value.project)
    await this.source.assertSnapshot(scope, token)
    if (!guard.current()) fail('closed')
    const positions = stages.map(stage => stage.sort_order)
    if (new Set(positions).size !== positions.length || stages.some(stage => stage.unit !== project.unit)) fail('corrupt_record')
    return stages.sort(order)
  }

  /** Compare the whole stage inventory and project source before every write. */
  private async write(scope: BrowserSyncScope, projectId: string, expected: StageRow[], next: StageRow[], removed: string[], token: LocalSourceToken, current: () => boolean): Promise<void> {
    if (!current()) fail('closed')
    await this.transaction<void>(scope, ['localProjects', 'localNotes', 'localStages', 'projectBindings'], 'readwrite', (tx, result, abort) => {
      assertLocalSourceInTransaction(tx, scope, token, () => {
        const request = tx.objectStore('localStages').getAll(range(scope, projectId))
        const binding = tx.objectStore('projectBindings').get([scope.accountId, projectId])
        let received = 0
        const finish = () => { if (++received !== 2) return; try {
          if (!current()) fail('closed')
          if (binding.result) fail('unsupported_local_source')
          const rows = request.result.map(value => validateRow(value, scope, projectId))
          if (!same(rows, expected)) fail('stale_source')
          const store = tx.objectStore('localStages')
          for (const id of removed) store.delete([scope.accountId, projectId, id])
          for (const row of next) store.put(row)
          if (!current()) fail('closed')
          result(undefined)
        } catch (error) { abort(error) } }
        request.onsuccess = finish; binding.onsuccess = finish
      }, abort)
    })
  }

  async create(scope: BrowserSyncScope, projectId: string, name: string, unit: string): Promise<LocalStage> {
    scope = snapshotBrowserSyncScope(scope); localId(projectId)
    if (!name.trim() || new TextEncoder().encode(name).length > 512) fail('invalid_local_source')
    const token = await this.snapshot(scope, projectId, true), guard = await this.guard(scope)
    const existing = await this.list(scope, projectId)
    const project = await this.source.withDecryptedSnapshot(scope, token, async value => value.project)
    if (project.unit !== unit) fail('invalid_local_source')
    if (existing.length >= 4096) fail('source_limit')
    if (existing.some(stage => stage.name === name.trim())) fail('conflicting_record')
    const expected = await this.readRows(scope, projectId)
    const position = existing.length ? Math.max(...existing.map(item => item.sort_order)) + 1 : 0
    if (!localSafe(position)) fail('source_limit')
    const at = now(), stage: LocalStage = { id: crypto.randomUUID(), project_id: projectId, name: name.trim(), goal: null, infinite: true, unit, status: 'активен', deadline: null, personal_goal: 0, auto_freeze: true, streak_enabled: false, work_method: 'manual', created_at: at, completed_at: null, sort_order: position, updated_at: at, revision: 1 }
    const row = await guard.lease.use(amk => this.seal(scope, stage, amk))
    await this.write(scope, projectId, expected, [row], [], token, guard.current)
    return stage
  }

  async rename(scope: BrowserSyncScope, projectId: string, stageId: string, name: string, expectedRevision: number): Promise<LocalStage> {
    scope = snapshotBrowserSyncScope(scope); localId(stageId)
    if (!name.trim() || new TextEncoder().encode(name).length > 512) fail('invalid_local_source')
    const token = await this.snapshot(scope, projectId, true), guard = await this.guard(scope)
    const stages = await this.list(scope, projectId), old = stages.find(stage => stage.id === stageId)
    if (!old) return fail('missing_local_source')
    if (old.revision !== expectedRevision) fail('stale_source')
    if (stages.some(stage => stage.id !== stageId && stage.name === name.trim())) fail('conflicting_record')
    if (old.revision === Number.MAX_SAFE_INTEGER) fail('source_limit')
    const next = { ...old, name: name.trim(), updated_at: now(), revision: old.revision + 1 }
    const expected = await this.readRows(scope, projectId), row = await guard.lease.use(amk => this.seal(scope, next, amk))
    await this.write(scope, projectId, expected, [row], [], token, guard.current)
    return next
  }

  async remove(scope: BrowserSyncScope, projectId: string, stageId: string, expectedRevision: number): Promise<void> {
    scope = snapshotBrowserSyncScope(scope); localId(stageId)
    const token = await this.snapshot(scope, projectId, true), guard = await this.guard(scope)
    const stages = await this.list(scope, projectId)
    const target = stages.find(stage => stage.id === stageId)
    if (!target) return fail('missing_local_source')
    if (target.revision !== expectedRevision) fail('stale_source')
    const source = await this.source.withDecryptedSnapshot(scope, token, async value => value)
    if (source.notes.some(note => note.note.stage_id === stageId)) fail('unsupported_local_source')
    const expected = await this.readRows(scope, projectId)
    await this.write(scope, projectId, expected, [], [stageId], token, guard.current)
  }

  async reorder(scope: BrowserSyncScope, projectId: string, ids: string[], expectedRevisions: Record<string, number>): Promise<void> {
    scope = snapshotBrowserSyncScope(scope)
    if (!Array.isArray(ids) || new Set(ids).size !== ids.length) fail('invalid_local_source')
    const token = await this.snapshot(scope, projectId, true), guard = await this.guard(scope)
    const stages = await this.list(scope, projectId)
    if (ids.length !== stages.length || ids.some(id => !stages.some(stage => stage.id === id))) fail('invalid_local_source')
    if (!localExact(expectedRevisions, ids) || stages.some(stage => expectedRevisions[stage.id] !== stage.revision)) fail('stale_source')
    const expected = await this.readRows(scope, projectId)
    const next = await guard.lease.use(amk => Promise.all(ids.map((id, index) => {
      const old = stages.find(stage => stage.id === id)!
      if (old.revision === Number.MAX_SAFE_INTEGER) fail('source_limit')
      return this.seal(scope, { ...old, sort_order: index, revision: old.revision + 1, updated_at: now() }, amk)
    })))
    await this.write(scope, projectId, expected, next, [], token, guard.current)
  }
}
