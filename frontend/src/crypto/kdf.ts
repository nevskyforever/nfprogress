import {
  ARGON2ID13,
  ARGON2ID_SALT_BYTES,
  C11_ARGON2ID_MEMLIMIT,
  C11_ARGON2ID_OPSLIMIT,
  KDF_VERSION,
  KEY_BYTES,
} from './constants'
import { isUint8Array } from './bytes'
import { CryptoError } from './errors'
import { getSodium } from './sodium'
import type { Argon2idKdfRecord, KeyEncryptionKey } from './types'

function validateKdfRecord(record: Argon2idKdfRecord): void {
  if (record.kdf_version !== KDF_VERSION || record.algorithm !== ARGON2ID13
    || !isUint8Array(record.salt) || record.salt.length !== ARGON2ID_SALT_BYTES
    || !Number.isSafeInteger(record.opslimit) || record.opslimit < 1
    || !Number.isSafeInteger(record.memlimit) || record.memlimit < 1) {
    throw new CryptoError(record.kdf_version !== KDF_VERSION || record.algorithm !== ARGON2ID13
      ? 'unsupported_version'
      : 'invalid_format')
  }
}

export async function createArgon2idKdfRecord(): Promise<Argon2idKdfRecord> {
  const sodium = await getSodium()
  if (sodium.crypto_pwhash_SALTBYTES !== ARGON2ID_SALT_BYTES) throw new CryptoError('runtime_unavailable')
  return {
    kdf_version: KDF_VERSION,
    algorithm: ARGON2ID13,
    salt: sodium.randombytes_buf(ARGON2ID_SALT_BYTES),
    opslimit: C11_ARGON2ID_OPSLIMIT,
    memlimit: C11_ARGON2ID_MEMLIMIT,
  }
}

/** The passphrase is only used for this call; the returned KEK is caller-owned. */
export async function deriveKek(passphrase: string, record: Argon2idKdfRecord): Promise<KeyEncryptionKey> {
  validateKdfRecord(record)
  if (typeof passphrase !== 'string') throw new CryptoError('invalid_format')
  const sodium = await getSodium()
  try {
    return sodium.crypto_pwhash(
      KEY_BYTES,
      passphrase,
      record.salt,
      record.opslimit,
      record.memlimit,
      sodium.crypto_pwhash_ALG_ARGON2ID13,
    ) as KeyEncryptionKey
  } catch {
    throw new CryptoError('kdf_failed')
  }
}

export function assertSupportedKdfRecord(record: Argon2idKdfRecord): void {
  validateKdfRecord(record)
}
