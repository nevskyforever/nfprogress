// @vitest-environment node
import { describe, expect, it } from 'vitest'
import sodium from 'libsodium-wrappers-sumo'
import { hkdfSync } from 'node:crypto'
import vectors from './account-object-v2.vectors.json'
import { accountObjectAad, encodeAccountTuple, deriveAccountObjectKey, decryptAccountObject, encryptAccountObject, type AccountObjectContext } from './accountObjectCrypto'
import { asAccountMasterKey, encryptObjectBytes, decryptObjectBytes, deriveObjectKey } from './index'
const bytes = (value: string) => Uint8Array.from(value.match(/../g) ?? [], b => parseInt(b, 16))
const hex = (value: Uint8Array) => Buffer.from(value).toString('hex')
const context: AccountObjectContext = { ...vectors.context, scope: 'account' }
const amk = asAccountMasterKey(bytes(vectors.amk))
const envelope = { crypto_version: 2 as const, aad_version: 2 as const, nonce: bytes(vectors.nonce), ciphertext: bytes(vectors.ciphertext) }
describe('account v2 namespace', () => {
  it('matches independent Node HKDF and byte-exact tuple/AAD/AEAD fixture', async () => {
    expect(hex(encodeAccountTuple(context))).toBe(vectors.tuple)
    expect(hex(accountObjectAad(context))).toBe(vectors.aad)
    expect(hex(await deriveAccountObjectKey(amk, context))).toBe(vectors.key)
    expect(Buffer.from(hkdfSync('sha256', bytes(vectors.amk), Buffer.from('worta/hkdf/account-object-key/salt/v1'), bytes(vectors.info), 32)).toString('hex')).toBe(vectors.key)
    await sodium.ready
    expect(hex(sodium.crypto_aead_xchacha20poly1305_ietf_encrypt(bytes(vectors.plaintext),bytes(vectors.aad),null,bytes(vectors.nonce),bytes(vectors.key)))).toBe(vectors.ciphertext)
    expect(hex(await decryptAccountObject(amk,context,envelope))).toBe(vectors.plaintext)
  })
  it('uses fresh production nonces and round trips opaque bytes', async () => {
    const a = await encryptAccountObject(amk,context,bytes(vectors.plaintext)), b = await encryptAccountObject(amk,context,bytes(vectors.plaintext))
    expect(a.nonce).not.toEqual(b.nonce)
    expect(hex(await decryptAccountObject(amk,context,a))).toBe(vectors.plaintext)
  })
  it('rejects every changed identity/version and both project/account directions without fallback', async () => {
    for (const changed of [{userId:'123e4567-e89b-42d3-a456-426614174001'}, {entityId:'other'}, {entityType:'folder_order'}, {scope:'project'}]) {
      await expect(decryptAccountObject(amk,{...context,...changed} as AccountObjectContext,envelope)).rejects.toThrow()
    }
    for (const changed of [{crypto_version:1},{aad_version:1}]) await expect(decryptAccountObject(amk,context,{...envelope,...changed} as never)).rejects.toThrow()
    const project = {userId:context.userId,projectId:'account',entityId:context.entityId,entityType:context.entityType}
    expect(await deriveObjectKey(amk,project)).not.toEqual(await deriveAccountObjectKey(amk,context))
    await expect(decryptObjectBytes(amk,project,envelope as never)).rejects.toThrow()
    // Even forcibly relabeling versions cannot cross the key/AAD namespace.
    await expect(decryptObjectBytes(amk,project,{...envelope,crypto_version:1,aad_version:1})).rejects.toThrow()
    const v1 = await encryptObjectBytes(amk,project,bytes(vectors.plaintext))
    await expect(decryptAccountObject(amk,context,v1 as never)).rejects.toThrow()
    await expect(decryptAccountObject(amk,context,{...v1,crypto_version:2,aad_version:2})).rejects.toThrow()
  })
  it('uses scalar UTF8 byte bounds and unambiguous length prefixes', () => {
    expect(encodeAccountTuple({...context,entityId:'a',entityType:'bc'})).not.toEqual(encodeAccountTuple({...context,entityId:'ab',entityType:'c'}))
    for (const field of ['userId','entityId','entityType'] as const) {
      for (const value of ['', '\ud800', '\udc00', '😀'.repeat(field==='entityType'?33:129)]) expect(()=>encodeAccountTuple({...context,[field]:value})).toThrow()
    }
    expect(()=>encodeAccountTuple({...context,entityId:'😀'.repeat(128)})).not.toThrow()
  })
})
