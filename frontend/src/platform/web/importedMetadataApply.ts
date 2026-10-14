import type { AuthoritativeAccountBinding } from '@/auth/accountBinding'
import type { RuntimeKeyContext } from '@/auth/keyContext'
import type { NormalUserAuthRuntime } from '@/auth/userAuth'
import type { V3Descriptor } from '@/api/encryptedSyncV3'
import { decodeBase64Url } from '@/api/base64url'
import { openProjectMetadataEvent, type ProjectMetadataEvent } from '@/cloud/projectMetadataCodec'
import { BrowserPersistenceError, type BrowserPersistenceCode } from './persistence'
import { validateBrowserProjectBinding, type BrowserProjectBinding } from './projectBindings'
import { validateBrowserSyncCursor, immutableWireIdentity, snapshotBrowserSyncScope, validateBrowserRetainedHistory, validateBrowserUploadPair, type BrowserSyncScope, type BrowserSyncTransaction, type BrowserSyncDurability, type BrowserRetainedEncryptedHistory } from './syncDurability'
import { validateBrowserMetadataHead, type BrowserMetadataHead, type BrowserMetadataProof } from './metadataApplyRecords'

/** Tokens have no public data/constructor; only the authenticated reader can mint one. */
export interface VerifiedImportedMetadataPlan { readonly verifiedImportedMetadata: unique symbol }
interface Plan {
  owner: BrowserImportedMetadataApply; scope: BrowserSyncScope; binding: BrowserProjectBinding; expected: BrowserMetadataHead | null; proof: BrowserMetadataProof
  retained: BrowserRetainedEncryptedHistory[]; current: () => boolean; auth: NormalUserAuthRuntime
}
const plans = new WeakMap<object, Plan>()
const same = (a: unknown, b: unknown) => immutableWireIdentity(a) === immutableWireIdentity(b)
function fail(code: BrowserPersistenceCode): never { throw new BrowserPersistenceError(code) }
export function metadataProofFor(scope: BrowserSyncScope, reference: V3Descriptor, event: ProjectMetadataEvent, wireDigest: string, protocol: 2 | 3): BrowserMetadataProof {
  const h = event.header
  if (reference.entity_type !== 'project_metadata' || reference.project_id !== h.project_id || reference.entity_id !== h.entity_id
    || reference.event_id !== h.event_id || reference.device_id !== h.device_id || reference.revision !== h.revision
    || reference.updated_at !== h.updated_at || reference.deleted_at !== event.deleted_at
    || reference.operation !== (h.operation === 'delete' ? 'delete' : 'upsert') || h.account_id !== scope.canonicalUserId) fail('conflicting_record')
  // Native explicit null has no material dependency. A non-null reference cannot be applied here.
  if (event.metadata?.cover_reference != null) fail('cover_material_unavailable')
  return { record_version: 1, protocol_version: protocol, metadata_codec_version: event.version, owner_kind: 'project_metadata', account_id: scope.accountId, project_id: h.project_id,
    bootstrap_id: h.bootstrap_id, event_id: h.event_id, source_device_id: h.device_id, server_sequence: reference.server_sequence,
    operation: h.operation, revision: h.revision, generation: h.generation, parent_event_ids: [...h.parent_event_ids], wire_digest: wireDigest, reference: { ...reference } }
}
function transition(scope: BrowserSyncScope, head: BrowserMetadataHead | null, proof: BrowserMetadataProof): BrowserMetadataHead {
  if (head && (head.owner_id !== proof.project_id || head.bootstrap_id !== proof.bootstrap_id)) fail('conflicting_record')
  if (!head) {
    if (proof.operation !== 'create' || proof.revision !== 1 || proof.generation !== 1 || proof.parent_event_ids.length) fail('missing_history')
  } else {
    if (proof.operation === 'create') fail('metadata_conflict')
    const parents = proof.parent_event_ids.map(id => head.history.find(p => p.event_id === id) ?? fail('missing_history'))
    if (proof.revision !== Math.max(...parents.map(p => p.revision)) + 1 || proof.generation <= Math.max(...parents.map(p => p.generation))) fail('metadata_rejected')
    if (!same(head.tip_event_ids, proof.parent_event_ids)) fail('metadata_conflict')
    if (proof.operation === 'genesis_resolution' && parents.some(p => p.operation !== 'create' || p.revision !== 1 || p.parent_event_ids.length)) fail('metadata_rejected')
  }
  return validateBrowserMetadataHead({ record_version: 1, account_id: scope.accountId, device_id: scope.deviceId,
    owner_kind: 'project_metadata', owner_id: proof.project_id, bootstrap_id: proof.bootstrap_id, tip_event_ids: [proof.event_id],
    history: [...(head?.history ?? []), proof].sort((a, b) => a.event_id.localeCompare(b.event_id)) }, scope)
}

/** Dormant imported Metadata only. Crypto outside IDB; one strict commit for authority+proof+state. */
export class BrowserImportedMetadataApply {
  constructor(private readonly transaction: BrowserSyncTransaction, private readonly history: BrowserSyncDurability) {}
  readHead(scope: BrowserSyncScope, projectId: string): Promise<BrowserMetadataHead | null> {
    scope = snapshotBrowserSyncScope(scope)
    return this.transaction(scope, ['ownerHeads'], 'readonly', (tx, result, abort) => {
      const read = tx.objectStore('ownerHeads').get([scope.accountId, 'project_metadata', projectId])
      read.onsuccess = () => { try { result(read.result === undefined ? null : validateBrowserMetadataHead(read.result, scope)) } catch (error) { abort(error) } }
    })
  }
  async prepareVerified(scope: BrowserSyncScope, reference: V3Descriptor, auth: NormalUserAuthRuntime, bindings: AuthoritativeAccountBinding, keys: RuntimeKeyContext): Promise<VerifiedImportedMetadataPlan> {
    scope = snapshotBrowserSyncScope(scope); reference = structuredClone(reference)
    const binding = await bindings.ensureForCurrentUser(scope.accountId), context = binding.context
    const lease = keys.leaseForAccount(scope.accountId)
    const current = () => auth.isCurrent(context) && !!lease?.isCurrent()
    if (context.userId !== scope.canonicalUserId || !lease || lease.localAccountId !== scope.accountId || lease.canonicalUserId !== context.userId || lease.authEpoch !== context.authEpoch || !current()) fail('account_mismatch')
    const lineage = await this.transaction<BrowserProjectBinding>(scope, ['projectBindings'], 'readonly', (tx, result, abort) => {
      const read = tx.objectStore('projectBindings').get([scope.accountId, reference.project_id])
      read.onsuccess = () => { try {
        if (!read.result) fail('missing_history')
        result(validateBrowserProjectBinding(read.result, scope))
      } catch (error) { abort(error) } }
    })
    if (lineage.mode !== 'import_remote' || lineage.phase !== 'captured' || lineage.remote_state !== 'active') fail('ineligible_lineage')
    const expected = await this.readHead(scope, reference.project_id)
    const references = [...(expected?.history.map(p => p.reference).filter(d => d.event_id !== reference.event_id) ?? []), reference]
    const retained = await this.history.readRetainedHistory(scope, references)
    if (retained.length !== references.length || new Set(retained.map(entry => entry.reference.event_id)).size !== retained.length || retained.some(entry => !references.some(ref => same(ref, entry.reference)))) fail('missing_history')
    return lease.use(async amk => {
      let proof: BrowserMetadataProof | undefined
      for (const entry of retained) {
        const raw = entry.inbox ? JSON.parse(entry.inbox.wire_item) : JSON.parse(entry.outbox!.raw_body).items[0]
        let nonce: Uint8Array | undefined, ciphertext: Uint8Array | undefined
        let identity: Uint8Array<ArrayBuffer> | undefined, digest: Uint8Array | undefined
        try {
          nonce = decodeBase64Url(raw.object.nonce); ciphertext = decodeBase64Url(raw.object.ciphertext)
          const event = await openProjectMetadataEvent(amk, { account_id: scope.canonicalUserId, project_id: reference.project_id,
            entity_id: reference.project_id, event_id: entry.reference.event_id }, { crypto_version: raw.object.crypto_version, aad_version: raw.object.aad_version, nonce, ciphertext })
          const protocol = (entry.inbox ?? entry.outbox!).protocol_version
          identity = new TextEncoder().encode(immutableWireIdentity({ protocol_version: protocol, event: entry.reference, object: raw.object }))
          digest = new Uint8Array(await crypto.subtle.digest('SHA-256', identity))
          const wireDigest = Array.from(digest, byte => byte.toString(16).padStart(2, '0')).join('')
          const verified = metadataProofFor(scope, entry.reference as V3Descriptor, event, wireDigest, protocol)
          if (verified.bootstrap_id !== lineage.bootstrap_id) fail('conflicting_record')
          if (entry.reference.event_id === reference.event_id) proof = verified
          else if (!same(expected!.history.find(p => p.event_id === verified.event_id), verified)) fail('corrupt_record')
        } catch (error) { if (error instanceof BrowserPersistenceError) throw error; fail('metadata_rejected') }
        finally { nonce?.fill(0); ciphertext?.fill(0); identity?.fill(0); digest?.fill(0) }
      }
      if (!current()) fail('closed')
      if (!proof) fail('missing_history')
      const token = Object.freeze({}) as VerifiedImportedMetadataPlan
      plans.set(token, { owner: this, scope, binding: lineage, expected, proof, retained: structuredClone(retained), current, auth })
      return token
    })
  }
  commitVerifiedImportedMetadataApply(scope: BrowserSyncScope, token: VerifiedImportedMetadataPlan): Promise<'applied' | 'already_applied'> {
    scope = snapshotBrowserSyncScope(scope)
    const plan = token && plans.get(token)
    if (!plan || plan.owner !== this || !same(plan.scope, scope)) fail('metadata_rejected')
    if (!plan.current()) fail('closed')
    let unsubscribe: (() => void) | undefined
    return this.transaction<'applied' | 'already_applied'>(scope, ['projectBindings','ownerHeads','inbox','outbox','receipts','cursors'], 'readwrite', (tx, result, abort) => {
      unsubscribe = plan.auth.onInvalidated(() => abort(new BrowserPersistenceError('closed')))
      const lineage = tx.objectStore('projectBindings').get([scope.accountId, plan.proof.project_id])
      const head = tx.objectStore('ownerHeads').get([scope.accountId, 'project_metadata', plan.proof.project_id])
      // Pending local metadata is incompatible, not proof of a native candidate/decision.
      const local = tx.objectStore('outbox').getAll(IDBKeyRange.bound([scope.accountId], [scope.accountId, []]))
      const localReceipts = tx.objectStore('receipts').getAll(IDBKeyRange.bound([scope.accountId], [scope.accountId, []]))
      const cursor = tx.objectStore('cursors').get([scope.accountId, scope.deviceId])
      const reads = plan.retained.map(entry => ({ entry,
        out: tx.objectStore('outbox').get([scope.accountId, entry.reference.event_id]),
        receipt: tx.objectStore('receipts').get([scope.accountId, entry.reference.event_id]),
        inbox: tx.objectStore('inbox').index('event').get([scope.accountId, entry.reference.event_id]) }))
      const requests = [lineage, head, local, localReceipts, cursor, ...reads.flatMap(r => [r.out, r.receipt, r.inbox])]
      let ready = 0
      const finish = () => {
        if (++ready !== requests.length) return
        try {
          if (!plan.current()) fail('closed')
          if (!lineage.result) fail('missing_history')
          const binding = validateBrowserProjectBinding(lineage.result, scope)
          if (binding.mode !== 'import_remote' || binding.phase !== 'captured' || binding.remote_state !== 'active') fail('ineligible_lineage')
          if (binding.project_id !== plan.proof.project_id || binding.bootstrap_id !== plan.proof.bootstrap_id) fail('conflicting_record')
          const state = validateBrowserSyncCursor(cursor.result, scope)
          if (state.pull_cursor < plan.proof.server_sequence) fail('corrupt_record')
          const actual = head.result === undefined ? null : validateBrowserMetadataHead(head.result, scope)
          let incoming: ReturnType<typeof validateBrowserRetainedHistory> | undefined
          for (const read of reads) {
            const retained = validateBrowserRetainedHistory(scope, read.entry.reference, read.out.result, read.receipt.result, read.inbox.result)
            const before = read.entry.inbox, after = retained.inbox
            const changedToApplied = before?.state === 'received' && after?.state === 'applied'
              && same({ ...after, record_version: 1, state: 'received', applied_proof: undefined }, { ...before, applied_proof: undefined })
              && same(after.applied_proof, plan.proof)
            if (!same(retained, read.entry) && !(changedToApplied && same(retained.outbox, read.entry.outbox) && same(retained.receipt, read.entry.receipt))) fail('conflicting_record')
            if (read.entry.reference.event_id === plan.proof.event_id) incoming = retained
          }
          const row = incoming?.inbox
          if (!row) fail('missing_history') // Upload receipt alone is never apply authority.
          if (row.state === 'applied') {
            if (!same(row.applied_proof, plan.proof) || !actual || !same(actual.history.find(p => p.event_id === plan.proof.event_id), plan.proof)) fail('conflicting_record')
            result('already_applied'); return // Old replay cannot roll back a descendant.
          }
          if (!same(binding, plan.binding)) fail('stale_lineage')
          if (!same(actual, plan.expected)) fail('stale_authority')
          if (plan.proof.source_device_id === scope.deviceId) fail('self_echo_unavailable')
          const outgoing = local.result.map(row => validateBrowserUploadPair(row, localReceipts.result.find(proof => proof.event_id === row.event_id), scope))
          if (localReceipts.result.some(proof => !outgoing.some(row => row.event_id === proof.event_id))) fail('corrupt_record')
          if (outgoing.some(row => JSON.parse(row.raw_body).items.some((item: { event: V3Descriptor }) => item.event.entity_type === 'project_metadata' && item.event.project_id === plan.proof.project_id))) fail('local_incompatible')
          const next = transition(scope, actual, plan.proof)
          const writes = [tx.objectStore('ownerHeads').put(next), tx.objectStore('inbox').put({ ...row, record_version: 2, state: 'applied', applied_proof: plan.proof })]
          writes.forEach(write => { write.onsuccess = () => { if (!plan.current()) abort(new BrowserPersistenceError('closed')) } })
          result('applied')
        } catch (error) { abort(error) }
      }
      requests.forEach(read => { read.onsuccess = finish })
    }).finally(() => unsubscribe?.())
  }
  async apply(scope: BrowserSyncScope, reference: V3Descriptor, auth: NormalUserAuthRuntime, bindings: AuthoritativeAccountBinding, keys: RuntimeKeyContext): Promise<'applied' | 'already_applied'> {
    const plan = await this.prepareVerified(scope, reference, auth, bindings, keys)
    return this.commitVerifiedImportedMetadataApply(scope, plan)
  }
}
