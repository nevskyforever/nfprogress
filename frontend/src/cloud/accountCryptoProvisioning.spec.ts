// @vitest-environment node
import { describe, expect, it, vi } from 'vitest'

import { ApiError } from '@/api/client'
import { decodeBase64Url } from '@/api/base64url'
import type {
  AccountCryptoProvisioningTransport,
  CurrentUserCryptoRecord,
  InitialAccountCryptoProvisioningRequest,
} from '@/api/accountCrypto'
import { unwrapAmkWithPassphrase, unwrapAmkWithRecoveryKey } from '@/crypto'
import { NormalUserAuthRuntime } from '@/auth/userAuth'
import {
  AccountCryptoAlreadyProvisionedError,
  AccountCryptoProvisioningConflictError,
  PendingAccountCryptoProvisioning,
  RecoveryKeyConfirmationRequiredError,
} from './accountCryptoProvisioning'

const USER = '123e4567-e89b-42d3-a456-426614174099'

function auth(): NormalUserAuthRuntime {
  return new NormalUserAuthRuntime({
    login: vi.fn().mockResolvedValue({ access_token: 'access', refresh_token: 'refresh', access_expires_in: 60 }),
    refresh: vi.fn(),
    logout: vi.fn().mockResolvedValue(undefined),
    me: vi.fn().mockResolvedValue({ id: USER, username: 'writer', email: 'writer@example.test', email_verified: true, role: 'user', status: 'active', created_at: 'now' }),
  })
}

function empty(): CurrentUserCryptoRecord {
  return { provisioned: false, password: null, recovery: null }
}

function stored(request: InitialAccountCryptoProvisioningRequest): CurrentUserCryptoRecord {
  return { provisioned: true, password: request.password, recovery: request.recovery }
}

function transport(state: { record: CurrentUserCryptoRecord }): AccountCryptoProvisioningTransport {
  return {
    get: vi.fn(async () => state.record),
    provision: vi.fn(async (_token, request) => {
      if (!state.record.provisioned) state.record = stored(request)
      return state.record
    }),
  }
}

function passwordRecord(request: InitialAccountCryptoProvisioningRequest) {
  return {
    crypto_version: request.password.crypto_version as 1,
    wrapping_version: request.password.wrapping_version as 1,
    kdf: {
      kdf_version: request.password.kdf.kdf_version as 1,
      algorithm: request.password.kdf.algorithm as 'argon2id13',
      salt: decodeBase64Url(request.password.kdf.salt, { expectedLength: 16 }),
      opslimit: request.password.kdf.opslimit,
      memlimit: request.password.kdf.memlimit,
    },
    nonce: decodeBase64Url(request.password.nonce, { expectedLength: 24 }),
    ciphertext: decodeBase64Url(request.password.ciphertext, { expectedLength: 48 }),
  }
}

function recoveryRecord(request: InitialAccountCryptoProvisioningRequest) {
  return {
    crypto_version: request.recovery.crypto_version as 1,
    wrapping_version: request.recovery.wrapping_version as 1,
    nonce: decodeBase64Url(request.recovery.nonce, { expectedLength: 24 }),
    ciphertext: decodeBase64Url(request.recovery.ciphertext, { expectedLength: 48 }),
  }
}

describe('initial account crypto provisioning', () => {
  it('wraps one generated AMK with independent password and Recovery Key records', async () => {
    const userAuth = auth(); await userAuth.login('writer', 'account-password')
    const state = { record: empty() }
    const api = transport(state)
    const pending = await PendingAccountCryptoProvisioning.begin(userAuth, 'encryption-password', api)
    const recoveryKey = pending.recoveryKeyForDisplay()
    expect(api.provision).not.toHaveBeenCalled()
    pending.confirmRecoveryKeySaved()
    await pending.submit(userAuth, api)

    const request = (api.provision as ReturnType<typeof vi.fn>).mock.calls[0]![1] as InitialAccountCryptoProvisioningRequest
    const byPassword = await unwrapAmkWithPassphrase('encryption-password', passwordRecord(request))
    const byRecovery = await unwrapAmkWithRecoveryKey(recoveryKey as never, recoveryRecord(request))
    expect(byPassword).toEqual(byRecovery)
    byPassword.fill(0); byRecovery.fill(0); recoveryKey.fill(0)
  })

  it('does not send wrappers before explicit Recovery Key confirmation', async () => {
    const userAuth = auth(); await userAuth.login('writer', 'account-password')
    const api = transport({ record: empty() })
    const pending = await PendingAccountCryptoProvisioning.begin(userAuth, 'encryption-password', api)
    await expect(pending.submit(userAuth, api)).rejects.toBeInstanceOf(RecoveryKeyConfirmationRequiredError)
    expect(api.provision).not.toHaveBeenCalled()
    pending.dispose()
  })

  it('reconciles a lost POST response only against the same immutable record', async () => {
    const userAuth = auth(); await userAuth.login('writer', 'account-password')
    const state = { record: empty() }
    const api = transport(state)
    ;(api.provision as ReturnType<typeof vi.fn>).mockImplementationOnce(async (_token, request) => {
      state.record = stored(request)
      throw new ApiError(0, 'network_error', 'network unavailable')
    })
    const pending = await PendingAccountCryptoProvisioning.begin(userAuth, 'encryption-password', api)
    pending.confirmRecoveryKeySaved()
    await expect(pending.submit(userAuth, api)).resolves.toEqual(state.record)
    expect(api.get).toHaveBeenCalledTimes(2)
    expect(api.provision).toHaveBeenCalledTimes(1)
  })

  it('retries the exact retained wrapper set when a lost request was not committed', async () => {
    const userAuth = auth(); await userAuth.login('writer', 'account-password')
    const state = { record: empty() }
    const api = transport(state)
    ;(api.provision as ReturnType<typeof vi.fn>).mockImplementationOnce(async () => {
      throw new ApiError(0, 'network_error', 'network unavailable')
    })
    const pending = await PendingAccountCryptoProvisioning.begin(userAuth, 'encryption-password', api)
    pending.confirmRecoveryKeySaved()
    await expect(pending.submit(userAuth, api)).rejects.toMatchObject({ status: 0 })
    await expect(pending.submit(userAuth, api)).resolves.toMatchObject({ provisioned: true })
    const first = (api.provision as ReturnType<typeof vi.fn>).mock.calls[0]![1]
    const second = (api.provision as ReturnType<typeof vi.fn>).mock.calls[1]![1]
    expect(second).toEqual(first)
  })

  it('fails closed for a different persisted wrapper set and does not generate over an existing account', async () => {
    const userAuth = auth(); await userAuth.login('writer', 'account-password')
    const state = { record: empty() }
    const api = transport(state)
    const pending = await PendingAccountCryptoProvisioning.begin(userAuth, 'secret-that-must-not-leak', api)
    pending.confirmRecoveryKeySaved()
    ;(api.provision as ReturnType<typeof vi.fn>).mockImplementationOnce(async () => {
      state.record = {
        provisioned: true,
        password: { crypto_version: 1, wrapping_version: 1, kdf: { kdf_version: 1, algorithm: 'argon2id13', salt: 'AAAAAAAAAAAAAAAAAAAAAA', opslimit: 2, memlimit: 67_108_864 }, nonce: 'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA', ciphertext: 'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA' },
        recovery: { crypto_version: 1, wrapping_version: 1, nonce: 'AQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEB', ciphertext: 'AQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEB' },
      }
      throw new ApiError(409, 'crypto_already_provisioned', 'existing')
    })
    await expect(pending.submit(userAuth, api)).rejects.toBeInstanceOf(AccountCryptoProvisioningConflictError)
    await expect(PendingAccountCryptoProvisioning.begin(userAuth, 'other-password', api)).rejects.toBeInstanceOf(AccountCryptoAlreadyProvisionedError)
    try {
      await pending.reconcile(userAuth, api)
    } catch (error) {
      expect((error as Error).message).not.toContain('secret-that-must-not-leak')
    }
    pending.dispose()
  })

  it('fails stale auth during POST and zeroes controlled transient buffers on disposal', async () => {
    const userAuth = auth(); await userAuth.login('writer', 'account-password')
    const api = transport({ record: empty() })
    ;(api.provision as ReturnType<typeof vi.fn>).mockImplementationOnce(async () => {
      await userAuth.logout()
      return empty()
    })
    const pending = await PendingAccountCryptoProvisioning.begin(userAuth, 'encryption-password', api)
    pending.confirmRecoveryKeySaved()
    await expect(pending.submit(userAuth, api)).rejects.toThrow()
    pending.dispose()
    const internal = pending as unknown as {
      recoveryKey: Uint8Array
      passwordRecord: { kdf: { salt: Uint8Array }, nonce: Uint8Array, ciphertext: Uint8Array }
      recoveryRecord: { nonce: Uint8Array, ciphertext: Uint8Array }
    }
    for (const bytes of [internal.recoveryKey, internal.passwordRecord.kdf.salt,
      internal.passwordRecord.nonce, internal.passwordRecord.ciphertext,
      internal.recoveryRecord.nonce, internal.recoveryRecord.ciphertext]) {
      expect(bytes.every(value => value === 0)).toBe(true)
    }
  })

  it('does not retain generated key material when auth changes during the initial GET', async () => {
    const userAuth = auth(); await userAuth.login('writer', 'account-password')
    const api: AccountCryptoProvisioningTransport = {
      get: vi.fn(async () => {
        await userAuth.logout()
        return empty()
      }),
      provision: vi.fn(),
    }
    await expect(PendingAccountCryptoProvisioning.begin(userAuth, 'encryption-password', api)).rejects.toThrow()
    expect(api.provision).not.toHaveBeenCalled()
  })
})
