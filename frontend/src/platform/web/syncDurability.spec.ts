import { describe, expect, it, vi } from 'vitest'
import { encodeBase64Url } from '@/api/base64url'
import { BrowserPersistenceError } from './persistence'
import { BrowserSyncDurability, immutableWireIdentity, validateBrowserInboundPage, validateBrowserSealedBody, type BrowserSyncScope } from './syncDurability'
const scope: BrowserSyncScope = { canonicalUserId: '11111111-1111-4111-8111-111111111111', accountId: '22222222-2222-4222-8222-222222222222', deviceId: '33333333-3333-4333-8333-333333333333' }
const eventId = '44444444-4444-4444-8444-444444444444'
const item = { event: { event_id: eventId, project_id: 'opaque-project', entity_id: 'opaque-note', entity_type: 'note', operation: 'upsert', revision: 1, updated_at: '2026-10-11T00:00:00Z', deleted_at: null }, object: { crypto_version: 1, aad_version: 1, nonce: encodeBase64Url(new Uint8Array(24)), ciphertext: encodeBase64Url(new Uint8Array(32).fill(7)) } }
const body = (version = 2, value: unknown = item) => JSON.stringify({ protocol_version: version, encrypted_sync_version: version, device_id: scope.deviceId, items: [value] })
const page = (version = 3, value: unknown = { ...item, event: { ...item.event, device_id: scope.deviceId, server_sequence: 1 } }) => JSON.stringify({ protocol_version: version, encrypted_sync_version: version, items: [value], next_cursor: 1, has_more: false })
const fails = (action: () => unknown, code = 'corrupt_record') => expect(action).toThrowError(expect.objectContaining({ code }))
describe('browser encrypted durability contract', () => {
  it.each([2, 3])('reuses existing v%i sealed descriptor/envelope allowlists', version => {
    expect(validateBrowserSealedBody(body(version), scope)).toEqual({ eventId, protocol: version, ciphertextBytes: 32 })
    expect(validateBrowserInboundPage(page(version), 0, scope).next_cursor).toBe(1)
  })
  it('accepts account crypto2 on the common v3 transport only for its bound user', () => {
    const account = { event: { event_id: eventId, canonical_user_id: scope.canonicalUserId, scope: 'account', entity_id: 'opaque-folder', entity_type: 'folder', operation: 'upsert', revision: 1, updated_at: item.event.updated_at, deleted_at: null }, object: { ...item.object, crypto_version: 2, aad_version: 2 } }
    expect(validateBrowserSealedBody(body(3, account), scope).protocol).toBe(3)
    fails(() => validateBrowserSealedBody(body(3, account), { ...scope, canonicalUserId: scope.accountId }), 'account_mismatch')
    fails(() => validateBrowserSealedBody(body(2, account), scope))
  })
  it.each(['password', 'AMK', 'RecoveryKey', 'content', 'access_token'])('rejects unexpected %s before storage', field => {
    fails(() => validateBrowserSealedBody(body(3, { ...item, [field]: 'DO_NOT_PERSIST' }), scope))
    fails(() => validateBrowserSealedBody(body(3, { ...item, event: { ...item.event, [field]: 'DO_NOT_PERSIST' } }), scope))
    fails(() => validateBrowserSealedBody(body(3, { ...item, object: { ...item.object, [field]: 'DO_NOT_PERSIST' } }), scope))
  })
  it('rejects unsupported envelopes/transport and receive-only outbound metadata', () => {
    fails(() => validateBrowserSealedBody(body(9), scope))
    fails(() => validateBrowserSealedBody(body(3, { ...item, object: { ...item.object, aad_version: 99 } }), scope))
    fails(() => validateBrowserSealedBody(body(3, { ...item, event: { ...item.event, server_sequence: 1 } }), scope))
    fails(() => validateBrowserSealedBody(body(3), { ...scope, deviceId: scope.accountId }), 'account_mismatch')
    fails(() => validateBrowserSealedBody('not JSON SECRET', scope))
  })
  it('enforces page bounds/order/event uniqueness while leaving ACK separate', () => {
    const first = JSON.parse(page())
    fails(() => validateBrowserInboundPage(JSON.stringify({ ...first, next_cursor: 2 }), 0, scope))
    fails(() => validateBrowserInboundPage(JSON.stringify({ ...first, items: [...first.items, ...first.items] }), 0, scope))
    fails(() => validateBrowserInboundPage(page(), 1, scope))
    fails(() => validateBrowserInboundPage(JSON.stringify({ ...first, items: [], has_more: true }), 0, scope))
    const gap = { ...item, event: { ...item.event, device_id: scope.deviceId, server_sequence: 5 } }
    expect(validateBrowserInboundPage(JSON.stringify({ ...first, items: [gap], next_cursor: 5 }), 0, scope).next_cursor).toBe(5)
  })
  it('compares canonical metadata/encrypted bytes independently of JSON key order', () => {
    const reversed = { object: { ...item.object }, event: { ...item.event } }
    expect(immutableWireIdentity(item)).toBe(immutableWireIdentity(reversed))
    expect(immutableWireIdentity(item)).not.toBe(immutableWireIdentity({ ...item, object: { ...item.object, ciphertext: encodeBase64Url(new Uint8Array(32).fill(8)) } }))
  })
  it('rejects overwritten JSON fields that could hide secrets in raw retry bytes', () => {
    fails(() => validateBrowserSealedBody(body(3).replace('\"nonce\":', '\"nonce\":\"SECRET\",\"nonce\":'), scope))
    expect(validateBrowserSealedBody(JSON.stringify(JSON.parse(body(3)), null, 2), scope).eventId).toBe(eventId)
  })
  it('refuses malformed enqueue before entering storage with bounded errors', () => {
    const transaction = vi.fn()
    const repository = new BrowserSyncDurability(transaction)
    fails(() => repository.enqueue(scope, [JSON.stringify({ password: 'SECRET' })]))
    fails(() => repository.enqueue(scope, []))
    fails(() => repository.enqueue(scope, 'not-array' as unknown as string[]))
    fails(() => repository.readCheckpoint({ ...scope, canonicalUserId: undefined } as unknown as BrowserSyncScope), 'account_mismatch')
    expect(transaction).not.toHaveBeenCalled()
    expect(new BrowserPersistenceError('conflicting_record').message).toBe('web_persistence_conflicting_record')
  })
})
