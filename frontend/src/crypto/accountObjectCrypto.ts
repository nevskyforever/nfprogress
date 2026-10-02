import { asAccountMasterKey } from './keys'
import { CryptoError } from './errors'
import { getSodium } from './sodium'
import type { AccountMasterKey } from './types'

export const ACCOUNT_ENTITY_TYPES = ['folder', 'folder_order', 'folder_membership', 'project_order'] as const
export type AccountEntityType = typeof ACCOUNT_ENTITY_TYPES[number]
export interface AccountObjectContext { userId: string; scope: 'account'; entityId: string; entityType: string }
export interface AccountObjectEnvelope { crypto_version: 2; aad_version: 2; nonce: Uint8Array; ciphertext: Uint8Array }
const encoder = new TextEncoder()
const concat = (...parts: Uint8Array[]): Uint8Array => {
  const out = new Uint8Array(parts.reduce((sum, part) => sum + part.length, 0))
  let offset = 0
  for (const part of parts) { out.set(part, offset); offset += part.length }
  return out
}
function field(value: string, maximum: number): Uint8Array {
  if (typeof value !== 'string' || !value) throw new CryptoError('invalid_format')
  for (let i = 0; i < value.length; i++) {
    const c = value.charCodeAt(i)
    if (c >= 0xd800 && c <= 0xdbff) {
      const next = value.charCodeAt(++i)
      if (!(next >= 0xdc00 && next <= 0xdfff)) throw new CryptoError('invalid_format')
    } else if (c >= 0xdc00 && c <= 0xdfff) throw new CryptoError('invalid_format')
  }
  const bytes = encoder.encode(value)
  if (bytes.length > maximum) throw new CryptoError('invalid_format')
  const size = new Uint8Array(4)
  new DataView(size.buffer).setUint32(0, bytes.length, false)
  return concat(size, bytes)
}
export function encodeAccountTuple(context: AccountObjectContext): Uint8Array {
  if (context.scope !== 'account') throw new CryptoError('invalid_format')
  return concat(field(context.userId, 512), field(context.scope, 7), field(context.entityId, 512), field(context.entityType, 128))
}
export function accountObjectAad(context: AccountObjectContext): Uint8Array {
  return concat(encoder.encode('worta/account-object-aad/v1'), new Uint8Array([2, 2]), encodeAccountTuple(context))
}
export async function deriveAccountObjectKey(amk: AccountMasterKey, context: AccountObjectContext): Promise<Uint8Array> {
  const input = new Uint8Array(asAccountMasterKey(amk))
  try {
    const key = await globalThis.crypto.subtle.importKey('raw', input, 'HKDF', false, ['deriveBits'])
    return new Uint8Array(await globalThis.crypto.subtle.deriveBits({ name: 'HKDF', hash: 'SHA-256',
      salt: encoder.encode('worta/hkdf/account-object-key/salt/v1'),
      info: new Uint8Array(concat(encoder.encode('worta/account-object-key/v1'), new Uint8Array([2, 2]), encodeAccountTuple(context))),
    }, key, 256))
  } finally { input.fill(0) }
}
export async function encryptAccountObject(amk: AccountMasterKey, context: AccountObjectContext, plaintext: Uint8Array): Promise<AccountObjectEnvelope> {
  const key = await deriveAccountObjectKey(amk, context)
  try {
    const sodium = await getSodium(), nonce = sodium.randombytes_buf(24)
    const ciphertext = sodium.crypto_aead_xchacha20poly1305_ietf_encrypt(plaintext, accountObjectAad(context), null, nonce, key)
    return { crypto_version: 2, aad_version: 2, nonce, ciphertext }
  } finally { key.fill(0) }
}
export async function decryptAccountObject(amk: AccountMasterKey, context: AccountObjectContext, envelope: AccountObjectEnvelope): Promise<Uint8Array> {
  if (envelope.crypto_version !== 2 || envelope.aad_version !== 2) throw new CryptoError('unsupported_version')
  if (!(envelope.nonce instanceof Uint8Array) || envelope.nonce.length !== 24 || !(envelope.ciphertext instanceof Uint8Array) || envelope.ciphertext.length < 16) throw new CryptoError('invalid_format')
  const key = await deriveAccountObjectKey(amk, context)
  try {
    const sodium = await getSodium()
    try { return sodium.crypto_aead_xchacha20poly1305_ietf_decrypt(null, envelope.ciphertext, accountObjectAad(context), envelope.nonce, key) }
    catch { throw new CryptoError('decrypt_failed') }
  } finally { key.fill(0) }
}
