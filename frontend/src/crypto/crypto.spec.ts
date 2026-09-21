// @vitest-environment node
import { describe, expect, it } from 'vitest'
import sodium from 'libsodium-wrappers-sumo'

import {
  C11_ARGON2ID_MEMLIMIT,
  C11_ARGON2ID_OPSLIMIT,
  CRYPTO_VERSION,
  CryptoError,
  PASSWORD_WRAP_AAD_DOMAIN,
  PASSWORD_WRAPPING_VERSION,
  asAccountMasterKey,
  deriveKek,
  deriveObjectKey,
  encodeFixedAad,
  encodeObjectAad,
  encodeObjectKeyContext,
  encryptObjectBytes,
  decryptObjectBytes,
  generateAccountMasterKey,
  generateRecoveryKey,
  unwrapAmkWithPassphrase,
  unwrapAmkWithRecoveryKey,
  wrapAmkWithPassphrase,
  wrapAmkWithRecoveryKey,
} from './index'
import type { ObjectCryptoContext } from './types'

const encoder = new TextEncoder()
const decoder = new TextDecoder()
const context: ObjectCryptoContext = {
  userId: 'user-α',
  projectId: 'project-β',
  entityId: 'entity-γ',
  entityType: 'document',
}

function hex(value: Uint8Array): string {
  return Array.from(value, (byte) => byte.toString(16).padStart(2, '0')).join('')
}

async function expectCryptoError(action: () => Promise<unknown>, code: CryptoError['code']): Promise<void> {
  await expect(action()).rejects.toMatchObject({ name: 'CryptoError', code })
}

describe('C11 client crypto module', () => {
  it('generates independent 256-bit AMKs and Recovery Keys', async () => {
    const [first, second, recovery] = await Promise.all([
      generateAccountMasterKey(),
      generateAccountMasterKey(),
      generateRecoveryKey(),
    ])
    expect(first).toHaveLength(32)
    expect(second).toHaveLength(32)
    expect(recovery).toHaveLength(32)
    expect(hex(first)).not.toBe(hex(second))
  })

  it('wraps AMK with explicit Argon2id13 parameters and unwraps using the record', async () => {
    const amk = await generateAccountMasterKey()
    const record = await wrapAmkWithPassphrase(amk, 'correct horse battery staple')
    expect(record.kdf).toMatchObject({
      kdf_version: 1,
      algorithm: 'argon2id13',
      opslimit: C11_ARGON2ID_OPSLIMIT,
      memlimit: C11_ARGON2ID_MEMLIMIT,
    })
    expect(record.kdf.salt).toHaveLength(16)
    expect(await unwrapAmkWithPassphrase('correct horse battery staple', record)).toEqual(amk)
  })

  it('unwraps with stored KDF parameters rather than current v1 defaults', async () => {
    const amk = asAccountMasterKey(new Uint8Array(32).fill(4))
    const kdf = {
      kdf_version: 1 as const,
      algorithm: 'argon2id13' as const,
      salt: new Uint8Array(16).fill(9),
      opslimit: C11_ARGON2ID_OPSLIMIT + 1,
      memlimit: C11_ARGON2ID_MEMLIMIT,
    }
    const kek = await deriveKek('record-specific-parameters', kdf)
    await sodium.ready
    const nonce = new Uint8Array(24).fill(3)
    const record = {
      wrapping_version: PASSWORD_WRAPPING_VERSION,
      crypto_version: CRYPTO_VERSION,
      kdf,
      nonce,
      ciphertext: sodium.crypto_aead_xchacha20poly1305_ietf_encrypt(amk, encodeFixedAad(PASSWORD_WRAP_AAD_DOMAIN), null, nonce, kek),
    }
    sodium.memzero(kek)
    expect(await unwrapAmkWithPassphrase('record-specific-parameters', record)).toEqual(amk)
  })

  it('fails closed for a wrong passphrase and never exposes it in its message', async () => {
    const secret = 'passphrase-that-must-not-leak'
    const record = await wrapAmkWithPassphrase(await generateAccountMasterKey(), secret)
    await expectCryptoError(() => unwrapAmkWithPassphrase('wrong-passphrase-secret', record), 'decrypt_failed')
    try {
      await unwrapAmkWithPassphrase('wrong-passphrase-secret', record)
    } catch (error) {
      expect((error as Error).message).not.toContain(secret)
      expect((error as Error).message).not.toContain('wrong-passphrase-secret')
    }
  })

  it('wraps and unwraps AMK with a separate Recovery Key domain', async () => {
    const amk = await generateAccountMasterKey()
    const recovery = await generateRecoveryKey()
    const record = await wrapAmkWithRecoveryKey(amk, recovery)
    expect(await unwrapAmkWithRecoveryKey(recovery, record)).toEqual(amk)
    const wrongRecovery = await generateRecoveryKey()
    await expectCryptoError(() => unwrapAmkWithRecoveryKey(wrongRecovery, record), 'decrypt_failed')
  })

  it('encrypts objects with fresh nonces and authenticates their identity context', async () => {
    const amk = await generateAccountMasterKey()
    const plaintext = encoder.encode('Зашифрованный текст')
    const [first, second] = await Promise.all([
      encryptObjectBytes(amk, context, plaintext),
      encryptObjectBytes(amk, context, plaintext),
    ])
    expect(first.nonce).toHaveLength(24)
    expect(hex(first.nonce)).not.toBe(hex(second.nonce))
    expect(hex(first.ciphertext)).not.toBe(hex(second.ciphertext))
    expect(decoder.decode(await decryptObjectBytes(amk, context, first))).toBe('Зашифрованный текст')

    const tampered = { ...first, ciphertext: new Uint8Array(first.ciphertext) }
    tampered.ciphertext[0] = (tampered.ciphertext[0] ?? 0) ^ 1
    await expectCryptoError(() => decryptObjectBytes(amk, context, tampered), 'decrypt_failed')
    await expectCryptoError(() => decryptObjectBytes(amk, { ...context, projectId: 'other-project' }, first), 'decrypt_failed')
    await expectCryptoError(() => decryptObjectBytes(amk, { ...context, userId: 'other-user' }, first), 'decrypt_failed')
    await expectCryptoError(() => decryptObjectBytes(amk, { ...context, entityId: 'other-entity' }, first), 'decrypt_failed')
    await expectCryptoError(() => decryptObjectBytes(amk, { ...context, entityType: 'note' }, first), 'decrypt_failed')
  })

  it('derives deterministic, domain-separated object keys and preserves Unicode canonical bytes', async () => {
    const amk = asAccountMasterKey(new Uint8Array(32).fill(7))
    const first = await deriveObjectKey(amk, context)
    expect(await deriveObjectKey(amk, context)).toEqual(first)
    for (const changed of [
      { ...context, userId: 'user-δ' },
      { ...context, projectId: 'project-δ' },
      { ...context, entityId: 'entity-δ' },
      { ...context, entityType: 'note' },
    ]) {
      expect(await deriveObjectKey(amk, changed)).not.toEqual(first)
    }
    expect(hex(encodeObjectKeyContext(context))).toBe('776f7274612f6f626a6563742d6b65792f7631010100000007757365722dceb10000000a70726f6a6563742dceb200000009656e746974792dceb300000008646f63756d656e74')
    expect(hex(encodeObjectAad(context))).toBe('776f7274612f6f626a6563742d6161642f7631010100000007757365722dceb10000000a70726f6a6563742dceb200000009656e746974792dceb300000008646f63756d656e74')
    expect(hex(first)).toBe('6bc270db196c49959307057b293d028a41d1c1aeb2e78a1a8e6f2d79d7194147')
  })

  it('rejects malformed contexts, unknown versions, and invalid key or nonce lengths', async () => {
    const amk = await generateAccountMasterKey()
    await expectCryptoError(() => deriveObjectKey(amk, { ...context, entityId: '' }), 'invalid_format')
    await expectCryptoError(() => deriveObjectKey(amk, { ...context, entityId: '\ud800' }), 'invalid_format')
    try {
      asAccountMasterKey(new Uint8Array(31))
      throw new Error('Expected invalid key length to throw.')
    } catch (error) {
      expect(error).toMatchObject({ code: 'invalid_key_length' })
    }

    const envelope = await encryptObjectBytes(amk, context, encoder.encode('ok'))
    await expectCryptoError(() => decryptObjectBytes(amk, context, { ...envelope, crypto_version: 2 } as never), 'unsupported_version')
    await expectCryptoError(() => decryptObjectBytes(amk, context, { ...envelope, aad_version: 2 } as never), 'unsupported_version')
    await expectCryptoError(() => decryptObjectBytes(amk, context, { ...envelope, nonce: new Uint8Array(23) }), 'invalid_format')

    const wrapped = await wrapAmkWithPassphrase(amk, 'test passphrase')
    await expectCryptoError(() => unwrapAmkWithPassphrase('test passphrase', { ...wrapped, wrapping_version: 2 } as never), 'unsupported_version')
    await expectCryptoError(() => unwrapAmkWithPassphrase('test passphrase', { ...wrapped, kdf: { ...wrapped.kdf, kdf_version: 2 } } as never), 'unsupported_version')
    const recovery = await wrapAmkWithRecoveryKey(amk, await generateRecoveryKey())
    const anotherRecovery = await generateRecoveryKey()
    await expectCryptoError(() => unwrapAmkWithRecoveryKey(anotherRecovery, { ...recovery, nonce: new Uint8Array(25) }), 'invalid_format')
    await expectCryptoError(() => unwrapAmkWithRecoveryKey(anotherRecovery, { ...recovery, wrapping_version: 2 } as never), 'unsupported_version')
  })
})
