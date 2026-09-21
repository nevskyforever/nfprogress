// @vitest-environment node
import { describe, expect, it, vi } from 'vitest'
import sodium from 'libsodium-wrappers-sumo'

import {
  CRYPTO_VERSION,
  CryptoError,
  PASSWORD_WRAP_AAD_DOMAIN,
  RECOVERY_WRAP_AAD_DOMAIN,
  asAccountMasterKey,
  asRecoveryKey,
  decryptObjectBytes,
  deriveKek,
  deriveObjectKey,
  encodeFixedAad,
  encodeObjectAad,
  encodeObjectKeyContext,
  encryptObjectBytes,
  generateAccountMasterKey,
  generateRecoveryKey,
  unwrapAmkWithPassphrase,
  unwrapAmkWithRecoveryKey,
  wrapAmkWithPassphrase,
  wrapAmkWithRecoveryKey,
} from './index'
import type { ObjectCryptoContext } from './types'

const text = new TextEncoder()
const context: ObjectCryptoContext = { userId: 'user-α', projectId: 'project-β', entityId: 'entity-γ', entityType: 'document' }

function hex(value: Uint8Array): string {
  return Array.from(value, byte => byte.toString(16).padStart(2, '0')).join('')
}

async function expectCryptoError(action: () => Promise<unknown>, code: CryptoError['code']): Promise<void> {
  await expect(action()).rejects.toMatchObject({ name: 'CryptoError', code })
}

describe('C12 object encryption authentication contract', () => {
  it.each([
    ['empty', new Uint8Array()],
    ['binary', Uint8Array.from([0, 0xff, 0, 1, 0x80])],
    ['Unicode UTF-8', text.encode('Текст αβγ — こんにちは 🔐')],
    ['large in-memory object', new Uint8Array(512 * 1024).fill(0x5a)],
  ])('round-trips %s without exposing plaintext in ciphertext', async (_label, plaintext) => {
    const amk = await generateAccountMasterKey()
    const envelope = await encryptObjectBytes(amk, context, plaintext)
    expect(envelope.nonce).toHaveLength(24)
    expect(hex(envelope.ciphertext)).not.toBe(hex(plaintext))
    expect(await decryptObjectBytes(amk, context, envelope)).toEqual(plaintext)
  })

  it('fails closed for each tampered encrypted field and never returns partial plaintext', async () => {
    const amk = await generateAccountMasterKey()
    const envelope = await encryptObjectBytes(amk, context, text.encode('only authenticated plaintext'))
    for (const altered of [
      { ...envelope, ciphertext: Uint8Array.from(envelope.ciphertext, (byte, index) => index === 0 ? byte ^ 1 : byte) },
      { ...envelope, ciphertext: Uint8Array.from(envelope.ciphertext, (byte, index) => index === envelope.ciphertext.length - 1 ? byte ^ 1 : byte) },
      { ...envelope, nonce: Uint8Array.from(envelope.nonce, (byte, index) => index === 0 ? byte ^ 1 : byte) },
    ]) await expectCryptoError(() => decryptObjectBytes(amk, context, altered), 'decrypt_failed')
    await expectCryptoError(() => decryptObjectBytes(amk, context, { ...envelope, crypto_version: 2 } as never), 'unsupported_version')
    await expectCryptoError(() => decryptObjectBytes(amk, context, { ...envelope, aad_version: 2 } as never), 'unsupported_version')
  })

  it('binds all canonical identity fields in both HKDF and AEAD', async () => {
    const amk = await generateAccountMasterKey()
    const envelope = await encryptObjectBytes(amk, context, text.encode('bound object'))
    const first = await deriveObjectKey(amk, context)
    for (const changed of [
      { ...context, userId: 'other-user' }, { ...context, projectId: 'other-project' },
      { ...context, entityId: 'other-entity' }, { ...context, entityType: 'note' },
    ]) {
      expect(await deriveObjectKey(amk, changed)).not.toEqual(first)
      await expectCryptoError(() => decryptObjectBytes(amk, changed, envelope), 'decrypt_failed')
    }
  })

  it('uses fresh 24-byte nonces in repeated object encryption', async () => {
    const amk = await generateAccountMasterKey()
    const outputs = await Promise.all(Array.from({ length: 100 }, () => encryptObjectBytes(amk, context, text.encode('same'))))
    expect(new Set(outputs.map(output => hex(output.nonce))).size).toBe(outputs.length)
    expect(new Set(outputs.map(output => hex(output.ciphertext))).size).toBe(outputs.length)
  })
})

describe('C12 canonical encoding and runtime-format contract', () => {
  it('uses UTF-8 byte length prefixes and prevents ambiguous concatenation', () => {
    const multibyte: ObjectCryptoContext = { userId: 'é', projectId: '界', entityId: 'x', entityType: 'd' }
    expect(hex(encodeObjectKeyContext(multibyte))).toContain('00000002c3a9')
    expect(hex(encodeObjectAad(multibyte))).toContain('00000003e7958c')
    expect(hex(encodeObjectKeyContext({ ...context, userId: 'ab', projectId: 'c' })))
      .not.toBe(hex(encodeObjectKeyContext({ ...context, userId: 'a', projectId: 'bc' })))
  })

  it.each(['', '\ud800', '\udc00', 'a\ud800b', 'a\udc00b', '😀'.repeat(129)])('rejects invalid identifiers: %j', async value => {
    const amk = await generateAccountMasterKey()
    await expectCryptoError(() => deriveObjectKey(amk, { ...context, entityId: value }), 'invalid_format')
  })

  it('rejects entity types over their UTF-8 byte limit and malformed envelopes', async () => {
    const amk = await generateAccountMasterKey()
    await expectCryptoError(() => deriveObjectKey(amk, { ...context, entityType: '界'.repeat(43) }), 'invalid_format')
    const malformed: unknown[] = [null, [], {}, { crypto_version: 1, aad_version: 1, nonce: new Uint8Array(23), ciphertext: new Uint8Array(16) }, { crypto_version: 1, aad_version: 1, nonce: new Uint8Array(24), ciphertext: new Uint8Array(15) }]
    for (const envelope of malformed) await expectCryptoError(() => decryptObjectBytes(amk, context, envelope as never), 'invalid_format')
  })
})

describe('C12 password and Recovery wrapping contract', () => {
  it('uses fresh password KDF salts/nonces and fresh Recovery nonces', async () => {
    const amk = await generateAccountMasterKey()
    const [passwordA, passwordB] = await Promise.all([wrapAmkWithPassphrase(amk, 'passphrase'), wrapAmkWithPassphrase(amk, 'passphrase')])
    const recovery = await generateRecoveryKey()
    const [recoveryA, recoveryB] = await Promise.all([wrapAmkWithRecoveryKey(amk, recovery), wrapAmkWithRecoveryKey(amk, recovery)])
    expect(hex(passwordA.kdf.salt)).not.toBe(hex(passwordB.kdf.salt)); expect(hex(passwordA.nonce)).not.toBe(hex(passwordB.nonce))
    expect(hex(recoveryA.nonce)).not.toBe(hex(recoveryB.nonce))
  })

  it('preserves AMK across password rewrap and Recovery regeneration without object re-encryption', async () => {
    const amk = await generateAccountMasterKey(); const object = await encryptObjectBytes(amk, context, text.encode('persists'))
    const oldRecord = await wrapAmkWithPassphrase(amk, 'old'); const unwrapped = await unwrapAmkWithPassphrase('old', oldRecord)
    const newRecord = await wrapAmkWithPassphrase(unwrapped, 'new')
    expect(await unwrapAmkWithPassphrase('new', newRecord)).toEqual(amk); await expectCryptoError(() => unwrapAmkWithPassphrase('old', newRecord), 'decrypt_failed')
    expect(await decryptObjectBytes(unwrapped, context, object)).toEqual(text.encode('persists'))
    const oldRecovery = await generateRecoveryKey(); const oldRecoveryRecord = await wrapAmkWithRecoveryKey(amk, oldRecovery); const newRecovery = await generateRecoveryKey()
    const replacement = await wrapAmkWithRecoveryKey(amk, newRecovery)
    expect(await unwrapAmkWithRecoveryKey(oldRecovery, oldRecoveryRecord)).toEqual(amk)
    await expectCryptoError(() => unwrapAmkWithRecoveryKey(oldRecovery, replacement), 'decrypt_failed')
    expect(await unwrapAmkWithRecoveryKey(newRecovery, replacement)).toEqual(amk)
  })

  it('fails closed for malformed password KDF/wrapping fields before expensive allocation', async () => {
    const amk = asAccountMasterKey(new Uint8Array(32).fill(1))
    const record = await wrapAmkWithPassphrase(amk, 'correct')
    for (const kdf of [null, [], {}, { ...record.kdf, kdf_version: undefined }, { ...record.kdf, algorithm: undefined }, { ...record.kdf, kdf_version: '1' }, { ...record.kdf, algorithm: 1 }, { ...record.kdf, salt: new Uint8Array(15) }, { ...record.kdf, opslimit: Number.NaN }, { ...record.kdf, opslimit: 1.5 }, { ...record.kdf, opslimit: 0 }, { ...record.kdf, memlimit: -1 }, { ...record.kdf, memlimit: Number.MAX_SAFE_INTEGER }]) {
      await expectCryptoError(() => unwrapAmkWithPassphrase('correct', { ...record, kdf } as never), 'invalid_format')
    }
    await expectCryptoError(() => unwrapAmkWithPassphrase('correct', { ...record, kdf: { ...record.kdf, algorithm: 'argon2i13' } } as never), 'unsupported_version')
    await expectCryptoError(() => unwrapAmkWithPassphrase('correct', { ...record, kdf: { ...record.kdf, kdf_version: 2 } } as never), 'unsupported_version')
    await expectCryptoError(() => unwrapAmkWithPassphrase('correct', { ...record, wrapping_version: 2 } as never), 'unsupported_version')
    await expectCryptoError(() => unwrapAmkWithPassphrase('correct', { ...record, crypto_version: 2 } as never), 'unsupported_version')
    await expectCryptoError(() => unwrapAmkWithPassphrase('correct', { ...record, nonce: new Uint8Array(25) } as never), 'invalid_format')
    await expectCryptoError(() => unwrapAmkWithPassphrase('correct', { ...record, ciphertext: new Uint8Array(47) } as never), 'invalid_format')
    await expectCryptoError(() => unwrapAmkWithPassphrase('correct', { ...record, ciphertext: Uint8Array.from(record.ciphertext, (byte, index) => index === 0 ? byte ^ 1 : byte) }), 'decrypt_failed')
    await expectCryptoError(() => unwrapAmkWithPassphrase('correct', { ...record, nonce: Uint8Array.from(record.nonce, (byte, index) => index === 0 ? byte ^ 1 : byte) }), 'decrypt_failed')
    await expectCryptoError(() => unwrapAmkWithPassphrase('correct', { ...record, kdf: { ...record.kdf, salt: Uint8Array.from(record.kdf.salt, (byte, index) => index === 0 ? byte ^ 1 : byte) } }), 'decrypt_failed')
  })

  it('enforces the complete runtime Argon2id minimum and maximum range before crypto_pwhash', async () => {
    await sodium.ready
    const kdf = { kdf_version: 1 as const, algorithm: 'argon2id13' as const, salt: new Uint8Array(16), opslimit: sodium.crypto_pwhash_OPSLIMIT_MIN, memlimit: sodium.crypto_pwhash_MEMLIMIT_MIN }
    const pwhashSpy = vi.spyOn(sodium, 'crypto_pwhash')
    if (sodium.crypto_pwhash_OPSLIMIT_MIN > 0) {
      await expectCryptoError(() => deriveKek('minimum', { ...kdf, opslimit: sodium.crypto_pwhash_OPSLIMIT_MIN - 1 }), 'invalid_format')
    }
    await expectCryptoError(() => deriveKek('minimum', { ...kdf, memlimit: sodium.crypto_pwhash_MEMLIMIT_MIN - 1 }), 'invalid_format')
    expect(pwhashSpy).not.toHaveBeenCalled()
    pwhashSpy.mockRestore()
    expect(await deriveKek('minimum', kdf)).toHaveLength(32)
  })

  it('requires exact 48-byte combined ciphertext for password and Recovery AMK wrappers', async () => {
    const amk = await generateAccountMasterKey(); const recovery = await generateRecoveryKey()
    const password = await wrapAmkWithPassphrase(amk, 'correct'); const recoveryRecord = await wrapAmkWithRecoveryKey(amk, recovery)
    expect(password.ciphertext).toHaveLength(48); expect(recoveryRecord.ciphertext).toHaveLength(48)
    expect(await unwrapAmkWithPassphrase('correct', password)).toEqual(amk); expect(await unwrapAmkWithRecoveryKey(recovery, recoveryRecord)).toEqual(amk)
    for (const size of [47, 49]) {
      await expectCryptoError(() => unwrapAmkWithPassphrase('correct', { ...password, ciphertext: new Uint8Array(size) }), 'invalid_format')
      await expectCryptoError(() => unwrapAmkWithRecoveryKey(recovery, { ...recoveryRecord, ciphertext: new Uint8Array(size) }), 'invalid_format')
    }
  })

  it('keeps password and Recovery wrapping domains non-interchangeable even with identical key material', async () => {
    await sodium.ready
    const material = new Uint8Array(32).fill(9); const amk = asAccountMasterKey(new Uint8Array(32).fill(4)); const nonce = new Uint8Array(24).fill(2)
    const passwordCiphertext = sodium.crypto_aead_xchacha20poly1305_ietf_encrypt(amk, encodeFixedAad(PASSWORD_WRAP_AAD_DOMAIN), null, nonce, material)
    const recoveryCiphertext = sodium.crypto_aead_xchacha20poly1305_ietf_encrypt(amk, encodeFixedAad(RECOVERY_WRAP_AAD_DOMAIN), null, nonce, material)
    await expectCryptoError(() => unwrapAmkWithRecoveryKey(asRecoveryKey(material), { wrapping_version: 1, crypto_version: CRYPTO_VERSION, nonce, ciphertext: passwordCiphertext }), 'decrypt_failed')
    expect(() => sodium.crypto_aead_xchacha20poly1305_ietf_decrypt(null, recoveryCiphertext, encodeFixedAad(PASSWORD_WRAP_AAD_DOMAIN), nonce, material)).toThrow()
  })

  it('rejects damaged and unsupported Recovery records', async () => {
    const amk = await generateAccountMasterKey(); const recovery = await generateRecoveryKey()
    const record = await wrapAmkWithRecoveryKey(amk, recovery)
    await expectCryptoError(() => unwrapAmkWithRecoveryKey(recovery, { ...record, ciphertext: Uint8Array.from(record.ciphertext, (byte, index) => index === 0 ? byte ^ 1 : byte) }), 'decrypt_failed')
    await expectCryptoError(() => unwrapAmkWithRecoveryKey(recovery, { ...record, nonce: Uint8Array.from(record.nonce, (byte, index) => index === 0 ? byte ^ 1 : byte) }), 'decrypt_failed')
    await expectCryptoError(() => unwrapAmkWithRecoveryKey(recovery, { ...record, wrapping_version: 2 } as never), 'unsupported_version')
    await expectCryptoError(() => unwrapAmkWithRecoveryKey(recovery, [] as never), 'invalid_format')
  })

  it('does not mutate caller-owned key, plaintext, or envelope buffers', async () => {
    const amk = asAccountMasterKey(new Uint8Array(32).fill(3)); const recovery = asRecoveryKey(new Uint8Array(32).fill(4)); const plaintext = Uint8Array.from([0, 1, 2])
    const amkBefore = Uint8Array.from(amk); const recoveryBefore = Uint8Array.from(recovery); const plaintextBefore = Uint8Array.from(plaintext)
    const envelope = await encryptObjectBytes(amk, context, plaintext); const nonceBefore = Uint8Array.from(envelope.nonce); const ciphertextBefore = Uint8Array.from(envelope.ciphertext)
    const result = await decryptObjectBytes(amk, context, envelope); result[0] = 99
    expect(amk).toEqual(amkBefore); expect(recovery).toEqual(recoveryBefore); expect(plaintext).toEqual(plaintextBefore)
    expect(envelope.nonce).toEqual(nonceBefore); expect(envelope.ciphertext).toEqual(ciphertextBefore)
    expect(await decryptObjectBytes(amk, context, envelope)).toEqual(plaintextBefore)
  })
})
