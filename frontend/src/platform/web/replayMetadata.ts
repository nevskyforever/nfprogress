import { CryptoError } from '@/crypto'
import type { NormalUserAuthRuntime } from '@/auth/userAuth'
import type { AuthoritativeAccountBinding } from '@/auth/accountBinding'
import type { RuntimeKeyContext } from '@/auth/keyContext'
import { cloudProjectsApi } from '@/api/cloudProjects'
import { encryptedSyncV2Api } from '@/api/encryptedSyncV2'
import { encryptedSyncV3Api, type V3Descriptor } from '@/api/encryptedSyncV3'
import { BrowserSyncDurability, type BrowserSyncScope, type BrowserSyncTransaction } from './syncDurability'
import { BrowserStageApply, prepareStagePrefix, stageSequences } from './stageApply'
import { BrowserStageOrderApply, prepareStageOrderPrefix, stageOrderSequences } from './stageOrderApply'
import { BrowserImportedMetadataApply } from './importedMetadataApply'
import { prepareMetadataPrefix, verifiedMetadataSequences } from './metadataPrefixProof'
import { BrowserReplayError, prepareReplayPage, replayAnchor, replaySame } from './replayRecords'
import type { ReplaySnapshot } from './replayInventory'
import type { AccountMasterKey } from '@/crypto'
import { reauthenticateReplayNotes } from './replayNoteProof'
import { BrowserLocalAuthority } from './localAuthority'
import { BrowserLegacyNoteApply } from './legacyNoteApply'

export interface ReplayMetadataResult {
  readonly kind: 'metadata_owner_applied'; readonly cursor: number; readonly ownerProofs: number; readonly projects: number
  readonly generation: string; readonly projectOpened: false; readonly ready: false; readonly declarationAllowed: false; readonly writerAuthorized: false
}
export interface ReplayStructuralResult extends Omit<ReplayMetadataResult, 'kind'> {
  readonly kind: 'structural_owners_applied'; readonly metadataProofs: number; readonly stageProofs: number; readonly stageOrderProofs: number
}
export interface ReplayInitialNoteResult extends Omit<ReplayStructuralResult, 'kind'> {
  readonly kind: 'initial_legacy_notes_applied'; readonly noteProofs: number
}
interface MetadataPort {
  read(): Promise<ReplaySnapshot>
  transaction(expected: ReplaySnapshot, sequence: number, server: () => Promise<void>): BrowserSyncTransaction
}

/** Force the genuine owner certificates over every retained applied row. */
export async function reauthenticateReplayOwners(scope: BrowserSyncScope, snapshot: ReplaySnapshot, amk: AccountMasterKey,
  current: () => boolean, structural = true, notes: ReadonlySet<number> = new Set()): Promise<void> {
  const inventory = { rows: snapshot.rows, bindings: snapshot.bindings, owners: snapshot.owners, out: [], receipts: [], history: [],
    cursor: { pull_cursor: snapshot.manifest!.receive_cursor, ack_cursor: 0, proven_prefix: 0, next_local_ordinal: 1 } }
  const meta = await prepareMetadataPrefix(scope, inventory, amk, current, true)
  const certificates = new Map<string, ReadonlySet<number>>([['applied', verifiedMetadataSequences(meta, scope, inventory)]])
  if (structural) {
    certificates.set('stage_proven', stageSequences(await prepareStagePrefix(scope, inventory, amk, current, meta, true), scope, inventory))
    certificates.set('stage_order_proven', stageOrderSequences(await prepareStageOrderPrefix(scope, inventory, amk, current, meta, true), scope, inventory))
  }
  let authenticated = 0
  for (const row of snapshot.rows) if (row.state !== 'received') {
    if (!(row.state === 'note_proven' ? notes.has(row.server_sequence) : certificates.get(row.state)?.has(row.server_sequence)))
      throw new BrowserReplayError(structural ? 'structural_proof_reauthentication_failed' : 'metadata_proof_reauthentication_failed')
    authenticated++
  }
  if (authenticated !== snapshot.manifest!.applied_cursor) throw new BrowserReplayError(structural ? 'structural_proof_reauthentication_failed' : 'metadata_proof_reauthentication_failed')
  if (!current()) throw new BrowserReplayError('session_closed')
}

/** No reducer: the existing Metadata/Structural commits and prefix verifiers own every outcome. */
export async function composeReplayMetadata(port: MetadataPort, scope: BrowserSyncScope, signal: AbortSignal, current: () => boolean,
  auth: NormalUserAuthRuntime, bindings: AuthoritativeAccountBinding, keys: RuntimeKeyContext, structural = false, initialNotes = false): Promise<ReplayMetadataResult | ReplayStructuralResult | ReplayInitialNoteResult> {
  const context = auth.requireContext(), lease = keys.leaseForAccount(scope.accountId)
  const check = () => {
    if (signal.aborted || !current() || !auth.isCurrent(context) || !lease?.isCurrent() || lease.localAccountId !== scope.accountId
      || lease.canonicalUserId !== scope.canonicalUserId || lease.authEpoch !== context.authEpoch) throw new BrowserReplayError('session_closed')
  }
  check()
  let snapshot = await port.read(); check()
  if (!snapshot.manifest) throw new BrowserReplayError('metadata_history_incomplete')
  const anchor = snapshot.manifest.anchor
  if (snapshot.manifest.phase !== 'received' || snapshot.rows.length !== anchor.registry.current_cursor || !snapshot.rows.length) throw new BrowserReplayError('metadata_history_incomplete')
  // Whole-account admissibility; an unsupported earlier event is never filtered.
  for (const row of snapshot.rows) {
    const event = JSON.parse(row.wire_item).event as V3Descriptor
    if (row.protocol_version !== 3 || !(initialNotes ? ['note', 'project_metadata', 'stage', 'stage_order'] : structural ? ['project_metadata', 'stage', 'stage_order'] : ['project_metadata']).includes(event.entity_type)) throw new BrowserReplayError('unsupported_history_family')
    if (event.operation !== 'upsert' || event.deleted_at !== null) throw new BrowserReplayError('unsupported_metadata_operation')
    if (event.device_id === scope.deviceId) throw new BrowserReplayError('metadata_self_echo_unsupported')
    if (event.device_id !== anchor.registry.projects.find(project => project.project_id === event.project_id)?.origin_device_id) throw new BrowserReplayError('metadata_origin_mismatch')
    if (event.entity_type === 'note') {
      const seed = snapshot.manifest.source_seeds?.find(value => value.project_id === event.project_id)
      if (!seed || row.server_sequence > seed.initial_max_server_sequence || event.revision !== 1 || row.state !== 'received' && row.state !== 'note_proven')
        throw new BrowserReplayError('unsupported_initial_note_history')
    }
  }
  // Current owners reauthenticate full current Stage membership. Later membership
  // expansion after an order is a separate cohort, never a silently weakened proof.
  if (structural) {
    const ordered = new Set<string>(), known = new Set<string>()
    for (const row of snapshot.rows) {
      const event = JSON.parse(row.wire_item).event as V3Descriptor
      if (event.entity_type === 'stage_order') ordered.add(event.project_id)
      if (event.entity_type === 'stage') {
        const id = JSON.stringify([event.project_id, event.entity_id])
        if (!known.has(id) && ordered.has(event.project_id)) throw new BrowserReplayError('structural_membership_expansion_unsupported')
        known.add(id)
      }
    }
  }
  const server = async () => {
    check()
    const registry = await auth.authorized(token => cloudProjectsApi.listBootstraps(token, signal)); check()
    const mode = await auth.authorized(token => encryptedSyncV2Api.capabilities(token, signal)); check()
    if (!replaySame(replayAnchor(registry.value, mode.value), anchor)) throw new BrowserReplayError('server_changed')
    // Fresh device/family gate check, including a concurrently advanced account tail.
    const tail = await auth.authorized(token => encryptedSyncV3Api.pullRaw(token, scope.deviceId, anchor.registry.current_cursor, 1, signal)); check()
    const { page } = prepareReplayPage(tail.value, anchor.registry.current_cursor, scope, anchor)
    if (page.items.length || page.has_more) throw new BrowserReplayError('server_changed')
  }
  const reauthenticate = async () => {
    check()
    await lease!.use(async amk => {
      const noteSequences = initialNotes ? await reauthenticateReplayNotes(scope, snapshot, amk, () => { try { check(); return true } catch { return false } },
        async projectId => {
          const local = new BrowserLocalAuthority(port.transaction(snapshot, 0, server)).bind(auth, bindings, keys)
          const source = await local.readSnapshot(scope, projectId)
          const project = await local.withDecryptedSnapshot(scope, source.token, async opened => structuredClone(opened.project))
          return { source, project }
        }) : new Set<number>()
      await reauthenticateReplayOwners(scope, snapshot, amk, () => { try { check(); return true } catch { return false } }, structural, noteSequences)
    })
    check()
  }
  await reauthenticate()
  for (const row of snapshot.rows) {
    if (row.state !== 'received') continue // Only after actual owner proof reauthentication above.
    check()
    const reference = JSON.parse(row.wire_item).event as V3Descriptor
    const transaction = port.transaction(snapshot, row.server_sequence, server)
    if (reference.entity_type === 'note') {
      const owner = new BrowserLegacyNoteApply(transaction, new BrowserLocalAuthority(transaction), current).bind(auth, bindings, keys)
      const token = await owner.prepare(scope, row.server_sequence); check()
      if (await owner.commit(token) !== 'applied') throw new BrowserReplayError('initial_note_not_applied')
      check()
    } else if (reference.entity_type === 'project_metadata') {
      const owner = new BrowserImportedMetadataApply(transaction, new BrowserSyncDurability(transaction))
      const token = snapshot.bindings.some(binding => binding.project_id === reference.project_id)
        ? await owner.prepareVerifiedOrdinary(scope, reference, auth, bindings, keys)
        : await owner.prepareVerifiedRemoteGenesis(scope, reference, auth, bindings, keys, signal)
      check(); await owner.commitVerifiedImportedMetadataApply(scope, token); check()
    } else {
      try {
        // Existing opaque preparation and actual owner commit, through the same CAS adapter.
        if (reference.entity_type === 'stage') {
          const owner = new BrowserStageApply(transaction, current).bind(auth, bindings, keys)
          const token = await owner.prepare(scope, row.server_sequence); check(); await owner.commit(token)
        } else {
          const owner = new BrowserStageOrderApply(transaction, current).bind(auth, bindings, keys)
          const token = await owner.prepare(scope, row.server_sequence); check(); await owner.commit(token)
        }
      } catch (error) {
        if (error instanceof CryptoError) throw new BrowserReplayError('structural_ciphertext_rejected')
        throw error
      }
      check()
    }
    snapshot = await port.read(); check()
  }
  await reauthenticate(); await server()
  if (!replaySame(await port.read(), snapshot)) throw new BrowserReplayError('metadata_inventory_changed')
  check()
  const metadataProofs = snapshot.rows.filter(row => row.state === 'applied').length
  const stageProofs = snapshot.rows.filter(row => row.state === 'stage_proven').length
  const stageOrderProofs = snapshot.rows.filter(row => row.state === 'stage_order_proven').length
  const result = { cursor: snapshot.manifest!.receive_cursor, generation: snapshot.manifest!.generation,
    ownerProofs: snapshot.manifest!.applied_cursor!, projects: snapshot.owners.filter(head => head.owner_kind === 'project_metadata').length,
    projectOpened: false as const, ready: false as const, declarationAllowed: false as const, writerAuthorized: false as const }
  return initialNotes ? { ...result, kind: 'initial_legacy_notes_applied', metadataProofs, stageProofs, stageOrderProofs,
    noteProofs: snapshot.rows.filter(row => row.state === 'note_proven').length }
    : structural ? { ...result, kind: 'structural_owners_applied', metadataProofs, stageProofs, stageOrderProofs }
    : { ...result, kind: 'metadata_owner_applied' }
}
