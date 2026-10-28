import { BrowserPersistenceError } from './persistence'
import { validateBrowserInboxRecord, validateBrowserSyncCursor, type BrowserInboxRecord, type BrowserSyncScope } from './syncDurability'
import { validateBrowserProjectBinding, type BrowserProjectBinding } from './projectBindings'
import type { BrowserMetadataHead, BrowserMetadataProof } from './metadataApplyRecords'
import { validateBrowserOwnerHead, stageOwnerId, type BrowserStageHead, type BrowserStageProof } from './stageRecords'
import type { BrowserStageOrderHead, BrowserStageOrderProof } from './stageOrderRecords'
import { validateLocalProjectRecord, type LocalProjectRecord } from './localAuthorityRecords'
import { REPLAY_LIMITS, replayExact, replaySame, replayUuid, validateReplayManifest, type ReplayManifest } from './replayRecords'

export interface ReplaySnapshot {
  manifest: ReplayManifest | null; rows: BrowserInboxRecord[]; bindings: BrowserProjectBinding[]; owners: Array<BrowserMetadataHead | BrowserStageHead | BrowserStageOrderHead>
  sources?: LocalProjectRecord[]
}
/** Derived coverage is never a qualified cursor or owner certificate. */
export function replayCoverage(manifest: ReplayManifest, row: BrowserInboxRecord) {
  const sequence = row.server_sequence
  return { ...manifest, applied_cursor: sequence, metadata_cursor: row.state === 'applied' && sequence === (manifest.metadata_cursor ?? 0) + 1 ? sequence : manifest.metadata_cursor,
    revision: manifest.revision + 1 }
}
export function replayAppliedProof(row: BrowserInboxRecord): BrowserMetadataProof | BrowserStageProof | BrowserStageOrderProof | undefined {
  return row.state === 'applied' ? row.applied_proof : row.state === 'stage_proven' ? row.stage_proof : row.state === 'stage_order_proven' ? row.stage_order_proof : undefined
}
export function assertReplayOwnerTransition(before: ReplaySnapshot, after: ReplaySnapshot, sequence: number, status: unknown): void {
  if (status === 'already_applied') { if (!replaySame(before, after)) fail(); return }
  const manifest = before.manifest!, previous = before.rows[sequence - 1], row = after.rows[sequence - 1], proof = row && replayAppliedProof(row)
  if (status !== 'applied' || !previous || previous.state !== 'received' || !proof
    || sequence !== (manifest.applied_cursor ?? 0) + 1 || !replaySame(after.manifest, replayCoverage(manifest, row!))) fail()
  const wire = { ...row } as Record<string, unknown>
  for (const key of ['applied_proof', 'stage_proof', 'stage_order_proof']) delete wire[key]
  if (!replaySame({ ...wire, record_version: 1, state: 'received' }, previous)
    || !replaySame(before.rows.filter(value => value.server_sequence !== sequence), after.rows.filter(value => value.server_sequence !== sequence))) fail()
  const ownerId = proof.owner_kind === 'stage' ? stageOwnerId(proof.project_id, proof.stage_id) : proof.project_id
  const other = (head: ReplaySnapshot['owners'][number]) => head.owner_kind !== proof.owner_kind || head.owner_id !== ownerId
  if (!replaySame(before.owners.filter(other), after.owners.filter(other))) fail()
  if (!replaySame(before.sources, after.sources)) fail()
  const oldBinding = before.bindings.find(binding => binding.project_id === proof.project_id)
  if (proof.owner_kind !== 'project_metadata' || oldBinding) {
    if (!replaySame(before.bindings, after.bindings)) fail()
  } else if (!replaySame(before.bindings, after.bindings.filter(binding => binding.project_id !== proof.project_id))) fail()
}
export const replayEmptyStores = ['outbox', 'receipts', 'localNotes', 'legacyNoteHistory', 'legacyNoteIntents']
function fail(): never { throw new BrowserPersistenceError('corrupt_record') }
const range = (account: string) => IDBKeyRange.bound([account], [account, []])

/** Complete account snapshot, with structural joins only. Crypto is owned by the existing family certificates. */
export function scheduleReplaySnapshot(tx: IDBTransaction, s: BrowserSyncScope, check: () => void,
  result: (snapshot: ReplaySnapshot) => void, abort: (error: unknown) => void, version: 1 | 2 | 3 | 4 = 4): void {
  const bound = range(s.accountId), rows: BrowserInboxRecord[] = []
  const identity = tx.objectStore('identities').get(s.canonicalUserId), alias = tx.objectStore('identities').index('local_account_id').get(s.accountId)
  const binding = tx.objectStore('accountBindings').get(s.accountId), cursors = tx.objectStore('cursors').getAll(bound)
  const manifests = tx.objectStore('replayManifest').getAll(bound), bindings = tx.objectStore('projectBindings').getAll(bound), owners = tx.objectStore('ownerHeads').getAll(bound)
  const projects = tx.objectStore('localProjects').getAll(bound)
  const counts = replayEmptyStores.map(name => tx.objectStore(name).count(bound))
  let pending = 9 + counts.length, bytes = 0
  const finish = () => {
    try {
      check(); if (--pending) return
      if (counts.some(request => request.result !== 0) || version < 4 && projects.result.length || cursors.result.length > 1 || manifests.result.length > 1
        || bindings.result.length > 200 || owners.result.length > 200 || version === 1 && (bindings.result.length || owners.result.length)) fail()
      const i: unknown = identity.result, b: unknown = binding.result
      if (i === undefined ? b !== undefined || alias.result !== undefined : !replayExact(i, ['record_version', 'canonical_user_id', 'local_account_id', 'device_id'])
        || i.record_version !== 1 || i.canonical_user_id !== s.canonicalUserId || i.local_account_id !== s.accountId || i.device_id !== s.deviceId
        || !replaySame(alias.result, i) || !replayExact(b, ['record_version', 'local_account_id', 'canonical_user_id'])
        || b.record_version !== 1 || b.local_account_id !== s.accountId || b.canonical_user_id !== s.canonicalUserId) fail()
      const manifest = manifests.result.length ? validateReplayManifest(manifests.result[0], s, version) : null
      const checkpoint = validateBrowserSyncCursor(cursors.result[0], s), metadata = manifest?.metadata_cursor ?? 0, applied = version >= 3 ? manifest?.applied_cursor ?? 0 : metadata
      if (checkpoint.ack_cursor !== 0 || checkpoint.proven_prefix !== 0 || checkpoint.next_local_ordinal !== 1
        || checkpoint.pull_cursor !== rows.length || !manifest && (rows.length || cursors.result.length || bindings.result.length || owners.result.length || projects.result.length)
        || manifest && (i === undefined || !cursors.result.length || manifest.receive_cursor !== rows.length)) fail()
      const imported = bindings.result.map(raw => validateBrowserProjectBinding(raw, s)), heads = owners.result.map(raw => validateBrowserOwnerHead(raw, s))
      const sources = projects.result.map(raw => validateLocalProjectRecord(raw, s))
      if (sources.length !== (manifest?.source_seeds?.length ?? 0) || sources.some(row => row.deleted || row.source_revision !== 1
        || !manifest?.source_seeds?.some(seed => seed.project_id === row.project_id))
        || new Set(sources.map(row => row.project_id)).size !== sources.length) fail()
      for (const seed of manifest?.source_seeds ?? []) {
        const genesis = rows.find(row => row.event_id === seed.genesis_event_id)
        if (!genesis || !sources.some(source => source.project_id === seed.project_id)) fail()
        const descriptor = JSON.parse(genesis.wire_item).event
        if (descriptor.entity_type !== 'project_metadata' || descriptor.project_id !== seed.project_id
          || descriptor.device_id !== seed.origin_device_id || descriptor.revision !== 1) fail()
      }
      if (version < 3 && heads.some(head => head.owner_kind !== 'project_metadata')) fail()
      let ciphertextBytes = 0
      const ids = new Set<string>()
      for (const [index, row] of rows.entries()) {
        if (row.server_sequence !== index + 1 || ids.has(row.event_id) || (row.server_sequence <= applied) !== !!replayAppliedProof(row)) fail()
        ids.add(row.event_id)
        const wire = JSON.parse(row.wire_item) as { event: { project_id: string }; object: { ciphertext: string } }
        ciphertextBytes += Math.floor(wire.object.ciphertext.length * 3 / 4)
        const proof = replayAppliedProof(row)
        if (proof) {
          const head = heads.find(value => value.owner_kind === proof.owner_kind && value.owner_id === (proof.owner_kind === 'stage' ? stageOwnerId(proof.project_id, proof.stage_id) : proof.project_id))
          if (!head || !replaySame(head.history.find(value => value.event_id === row.event_id), proof)) fail()
          if (proof.owner_kind !== 'project_metadata') {
            const metadataHead = heads.find(value => value.owner_kind === 'project_metadata' && value.owner_id === proof.project_id)
            const dependency = metadataHead?.history.find(value => value.event_id === proof.metadata_event_id)
            if (!dependency || dependency.server_sequence >= proof.server_sequence) fail()
            if (proof.owner_kind === 'stage_order') for (const stage of proof.stage_dependencies) for (const id of stage.event_ids) {
              const head = heads.find(value => value.owner_kind === 'stage' && value.project_id === proof.project_id && value.stage_id === stage.stage_id)
              const parent = head?.history.find(value => value.event_id === id)
              if (!parent || parent.server_sequence >= proof.server_sequence) fail()
            }
          }
        }
      }
      const metadataPrefix = rows.findIndex(row => row.state !== 'applied')
      if (metadata !== (metadataPrefix < 0 ? rows.length : metadataPrefix)) fail()
      for (const record of imported) {
        const remote = manifest?.anchor.registry.projects.find(project => project.project_id === record.project_id)
        if (!remote || remote.bootstrap_id !== record.bootstrap_id || record.mode !== 'import_remote' || record.phase !== 'captured' || record.remote_state !== 'active' || record.remote_high_water !== manifest!.anchor.registry.current_cursor
          || !heads.some(head => head.owner_kind === 'project_metadata' && head.owner_id === record.project_id)) fail()
      }
      for (const head of heads) {
        const project = head.owner_kind === 'project_metadata' ? head.owner_id : head.project_id
        if (!imported.some(record => record.project_id === project && record.bootstrap_id === head.bootstrap_id)) fail()
        for (const proof of head.history) {
          const row = rows.find(value => value.event_id === proof.event_id)
          if (!row || !replaySame(replayAppliedProof(row), proof) || !['create', 'update'].includes(proof.operation)
            || proof.protocol_version !== 3 || proof.source_device_id === s.deviceId) fail()
        }
        const genesis = head.history.find(proof => proof.operation === 'create')
        if (!genesis || genesis.source_device_id !== manifest!.anchor.registry.projects.find(record => record.project_id === project)?.origin_device_id) fail()
      }
      bytes += new TextEncoder().encode(JSON.stringify({ manifest, imported, heads, sources })).length + REPLAY_LIMITS.controlReserveBytes
      if (manifest && (ciphertextBytes !== manifest.ciphertext_bytes || bytes > REPLAY_LIMITS.inventoryBytes)) fail()
      result({ manifest, rows, bindings: imported, owners: heads, sources })
    } catch (error) { abort(error) }
  }
  for (const request of [identity, alias, binding, cursors, manifests, bindings, owners, projects, ...counts]) request.onsuccess = finish
  const scan = tx.objectStore('inbox').openCursor(bound)
  scan.onsuccess = () => {
    try {
      check(); const cursor = scan.result
      if (!cursor) { finish(); return }
      if (rows.length >= REPLAY_LIMITS.events) fail()
      const row = validateBrowserInboxRecord(cursor.value, s)
      if (!(row.state === 'received' && row.record_version === 1 || version >= 2 && row.state === 'applied' && row.record_version === 2 || version >= 3 && (row.state === 'stage_proven' && row.record_version === 5 || row.state === 'stage_order_proven' && row.record_version === 6))
        || row.protocol_version !== 3 || !replaySame(cursor.primaryKey, [s.accountId, row.server_sequence])) fail()
      bytes += new TextEncoder().encode(JSON.stringify(row)).length
      if (bytes > REPLAY_LIMITS.inventoryBytes) fail()
      rows.push(row); cursor.continue()
    } catch (error) { abort(error) }
  }
}

/** Versionchange has no HTTP/crypto and never invents bindings, heads or applied outcomes. */
export function migrateReplay(tx: IDBTransaction, names: readonly string[], check: () => void, abort: (error: unknown) => void, version: 1 | 2 | 3): void {
  const all = new Map<string, unknown[]>(); let remaining = names.length, bytes = 0
  const validate = () => {
    try {
      check(); if (--remaining) return
      const identities = all.get('identities')!, bindings = all.get('accountBindings')!
      if (identities.length !== bindings.length) fail()
      const scopes = identities.map(value => {
        const identity = value as { canonical_user_id: string; local_account_id: string; device_id: string }
        if (![identity.canonical_user_id, identity.local_account_id, identity.device_id].every(replayUuid)) fail()
        return { canonicalUserId: identity.canonical_user_id, accountId: identity.local_account_id, deviceId: identity.device_id }
      })
      for (const [name, values] of all) for (const value of values) {
        const row = value as Record<string, unknown>
        if (!scopes.some(scope => name === 'identities' ? row.canonical_user_id === scope.canonicalUserId : name === 'accountBindings' ? row.local_account_id === scope.accountId : row.account_id === scope.accountId)) fail()
      }
      let pending = scopes.length
      const updates: ReplayManifest[] = []
      for (const scope of scopes) scheduleReplaySnapshot(tx, scope, check, snapshot => {
        try {
          if (snapshot.manifest) updates.push({ ...snapshot.manifest, record_version: 4, contract_version: 4, metadata_cursor: snapshot.manifest.metadata_cursor ?? 0,
            applied_cursor: snapshot.manifest.applied_cursor ?? snapshot.manifest.metadata_cursor ?? 0, source_seeds: [] })
          if (--pending) return
          check()
          for (const manifest of updates) tx.objectStore('replayManifest').put(manifest)
        } catch (error) { abort(error) }
      }, abort, version)
    } catch (error) { abort(error) }
  }
  for (const name of names) {
    const rows: unknown[] = []; all.set(name, rows)
    const request = tx.objectStore(name).openCursor()
    request.onsuccess = () => {
      try {
        check(); const cursor = request.result
        if (!cursor) { validate(); return }
        if (rows.length >= 16384) fail()
        const row: unknown = cursor.value
        bytes += new TextEncoder().encode(JSON.stringify(row)).length
        if (bytes > REPLAY_LIMITS.inventoryBytes) fail()
        rows.push(row); cursor.continue()
      } catch (error) { abort(error) }
    }
  }
}
