import {
  AAD_VERSION,
  CONTEXT_VERSION,
  CRYPTO_VERSION,
  MAX_ENTITY_TYPE_BYTES,
  MAX_IDENTIFIER_BYTES,
  OBJECT_AAD_DOMAIN,
  OBJECT_KEY_CONTEXT_DOMAIN,
} from './constants'
import { CryptoError } from './errors'
import type { ObjectCryptoContext } from './types'

const encoder = new TextEncoder()

function hasUnpairedSurrogate(value: string): boolean {
  for (let index = 0; index < value.length; index += 1) {
    const code = value.charCodeAt(index)
    if (code >= 0xd800 && code <= 0xdbff) {
      const next = value.charCodeAt(index + 1)
      if (!(next >= 0xdc00 && next <= 0xdfff)) return true
      index += 1
    } else if (code >= 0xdc00 && code <= 0xdfff) {
      return true
    }
  }
  return false
}

function encodeRequired(value: string, maximumBytes: number): Uint8Array {
  if (typeof value !== 'string' || value.length === 0 || hasUnpairedSurrogate(value)) {
    throw new CryptoError('invalid_format')
  }
  const bytes = encoder.encode(value)
  if (bytes.length === 0 || bytes.length > maximumBytes) throw new CryptoError('invalid_format')
  return bytes
}

function u32be(value: number): Uint8Array {
  const output = new Uint8Array(4)
  new DataView(output.buffer).setUint32(0, value, false)
  return output
}

function concatenate(parts: readonly Uint8Array[]): Uint8Array {
  const length = parts.reduce((total, part) => total + part.length, 0)
  const result = new Uint8Array(length)
  let offset = 0
  for (const part of parts) {
    result.set(part, offset)
    offset += part.length
  }
  return result
}

function contextFields(context: ObjectCryptoContext): Uint8Array[] {
  return [
    encodeRequired(context.userId, MAX_IDENTIFIER_BYTES),
    encodeRequired(context.projectId, MAX_IDENTIFIER_BYTES),
    encodeRequired(context.entityId, MAX_IDENTIFIER_BYTES),
    encodeRequired(context.entityType, MAX_ENTITY_TYPE_BYTES),
  ]
}

function encodeDomainSeparatedContext(domain: string, formatVersion: number, context: ObjectCryptoContext): Uint8Array {
  const fields = contextFields(context)
  const parts: Uint8Array[] = [encoder.encode(domain), Uint8Array.of(formatVersion, CRYPTO_VERSION)]
  for (const field of fields) parts.push(u32be(field.length), field)
  return concatenate(parts)
}

/** Fixed bytes: ASCII domain, one format byte, one crypto byte, then four u32be UTF-8 fields. */
export function encodeObjectKeyContext(context: ObjectCryptoContext): Uint8Array {
  return encodeDomainSeparatedContext(OBJECT_KEY_CONTEXT_DOMAIN, CONTEXT_VERSION, context)
}

/** Object AEAD AAD uses the same stable identity fields, but an independent domain/version. */
export function encodeObjectAad(context: ObjectCryptoContext): Uint8Array {
  return encodeDomainSeparatedContext(OBJECT_AAD_DOMAIN, AAD_VERSION, context)
}

export function encodeFixedAad(domain: string): Uint8Array {
  return concatenate([encoder.encode(domain), Uint8Array.of(CRYPTO_VERSION)])
}

export function utf8Encode(value: string): Uint8Array {
  return encoder.encode(value)
}
