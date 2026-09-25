import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

vi.mock('@/platform/runtime', () => ({ currentPlatform: vi.fn(() => 'tauri') }))

import type { CurrentUserCryptoRecord } from '@/api/accountCrypto'
import { ApiError } from '@/api/client'
import { currentPlatform } from '@/platform/runtime'
import type { PendingAccountCryptoProvisioning } from '@/cloud/accountCryptoProvisioning'
import { AccountCryptoProvisioningConflictError } from '@/cloud/accountCryptoProvisioning'
import type { NoteSyncOrchestratorResult } from '@/cloud/noteSyncOrchestrator'
import type { CloudProjectBootstrapProgress, CloudRegistryReconciliation } from '@/cloud/projectBootstrap'
import type { CloudProjectBootstrapRecord } from '@/infrastructure/sqlite/cloudProjectBootstrapRepository'
import {
  configureCloudSessionProjectLoaderForTests,
  configureCloudSessionRuntimeFactoryForTests,
  useCloudSessionStore,
  type CloudSessionRuntime,
} from './cloudSession'

const PROVISIONED: CurrentUserCryptoRecord = {
  provisioned: true,
  password: {
    crypto_version: 1, wrapping_version: 1,
    kdf: { kdf_version: 1, algorithm: 'argon2id13', salt: 'salt', opslimit: 2, memlimit: 67108864 },
    nonce: 'nonce', ciphertext: 'ciphertext',
  },
  recovery: { crypto_version: 1, wrapping_version: 1, nonce: 'recovery-nonce', ciphertext: 'recovery-ciphertext' },
}
const UNPROVISIONED: CurrentUserCryptoRecord = { provisioned: false, password: null, recovery: null }
const EMPTY_CYCLE: NoteSyncOrchestratorResult = {
  stages: [], sealed: [], uploaded: 0, pulled: [], applied: [], blocked: [], errors: [], hasRemainingWork: false,
}
const READY_REGISTRY = { readyForCycle: true, readyForNormalCycle: true, reasons: [], remote: [], local: [], currentCursor: 0 }
const PROJECT = '123e4567-e89b-42d3-a456-426614174010'
const DEVICE = '123e4567-e89b-42d3-a456-426614174001'
const TOKEN = '123e4567-e89b-42d3-a456-426614174020'

function bootstrapRecord(phase: CloudProjectBootstrapRecord['phase'] = 'ready', mode: CloudProjectBootstrapRecord['mode'] = 'upload_existing'): CloudProjectBootstrapRecord {
  return {
    project_id: PROJECT, account_id: 'local-account', device_id: DEVICE,
    bootstrap_id: TOKEN, mode, phase, remote_state: 'active',
    initial_event_count: 1, initial_local_ordinal_hi: 1, remote_high_water: 1,
    initial_max_server_sequence: 1, blocked_reason: null,
  }
}

function registry(options: Partial<CloudRegistryReconciliation> = {}): CloudRegistryReconciliation {
  return {
    readyForCycle: true, readyForNormalCycle: true, reasons: [], remote: [], local: [], currentCursor: 0,
    ...options,
  }
}

function progress(value: CloudRegistryReconciliation, record = bootstrapRecord()): CloudProjectBootstrapProgress {
  return { project: record, registry: value, cycle: EMPTY_CYCLE, hasRemainingWork: false }
}

function pending(): PendingAccountCryptoProvisioning {
  return {
    recoveryKeyForDisplay: vi.fn(() => new Uint8Array([1, 2, 3])),
    confirmRecoveryKeySaved: vi.fn(),
    dispose: vi.fn(),
  } as unknown as PendingAccountCryptoProvisioning
}

function deferred<T>() {
  let resolve!: (value: T) => void
  const promise = new Promise<T>(done => { resolve = done })
  return { promise, resolve }
}

function runtime(record: CurrentUserCryptoRecord = PROVISIONED): CloudSessionRuntime {
  const prepared = pending()
  return {
    login: vi.fn().mockResolvedValue({ context: { username: 'normal-user' } }),
    cryptoRecord: vi.fn().mockResolvedValue(record),
    beginCryptoProvisioning: vi.fn().mockResolvedValue(prepared),
    submitCryptoProvisioning: vi.fn().mockResolvedValue(PROVISIONED),
    reconcileCryptoProvisioning: vi.fn().mockResolvedValue(null),
    unlock: vi.fn().mockResolvedValue({ identity: {}, registry: READY_REGISTRY }),
    reconcileProjects: vi.fn().mockResolvedValue(READY_REGISTRY),
    preflightLocalProject: vi.fn().mockResolvedValue([]),
    bootstrapLocalProject: vi.fn(),
    importRemoteProject: vi.fn(),
    setProjectPaused: vi.fn().mockResolvedValue(READY_REGISTRY),
    retry: vi.fn().mockResolvedValue(EMPTY_CYCLE),
    lock: vi.fn().mockResolvedValue(undefined),
    logout: vi.fn().mockResolvedValue(undefined),
    dispose: vi.fn().mockResolvedValue(undefined),
  }
}

describe('desktop cloud session owner', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    configureCloudSessionRuntimeFactoryForTests(null)
    configureCloudSessionProjectLoaderForTests(async () => [])
    vi.mocked(currentPlatform).mockReturnValue('tauri')
  })

  it('constructs exactly one desktop runtime and exposes no transient key material in Pinia state', () => {
    const instance = runtime()
    const factory = vi.fn(() => instance)
    configureCloudSessionRuntimeFactoryForTests(factory)
    const store = useCloudSessionStore()

    store.initialize(); store.initialize()

    expect(factory).toHaveBeenCalledTimes(1)
    expect(store.status).toBe('logged_out')
    expect(Object.keys(store.$state)).not.toEqual(expect.arrayContaining([
      'runtime', 'pending', 'recoveryKey', 'encryptionPassword', 'accountPassword', 'amk', 'kek',
    ]))
  })

  it('does not construct a cloud runtime outside Tauri', () => {
    vi.mocked(currentPlatform).mockReturnValue('web')
    const factory = vi.fn(() => runtime())
    configureCloudSessionRuntimeFactoryForTests(factory)
    const store = useCloudSessionStore()
    store.initialize()
    expect(factory).not.toHaveBeenCalled()
    expect(store.status).toBe('unavailable')
  })

  it('orders login, Recovery Key confirmation, then immutable provisioning POST', async () => {
    const instance = runtime(UNPROVISIONED)
    configureCloudSessionRuntimeFactoryForTests(() => instance)
    const store = useCloudSessionStore(); store.initialize()

    await store.login('normal-user', 'account-password')
    expect(store.status).toBe('provisioning')
    const display = await store.prepareProvisioning('separate-e2ee-password')
    expect(display).toEqual(new Uint8Array([1, 2, 3]))
    expect(instance.submitCryptoProvisioning).not.toHaveBeenCalled()

    await store.submitProvisioning()
    expect((instance.beginCryptoProvisioning as ReturnType<typeof vi.fn>).mock.invocationCallOrder[0]!)
      .toBeLessThan((instance.submitCryptoProvisioning as ReturnType<typeof vi.fn>).mock.invocationCallOrder[0]!)
    expect(store.status).toBe('key_locked')
    expect(store.hasProvisionedKey).toBe(true)
  })

  it('keeps the pending immutable request for a safe lost-response retry and blocks conflicting state', async () => {
    const instance = runtime(UNPROVISIONED)
    const retained = pending()
    ;(instance.beginCryptoProvisioning as ReturnType<typeof vi.fn>).mockResolvedValue(retained)
    ;(instance.submitCryptoProvisioning as ReturnType<typeof vi.fn>)
      .mockRejectedValueOnce(new Error('network unknown'))
      .mockResolvedValueOnce(PROVISIONED)
    configureCloudSessionRuntimeFactoryForTests(() => instance)
    const store = useCloudSessionStore(); store.initialize()
    await store.login('normal-user', 'account-password')
    await store.prepareProvisioning('separate-e2ee-password')

    await expect(store.submitProvisioning()).rejects.toThrow('network unknown')
    await store.submitProvisioning()
    expect(instance.beginCryptoProvisioning).toHaveBeenCalledTimes(1)
    expect(instance.submitCryptoProvisioning).toHaveBeenCalledTimes(2)
    expect(store.status).toBe('key_locked')
  })

  it('locks and invalidates the visible session after a 401 without retaining onboarding material', async () => {
    const instance = runtime(UNPROVISIONED)
    const retained = pending()
    ;(instance.beginCryptoProvisioning as ReturnType<typeof vi.fn>).mockResolvedValue(retained)
    ;(instance.submitCryptoProvisioning as ReturnType<typeof vi.fn>).mockRejectedValue(new ApiError(401, 'unauthorized', 'expired'))
    configureCloudSessionRuntimeFactoryForTests(() => instance)
    const store = useCloudSessionStore(); store.initialize()
    await store.login('normal-user', 'account-password')
    await store.prepareProvisioning('separate-e2ee-password')

    await expect(store.submitProvisioning()).rejects.toBeDefined()
    expect(store.status).toBe('logged_out')
    expect(store.username).toBeNull()
    expect(store.busy).toBe(false)
    expect(retained.dispose).toHaveBeenCalled()
  })

  it('disposes a pending setup on logout or account switch and surfaces immutable conflicts as blocked', async () => {
    const instance = runtime(UNPROVISIONED)
    const retained = pending()
    ;(instance.beginCryptoProvisioning as ReturnType<typeof vi.fn>).mockResolvedValue(retained)
    configureCloudSessionRuntimeFactoryForTests(() => instance)
    const store = useCloudSessionStore(); store.initialize()
    await store.login('first-user', 'account-password')
    await store.prepareProvisioning('separate-e2ee-password')
    await store.login('second-user', 'account-password')
    expect(retained.dispose).toHaveBeenCalled()

    const conflicting = pending()
    ;(instance.beginCryptoProvisioning as ReturnType<typeof vi.fn>).mockResolvedValue(conflicting)
    ;(instance.submitCryptoProvisioning as ReturnType<typeof vi.fn>)
      .mockRejectedValue(new AccountCryptoProvisioningConflictError())
    await store.prepareProvisioning('second-e2ee-password')
    await expect(store.submitProvisioning()).rejects.toBeInstanceOf(AccountCryptoProvisioningConflictError)
    expect(store.status).toBe('blocked')
    await store.logout()
    expect(conflicting.dispose).toHaveBeenCalled()
    expect(store.status).toBe('logged_out')
  })

  it('uses a single flight and reports bounded-cycle status without claiming global sync', async () => {
    const instance = runtime()
    let resolve!: (value: NoteSyncOrchestratorResult) => void
    ;(instance.retry as ReturnType<typeof vi.fn>).mockImplementation(() => new Promise(done => { resolve = done }))
    configureCloudSessionRuntimeFactoryForTests(() => instance)
    const store = useCloudSessionStore(); store.initialize()
    await store.login('normal-user', 'account-password')

    const first = store.retry(); const second = store.retry()
    expect(instance.retry).toHaveBeenCalledTimes(1)
    resolve({ ...EMPTY_CYCLE, hasRemainingWork: true })
    await Promise.all([first, second])
    expect(store.status).toBe('remaining_work')
    expect(store.hasRemainingWork).toBe(true)
  })

  it('does not start a cycle on unlock and exposes an unreconciled registry as blocked', async () => {
    const instance = runtime()
    ;(instance.unlock as ReturnType<typeof vi.fn>).mockResolvedValue({
      identity: {}, registry: {
        ...READY_REGISTRY, readyForCycle: false, readyForNormalCycle: false,
        reasons: ['missing_local_binding:remote-project'],
      },
    })
    configureCloudSessionRuntimeFactoryForTests(() => instance)
    const store = useCloudSessionStore(); store.initialize()
    await store.login('normal-user', 'account-password')
    await store.unlock('separate-e2ee-password')

    expect(instance.retry).not.toHaveBeenCalled()
    expect(store.status).toBe('blocked')
    expect(store.blockedEvents).toEqual(['Удалённый проект ещё не импортирован на это устройство.'])
    expect(store.lastCycleAt).toBeNull()
  })

  it('keeps projects local-only until native preflight and a separate explicit confirmation', async () => {
    const instance = runtime()
    const ready = registry({
      remote: [{ project_id: PROJECT, bootstrap_id: TOKEN, origin_device_id: DEVICE, state: 'active', initial_event_count: 1, initial_max_server_sequence: 1 }],
      local: [bootstrapRecord()],
    })
    ;(instance.bootstrapLocalProject as ReturnType<typeof vi.fn>).mockResolvedValue(progress(ready))
    configureCloudSessionRuntimeFactoryForTests(() => instance)
    configureCloudSessionProjectLoaderForTests(async () => [{ id: PROJECT, name: 'Роман' }])
    const store = useCloudSessionStore(); store.initialize()
    await store.login('normal-user', 'account-password')
    await store.unlock('e2ee-password')

    expect(store.projects).toMatchObject([{ projectId: PROJECT, status: 'local_only', connectionAvailable: true }])
    expect(instance.bootstrapLocalProject).not.toHaveBeenCalled()
    await expect(store.prepareProjectConnection(PROJECT)).resolves.toBe(true)
    expect(instance.preflightLocalProject).toHaveBeenCalledWith(PROJECT)
    expect(instance.bootstrapLocalProject).not.toHaveBeenCalled()

    await store.bootstrapProject(PROJECT)
    expect(instance.bootstrapLocalProject).toHaveBeenCalledTimes(1)
    expect(store.projects).toMatchObject([{ projectId: PROJECT, status: 'initial_sync_completed' }])
    expect(JSON.stringify(store.$state)).not.toContain(TOKEN)
  })

  it('blocks the whole project before registration when one Note is unsupported', async () => {
    const instance = runtime()
    ;(instance.preflightLocalProject as ReturnType<typeof vi.fn>).mockResolvedValue([
      { note_id: 'note-id', code: 'dependency_not_synced' },
    ])
    configureCloudSessionRuntimeFactoryForTests(() => instance)
    configureCloudSessionProjectLoaderForTests(async () => [{ id: PROJECT, name: 'Роман' }])
    const store = useCloudSessionStore(); store.initialize()
    await store.login('normal-user', 'account-password')
    await store.unlock('e2ee-password')

    expect(store.projects[0]).toMatchObject({ status: 'unsupported', connectionAvailable: false })
    await expect(store.prepareProjectConnection(PROJECT)).resolves.toBe(false)
    expect(instance.bootstrapLocalProject).not.toHaveBeenCalled()
  })

  it('offers explicit second-device import but blocks an unproven same-ID local collision', async () => {
    const remoteRegistry = registry({
      readyForCycle: false, readyForNormalCycle: false,
      reasons: [`missing_local_binding:${PROJECT}`],
      remote: [{ project_id: PROJECT, bootstrap_id: TOKEN, origin_device_id: DEVICE, state: 'active', initial_event_count: 1, initial_max_server_sequence: 1 }],
    })
    const importedRegistry = registry({ remote: remoteRegistry.remote, local: [bootstrapRecord('ready', 'import_remote')] })
    const instance = runtime()
    ;(instance.unlock as ReturnType<typeof vi.fn>).mockResolvedValue({ identity: {}, registry: remoteRegistry })
    ;(instance.importRemoteProject as ReturnType<typeof vi.fn>).mockResolvedValue(progress(importedRegistry, bootstrapRecord('ready', 'import_remote')))
    let localProjects: Array<{ id: string, name: string }> = []
    configureCloudSessionRuntimeFactoryForTests(() => instance)
    configureCloudSessionProjectLoaderForTests(async () => localProjects)
    const store = useCloudSessionStore(); store.initialize()
    await store.login('normal-user', 'account-password')
    await store.unlock('e2ee-password')
    expect(store.projects[0]).toMatchObject({ origin: 'remote', status: 'import_available' })

    localProjects = [{ id: PROJECT, name: 'Импортированный роман' }]
    await store.importProject(PROJECT, 'Импортированный роман')
    expect(instance.importRemoteProject).toHaveBeenCalledWith(PROJECT, 'Импортированный роман', expect.any(Function))
    expect(store.projects[0]).toMatchObject({ status: 'initial_sync_completed', mode: 'import_remote' })

    const collisionInstance = runtime()
    ;(collisionInstance.unlock as ReturnType<typeof vi.fn>).mockResolvedValue({ identity: {}, registry: remoteRegistry })
    configureCloudSessionRuntimeFactoryForTests(() => collisionInstance)
    configureCloudSessionProjectLoaderForTests(async () => [{ id: PROJECT, name: 'Другой локальный проект' }])
    setActivePinia(createPinia())
    const collision = useCloudSessionStore(); collision.initialize()
    await collision.login('normal-user', 'account-password')
    await collision.unlock('e2ee-password')
    expect(collision.projects[0]).toMatchObject({ status: 'blocked', connectionAvailable: false })
    expect(collision.projects[0]!.reason).toContain('общая история')
    expect(collisionInstance.importRemoteProject).not.toHaveBeenCalled()
  })

  it('keeps one project flight and ignores its stale completion after logout', async () => {
    const instance = runtime()
    configureCloudSessionRuntimeFactoryForTests(() => instance)
    configureCloudSessionProjectLoaderForTests(async () => [{ id: PROJECT, name: 'Роман' }])
    const store = useCloudSessionStore(); store.initialize()
    await store.login('normal-user', 'account-password')
    await store.unlock('e2ee-password')
    const pendingBootstrap = deferred<CloudProjectBootstrapProgress>()
    ;(instance.bootstrapLocalProject as ReturnType<typeof vi.fn>).mockReturnValue(pendingBootstrap.promise)

    const first = store.bootstrapProject(PROJECT)
    const second = store.bootstrapProject(PROJECT)
    expect(instance.bootstrapLocalProject).toHaveBeenCalledTimes(1)
    await store.logout()
    pendingBootstrap.resolve(progress(registry()))
    await Promise.all([first, second])
    expect(store.status).toBe('logged_out')
    expect(store.projects).toEqual([])
  })

  it('does not let an old bootstrap callback overwrite a newly logged-in account', async () => {
    const instance = runtime()
    configureCloudSessionRuntimeFactoryForTests(() => instance)
    configureCloudSessionProjectLoaderForTests(async () => [{ id: PROJECT, name: 'Роман' }])
    const store = useCloudSessionStore(); store.initialize()
    await store.login('first-user', 'account-password')
    await store.unlock('e2ee-password')
    const pendingBootstrap = deferred<CloudProjectBootstrapProgress>()
    ;(instance.bootstrapLocalProject as ReturnType<typeof vi.fn>).mockReturnValue(pendingBootstrap.promise)

    const oldOperation = store.bootstrapProject(PROJECT)
    await store.login('second-user', 'account-password')
    pendingBootstrap.resolve(progress(registry()))
    await oldOperation

    expect(store.username).toBe('normal-user')
    expect(store.status).toBe('key_locked')
    expect(store.projects).toEqual([])
  })

  it('locks stale bootstrap callbacks and invalidates project UI on a 401', async () => {
    const instance = runtime()
    configureCloudSessionRuntimeFactoryForTests(() => instance)
    configureCloudSessionProjectLoaderForTests(async () => [{ id: PROJECT, name: 'Роман' }])
    const store = useCloudSessionStore(); store.initialize()
    await store.login('normal-user', 'account-password')
    await store.unlock('e2ee-password')
    const pendingBootstrap = deferred<CloudProjectBootstrapProgress>()
    ;(instance.bootstrapLocalProject as ReturnType<typeof vi.fn>).mockReturnValueOnce(pendingBootstrap.promise)
    const staleOperation = store.bootstrapProject(PROJECT)
    await store.lock()
    pendingBootstrap.resolve(progress(registry()))
    await staleOperation
    expect(store.status).toBe('key_locked')
    expect(store.projects).toEqual([])

    await store.unlock('e2ee-password')
    ;(instance.bootstrapLocalProject as ReturnType<typeof vi.fn>).mockRejectedValueOnce(
      new ApiError(401, 'unauthorized', 'sensitive server detail'),
    )
    await expect(store.bootstrapProject(PROJECT)).rejects.toBeInstanceOf(ApiError)
    expect(store.status).toBe('logged_out')
    expect(store.username).toBeNull()
    expect(store.errorMessage).toBeNull()
    expect(store.busy).toBe(false)
  })

  it('surfaces paused projects and resumes without deleting durable state', async () => {
    const paused = bootstrapRecord('paused')
    const pausedRegistry = registry({
      readyForCycle: false, readyForNormalCycle: false, reasons: [`paused:${PROJECT}`],
      remote: [{ project_id: PROJECT, bootstrap_id: TOKEN, origin_device_id: DEVICE, state: 'active', initial_event_count: 1, initial_max_server_sequence: 1 }],
      local: [paused],
    })
    const instance = runtime()
    ;(instance.unlock as ReturnType<typeof vi.fn>).mockResolvedValue({ identity: {}, registry: pausedRegistry })
    ;(instance.setProjectPaused as ReturnType<typeof vi.fn>).mockResolvedValue(registry({ remote: pausedRegistry.remote, local: [bootstrapRecord()] }))
    configureCloudSessionRuntimeFactoryForTests(() => instance)
    configureCloudSessionProjectLoaderForTests(async () => [{ id: PROJECT, name: 'Роман' }])
    const store = useCloudSessionStore(); store.initialize()
    await store.login('normal-user', 'account-password')
    await store.unlock('e2ee-password')
    expect(store.projects[0]?.status).toBe('paused')
    await store.resumeProject(PROJECT)
    expect(instance.setProjectPaused).toHaveBeenCalledWith(PROJECT, false)
    expect(store.projects[0]?.status).toBe('initial_sync_completed')
  })
})
