import { accountCryptoApi, type AccountCryptoTransport, type PasswordWrappedAmkWireRecord } from '@/api/accountCrypto'
import { decodeBase64Url } from '@/api/base64url'
import {
  asAccountMasterKey,
  unwrapAmkWithPassphrase,
  type AccountMasterKey,
  type PasswordWrappedAmkRecord,
} from '@/crypto'
import { AuthoritativeAccountBinding } from './accountBinding'
import { NormalUserAuthRuntime, StaleAuthContextError } from './userAuth'

export interface KeyContextIdentity {
  readonly localAccountId: string
  readonly canonicalUserId: string
  readonly authEpoch: number
  readonly keyContextId: string
  readonly keyEpoch: number
}

export interface AuthoritativeKeyContextLease extends KeyContextIdentity {
  isCurrent(): boolean
  use<T>(operation: (masterKey: AccountMasterKey) => Promise<T>): Promise<T>
}

export class KeyNotProvisionedError extends Error {
  readonly name = 'KeyNotProvisionedError'
}

interface ActiveKeyContext extends KeyContextIdentity {
  masterKey: AccountMasterKey
}

function passwordRecord(value: PasswordWrappedAmkWireRecord): PasswordWrappedAmkRecord {
  if (value.crypto_version !== 1 || value.wrapping_version !== 1
    || value.kdf.kdf_version !== 1 || value.kdf.algorithm !== 'argon2id13') {
    throw new TypeError('Unsupported wrapped AMK record.')
  }
  return {
    crypto_version: 1,
    wrapping_version: 1,
    kdf: {
      kdf_version: 1,
      algorithm: 'argon2id13',
      salt: decodeBase64Url(value.kdf.salt, { expectedLength: 16 }),
      opslimit: value.kdf.opslimit,
      memlimit: value.kdf.memlimit,
    },
    nonce: decodeBase64Url(value.nonce, { expectedLength: 24 }),
    ciphertext: decodeBase64Url(value.ciphertext, { expectedLength: 48 }),
  }
}

async function keyContextId(userId: string, record: PasswordWrappedAmkWireRecord): Promise<string> {
  const canonical = JSON.stringify([
    'worta/key-context/v1', userId,
    record.crypto_version, record.wrapping_version,
    record.kdf.kdf_version, record.kdf.algorithm, record.kdf.salt,
    record.kdf.opslimit, record.kdf.memlimit, record.nonce, record.ciphertext,
  ])
  const digest = new Uint8Array(await globalThis.crypto.subtle.digest(
    'SHA-256', new TextEncoder().encode(canonical),
  ))
  return Array.from(digest, byte => byte.toString(16).padStart(2, '0')).join('')
}

class RuntimeKeyContextLease implements AuthoritativeKeyContextLease {
  constructor(
    private readonly runtime: RuntimeKeyContext,
    private readonly identity: KeyContextIdentity,
  ) {}

  get localAccountId(): string { return this.identity.localAccountId }
  get canonicalUserId(): string { return this.identity.canonicalUserId }
  get authEpoch(): number { return this.identity.authEpoch }
  get keyContextId(): string { return this.identity.keyContextId }
  get keyEpoch(): number { return this.identity.keyEpoch }

  isCurrent(): boolean {
    return this.runtime.isCurrent(this.identity)
  }

  async use<T>(operation: (masterKey: AccountMasterKey) => Promise<T>): Promise<T> {
    const masterKey = this.runtime.copyMasterKey(this.identity)
    try {
      return await operation(masterKey)
    } finally {
      masterKey.fill(0)
    }
  }
}

export class RuntimeKeyContext {
  private active: ActiveKeyContext | null = null
  private epoch = 0
  private readonly unsubscribe: () => void

  constructor(
    private readonly auth: NormalUserAuthRuntime,
    private readonly bindings: AuthoritativeAccountBinding,
    private readonly cryptoTransport: AccountCryptoTransport = accountCryptoApi,
  ) {
    this.unsubscribe = auth.onInvalidated(() => this.lock())
  }

  get keyEpoch(): number { return this.epoch }

  lock(): void {
    this.active?.masterKey.fill(0)
    this.active = null
    this.epoch += 1
  }

  dispose(): void {
    this.unsubscribe()
    this.lock()
  }

  async unlockWithPassphrase(localAccountId: string, passphrase: string): Promise<AuthoritativeKeyContextLease> {
    this.lock()
    const binding = await this.bindings.ensureForCurrentUser(localAccountId)
    const fetched = await this.auth.authorized(accessToken => this.cryptoTransport.get(accessToken))
    if (binding.context.authEpoch !== fetched.context.authEpoch
      || binding.context.userId !== fetched.context.userId) {
      throw new StaleAuthContextError()
    }
    if (!fetched.value.provisioned) throw new KeyNotProvisionedError()
    const contextId = await keyContextId(fetched.context.userId, fetched.value.password)
    const masterKey = await unwrapAmkWithPassphrase(passphrase, passwordRecord(fetched.value.password))
    if (!this.auth.isCurrent(fetched.context)) {
      masterKey.fill(0)
      throw new StaleAuthContextError()
    }
    this.epoch += 1
    const active: ActiveKeyContext = {
      localAccountId,
      canonicalUserId: fetched.context.userId,
      authEpoch: fetched.context.authEpoch,
      keyContextId: contextId,
      keyEpoch: this.epoch,
      masterKey,
    }
    this.active = active
    return new RuntimeKeyContextLease(this, active)
  }

  isCurrent(identity: KeyContextIdentity): boolean {
    return this.active !== null
      && this.active.keyEpoch === identity.keyEpoch
      && this.active.authEpoch === identity.authEpoch
      && this.active.localAccountId === identity.localAccountId
      && this.active.canonicalUserId === identity.canonicalUserId
      && this.active.keyContextId === identity.keyContextId
      && this.auth.isCurrent({
        userId: identity.canonicalUserId,
        username: '',
        authEpoch: identity.authEpoch,
      })
  }

  copyMasterKey(identity: KeyContextIdentity): AccountMasterKey {
    if (!this.isCurrent(identity) || this.active === null) throw new StaleAuthContextError()
    return asAccountMasterKey(Uint8Array.from(this.active.masterKey))
  }
}
