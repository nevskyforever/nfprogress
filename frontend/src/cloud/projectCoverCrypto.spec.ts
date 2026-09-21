import { beforeAll, describe, expect, it } from 'vitest'
import { decryptObjectBytes, generateAccountMasterKey } from '@/crypto'
import { decryptProjectCover, encryptProjectCover } from './projectCoverCrypto'

describe('C14 project cover crypto', () => {
  const identity = { userId: 'user', projectId: 'project', blobId: '00000000-0000-4000-8000-000000000001' }
  let amk: Awaited<ReturnType<typeof generateAccountMasterKey>>
  beforeAll(async () => { amk = await generateAccountMasterKey() })

  it('roundtrips and binds every identity field', async () => {
    const plaintext = Uint8Array.of(1, 2, 3)
    const envelope = await encryptProjectCover(amk, identity, plaintext)
    await expect(decryptProjectCover(amk, identity, envelope)).resolves.toEqual(plaintext)
    for (const changed of [{ userId: 'other' }, { projectId: 'other' }, { blobId: '00000000-0000-4000-8000-000000000002' }]) {
      await expect(decryptProjectCover(amk, { ...identity, ...changed }, envelope)).rejects.toMatchObject({ code: 'decrypt_failed' })
    }
    await expect(decryptObjectBytes(amk, { userId: identity.userId, projectId: identity.projectId, entityId: identity.blobId, entityType: 'other_type' }, envelope)).rejects.toMatchObject({ code: 'decrypt_failed' })
    const tampered = { ...envelope, ciphertext: new Uint8Array(envelope.ciphertext) }; tampered.ciphertext[0]! ^= 1
    await expect(decryptProjectCover(amk, identity, tampered)).rejects.toMatchObject({ code: 'decrypt_failed' })
  })

  it('rejects excess plaintext and creates fresh envelopes without mutating caller buffers', async () => {
    const plaintext = Uint8Array.of(8, 9); const original = new Uint8Array(plaintext); const amkOriginal = new Uint8Array(amk)
    await expect(encryptProjectCover(amk, identity, new Uint8Array(2 * 1024 * 1024 + 1))).rejects.toThrow(RangeError)
    const first = await encryptProjectCover(amk, identity, plaintext); const second = await encryptProjectCover(amk, identity, plaintext)
    expect(first.nonce).not.toEqual(second.nonce); expect(first.ciphertext).not.toEqual(second.ciphertext)
    expect(plaintext).toEqual(original); expect(amk).toEqual(amkOriginal)
  })
})
