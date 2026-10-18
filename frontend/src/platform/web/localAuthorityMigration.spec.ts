import { describe, expect, it } from 'vitest'
import { validateBrowserV5State } from './localAuthorityMigration'
import { WEB_DATABASE_VERSION } from './persistence'
const scope = { canonicalUserId: '11111111-1111-4111-8111-111111111111', accountId: '22222222-2222-4222-8222-222222222222', deviceId: '33333333-3333-4333-8333-333333333333' }
const peer = '44444444-4444-4444-8444-444444444444', boot = '55555555-5555-4555-8555-555555555555', id = '66666666-6666-4666-8666-666666666666'
function fixture(): unknown[][] {
  const reference = { event_id: id, device_id: peer, server_sequence: 1, project_id: 'p', entity_id: 'p', entity_type: 'project_metadata', operation: 'upsert', revision: 1, updated_at: '2026-10-13T00:00:00.000000Z', deleted_at: null }
  const proof = { record_version: 1, protocol_version: 3, metadata_codec_version: 1, owner_kind: 'project_metadata', account_id: scope.accountId, project_id: 'p', bootstrap_id: boot, event_id: id, source_device_id: peer, server_sequence: 1, operation: 'create', revision: 1, generation: 1, parent_event_ids: [], wire_digest: '0'.repeat(64), reference }
  const inbox = { record_version: 2, account_id: scope.accountId, device_id: scope.deviceId, event_id: id, server_sequence: 1, protocol_version: 3, state: 'applied', applied_proof: proof, wire_item: JSON.stringify({ event: reference, object: { crypto_version: 1, aad_version: 1, nonce: 'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA', ciphertext: 'AAAAAAAAAAAAAAAAAAAAAA' } }) }
  const cursor = { record_version: 1, account_id: scope.accountId, device_id: scope.deviceId, pull_cursor: 1, ack_cursor: 0, proven_prefix: 0, next_local_ordinal: 1 }
  const binding = { record_version: 1, account_id: scope.accountId, device_id: scope.deviceId, project_id: 'p', bootstrap_id: boot, mode: 'import_remote', phase: 'captured', remote_state: 'active', initial_event_count: 0, initial_local_ordinal_hi: 0, remote_high_water: 1, initial_max_server_sequence: null, blocked_reason: null }
  const head = { record_version: 1, account_id: scope.accountId, device_id: scope.deviceId, owner_kind: 'project_metadata', owner_id: 'p', bootstrap_id: boot, tip_event_ids: [id], history: [structuredClone(proof)] }
  return [[],[inbox],[cursor],[],[binding],[head]]
}
describe('v5 to v6 local authority migration structural validation', () => {
  it('supports v6 and validates empty old state without inventing source', () => { expect(WEB_DATABASE_VERSION).toBe(9); validateBrowserV5State([scope], [[],[],[],[],[],[]]) })
  it('preserves applied Metadata proofs, heads and wire bytes exactly', () => { const old = fixture(), original = structuredClone(old); validateBrowserV5State([scope], old); expect(old).toEqual(original) })
  it.each([1,2,4,5])('refuses corrupt record version in old store %s', index => { const old = fixture(); (old[index]![0] as Record<string,unknown>).record_version = 99; expect(() => validateBrowserV5State([scope], old)).toThrow() })
  it('refuses applied proof without head', () => { const old = fixture(); old[5] = []; expect(() => validateBrowserV5State([scope], old)).toThrow() })
  it('refuses head without retained applied inbox', () => { const old = fixture(); old[1] = []; (old[2]![0] as Record<string,unknown>).pull_cursor = 0; expect(() => validateBrowserV5State([scope], old)).toThrow() })
  it('refuses head and inbox proof disagreement', () => { const old = fixture(); (old[5]![0] as { history: {wire_digest: string}[] }).history[0]!.wire_digest = '1'.repeat(64); expect(() => validateBrowserV5State([scope], old)).toThrow() })
  it('refuses wrong bootstrap lineage', () => { const old = fixture(); (old[4]![0] as Record<string,unknown>).bootstrap_id = peer; expect(() => validateBrowserV5State([scope], old)).toThrow() })
  it('refuses orphan account/device authority', () => { expect(() => validateBrowserV5State([], fixture())).toThrow(); const old = fixture(); (old[5]![0] as Record<string,unknown>).device_id = peer; expect(() => validateBrowserV5State([scope], old)).toThrow() })
  it('refuses duplicated owner heads', () => { const old = fixture(); old[5]!.push(structuredClone(old[5]![0])); expect(() => validateBrowserV5State([scope], old)).toThrow() })
  it('refuses ACK and inferred prefix advancement during migration', () => { for (const key of ['ack_cursor','proven_prefix']) { const old = fixture(); (old[2]![0] as Record<string,unknown>)[key] = 1; expect(() => validateBrowserV5State([scope], old)).toThrow() } })
  it('does not rewrite received-only transport as applied authority', () => { const old = fixture(); const row = old[1]![0] as Record<string,unknown>; delete row.applied_proof; row.record_version = 1; row.state = 'received'; old[5] = []; const original = structuredClone(old); validateBrowserV5State([scope], old); expect(old).toEqual(original) })
})
