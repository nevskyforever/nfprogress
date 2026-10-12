import { describe, expect, it } from 'vitest'
import { validateBrowserV3SyncState } from './syncDurability'
const scope = { canonicalUserId: '11111111-1111-4111-8111-111111111111', accountId: '22222222-2222-4222-8222-222222222222', deviceId: '33333333-3333-4333-8333-333333333333' }
const event = { event_id: '44444444-4444-4444-8444-444444444444', project_id: 'opaque-project', entity_id: 'opaque-note', entity_type: 'note', operation: 'upsert', revision: 1, updated_at: '2026-10-11T00:00:00Z', deleted_at: null }
const object = { crypto_version: 1, aad_version: 1, nonce: 'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA', ciphertext: 'AAAAAAAAAAAAAAAAAAAAAA' }
const out = { record_version: 1, account_id: scope.accountId, device_id: scope.deviceId, event_id: event.event_id, local_ordinal: 1, protocol_version: 2, state: 'accepted', raw_body: JSON.stringify({ protocol_version: 2, encrypted_sync_version: 2, device_id: scope.deviceId, items: [{ event, object }] }) }
const incoming = { record_version: 1, account_id: scope.accountId, device_id: scope.deviceId, event_id: event.event_id, server_sequence: 5, protocol_version: 3, state: 'received', wire_item: JSON.stringify({ event: { ...event, device_id: scope.deviceId, server_sequence: 5 }, object }) }
const checkpoint = { record_version: 1, account_id: scope.accountId, device_id: scope.deviceId, pull_cursor: 5, ack_cursor: 0, proven_prefix: 0, next_local_ordinal: 2 }
const receipt = { record_version: 1, account_id: scope.accountId, device_id: scope.deviceId, event_id: event.event_id, protocol_version: 2, server_sequence: 5, duplicate: false }
const fails = (operation: () => unknown) => expect(operation).toThrowError(expect.objectContaining({ name: 'BrowserPersistenceError' }))
describe('v3 to v4 non-destructive validation', () => {
  it('preserves accepted v3 bodies/proofs and own v3 echo without manufacturing project bindings', () => {
    const rows = structuredClone([[out],[incoming],[checkpoint],[receipt]]), original = structuredClone(rows)
    validateBrowserV3SyncState([scope], rows[0]!, rows[1]!, rows[2]!, rows[3]!)
    expect(rows).toEqual(original)
    validateBrowserV3SyncState([scope], [], [], [], [])
  })
  it('rejects missing/orphan/unknown/inconsistent upload proofs', () => {
    fails(() => validateBrowserV3SyncState([scope], [out], [incoming], [checkpoint], []))
    fails(() => validateBrowserV3SyncState([scope], [], [incoming], [checkpoint], [receipt]))
    for (const changed of [{ record_version: 99 }, { server_sequence: 0 }, { device_id: scope.accountId }, { server_sequence: 6 }, { secret: 'SECRET' }]) fails(() => validateBrowserV3SyncState([scope], [out], [incoming], [checkpoint], [{ ...receipt, ...changed }]))
    fails(() => validateBrowserV3SyncState([scope], [{ ...out, state: 'sealed' }], [incoming], [checkpoint], [receipt]))
  })
  it('rejects duplicate receipt identities and foreign binding scope', () => {
    fails(() => validateBrowserV3SyncState([scope], [out], [incoming], [checkpoint], [receipt, receipt]))
    fails(() => validateBrowserV3SyncState([], [out], [incoming], [checkpoint], [receipt]))
  })
  it('rejects corrupt inbox/cursor/allocator and dormant ACK changes without repair', () => {
    fails(() => validateBrowserV3SyncState([scope], [out], [{ ...incoming, record_version: 99 }], [checkpoint], [receipt]))
    for (const changed of [{ ack_cursor: 1 }, { proven_prefix: 1 }, { pull_cursor: 6 }, { next_local_ordinal: 1 }]) fails(() => validateBrowserV3SyncState([scope], [out], [incoming], [{ ...checkpoint, ...changed }], [receipt]))
    fails(() => validateBrowserV3SyncState([scope], [out], [incoming], [], [receipt]))
  })
})
