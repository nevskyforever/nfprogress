import { describe, expect, it, vi } from 'vitest'

import { ApiError } from '@/api/client'
import { KeyNotProvisionedError } from '@/auth/keyContext'
import { NormalUserAuthRuntime, StaleAuthContextError } from '@/auth/userAuth'
import { CloudIdentityUnavailableError, NoteSyncRuntime, NoteSyncRuntimeDisposedError } from './noteSyncRuntime'

const USER = '123e4567-e89b-42d3-a456-426614174099'
const IDENTITY = { local_account_id: 'local-account', device_id: '123e4567-e89b-42d3-a456-426614174001' }
const EMPTY_RESULT = { stages: [], sealed: [], uploaded: 0, pulled: [], applied: [], blocked: [], errors: [], hasRemainingWork: false }
const READY_REGISTRY = { readyForCycle: true, readyForNormalCycle: true, reasons: [], remote: [], local: [], currentCursor: 0 }

function auth(): NormalUserAuthRuntime {
  return new NormalUserAuthRuntime({
    login: vi.fn().mockResolvedValue({ access_token: 'token', refresh_token: 'refresh', access_expires_in: 60 }),
    refresh: vi.fn(), logout: vi.fn().mockResolvedValue(undefined),
    me: vi.fn().mockResolvedValue({ id: USER, username: 'user', email: 'u@example.test', email_verified: true, role: 'user', status: 'active', created_at: 'now' }),
  })
}

function deferred<T>() {
  let resolve!: (value: T) => void
  const promise = new Promise<T>(done => { resolve = done })
  return { promise, resolve }
}

function harness() {
  const userAuth = auth()
  let active = false
  const lease = {
    localAccountId: IDENTITY.local_account_id, canonicalUserId: USER, authEpoch: 1,
    keyContextId: 'key-context', keyEpoch: 1, isCurrent: vi.fn(() => active), use: vi.fn(),
  }
  const identity = { provision: vi.fn().mockResolvedValue(IDENTITY), read: vi.fn().mockResolvedValue(IDENTITY) }
  const bindings = { ensureForCurrentUser: vi.fn(async () => ({ context: userAuth.requireContext(), result: 'validated' as const })) }
  const keys = {
    unlockWithPassphrase: vi.fn(async () => { active = true; return { ...lease, authEpoch: userAuth.requireContext().authEpoch } }),
    leaseForAccount: vi.fn(() => active ? { ...lease, authEpoch: userAuth.requireContext().authEpoch } : null),
    lock: vi.fn(async () => { active = false }), dispose: vi.fn(async () => { active = false }),
  }
  const orchestrator = { runOnce: vi.fn().mockResolvedValue(EMPTY_RESULT) }
  const bootstrap = {
    reconcile: vi.fn().mockResolvedValue(READY_REGISTRY),
    preflightLocalProject: vi.fn().mockResolvedValue([]),
    runReadyCycle: vi.fn().mockResolvedValue(EMPTY_RESULT),
    bootstrapLocalProject: vi.fn(), importRemoteProject: vi.fn(),
    setPaused: vi.fn().mockResolvedValue(READY_REGISTRY),
  }
  const runtime = new NoteSyncRuntime({
    auth: userAuth, identityRepository: identity, bindings: bindings as never, keys: keys as never,
    orchestrator: orchestrator as never, bootstrap: bootstrap as never,
  })
  return { runtime, userAuth, identity, bindings, keys, orchestrator, bootstrap, activate: () => { active = true } }
}

describe('headless normal-user Notes sync runtime', () => {
  it('does not provision, unlock, or sync before normal-user login', async () => {
    const h = harness()
    await expect(h.runtime.retry()).rejects.toThrow()
    expect(h.identity.read).not.toHaveBeenCalled()
    expect(h.keys.unlockWithPassphrase).not.toHaveBeenCalled()
    expect(h.orchestrator.runOnce).not.toHaveBeenCalled()
  })

  it('provisions identity from the authenticated canonical user and reuses it on later login', async () => {
    const h = harness()
    await expect(h.runtime.login('user', 'account-password')).resolves.toMatchObject({ identity: IDENTITY, context: { userId: USER } })
    expect(h.identity.provision).toHaveBeenCalledWith(USER)
    expect(h.bindings.ensureForCurrentUser).toHaveBeenCalledWith(IDENTITY.local_account_id)
    await h.runtime.logout(); h.activate()
    await h.runtime.login('user', 'account-password')
    expect(h.identity.provision).toHaveBeenCalledTimes(2)
    expect(h.identity.provision.mock.results[1]!.value).resolves.toEqual(IDENTITY)
    expect(h.orchestrator.runOnce).not.toHaveBeenCalled()
  })

  it('requires unlock before registration, upload, pull, or ACK can be reached', async () => {
    const h = harness(); await h.runtime.login('user', 'account-password')
    await expect(h.runtime.retry()).rejects.toBeInstanceOf(KeyNotProvisionedError)
    expect(h.orchestrator.runOnce).not.toHaveBeenCalled()
  })

  it('unlocks and reconciles the account registry without starting upload, pull, or ACK', async () => {
    const h = harness(); await h.runtime.login('user', 'account-password')
    await expect(h.runtime.unlock('e2ee-passphrase')).resolves.toMatchObject({ identity: IDENTITY, registry: READY_REGISTRY })
    expect(h.keys.unlockWithPassphrase).toHaveBeenCalledWith(IDENTITY.local_account_id, 'e2ee-passphrase')
    expect(h.bootstrap.reconcile).toHaveBeenCalledWith({ localAccountId: IDENTITY.local_account_id, deviceId: IDENTITY.device_id })
    expect(h.bootstrap.runReadyCycle).not.toHaveBeenCalled()
    expect(h.orchestrator.runOnce).not.toHaveBeenCalled()
  })

  it('joins concurrent explicit retries for one authenticated key context', async () => {
    const h = harness(); await h.runtime.login('user', 'account-password'); await h.runtime.unlock('passphrase')
    h.bootstrap.runReadyCycle.mockClear()
    const pending = deferred<typeof EMPTY_RESULT>()
    h.bootstrap.runReadyCycle.mockReturnValueOnce(pending.promise)
    const first = h.runtime.retry(); const second = h.runtime.retry()
    await vi.waitFor(() => expect(h.bootstrap.runReadyCycle).toHaveBeenCalledTimes(1))
    pending.resolve(EMPTY_RESULT)
    await expect(Promise.all([first, second])).resolves.toHaveLength(2)
  })

  it('keeps project preflight, bootstrap, import and pause behind current auth and key authority', async () => {
    const h = harness(); await h.runtime.login('user', 'account-password')
    await expect(h.runtime.preflightLocalProject('project')).rejects.toBeInstanceOf(KeyNotProvisionedError)
    await h.runtime.unlock('passphrase')
    const report = vi.fn()
    h.bootstrap.bootstrapLocalProject.mockResolvedValue({ project: {}, registry: READY_REGISTRY, hasRemainingWork: true })
    h.bootstrap.importRemoteProject.mockResolvedValue({ project: {}, registry: READY_REGISTRY, hasRemainingWork: true })

    await h.runtime.preflightLocalProject('project')
    await h.runtime.bootstrapLocalProject('project', report)
    await h.runtime.importRemoteProject('remote', 'Импорт', report)
    await h.runtime.setProjectPaused('project', true)

    const identity = { localAccountId: IDENTITY.local_account_id, deviceId: IDENTITY.device_id }
    expect(h.bootstrap.preflightLocalProject).toHaveBeenCalledWith('project')
    expect(h.bootstrap.bootstrapLocalProject).toHaveBeenCalledWith(identity, 'project', report)
    expect(h.bootstrap.importRemoteProject).toHaveBeenCalledWith(identity, 'remote', 'Импорт', report)
    expect(h.bootstrap.setPaused).toHaveBeenCalledWith(identity, 'project', true)
  })

  it('does not run when passphrase unlock fails or the wrapped key is unprovisioned', async () => {
    const h = harness(); await h.runtime.login('user', 'account-password')
    h.keys.unlockWithPassphrase.mockRejectedValueOnce(new Error('wrong passphrase'))
    await expect(h.runtime.unlock('wrong')).rejects.toThrow('wrong passphrase')
    h.keys.unlockWithPassphrase.mockRejectedValueOnce(new KeyNotProvisionedError())
    await expect(h.runtime.unlock('anything')).rejects.toBeInstanceOf(KeyNotProvisionedError)
    expect(h.bootstrap.runReadyCycle).not.toHaveBeenCalled()
  })

  it('fails closed for missing or malformed durable identity before key use', async () => {
    const h = harness(); await h.runtime.login('user', 'account-password')
    h.identity.read.mockResolvedValueOnce(null)
    await expect(h.runtime.unlock('passphrase')).rejects.toBeInstanceOf(CloudIdentityUnavailableError)
    h.identity.read.mockResolvedValueOnce({ local_account_id: 'local', device_id: 'not-a-uuid' })
    await expect(h.runtime.retry()).rejects.toBeInstanceOf(CloudIdentityUnavailableError)
    h.bindings.ensureForCurrentUser.mockRejectedValueOnce(new Error('immutable binding mismatch'))
    await expect(h.runtime.retry()).rejects.toThrow('immutable binding mismatch')
    expect(h.orchestrator.runOnce).not.toHaveBeenCalled()
  })

  it('rejects stale auth during provisioning and does not unlock or sync it', async () => {
    const h = harness()
    h.identity.provision.mockImplementationOnce(async () => { await h.userAuth.logout(); return IDENTITY })
    await expect(h.runtime.login('user', 'account-password')).rejects.toBeInstanceOf(StaleAuthContextError)
    expect(h.keys.unlockWithPassphrase).not.toHaveBeenCalled()
    expect(h.orchestrator.runOnce).not.toHaveBeenCalled()
  })

  it('blocks retry after key lock or 401 auth invalidation without deleting durable identity', async () => {
    const h = harness(); await h.runtime.login('user', 'account-password'); await h.runtime.unlock('passphrase')
    h.bootstrap.runReadyCycle.mockClear()
    await h.runtime.lock()
    await expect(h.runtime.retry()).rejects.toBeInstanceOf(KeyNotProvisionedError)
    expect(h.bootstrap.runReadyCycle).not.toHaveBeenCalled()

    h.activate(); await h.runtime.logout(); await h.runtime.login('user', 'account-password')
    await expect(h.userAuth.authorized(async () => { throw new ApiError(401, 'expired', 'expired') })).rejects.toBeInstanceOf(ApiError)
    await expect(h.runtime.retry()).rejects.toThrow()
    expect(h.identity.provision).toHaveBeenCalledWith(USER)
  })

  it('disposes key resources once and prevents future session operations', async () => {
    const h = harness(); await h.runtime.dispose(); await h.runtime.dispose()
    expect(h.keys.dispose).toHaveBeenCalledTimes(1)
    await expect(h.runtime.login('user', 'account-password')).rejects.toBeInstanceOf(NoteSyncRuntimeDisposedError)
  })
})
