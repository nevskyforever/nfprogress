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

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function validateKdfRecordShape(record: unknown): asserts record is Argon2idKdfRecord {
  const candidate = record as Partial<Argon2idKdfRecord>
  if (!isRecord(record) || typeof candidate.kdf_version !== 'number' || !Number.isSafeInteger(candidate.kdf_version) || candidate.kdf_version < 1
    || typeof candidate.algorithm !== 'string' || candidate.algorithm.length === 0
    || !isUint8Array(candidate.salt) || candidate.salt.length !== ARGON2ID_SALT_BYTES
    || typeof candidate.opslimit !== 'number' || !Number.isSafeInteger(candidate.opslimit) || candidate.opslimit < 1
    || typeof candidate.memlimit !== 'number' || !Number.isSafeInteger(candidate.memlimit) || candidate.memlimit < 1) {
    throw new CryptoError('invalid_format')
  }
  if (candidate.kdf_version !== KDF_VERSION || candidate.algorithm !== ARGON2ID13) {
    throw new CryptoError('unsupported_version')
  }
}

function normalizeUnsignedWasmLimit(value: number): number {
  return value >= 0 ? value : value >>> 0
}

async function validateKdfRecord(record: unknown): Promise<Argon2idKdfRecord> {
  validateKdfRecordShape(record)
  const sodium = await getSodium()
  // WASM exposes size_t maxima as signed i32 values. Normalize only those limits.
  const opslimitMaximum = normalizeUnsignedWasmLimit(sodium.crypto_pwhash_OPSLIMIT_MAX)
  const memlimitMaximum = normalizeUnsignedWasmLimit(sodium.crypto_pwhash_MEMLIMIT_MAX)
  if (record.opslimit < sodium.crypto_pwhash_OPSLIMIT_MIN || record.opslimit > opslimitMaximum
    || record.memlimit < sodium.crypto_pwhash_MEMLIMIT_MIN || record.memlimit > memlimitMaximum) {
    throw new CryptoError('invalid_format')
  }
  return record
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
  const validRecord = await validateKdfRecord(record)
  if (typeof passphrase !== 'string') throw new CryptoError('invalid_format')
  const sodium = await getSodium()
  try {
    return sodium.crypto_pwhash(
      KEY_BYTES,
      passphrase,
      validRecord.salt,
      validRecord.opslimit,
      validRecord.memlimit,
      sodium.crypto_pwhash_ALG_ARGON2ID13,
    ) as KeyEncryptionKey
  } catch {
    throw new CryptoError('kdf_failed')
  }
}

export async function assertSupportedKdfRecord(record: unknown): Promise<void> {
  await validateKdfRecord(record)
}
