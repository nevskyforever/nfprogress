import { ApiError } from '@/api/client'
import {
  accountCryptoApi,
  type AccountCryptoProvisioningTransport,
  type CurrentUserCryptoRecord,
  type InitialAccountCryptoProvisioningRequest,
  type PasswordWrappedAmkWireRecord,
  type RecoveryWrappedAmkWireRecord,
} from '@/api/accountCrypto'
import { encodeBase64Url } from '@/api/base64url'
import { NormalUserAuthRuntime, StaleAuthContextError } from '@/auth/userAuth'
import {
  generateAccountMasterKey,
  generateRecoveryKey,
  wrapAmkWithPassphrase,
  wrapAmkWithRecoveryKey,
  type PasswordWrappedAmkRecord,
  type RecoveryWrappedAmkRecord,
  type RecoveryKey,
} from '@/crypto'

export class AccountCryptoAlreadyProvisionedError extends Error {
  readonly name = 'AccountCryptoAlreadyProvisionedError'
  constructor() { super('Account encryption is already provisioned.') }
}

export class AccountCryptoProvisioningConflictError extends Error {
  readonly name = 'AccountCryptoProvisioningConflictError'
  constructor() { super('Account encryption was provisioned with a different key record.') }
}

export class RecoveryKeyConfirmationRequiredError extends Error {
  readonly name = 'RecoveryKeyConfirmationRequiredError'
  constructor() { super('Recovery Key confirmation is required before provisioning.') }
}

export class AccountCryptoProvisioningDisposedError extends Error {
  readonly name = 'AccountCryptoProvisioningDisposedError'
  constructor() { super('Account encryption provisioning context is no longer available.') }
}

function passwordWire(record: PasswordWrappedAmkRecord): PasswordWrappedAmkWireRecord {
  return {
    crypto_version: record.crypto_version,
    wrapping_version: record.wrapping_version,
    kdf: {
      kdf_version: record.kdf.kdf_version,
      algorithm: record.kdf.algorithm,
      salt: encodeBase64Url(record.kdf.salt),
      opslimit: record.kdf.opslimit,
      memlimit: record.kdf.memlimit,
    },
    nonce: encodeBase64Url(record.nonce),
    ciphertext: encodeBase64Url(record.ciphertext),
  }
}

function recoveryWire(record: RecoveryWrappedAmkRecord): RecoveryWrappedAmkWireRecord {
  return {
    crypto_version: record.crypto_version,
    wrapping_version: record.wrapping_version,
    nonce: encodeBase64Url(record.nonce),
    ciphertext: encodeBase64Url(record.ciphertext),
  }
}

function samePassword(left: PasswordWrappedAmkWireRecord, right: PasswordWrappedAmkWireRecord): boolean {
  return left.crypto_version === right.crypto_version
    && left.wrapping_version === right.wrapping_version
    && left.kdf.kdf_version === right.kdf.kdf_version
    && left.kdf.algorithm === right.kdf.algorithm
    && left.kdf.salt === right.kdf.salt
    && left.kdf.opslimit === right.kdf.opslimit
    && left.kdf.memlimit === right.kdf.memlimit
    && left.nonce === right.nonce
    && left.ciphertext === right.ciphertext
}

function sameRecovery(left: RecoveryWrappedAmkWireRecord, right: RecoveryWrappedAmkWireRecord): boolean {
  return left.crypto_version === right.crypto_version
    && left.wrapping_version === right.wrapping_version
    && left.nonce === right.nonce
    && left.ciphertext === right.ciphertext
}

function matchesRequest(record: CurrentUserCryptoRecord, request: InitialAccountCryptoProvisioningRequest): boolean {
  return record.provisioned && record.recovery !== null
    && samePassword(record.password, request.password)
    && sameRecovery(record.recovery, request.recovery)
}

/**
 * Transient client-only first-provisioning context. Its Recovery Key is exposed
 * solely as a caller-owned copy for a future UI to display before confirmation.
 */
export class PendingAccountCryptoProvisioning {
  private confirmed = false
  private disposed = false

  private constructor(
    private readonly recoveryKey: RecoveryKey,
    private readonly passwordRecord: PasswordWrappedAmkRecord,
    private readonly recoveryRecord: RecoveryWrappedAmkRecord,
  ) {}

  static async begin(
    auth: NormalUserAuthRuntime,
    encryptionPassword: string,
    transport: AccountCryptoProvisioningTransport = accountCryptoApi,
  ): Promise<PendingAccountCryptoProvisioning> {
    const existing = await auth.authorized(accessToken => transport.get(accessToken))
    if (existing.value.provisioned) throw new AccountCryptoAlreadyProvisionedError()

    const amk = await generateAccountMasterKey()
    let recoveryKey: RecoveryKey | null = null
    let passwordRecord: PasswordWrappedAmkRecord | null = null
    let recoveryRecord: RecoveryWrappedAmkRecord | null = null
    try {
      recoveryKey = await generateRecoveryKey()
      passwordRecord = await wrapAmkWithPassphrase(amk, encryptionPassword)
      recoveryRecord = await wrapAmkWithRecoveryKey(amk, recoveryKey)
      if (!auth.isCurrent(existing.context)) throw new StaleAuthContextError()
      return new PendingAccountCryptoProvisioning(recoveryKey, passwordRecord, recoveryRecord)
    } catch (error) {
      recoveryKey?.fill(0)
      passwordRecord?.kdf.salt.fill(0)
      passwordRecord?.nonce.fill(0)
      passwordRecord?.ciphertext.fill(0)
      recoveryRecord?.nonce.fill(0)
      recoveryRecord?.ciphertext.fill(0)
      throw error
    } finally {
      amk.fill(0)
    }
  }

  /** Returns a caller-owned display copy. Callers must not persist or log it. */
  recoveryKeyForDisplay(): Uint8Array {
    this.assertAvailable()
    return Uint8Array.from(this.recoveryKey)
  }

  confirmRecoveryKeySaved(): void {
    this.assertAvailable()
    this.confirmed = true
  }

  async submit(
    auth: NormalUserAuthRuntime,
    transport: AccountCryptoProvisioningTransport = accountCryptoApi,
  ): Promise<CurrentUserCryptoRecord> {
    this.assertAvailable()
    if (!this.confirmed) throw new RecoveryKeyConfirmationRequiredError()
    const request = this.request()
    try {
      const submitted = await auth.authorized(accessToken => transport.provision(accessToken, request))
      if (!matchesRequest(submitted.value, request)) throw new AccountCryptoProvisioningConflictError()
      this.dispose()
      return submitted.value
    } catch (error) {
      if (error instanceof ApiError && (error.status === 0 || error.status === 409)) {
        const reconciled = await this.reconcileAfterUnknownOutcome(auth, transport, request, error)
        if (reconciled !== null) return reconciled
      }
      throw error
    }
  }

  /** Re-check a retained immutable request; it never creates a replacement AMK. */
  async reconcile(
    auth: NormalUserAuthRuntime,
    transport: AccountCryptoProvisioningTransport = accountCryptoApi,
  ): Promise<CurrentUserCryptoRecord | null> {
    this.assertAvailable()
    return this.reconcileAfterUnknownOutcome(auth, transport, this.request(), null)
  }

  dispose(): void {
    if (this.disposed) return
    this.disposed = true
    this.recoveryKey.fill(0)
    this.passwordRecord.kdf.salt.fill(0)
    this.passwordRecord.nonce.fill(0)
    this.passwordRecord.ciphertext.fill(0)
    this.recoveryRecord.nonce.fill(0)
    this.recoveryRecord.ciphertext.fill(0)
  }

  private async reconcileAfterUnknownOutcome(
    auth: NormalUserAuthRuntime,
    transport: AccountCryptoProvisioningTransport,
    request: InitialAccountCryptoProvisioningRequest,
    originalError: ApiError | null,
  ): Promise<CurrentUserCryptoRecord | null> {
    let fetched: { value: CurrentUserCryptoRecord }
    try {
      fetched = await auth.authorized(accessToken => transport.get(accessToken))
    } catch (error) {
      if (originalError !== null) throw originalError
      throw error
    }
    if (!fetched.value.provisioned) return null
    if (!matchesRequest(fetched.value, request)) throw new AccountCryptoProvisioningConflictError()
    this.dispose()
    return fetched.value
  }

  private request(): InitialAccountCryptoProvisioningRequest {
    return { password: passwordWire(this.passwordRecord), recovery: recoveryWire(this.recoveryRecord) }
  }

  private assertAvailable(): void {
    if (this.disposed) throw new AccountCryptoProvisioningDisposedError()
  }
}
