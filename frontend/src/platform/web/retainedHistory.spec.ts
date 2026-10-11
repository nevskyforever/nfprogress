import { describe, expect, it } from 'vitest'
import { validateBrowserRetainedHistory, type BrowserEncryptedHistoryReference } from './syncDurability'
const scope = { canonicalUserId: '11111111-1111-4111-8111-111111111111', accountId: '22222222-2222-4222-8222-222222222222', deviceId: '33333333-3333-4333-8333-333333333333' }
const event = { event_id: '44444444-4444-4444-8444-444444444444', device_id: scope.deviceId, server_sequence: 7, project_id: 'opaque-project', entity_id: 'opaque-note', entity_type: 'note' as const, operation: 'upsert' as const, revision: 1, updated_at: '2026-10-11T00:00:00Z', deleted_at: null }
const object = { crypto_version: 1, aad_version: 1, nonce: 'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA', ciphertext: 'AAAAAAAAAAAAAAAAAAAAAA' }
function fixture(reference: BrowserEncryptedHistoryReference = event) {
  const { device_id: _device, server_sequence: _sequence, ...descriptor } = reference
  const envelope = 'scope' in reference ? { ...object, crypto_version: 2, aad_version: 2 } : object
  const outbox = { record_version: 1, account_id: scope.accountId, device_id: scope.deviceId, event_id: reference.event_id, local_ordinal: 1, protocol_version: 3, state: 'accepted', raw_body: JSON.stringify({ protocol_version: 3, encrypted_sync_version: 3, device_id: scope.deviceId, items: [{ event: descriptor, object: envelope }] }) }
  const receipt = { record_version: 1, account_id: scope.accountId, device_id: scope.deviceId, event_id: reference.event_id, protocol_version: 3, server_sequence: reference.server_sequence, duplicate: false }
  const inbox = { record_version: 1, account_id: scope.accountId, device_id: scope.deviceId, event_id: reference.event_id, server_sequence: reference.server_sequence, protocol_version: 3, state: 'received', wire_item: JSON.stringify({ event: reference, object: envelope }) }
  return { outbox, receipt, inbox }
}
const fails = (action: () => unknown, code = 'corrupt_record') => expect(action).toThrowError(expect.objectContaining({ name: 'BrowserPersistenceError', code }))
describe('retained encrypted history reference boundary', () => {
  it('returns exact existing records without inventing apply proof or changing stored data', () => {
    const f = fixture(), original = structuredClone(f)
    const result = validateBrowserRetainedHistory(scope, event, f.outbox, f.receipt, f.inbox)
    expect(result).toEqual({ reference: event, ...f }); expect(f).toEqual(original)
    expect(Object.keys(result).sort()).toEqual(['inbox','outbox','receipt','reference'])
    expect(result.inbox?.state).toBe('received')
  })
  it('accepts upload-only and received-only peer history without implying apply', () => {
    const f = fixture()
    expect(validateBrowserRetainedHistory(scope, event, f.outbox, f.receipt, undefined).inbox).toBeNull()
    const peer = { ...event, device_id: scope.accountId }, remote = fixture(peer)
    expect(validateBrowserRetainedHistory(scope, peer, undefined, undefined, remote.inbox)).toEqual({ reference: peer, outbox: null, receipt: null, inbox: remote.inbox })
  })
  it('reads retained v2 Note upload with its identical v3 own echo', () => {
    const f = fixture(), body = JSON.parse(f.outbox.raw_body)
    body.protocol_version = 2; body.encrypted_sync_version = 2
    const out = { ...f.outbox, protocol_version: 2, raw_body: JSON.stringify(body) }
    expect(validateBrowserRetainedHistory(scope, event, out, { ...f.receipt, protocol_version: 2 }, f.inbox).outbox).toEqual(out)
  })
  it('excludes sealed local data; received own echo remains readable', () => {
    const f = fixture(), sealed = { ...f.outbox, state: 'sealed' }
    fails(() => validateBrowserRetainedHistory(scope, event, sealed, undefined, undefined), 'missing_history')
    expect(validateBrowserRetainedHistory(scope, event, sealed, undefined, f.inbox).outbox).toBeNull()
  })
  it.each(['project_metadata','stage','stage_order','map','document','progress','project_game'] as const)('keeps exact project descriptor distinctions: %s', kind => {
    const reference = { ...event, entity_type: kind, entity_id: kind === 'project_metadata' ? event.project_id : kind === 'stage_order' ? 'stage_order' : kind === 'map' ? 'project-map' : kind === 'project_game' ? `game:project:${event.event_id}` : event.entity_id, operation: ['map','document','progress','project_game'].includes(kind) ? 'event' as const : 'upsert' as const }
    const f = fixture(reference)
    expect(validateBrowserRetainedHistory(scope, reference, f.outbox, f.receipt, f.inbox).reference).toEqual(reference)
  })
  it.each(['folder','folder_order','folder_membership','project_order','account_game'] as const)('keeps exact account scope/type: %s', kind => {
    const { project_id: _project, ...base } = event
    const reference = { ...base, scope: 'account' as const, canonical_user_id: scope.canonicalUserId, entity_type: kind, entity_id: kind === 'account_game' ? `game:${event.event_id}` : event.entity_id }
    const f = fixture(reference)
    expect(validateBrowserRetainedHistory(scope, reference, f.outbox, f.receipt, f.inbox).reference).toEqual(reference)
    fails(() => validateBrowserRetainedHistory(scope, { ...reference, canonical_user_id: scope.accountId }, f.outbox, f.receipt, f.inbox), 'account_mismatch')
  })
  it('rejects missing references, unknown versions/states and broken acceptance halves', () => {
    const f = fixture()
    fails(() => validateBrowserRetainedHistory(scope, event, undefined, undefined, undefined), 'missing_history')
    for (const change of [{ state: 'applied' }, { record_version: 99 }, { account_id: scope.deviceId }, { device_id: scope.accountId }]) fails(() => validateBrowserRetainedHistory(scope, event, undefined, undefined, { ...f.inbox, ...change }))
    fails(() => validateBrowserRetainedHistory(scope, event, f.outbox, undefined, f.inbox))
    fails(() => validateBrowserRetainedHistory(scope, event, undefined, f.receipt, f.inbox))
    fails(() => validateBrowserRetainedHistory(scope, event, { ...f.outbox, state: 'sealed' }, f.receipt, f.inbox))
  })
  it('rejects owner/revision/sequence/source-device substitution and arbitrary fields', () => {
    const f = fixture()
    for (const change of [{ project_id: 'other' }, { entity_id: 'other' }, { revision: 2 }, { server_sequence: 8 }, { device_id: scope.accountId }]) fails(() => validateBrowserRetainedHistory(scope, { ...event, ...change }, f.outbox, f.receipt, f.inbox), 'conflicting_record')
    for (const reference of [null, 5, [], { ...event, title: 'SECRET' }, { ...event, server_sequence: 0 }]) fails(() => validateBrowserRetainedHistory(scope, reference as BrowserEncryptedHistoryReference, f.outbox, f.receipt, f.inbox))
    fails(() => validateBrowserRetainedHistory(scope, event, { ...f.outbox, account_id: scope.deviceId }, f.receipt, f.inbox))
  })
  it('rejects conflicting own ciphertext/receipt sequence without repair', () => {
    const f = fixture(), wire = JSON.parse(f.inbox.wire_item)
    wire.object.ciphertext = 'AQEBAQEBAQEBAQEBAQEBAQ'
    fails(() => validateBrowserRetainedHistory(scope, event, f.outbox, f.receipt, { ...f.inbox, wire_item: JSON.stringify(wire) }), 'conflicting_record')
    fails(() => validateBrowserRetainedHistory(scope, event, f.outbox, { ...f.receipt, server_sequence: 8 }, f.inbox), 'conflicting_record')
  })
})
