import { describe, expect, it } from 'vitest'
import { prepareBrowserUploadAcceptance, validateBrowserUploadPair, type BrowserOutboxRecord, type BrowserSyncScope } from './syncDurability'
const scope: BrowserSyncScope = { canonicalUserId: '11111111-1111-4111-8111-111111111111', accountId: '22222222-2222-4222-8222-222222222222', deviceId: '33333333-3333-4333-8333-333333333333' }
const eventId = '44444444-4444-4444-8444-444444444444'
const expected = (version: 2 | 3 = 2): BrowserOutboxRecord => ({ record_version: 1, account_id: scope.accountId, device_id: scope.deviceId, event_id: eventId, local_ordinal: 1, protocol_version: version, state: 'sealed', raw_body: JSON.stringify({ protocol_version: version, encrypted_sync_version: version, device_id: scope.deviceId, items: [{ event: { event_id: eventId, project_id: 'opaque-project', entity_id: 'opaque-note', entity_type: 'note', operation: 'upsert', revision: 1, updated_at: '2026-10-11T00:00:00Z', deleted_at: null }, object: { crypto_version: 1, aad_version: 1, nonce: 'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA', ciphertext: 'AAAAAAAAAAAAAAAAAAAAAA' } }] }) })
const response = (version: 2 | 3 = 2) => ({ protocol_version: version, encrypted_sync_version: version, current_cursor: 7, results: [{ event_id: eventId, server_sequence: 7, duplicate: false }] })
const fails = (action: () => unknown) => expect(action).toThrowError(expect.objectContaining({ name: 'BrowserPersistenceError' }))
describe('browser upload acceptance evidence', () => {
  it.each([2, 3] as const)('uses authoritative v%i fields without invented proof fields', version => {
    const receipt = prepareBrowserUploadAcceptance(scope, expected(version), response(version))
    expect(receipt).toEqual({ record_version: 1, account_id: scope.accountId, device_id: scope.deviceId, event_id: eventId, protocol_version: version, server_sequence: 7, duplicate: false })
    expect(validateBrowserUploadPair({ ...expected(version), state: 'accepted' }, receipt, scope).raw_body).toBe(expected(version).raw_body)
  })
  it('does not confuse response diagnostics/high water with stable acceptance identity', () => {
    const replay = { ...response(), current_cursor: 100, results: [{ ...response().results[0]!, duplicate: true }] }
    expect(prepareBrowserUploadAcceptance(scope, expected(), replay)).toEqual({ ...prepareBrowserUploadAcceptance(scope, expected(), response()), duplicate: true })
  })
  it.each([2, 3] as const)('rejects wrong event, wrong protocol and invalid authoritative sequence for v%i', version => {
    const valid = response(version)
    fails(() => prepareBrowserUploadAcceptance(scope, expected(version), { ...valid, results: [{ ...valid.results[0], event_id: scope.deviceId }] }))
    fails(() => prepareBrowserUploadAcceptance(scope, expected(version), response(version === 2 ? 3 : 2)))
    for (const sequence of [0, -1, 1.5, Number.MAX_SAFE_INTEGER + 1, 8]) fails(() => prepareBrowserUploadAcceptance(scope, expected(version), { ...valid, results: [{ ...valid.results[0], server_sequence: sequence }] }))
    fails(() => prepareBrowserUploadAcceptance(scope, expected(version), { status: 200 }))
  })
  it('rejects copied arbitrary backend fields and foreign expected scope', () => {
    fails(() => prepareBrowserUploadAcceptance(scope, expected(), { ...response(), token: 'SECRET' }))
    fails(() => prepareBrowserUploadAcceptance(scope, expected(), { ...response(), results: [{ ...response().results[0], message: 'SECRET' }] }))
    fails(() => prepareBrowserUploadAcceptance(scope, { ...expected(), account_id: scope.deviceId }, response()))
    fails(() => prepareBrowserUploadAcceptance(scope, { ...expected(), device_id: scope.accountId }, response()))
  })
  it('fails closed on either inconsistent durable half, unknown versions and states', () => {
    const event = expected(), receipt = prepareBrowserUploadAcceptance(scope, event, response())
    expect(validateBrowserUploadPair(event, undefined, scope)).toEqual(event)
    fails(() => validateBrowserUploadPair({ ...event, state: 'accepted' }, undefined, scope))
    fails(() => validateBrowserUploadPair(event, receipt, scope))
    fails(() => validateBrowserUploadPair(undefined, receipt, scope))
    for (const changed of [{ record_version: 99 }, { account_id: scope.deviceId }, { device_id: scope.accountId }, { event_id: scope.deviceId }, { protocol_version: 3 }, { server_sequence: 0 }, { password: 'SECRET' }]) fails(() => validateBrowserUploadPair({ ...event, state: 'accepted' }, { ...receipt, ...changed }, scope))
    fails(() => validateBrowserUploadPair({ ...event, state: 'unknown' }, receipt, scope))
  })
})
