import { describe, expect, it } from 'vitest'
import { validateBrowserV2SyncState } from './syncDurability'
const scope = { canonicalUserId: '11111111-1111-4111-8111-111111111111', accountId: '22222222-2222-4222-8222-222222222222', deviceId: '33333333-3333-4333-8333-333333333333' }
const event = { event_id: '44444444-4444-4444-8444-444444444444', project_id: 'opaque-project', entity_id: 'opaque-note', entity_type: 'note', operation: 'upsert', revision: 1, updated_at: '2026-10-11T00:00:00Z', deleted_at: null }
const object = { crypto_version: 1, aad_version: 1, nonce: 'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA', ciphertext: 'AAAAAAAAAAAAAAAAAAAAAA' }
const outbound = { record_version: 1, account_id: scope.accountId, device_id: scope.deviceId, event_id: event.event_id, local_ordinal: 1, protocol_version: 2, state: 'sealed', raw_body: JSON.stringify({ protocol_version: 2, encrypted_sync_version: 2, device_id: scope.deviceId, items: [{ event, object }] }) }
const inbound = { record_version: 1, account_id: scope.accountId, device_id: scope.deviceId, event_id: event.event_id, server_sequence: 5, protocol_version: 3, state: 'received', wire_item: JSON.stringify({ event: { ...event, device_id: scope.deviceId, server_sequence: 5 }, object }) }
const checkpoint = { record_version: 1, account_id: scope.accountId, device_id: scope.deviceId, pull_cursor: 5, ack_cursor: 0, proven_prefix: 0, next_local_ordinal: 2 }
const fails = (action: () => unknown) => expect(action).toThrowError(expect.objectContaining({ name: 'BrowserPersistenceError' }))
describe('v2 to v3 migration validation', () => {
  it('accepts and never modifies valid retained v2 state, including transport sequence gaps', () => {
    const values = structuredClone([[outbound], [inbound], [checkpoint]])
    const original = structuredClone(values)
    validateBrowserV2SyncState([scope], values[0]!, values[1]!, values[2]!)
    expect(values).toEqual(original)
    validateBrowserV2SyncState([scope], [], [], [])
  })
  it('rejects orphan scope/device, missing checkpoint and inconsistent positions', () => {
    fails(() => validateBrowserV2SyncState([], [outbound], [], [checkpoint]))
    fails(() => validateBrowserV2SyncState([scope], [outbound], [inbound], []))
    fails(() => validateBrowserV2SyncState([scope], [outbound], [inbound], [{ ...checkpoint, pull_cursor: 6 }]))
    fails(() => validateBrowserV2SyncState([scope], [outbound], [inbound], [{ ...checkpoint, next_local_ordinal: 1 }]))
    fails(() => validateBrowserV2SyncState([scope], [{ ...outbound, device_id: scope.accountId }], [inbound], [checkpoint]))
  })
  it('rejects unknown v2 record/state/envelope versions and dormant ACK mutations', () => {
    fails(() => validateBrowserV2SyncState([scope], [{ ...outbound, record_version: 99 }], [inbound], [checkpoint]))
    fails(() => validateBrowserV2SyncState([scope], [{ ...outbound, state: 'accepted' }], [inbound], [checkpoint]))
    fails(() => validateBrowserV2SyncState([scope], [outbound], [{ ...inbound, record_version: 99 }], [checkpoint]))
    fails(() => validateBrowserV2SyncState([scope], [outbound], [inbound], [{ ...checkpoint, ack_cursor: 1 }]))
    fails(() => validateBrowserV2SyncState([scope], [outbound], [inbound], [{ ...checkpoint, proven_prefix: 1 }]))
  })
  it('rejects mismatched own encrypted echo without dropping either retained record', () => {
    const changed = JSON.parse(inbound.wire_item); changed.object.ciphertext = 'AQEBAQEBAQEBAQEBAQEBAQ'
    fails(() => validateBrowserV2SyncState([scope], [outbound], [{ ...inbound, wire_item: JSON.stringify(changed) }], [checkpoint]))
    expect(inbound.wire_item).toContain(object.ciphertext)
  })
})
