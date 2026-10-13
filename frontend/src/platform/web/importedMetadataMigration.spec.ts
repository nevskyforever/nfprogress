import { describe, expect, it } from 'vitest'
import { validateBrowserV4ProjectState, WEB_DATABASE_VERSION } from './persistence'
import { validateBrowserV3SyncState } from './syncDurability'
const scope = { canonicalUserId: '11111111-1111-4111-8111-111111111111', accountId: '22222222-2222-4222-8222-222222222222', deviceId: '33333333-3333-4333-8333-333333333333' }
const row = { record_version: 1, account_id: scope.accountId, device_id: scope.deviceId, project_id: 'p', bootstrap_id: '44444444-4444-4444-8444-444444444444', mode: 'import_remote', phase: 'captured', remote_state: 'active', initial_event_count: 0, initial_local_ordinal_hi: 0, remote_high_water: 0, initial_max_server_sequence: null, blocked_reason: null }
describe('v4 to v5 imported Metadata migration validation', () => {
  it('keeps native lineage exactly without manufacturing authority/proof', () => {
    expect(WEB_DATABASE_VERSION).toBe(7)
    const rows = [structuredClone(row)], original = structuredClone(rows)
    validateBrowserV4ProjectState([scope], rows); expect(rows).toEqual(original)
    validateBrowserV4ProjectState([scope], [])
  })
  it.each([{ record_version: 99 }, { device_id: scope.accountId }, { phase: 'ready' }, { remote_state: 'initializing' }, { name: 'PRIVATE' }])('aborts corrupt old lineage %j', changed => {
    expect(() => validateBrowserV4ProjectState([scope], [{ ...row, ...changed }])).toThrowError(expect.objectContaining({ code: 'corrupt_record' }))
  })
  it('rejects orphan scopes and duplicate project/bootstrap identities', () => {
    expect(() => validateBrowserV4ProjectState([], [row])).toThrow()
    expect(() => validateBrowserV4ProjectState([scope], [row, row])).toThrow()
    expect(() => validateBrowserV4ProjectState([scope], [row, { ...row, project_id: 'q' }])).toThrow()
  })
  it('old v4 inbox cannot already contain v5 applied proof', () => {
    expect(() => validateBrowserV3SyncState([scope], [], [{ record_version: 2, state: 'applied' }], [], [])).toThrow()
  })
})
