// @vitest-environment node
import { describe, expect, it } from 'vitest'
import sodium from 'libsodium-wrappers-sumo'

import vectors from './c11-compatibility-vectors.v1.json'
import {
  asAccountMasterKey,
  deriveKek,
  deriveObjectKey,
  encodeFixedAad,
  encodeObjectKeyContext,
  PASSWORD_WRAP_AAD_DOMAIN,
  RECOVERY_WRAP_AAD_DOMAIN,
} from './index'

function bytes(hex: string): Uint8Array {
  return Uint8Array.from(hex.match(/../g) ?? [], byte => Number.parseInt(byte, 16))
}

function hex(value: Uint8Array): string {
  return Array.from(value, byte => byte.toString(16).padStart(2, '0')).join('')
}

describe('C11 v1 cross-runtime compatibility vectors', () => {
  it('fixes HKDF object-key context bytes and output', async () => {
    const amk = asAccountMasterKey(bytes(vectors.hkdf.amk))
    expect(hex(encodeObjectKeyContext(vectors.hkdf.context))).toBe(vectors.hkdf.encodedContext)
    expect(hex(await deriveObjectKey(amk, vectors.hkdf.context))).toBe(vectors.hkdf.objectKey)
  })

  it('fixes the libsodium-compatible XChaCha20-Poly1305-IETF primitive vector', async () => {
    await sodium.ready
    const vector = vectors.xchacha20poly1305Ietf
    expect(hex(sodium.crypto_aead_xchacha20poly1305_ietf_encrypt(
      bytes(vector.plaintext), bytes(vector.aad), null, bytes(vector.nonce), bytes(vector.key),
    ))).toBe(vector.ciphertext)
    expect(hex(sodium.crypto_aead_xchacha20poly1305_ietf_decrypt(
      null, bytes(vector.ciphertext), bytes(vector.aad), bytes(vector.nonce), bytes(vector.key),
    ))).toBe(vector.plaintext)
  })

  it('fixes explicit Argon2id13 inputs and output', async () => {
    const vector = vectors.argon2id13
    expect(hex(await deriveKek(vector.passphrase, {
      kdf_version: 1,
      algorithm: 'argon2id13',
      salt: bytes(vector.salt),
      opslimit: vector.opslimit,
      memlimit: vector.memlimit,
    }))).toBe(vector.kek)
  })

  it('fixes password and Recovery AMK-wrap primitive domains independently', async () => {
    await sodium.ready
    const password = vectors.passwordWrap
    const recovery = vectors.recoveryWrap
    expect(hex(encodeFixedAad(PASSWORD_WRAP_AAD_DOMAIN))).toBe(password.aad)
    expect(hex(encodeFixedAad(RECOVERY_WRAP_AAD_DOMAIN))).toBe(recovery.aad)
    expect(hex(sodium.crypto_aead_xchacha20poly1305_ietf_encrypt(
      bytes(password.amk), bytes(password.aad), null, bytes(password.nonce), bytes(password.kek),
    ))).toBe(password.ciphertext)
    expect(hex(sodium.crypto_aead_xchacha20poly1305_ietf_encrypt(
      bytes(recovery.amk), bytes(recovery.aad), null, bytes(recovery.nonce), bytes(recovery.recoveryKey),
    ))).toBe(recovery.ciphertext)
  })
})
