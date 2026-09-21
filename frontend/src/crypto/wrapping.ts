import {
  CRYPTO_VERSION,
  KEY_BYTES,
  PASSWORD_WRAP_AAD_DOMAIN,
  PASSWORD_WRAPPING_VERSION,
  RECOVERY_WRAP_AAD_DOMAIN,
  RECOVERY_WRAPPING_VERSION,
  XCHACHA20POLY1305_NONCE_BYTES,
} from './constants'
import { isUint8Array } from './bytes'
import { encodeFixedAad } from './encoding'
import { CryptoError } from './errors'
import { assertSupportedKdfRecord, createArgon2idKdfRecord, deriveKek } from './kdf'
import { asAccountMasterKey, asRecoveryKey } from './keys'
import { getSodium } from './sodium'
import type { AccountMasterKey, PasswordWrappedAmkRecord, RecoveryKey, RecoveryWrappedAmkRecord } from './types'

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null
}

function validateNonce(value: unknown): asserts value is Uint8Array {
  if (!isUint8Array(value) || value.length !== XCHACHA20POLY1305_NONCE_BYTES) {
    throw new CryptoError('invalid_format')
  }
}

function validateCiphertext(value: unknown): asserts value is Uint8Array {
  if (!isUint8Array(value) || value.length < KEY_BYTES + 16) throw new CryptoError('invalid_format')
}

function validatePasswordRecord(record: PasswordWrappedAmkRecord): void {
  if (!isRecord(record) || record.wrapping_version !== PASSWORD_WRAPPING_VERSION
    || record.crypto_version !== CRYPTO_VERSION || !isRecord(record.kdf)) {
    throw new CryptoError(
      isRecord(record) && (record.wrapping_version !== PASSWORD_WRAPPING_VERSION || record.crypto_version !== CRYPTO_VERSION)
        ? 'unsupported_version'
        : 'invalid_format',
    )
  }
  assertSupportedKdfRecord(record.kdf as PasswordWrappedAmkRecord['kdf'])
  validateNonce(record.nonce)
  validateCiphertext(record.ciphertext)
}

function validateRecoveryRecord(record: RecoveryWrappedAmkRecord): void {
  if (!isRecord(record) || record.wrapping_version !== RECOVERY_WRAPPING_VERSION
    || record.crypto_version !== CRYPTO_VERSION) {
    throw new CryptoError(
      isRecord(record) && (record.wrapping_version !== RECOVERY_WRAPPING_VERSION || record.crypto_version !== CRYPTO_VERSION)
        ? 'unsupported_version'
        : 'invalid_format',
    )
  }
  validateNonce(record.nonce)
  validateCiphertext(record.ciphertext)
}

async function encryptAmk(amk: AccountMasterKey, key: Uint8Array, domain: string): Promise<{ nonce: Uint8Array; ciphertext: Uint8Array }> {
  const sodium = await getSodium()
  const source = asAccountMasterKey(amk)
  if (key.length !== KEY_BYTES) throw new CryptoError('invalid_key_length')
  const nonce = sodium.randombytes_buf(XCHACHA20POLY1305_NONCE_BYTES)
  try {
    return {
      nonce,
      ciphertext: sodium.crypto_aead_xchacha20poly1305_ietf_encrypt(source, encodeFixedAad(domain), null, nonce, key),
    }
  } catch {
    throw new CryptoError('runtime_unavailable')
  }
}

async function decryptAmk(ciphertext: Uint8Array, nonce: Uint8Array, key: Uint8Array, domain: string): Promise<AccountMasterKey> {
  const sodium = await getSodium()
  try {
    return asAccountMasterKey(sodium.crypto_aead_xchacha20poly1305_ietf_decrypt(null, ciphertext, encodeFixedAad(domain), nonce, key))
  } catch {
    throw new CryptoError('decrypt_failed')
  }
}

export async function wrapAmkWithPassphrase(amk: AccountMasterKey, passphrase: string): Promise<PasswordWrappedAmkRecord> {
  const kdf = await createArgon2idKdfRecord()
  const kek = await deriveKek(passphrase, kdf)
  try {
    const encrypted = await encryptAmk(amk, kek, PASSWORD_WRAP_AAD_DOMAIN)
    return { wrapping_version: PASSWORD_WRAPPING_VERSION, crypto_version: CRYPTO_VERSION, kdf, ...encrypted }
  } finally {
    const sodium = await getSodium()
    sodium.memzero(kek)
  }
}

export async function unwrapAmkWithPassphrase(passphrase: string, record: PasswordWrappedAmkRecord): Promise<AccountMasterKey> {
  validatePasswordRecord(record)
  const kek = await deriveKek(passphrase, record.kdf)
  try {
    return await decryptAmk(record.ciphertext, record.nonce, kek, PASSWORD_WRAP_AAD_DOMAIN)
  } finally {
    const sodium = await getSodium()
    sodium.memzero(kek)
  }
}

export async function wrapAmkWithRecoveryKey(amk: AccountMasterKey, recoveryKey: RecoveryKey): Promise<RecoveryWrappedAmkRecord> {
  const encrypted = await encryptAmk(amk, asRecoveryKey(recoveryKey), RECOVERY_WRAP_AAD_DOMAIN)
  return { wrapping_version: RECOVERY_WRAPPING_VERSION, crypto_version: CRYPTO_VERSION, ...encrypted }
}

export async function unwrapAmkWithRecoveryKey(recoveryKey: RecoveryKey, record: RecoveryWrappedAmkRecord): Promise<AccountMasterKey> {
  validateRecoveryRecord(record)
  return decryptAmk(record.ciphertext, record.nonce, asRecoveryKey(recoveryKey), RECOVERY_WRAP_AAD_DOMAIN)
}
