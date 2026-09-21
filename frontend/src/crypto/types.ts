import type {
  AAD_VERSION,
  ARGON2ID13,
  CRYPTO_VERSION,
  KDF_VERSION,
  PASSWORD_WRAPPING_VERSION,
  RECOVERY_WRAPPING_VERSION,
} from './constants'

declare const accountMasterKeyBrand: unique symbol
declare const keyEncryptionKeyBrand: unique symbol
declare const objectKeyBrand: unique symbol
declare const recoveryKeyBrand: unique symbol

export type AccountMasterKey = Uint8Array & { readonly [accountMasterKeyBrand]: true }
export type KeyEncryptionKey = Uint8Array & { readonly [keyEncryptionKeyBrand]: true }
export type ObjectKey = Uint8Array & { readonly [objectKeyBrand]: true }
export type RecoveryKey = Uint8Array & { readonly [recoveryKeyBrand]: true }

export interface ObjectCryptoContext {
  userId: string
  projectId: string
  entityId: string
  entityType: string
}

export interface Argon2idKdfRecord {
  kdf_version: typeof KDF_VERSION
  algorithm: typeof ARGON2ID13
  salt: Uint8Array
  opslimit: number
  memlimit: number
}

export interface PasswordWrappedAmkRecord {
  wrapping_version: typeof PASSWORD_WRAPPING_VERSION
  crypto_version: typeof CRYPTO_VERSION
  kdf: Argon2idKdfRecord
  nonce: Uint8Array
  ciphertext: Uint8Array
}

export interface RecoveryWrappedAmkRecord {
  wrapping_version: typeof RECOVERY_WRAPPING_VERSION
  crypto_version: typeof CRYPTO_VERSION
  nonce: Uint8Array
  ciphertext: Uint8Array
}

export interface ObjectCryptoEnvelope {
  crypto_version: typeof CRYPTO_VERSION
  aad_version: typeof AAD_VERSION
  nonce: Uint8Array
  ciphertext: Uint8Array
}
