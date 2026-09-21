export interface Base64UrlDecodeOptions {
  expectedLength?: number
  minimumLength?: number
  maximumLength?: number
}

const BASE64URL = /^[A-Za-z0-9_-]*$/

function invalid(): never {
  throw new TypeError('Invalid canonical Base64URL value.')
}

/** Encode bytes as canonical, unpadded Base64URL. */
export function encodeBase64Url(value: Uint8Array): string {
  if (Object.prototype.toString.call(value) !== '[object Uint8Array]') invalid()
  let binary = ''
  for (const byte of value) binary += String.fromCharCode(byte)
  return btoa(binary).replaceAll('+', '-').replaceAll('/', '_').replace(/=+$/, '')
}

/** Decode only canonical, unpadded Base64URL and enforce decoded byte limits. */
export function decodeBase64Url(value: string, options: Base64UrlDecodeOptions = {}): Uint8Array {
  if (typeof value !== 'string' || !BASE64URL.test(value) || value.length % 4 === 1) invalid()
  let binary: string
  try {
    binary = atob(value.replaceAll('-', '+').replaceAll('_', '/') + '='.repeat((4 - value.length % 4) % 4))
  } catch {
    invalid()
  }
  const decoded = Uint8Array.from(binary, character => character.charCodeAt(0))
  if (encodeBase64Url(decoded) !== value) invalid()
  if (options.expectedLength !== undefined && decoded.byteLength !== options.expectedLength) invalid()
  if (options.minimumLength !== undefined && decoded.byteLength < options.minimumLength) invalid()
  if (options.maximumLength !== undefined && decoded.byteLength > options.maximumLength) invalid()
  return decoded
}
