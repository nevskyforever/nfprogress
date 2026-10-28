import { BrowserPersistenceError } from './persistence'
import { validateBrowserInboxRecord, validateBrowserSyncCursor, type BrowserInboxRecord, type BrowserSyncScope } from './syncDurability'
import { validateBrowserProjectBinding, type BrowserProjectBinding } from './projectBindings'
import { validateBrowserMetadataHead, type BrowserMetadataHead } from './metadataApplyRecords'
import { REPLAY_LIMITS, replayExact, replaySame, replayUuid, validateReplayManifest, type ReplayManifest } from './replayRecords'

export interface ReplaySnapshot {
  manifest: ReplayManifest | null; rows: BrowserInboxRecord[]; bindings: BrowserProjectBinding[]; owners: BrowserMetadataHead[]
}
export function assertReplayMetadataTransition(before: ReplaySnapshot, after: ReplaySnapshot, sequence: number, status: unknown): void {
  if (status === 'already_applied') { if (!replaySame(before, after)) fail(); return }
  const manifest = before.manifest!, previous = before.rows[sequence - 1], row = after.rows[sequence - 1]
  if (status !== 'applied' || !previous || previous.state !== 'received' || !row || row.state !== 'applied'
    || sequence !== (manifest.metadata_cursor ?? 0) + 1 || !replaySame(after.manifest, { ...manifest, metadata_cursor: sequence, revision: manifest.revision + 1 })) fail()
  const wire = { ...row } as Record<string, unknown>; delete wire.applied_proof
  if (!replaySame({ ...wire, record_version: 1, state: 'received' }, previous)
    || !replaySame(before.rows.filter(value => value.server_sequence !== sequence), after.rows.filter(value => value.server_sequence !== sequence))) fail()
  const project = row.applied_proof.project_id
  if (!replaySame(before.owners.filter(head => head.owner_id !== project), after.owners.filter(head => head.owner_id !== project))
    || !replaySame(before.bindings.filter(binding => binding.project_id !== project), after.bindings.filter(binding => binding.project_id !== project))) fail()
  const oldBinding = before.bindings.find(binding => binding.project_id === project)
  if (oldBinding && !replaySame(oldBinding, after.bindings.find(binding => binding.project_id === project))) fail()
}
export const replayEmptyStores = ['outbox', 'receipts', 'localProjects', 'localNotes', 'legacyNoteHistory', 'legacyNoteIntents']
function fail(): never { throw new BrowserPersistenceError('corrupt_record') }
const range = (account: string) => IDBKeyRange.bound([account], [account, []])

/** Complete account snapshot, with structural joins only. Crypto is owned by Metadata reauthentication. */
export function scheduleReplaySnapshot(tx: IDBTransaction, s: BrowserSyncScope, check: () => void,
  result: (snapshot: ReplaySnapshot) => void, abort: (error: unknown) => void, version: 1 | 2 = 2): void {
  const bound = range(s.accountId), rows: BrowserInboxRecord[] = []
  const identity = tx.objectStore('identities').get(s.canonicalUserId), alias = tx.objectStore('identities').index('local_account_id').get(s.accountId)
  const binding = tx.objectStore('accountBindings').get(s.accountId), cursors = tx.objectStore('cursors').getAll(bound)
  const manifests = tx.objectStore('replayManifest').getAll(bound), bindings = tx.objectStore('projectBindings').getAll(bound), owners = tx.objectStore('ownerHeads').getAll(bound)
  const counts = replayEmptyStores.map(name => tx.objectStore(name).count(bound))
  let pending = 8 + counts.length, bytes = 0
  const finish = () => {
    try {
      check(); if (--pending) return
      if (counts.some(request => request.result !== 0) || cursors.result.length > 1 || manifests.result.length > 1
        || bindings.result.length > 200 || owners.result.length > 200 || version === 1 && (bindings.result.length || owners.result.length)) fail()
      const i: unknown = identity.result, b: unknown = binding.result
      if (i === undefined ? b !== undefined || alias.result !== undefined : !replayExact(i, ['record_version', 'canonical_user_id', 'local_account_id', 'device_id'])
        || i.record_version !== 1 || i.canonical_user_id !== s.canonicalUserId || i.local_account_id !== s.accountId || i.device_id !== s.deviceId
        || !replaySame(alias.result, i) || !replayExact(b, ['record_version', 'local_account_id', 'canonical_user_id'])
        || b.record_version !== 1 || b.local_account_id !== s.accountId || b.canonical_user_id !== s.canonicalUserId) fail()
      const manifest = manifests.result.length ? validateReplayManifest(manifests.result[0], s, version) : null
      const checkpoint = validateBrowserSyncCursor(cursors.result[0], s), metadata = manifest?.metadata_cursor ?? 0
      if (checkpoint.ack_cursor !== 0 || checkpoint.proven_prefix !== 0 || checkpoint.next_local_ordinal !== 1
        || checkpoint.pull_cursor !== rows.length || !manifest && (rows.length || cursors.result.length || bindings.result.length || owners.result.length)
        || manifest && (i === undefined || !cursors.result.length || manifest.receive_cursor !== rows.length)) fail()
      const imported = bindings.result.map(raw => validateBrowserProjectBinding(raw, s)), heads = owners.result.map(raw => validateBrowserMetadataHead(raw, s))
      let ciphertextBytes = 0
      const ids = new Set<string>()
      for (const [index, row] of rows.entries()) {
        if (row.server_sequence !== index + 1 || ids.has(row.event_id) || (row.server_sequence <= metadata) !== (row.state === 'applied')) fail()
        ids.add(row.event_id)
        const wire = JSON.parse(row.wire_item) as { event: { project_id: string }; object: { ciphertext: string } }
        ciphertextBytes += Math.floor(wire.object.ciphertext.length * 3 / 4)
        if (row.state === 'applied') {
          const head = heads.find(value => value.owner_id === wire.event.project_id)
          if (!head || !replaySame(head.history.find(proof => proof.event_id === row.event_id), row.applied_proof)) fail()
        }
      }
      for (const record of imported) {
        const remote = manifest?.anchor.registry.projects.find(project => project.project_id === record.project_id)
        if (!remote || remote.bootstrap_id !== record.bootstrap_id || record.mode !== 'import_remote' || record.phase !== 'captured' || record.remote_state !== 'active' || record.remote_high_water !== manifest!.anchor.registry.current_cursor
          || !heads.some(head => head.owner_id === record.project_id)) fail()
      }
      for (const head of heads) {
        if (!imported.some(record => record.project_id === head.owner_id && record.bootstrap_id === head.bootstrap_id)) fail()
        for (const proof of head.history) {
          const row = rows.find(value => value.event_id === proof.event_id)
          if (!row || row.state !== 'applied' || !replaySame(row.applied_proof, proof) || !['create', 'update'].includes(proof.operation)
            || proof.protocol_version !== 3 || proof.source_device_id === s.deviceId) fail()
        }
        const genesis = head.history.find(proof => proof.operation === 'create')
        if (!genesis || genesis.source_device_id !== manifest!.anchor.registry.projects.find(project => project.project_id === head.owner_id)?.origin_device_id) fail()
      }
      bytes += new TextEncoder().encode(JSON.stringify({ manifest, imported, heads })).length + REPLAY_LIMITS.controlReserveBytes
      if (manifest && (ciphertextBytes !== manifest.ciphertext_bytes || bytes > REPLAY_LIMITS.inventoryBytes)) fail()
      result({ manifest, rows, bindings: imported, owners: heads })
    } catch (error) { abort(error) }
  }
  for (const request of [identity, alias, binding, cursors, manifests, bindings, owners, ...counts]) request.onsuccess = finish
  const scan = tx.objectStore('inbox').openCursor(bound)
  scan.onsuccess = () => {
    try {
      check(); const cursor = scan.result
      if (!cursor) { finish(); return }
      if (rows.length >= REPLAY_LIMITS.events) fail()
      const row = validateBrowserInboxRecord(cursor.value, s)
      if (!(row.state === 'received' && row.record_version === 1 || version === 2 && row.state === 'applied' && row.record_version === 2)
        || row.protocol_version !== 3 || !replaySame(cursor.primaryKey, [s.accountId, row.server_sequence])) fail()
      bytes += new TextEncoder().encode(JSON.stringify(row)).length
      if (bytes > REPLAY_LIMITS.inventoryBytes) fail()
      rows.push(row); cursor.continue()
    } catch (error) { abort(error) }
  }
}

/** Versionchange has no HTTP/crypto and never invents bindings, heads or applied outcomes. */
export function migrateReplayV1(tx: IDBTransaction, names: readonly string[], check: () => void, abort: (error: unknown) => void): void {
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
          if (snapshot.manifest) updates.push({ ...snapshot.manifest, record_version: 2, contract_version: 2, metadata_cursor: 0 })
          if (--pending) return
          check()
          for (const manifest of updates) tx.objectStore('replayManifest').put(manifest)
        } catch (error) { abort(error) }
      }, abort, 1)
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
