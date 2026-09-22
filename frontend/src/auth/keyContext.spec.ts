import { describe, expect, it, vi } from 'vitest'

import { encodeBase64Url } from '@/api/base64url'
import type { AccountCryptoTransport, CurrentUserCryptoRecord } from '@/api/accountCrypto'
import type { UserAuthTransport } from '@/api/userAuth'
import { generateAccountMasterKey, wrapAmkWithPassphrase } from '@/crypto'
import type { CloudAccountBindingRepository } from '@/infrastructure/sqlite/cloudAccountBindingRepository'
import { AuthoritativeAccountBinding } from './accountBinding'
import { KeyNotProvisionedError, RuntimeKeyContext } from './keyContext'
import { NormalUserAuthRuntime } from './userAuth'

const USER_ONE = '00000000-0000-0000-0000-000000000101'
const USER_TWO = '00000000-0000-0000-0000-000000000102'

function authTransport(): UserAuthTransport {
  return {
    login: vi.fn(async username => ({ access_token: username, refresh_token: `r-${username}`, access_expires_in: 60 })),
    refresh: vi.fn(),
    logout: vi.fn(async () => undefined),
    me: vi.fn(async token => ({ id: token === 'one' ? USER_ONE : USER_TWO, username: token, email: 'u@example.test', email_verified: true, role: 'user', status: 'active', created_at: 'now' })),
  }
}

async function cryptoRecord(passphrase = 'master passphrase'): Promise<{ record: CurrentUserCryptoRecord; amk: Uint8Array }> {
  const amk = await generateAccountMasterKey()
  const wrapped = await wrapAmkWithPassphrase(amk, passphrase)
  return {
    amk,
    record: {
      provisioned: true,
      password: {
        crypto_version: wrapped.crypto_version,
        wrapping_version: wrapped.wrapping_version,
        kdf: { ...wrapped.kdf, salt: encodeBase64Url(wrapped.kdf.salt) },
        nonce: encodeBase64Url(wrapped.nonce),
        ciphertext: encodeBase64Url(wrapped.ciphertext),
      },
      recovery: null,
    },
  }
}

async function runtime(record: CurrentUserCryptoRecord) {
  const auth = new NormalUserAuthRuntime(authTransport())
  await auth.login('one', 'account password')
  const repository: CloudAccountBindingRepository = { ensure: vi.fn(async () => 'validated' as const) }
  const binding = new AuthoritativeAccountBinding(auth, repository)
  const transport: AccountCryptoTransport = { get: vi.fn(async () => record) }
  return { auth, keys: new RuntimeKeyContext(auth, binding, transport), repository, transport }
}

function deferred(): { promise: Promise<void>; resolve: () => void } {
  let resolve!: () => void
  const promise = new Promise<void>(done => { resolve = done })
  return { promise, resolve }
}

describe('runtime-only authoritative key context', () => {
  it('creates a user-bound lease only after authenticated unwrap', async () => {
    const { record, amk } = await cryptoRecord()
    const { keys, repository, transport } = await runtime(record)
    const lease = await keys.unlockWithPassphrase('local-scope', 'master passphrase')

    expect(lease.canonicalUserId).toBe(USER_ONE)
    expect(lease.localAccountId).toBe('local-scope')
    expect(lease.keyContextId).toMatch(/^[0-9a-f]{64}$/)
    expect(lease.isCurrent()).toBe(true)
    await expect(lease.use(async key => Array.from(key))).resolves.toEqual(Array.from(amk))
    expect(repository.ensure).toHaveBeenCalledWith('local-scope', USER_ONE)
    expect(transport.get).toHaveBeenCalledWith('one')
    expect(JSON.stringify(lease)).not.toContain(encodeBase64Url(amk))
  })

  it.each(['wrong passphrase', 'damaged record'] as const)('%s creates no current lease', async scenario => {
    const { record } = await cryptoRecord()
    if (scenario === 'damaged record' && record.provisioned) {
      record.password.ciphertext = encodeBase64Url(new Uint8Array(48).fill(9))
    }
    const { keys } = await runtime(record)
    await expect(keys.unlockWithPassphrase('local-scope', scenario === 'wrong passphrase' ? 'wrong' : 'master passphrase')).rejects.toThrow()
    expect(keys.keyEpoch).toBeGreaterThan(0)
  })

  it('does not provision a missing record', async () => {
    const missing: CurrentUserCryptoRecord = { provisioned: false, password: null, recovery: null }
    const { keys, transport } = await runtime(missing)
    await expect(keys.unlockWithPassphrase('local-scope', 'anything')).rejects.toBeInstanceOf(KeyNotProvisionedError)
    expect(transport.get).toHaveBeenCalledTimes(1)
  })

  it('invalidates leases on key lock, logout, account switch, and subsequent unlock', async () => {
    const { record } = await cryptoRecord()
    const { auth, keys } = await runtime(record)
    const first = await keys.unlockWithPassphrase('local-scope', 'master passphrase')
    await keys.lock()
    expect(first.isCurrent()).toBe(false)
    const second = await keys.unlockWithPassphrase('local-scope', 'master passphrase')
    expect(second.keyEpoch).toBeGreaterThan(first.keyEpoch)
    await auth.logout()
    expect(second.isCurrent()).toBe(false)
    await auth.login('two', 'account password')
    expect(second.isCurrent()).toBe(false)
  })

  it('makes key lock wait for an in-flight lease while rejecting new uses', async () => {
    const { record } = await cryptoRecord()
    const { keys } = await runtime(record)
    const lease = await keys.unlockWithPassphrase('local-scope', 'master passphrase')
    const entered = deferred()
    const release = deferred()
    const operation = lease.use(async () => {
      entered.resolve()
      await release.promise
      return 'committed'
    })
    await entered.promise

    let lockCompleted = false
    const locking = keys.lock().then(() => { lockCompleted = true })
    await Promise.resolve()

    expect(lease.isCurrent()).toBe(false)
    expect(keys.leaseForAccount('local-scope')).toBeNull()
    expect(lockCompleted).toBe(false)
    await expect(lease.use(async () => 'must-not-run')).rejects.toBeInstanceOf(Error)

    release.resolve()
    await expect(operation).resolves.toBe('committed')
    await locking
    expect(lockCompleted).toBe(true)
  })

  it('does not complete logout or account switch before the protected lease drains', async () => {
    const { record } = await cryptoRecord()
    const { auth, keys } = await runtime(record)
    const lease = await keys.unlockWithPassphrase('local-scope', 'master passphrase')
    const entered = deferred()
    const release = deferred()
    const operation = lease.use(async () => {
      entered.resolve()
      await release.promise
    })
    await entered.promise

    let logoutCompleted = false
    const logout = auth.logout().then(() => { logoutCompleted = true })
    await Promise.resolve()
    expect(auth.state).toBe('unauthenticated')
    expect(logoutCompleted).toBe(false)

    release.resolve()
    await operation
    await logout
    expect(logoutCompleted).toBe(true)

    await auth.login('one', 'account password')
    const switchedLease = await keys.unlockWithPassphrase('local-scope', 'master passphrase')
    const switchEntered = deferred()
    const switchRelease = deferred()
    const secondOperation = switchedLease.use(async () => {
      switchEntered.resolve()
      await switchRelease.promise
    })
    await switchEntered.promise

    let switchCompleted = false
    const switching = auth.login('two', 'account password').then(() => { switchCompleted = true })
    await Promise.resolve()
    expect(switchCompleted).toBe(false)
    expect(switchedLease.isCurrent()).toBe(false)

    switchRelease.resolve()
    await secondOperation
    await switching
    expect(switchCompleted).toBe(true)
    expect(auth.requireContext().userId).toBe(USER_TWO)
  })

  it('does not write raw AMK through browser persistence or console APIs', async () => {
    const { record } = await cryptoRecord()
    const { keys } = await runtime(record)
    const storage = vi.spyOn(Storage.prototype, 'setItem')
    const log = vi.spyOn(console, 'log').mockImplementation(() => undefined)
    await keys.unlockWithPassphrase('local-scope', 'master passphrase')
    expect(storage).not.toHaveBeenCalled()
    expect(log).not.toHaveBeenCalled()
  })
})
