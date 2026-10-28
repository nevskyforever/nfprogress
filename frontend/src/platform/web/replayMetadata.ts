import type { NormalUserAuthRuntime } from '@/auth/userAuth'
import type { AuthoritativeAccountBinding } from '@/auth/accountBinding'
import type { RuntimeKeyContext } from '@/auth/keyContext'
import { cloudProjectsApi } from '@/api/cloudProjects'
import { encryptedSyncV2Api } from '@/api/encryptedSyncV2'
import { encryptedSyncV3Api, type V3Descriptor } from '@/api/encryptedSyncV3'
import { BrowserSyncDurability, type BrowserSyncScope, type BrowserSyncTransaction } from './syncDurability'
import { BrowserImportedMetadataApply } from './importedMetadataApply'
import { prepareMetadataPrefix, verifiedMetadataSequences } from './metadataPrefixProof'
import { BrowserReplayError, prepareReplayPage, replayAnchor, replaySame } from './replayRecords'
import type { ReplaySnapshot } from './replayInventory'

export interface ReplayMetadataResult {
  readonly kind: 'metadata_owner_applied'; readonly cursor: number; readonly ownerProofs: number; readonly projects: number
  readonly generation: string; readonly projectOpened: false; readonly ready: false; readonly declarationAllowed: false; readonly writerAuthorized: false
}
interface MetadataPort {
  read(): Promise<ReplaySnapshot>
  transaction(expected: ReplaySnapshot, sequence: number, server: () => Promise<void>): BrowserSyncTransaction
}

/** No reducer: existing Imported Metadata commit and prefix verifier own every outcome. */
export async function composeReplayMetadata(port: MetadataPort, scope: BrowserSyncScope, signal: AbortSignal, current: () => boolean,
  auth: NormalUserAuthRuntime, bindings: AuthoritativeAccountBinding, keys: RuntimeKeyContext): Promise<ReplayMetadataResult> {
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
    if (row.protocol_version !== 3 || event.entity_type !== 'project_metadata') throw new BrowserReplayError('unsupported_history_family')
    if (event.operation !== 'upsert' || event.deleted_at !== null) throw new BrowserReplayError('unsupported_metadata_operation')
    if (event.device_id === scope.deviceId) throw new BrowserReplayError('metadata_self_echo_unsupported')
    if (event.device_id !== anchor.registry.projects.find(project => project.project_id === event.project_id)?.origin_device_id) throw new BrowserReplayError('metadata_origin_mismatch')
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
    const inventory = { rows: snapshot.rows, bindings: snapshot.bindings, owners: snapshot.owners, out: [], receipts: [], history: [],
      cursor: { pull_cursor: snapshot.manifest!.receive_cursor, ack_cursor: 0, proven_prefix: 0, next_local_ordinal: 1 } }
    const safe = await lease!.use(async amk => verifiedMetadataSequences(await prepareMetadataPrefix(scope, inventory, amk, () => {
      try { check(); return true } catch { return false }
    }, true), scope, inventory))
    check()
    if (safe.size !== (snapshot.manifest!.metadata_cursor ?? 0) || snapshot.rows.some(row => row.state === 'applied' && !safe.has(row.server_sequence))) throw new BrowserReplayError('metadata_proof_reauthentication_failed')
  }
  await reauthenticate()
  for (const row of snapshot.rows) {
    if (row.state === 'applied') continue // Only after actual owner proof reauthentication above.
    check()
    const reference = JSON.parse(row.wire_item).event as V3Descriptor
    const transaction = port.transaction(snapshot, row.server_sequence, server)
    const owner = new BrowserImportedMetadataApply(transaction, new BrowserSyncDurability(transaction))
    const token = snapshot.bindings.some(binding => binding.project_id === reference.project_id)
      ? await owner.prepareVerifiedOrdinary(scope, reference, auth, bindings, keys)
      : await owner.prepareVerifiedRemoteGenesis(scope, reference, auth, bindings, keys, signal)
    check(); await owner.commitVerifiedImportedMetadataApply(scope, token); check()
    snapshot = await port.read(); check()
  }
  await reauthenticate(); await server()
  if (!replaySame(await port.read(), snapshot)) throw new BrowserReplayError('metadata_inventory_changed')
  check()
  return { kind: 'metadata_owner_applied', cursor: snapshot.manifest!.receive_cursor, generation: snapshot.manifest!.generation,
    ownerProofs: snapshot.manifest!.metadata_cursor!, projects: snapshot.owners.length, projectOpened: false,
    ready: false, declarationAllowed: false, writerAuthorized: false }
}
