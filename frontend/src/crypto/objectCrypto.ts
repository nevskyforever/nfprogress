import { AAD_VERSION, CRYPTO_VERSION, XCHACHA20POLY1305_NONCE_BYTES } from './constants'
import { isUint8Array } from './bytes'
import { encodeObjectAad } from './encoding'
import { CryptoError } from './errors'
import { asAccountMasterKey, deriveObjectKey } from './keys'
import { getSodium } from './sodium'
import type { AccountMasterKey, ObjectCryptoContext, ObjectCryptoEnvelope } from './types'

function validateEnvelope(envelope: ObjectCryptoEnvelope): void {
  if (typeof envelope !== 'object' || envelope === null || Array.isArray(envelope)) throw new CryptoError('invalid_format')
  if (typeof envelope.crypto_version !== 'number' || typeof envelope.aad_version !== 'number') {
    throw new CryptoError('invalid_format')
  }
  if (envelope.crypto_version !== CRYPTO_VERSION || envelope.aad_version !== AAD_VERSION) {
    throw new CryptoError('unsupported_version')
  }
  if (!isUint8Array(envelope.nonce) || envelope.nonce.length !== XCHACHA20POLY1305_NONCE_BYTES
    || !isUint8Array(envelope.ciphertext) || envelope.ciphertext.length < 16) {
    throw new CryptoError('invalid_format')
  }
}

export async function encryptObjectBytes(
  amk: AccountMasterKey,
  context: ObjectCryptoContext,
  plaintext: Uint8Array,
): Promise<ObjectCryptoEnvelope> {
  if (!isUint8Array(plaintext)) throw new CryptoError('invalid_format')
  const sodium = await getSodium()
  const key = await deriveObjectKey(asAccountMasterKey(amk), context)
  const nonce = sodium.randombytes_buf(XCHACHA20POLY1305_NONCE_BYTES)
  try {
    return {
      crypto_version: CRYPTO_VERSION,
      aad_version: AAD_VERSION,
      nonce,
      ciphertext: sodium.crypto_aead_xchacha20poly1305_ietf_encrypt(plaintext, encodeObjectAad(context), null, nonce, key),
    }
  } catch {
    throw new CryptoError('runtime_unavailable')
  } finally {
    sodium.memzero(key)
  }
}

export async function decryptObjectBytes(
  amk: AccountMasterKey,
  context: ObjectCryptoContext,
  envelope: ObjectCryptoEnvelope,
): Promise<Uint8Array> {
  validateEnvelope(envelope)
  const sodium = await getSodium()
  const key = await deriveObjectKey(asAccountMasterKey(amk), context)
  try {
    return sodium.crypto_aead_xchacha20poly1305_ietf_decrypt(null, envelope.ciphertext, encodeObjectAad(context), envelope.nonce, key)
  } catch {
    throw new CryptoError('decrypt_failed')
  } finally {
    sodium.memzero(key)
  }
}
