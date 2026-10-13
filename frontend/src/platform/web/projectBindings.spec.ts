import { describe, expect, it } from 'vitest'
import { browserProjectReadiness, compareBrowserProjectTransition, prepareBrowserProjectRegistration, validateBrowserProjectBinding, type BrowserProjectBinding } from './projectBindings'
const scope = { canonicalUserId: '11111111-1111-4111-8111-111111111111', accountId: '22222222-2222-4222-8222-222222222222', deviceId: '33333333-3333-4333-8333-333333333333' }
const prepared: BrowserProjectBinding = { record_version: 1, account_id: scope.accountId, device_id: scope.deviceId, project_id: 'opaque-project', bootstrap_id: '44444444-4444-4444-8444-444444444444', mode: 'upload_existing', phase: 'prepared', remote_state: null, initial_event_count: 0, initial_local_ordinal_hi: 0, remote_high_water: null, initial_max_server_sequence: null, blocked_reason: null }
const registration = { remote_state: 'initializing' as const, remote_high_water: 5 }
const registered = () => prepareBrowserProjectRegistration(scope, prepared, registration)
const fails = (operation: () => unknown, code = 'corrupt_record') => expect(operation).toThrowError(expect.objectContaining({ name: 'BrowserPersistenceError', code }))
describe('dormant browser project lineage contract', () => {
  it('retains exact native fields and immutable versioned preparation without plaintext', () => {
    expect(validateBrowserProjectBinding(prepared, scope)).toEqual(prepared)
    expect(Object.keys(prepared).sort()).toEqual(['record_version','account_id','device_id','project_id','bootstrap_id','mode','phase','remote_state','initial_event_count','initial_local_ordinal_hi','remote_high_water','initial_max_server_sequence','blocked_reason'].sort())
    expect(Object.isFrozen(validateBrowserProjectBinding(prepared, scope))).toBe(true)
  })
  it('prepares only the closed registration transition and preserves expected input', () => {
    const original = structuredClone(prepared), target = registered()
    expect(target).toEqual({ ...prepared, phase: 'registered', ...registration })
    expect(prepared).toEqual(original)
    expect(compareBrowserProjectTransition(scope, prepared, prepared, target)).toBe('changed')
    expect(compareBrowserProjectTransition(scope, target, prepared, target)).toBe('already_committed')
  })
  it('compares complete expected-old state; stale phase/high-water rejects', () => {
    const target = registered(), newer = { ...target, remote_high_water: 10 }
    fails(() => compareBrowserProjectTransition(scope, newer, prepared, target), 'stale_lineage')
    fails(() => compareBrowserProjectTransition(scope, newer, target, { ...target, remote_high_water: 6 }), 'stale_lineage')
  })
  it('keeps native registration high-water monotone and active state irreversible', () => {
    const active = prepareBrowserProjectRegistration(scope, registered(), { remote_state: 'active', remote_high_water: 10 })
    expect(prepareBrowserProjectRegistration(scope, active, { remote_state: 'active', remote_high_water: 2 })).toEqual(active)
    fails(() => prepareBrowserProjectRegistration(scope, active, registration), 'invalid_lineage_transition')
  })
  it.each(['account_id','device_id','project_id','bootstrap_id','mode'] as const)('rejects immutable lineage substitution: %s', field => {
    const replacement = field === 'project_id' ? 'other' : field === 'mode' ? 'import_remote' : scope.canonicalUserId
    fails(() => compareBrowserProjectTransition(scope, registered(), { ...prepared, [field]: replacement } as BrowserProjectBinding, registered()), field === 'project_id' || field === 'bootstrap_id' ? 'conflicting_record' : 'corrupt_record')
  })
  it.each(['unknown','completing','ready','paused','blocked'] as const)('does not admit unproven upload phase: %s', phase => {
    fails(() => validateBrowserProjectBinding({ ...registered(), phase, blocked_reason: phase === 'blocked' ? 'SECRET_ERROR' : null }, scope))
  })
  it('recognizes narrow initializing capture counters without admitting completion/readiness or an arbitrary registration phase transition', () => {
    const captured = { ...registered(), phase: 'captured' as const, initial_event_count: 2, initial_local_ordinal_hi: 7 }
    expect(validateBrowserProjectBinding(captured, scope)).toEqual(captured)
    expect(browserProjectReadiness(captured)).toMatchObject({ ready: false, code: 'bootstrap_completion_unavailable' })
    for (const changed of [{ initial_local_ordinal_hi: 1 }, { initial_event_count: 0 }, { remote_state: 'active' }, { initial_max_server_sequence: 1 }]) fails(() => validateBrowserProjectBinding({ ...captured, ...changed }, scope))
    fails(() => compareBrowserProjectTransition(scope, registered(), registered(), captured), 'invalid_lineage_transition')
  })
  it('does not invent previous phase or allow registration regression', () => {
    fails(() => compareBrowserProjectTransition(scope, registered(), registered(), prepared), 'invalid_lineage_transition')
    for (const phase of ['ready','paused']) fails(() => validateBrowserProjectBinding({ ...registered(), phase }, scope))
  })
  it('preserves native import captured/active/zero-cohort subset', () => {
    const imported = { ...prepared, mode: 'import_remote' as const, phase: 'captured' as const, remote_state: 'active' as const, remote_high_water: 0 }
    expect(validateBrowserProjectBinding(imported, scope)).toEqual(imported)
    for (const changed of [{ phase: 'registered' }, { remote_state: 'initializing' }, { initial_event_count: 1 }]) fails(() => validateBrowserProjectBinding({ ...imported, ...changed }, scope))
  })
  it('fails unknown version/state/reason, extra secret/name/path fields and invalid UUID identity', () => {
    for (const changed of [{ record_version: 99 }, { mode: 'unknown' }, { bootstrap_id: 'AAAAAAAA-1111-4111-8111-111111111111' }, { project_id: '' }, { project_id: 'X'.repeat(513) }, { blocked_reason: 'backend secret' }, { display_name: 'SECRET' }, { path: 'SECRET' }, { token: 'SECRET' }]) fails(() => validateBrowserProjectBinding({ ...prepared, ...changed }, scope))
    fails(() => prepareBrowserProjectRegistration(scope, prepared, { ...registration, ready: true } as never))
    fails(() => prepareBrowserProjectRegistration(scope, prepared, { ...registration, phase: 'ready' } as never))
  })
  it.each([-1, 1.5, Number.MAX_SAFE_INTEGER + 1])('rejects invalid registration counter %s', remote_high_water => {
    fails(() => prepareBrowserProjectRegistration(scope, prepared, { ...registration, remote_high_water }))
  })
  it('never accepts caller cohort counters or completion without atomic complete capture proof', () => {
    for (const changed of [{ initial_event_count: 1 }, { initial_local_ordinal_hi: 1 }, { initial_max_server_sequence: 0 }, { initial_event_count: -1 }, { initial_local_ordinal_hi: 1.5 }]) fails(() => validateBrowserProjectBinding({ ...registered(), ...changed }, scope))
    expect(browserProjectReadiness(registered())).toMatchObject({ ready: false, code: 'capture_proof_unavailable' })
  })
  it('cannot manufacture readiness, even for active remote and zero high-water', () => {
    expect(browserProjectReadiness(null)).toEqual({ ready: false, code: 'missing_lineage', required_cursor: null })
    expect(browserProjectReadiness(prepared)).toEqual({ ready: false, code: 'registration_required', required_cursor: 0 })
    const imported = { ...prepared, mode: 'import_remote' as const, phase: 'captured' as const, remote_state: 'active' as const, remote_high_water: 0 }
    expect(browserProjectReadiness(imported)).toEqual({ ready: false, code: 'ack_proof_unavailable', required_cursor: 0 })
  })
})
