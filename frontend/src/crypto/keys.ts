import { KEY_BYTES, OBJECT_KEY_HKDF_SALT } from './constants'
import { isUint8Array } from './bytes'
import { encodeObjectKeyContext, utf8Encode } from './encoding'
import { CryptoError } from './errors'
import { getSodium } from './sodium'
import type { AccountMasterKey, ObjectCryptoContext, ObjectKey, RecoveryKey } from './types'

function keyOfLength<T>(key: Uint8Array, label: 'invalid_key_length' | 'invalid_format'): T {
  if (!isUint8Array(key) || key.length !== KEY_BYTES) throw new CryptoError(label)
  return key as T
}

export function asAccountMasterKey(value: Uint8Array): AccountMasterKey {
  return keyOfLength<AccountMasterKey>(value, 'invalid_key_length')
}

export function asRecoveryKey(value: Uint8Array): RecoveryKey {
  return keyOfLength<RecoveryKey>(value, 'invalid_key_length')
}

export async function generateAccountMasterKey(): Promise<AccountMasterKey> {
  const sodium = await getSodium()
  return asAccountMasterKey(sodium.randombytes_buf(KEY_BYTES))
}

export async function generateRecoveryKey(): Promise<RecoveryKey> {
  const sodium = await getSodium()
  return asRecoveryKey(sodium.randombytes_buf(KEY_BYTES))
}

function subtleCrypto(): SubtleCrypto {
  const subtle = globalThis.crypto?.subtle
  if (subtle === undefined) throw new CryptoError('runtime_unavailable')
  return subtle
}

/** Derives a transient 32-byte key. The caller owns it and should zero it after use. */
export async function deriveObjectKey(amk: AccountMasterKey, context: ObjectCryptoContext): Promise<ObjectKey> {
  const source = asAccountMasterKey(amk)
  const input = Uint8Array.from(source)
  try {
    const subtle = subtleCrypto()
    // Copies also give Web Crypto an ArrayBuffer-backed view rather than a possibly shared caller buffer.
    const salt = Uint8Array.from(utf8Encode(OBJECT_KEY_HKDF_SALT))
    const info = Uint8Array.from(encodeObjectKeyContext(context))
    const material = await subtle.importKey('raw', input, 'HKDF', false, ['deriveBits'])
    const bits = await subtle.deriveBits({
      name: 'HKDF',
      hash: 'SHA-256',
      salt,
      info,
    }, material, KEY_BYTES * 8)
    return keyOfLength<ObjectKey>(new Uint8Array(bits), 'invalid_key_length')
  } catch (error) {
    if (error instanceof CryptoError) throw error
    throw new CryptoError('runtime_unavailable')
  } finally {
    // This is a best-effort erase of a temporary copy; JavaScript GC cannot guarantee erasure.
    input.fill(0)
  }
}
