export type CryptoErrorCode =
  | 'unsupported_version'
  | 'invalid_format'
  | 'invalid_key_length'
  | 'kdf_failed'
  | 'decrypt_failed'
  | 'runtime_unavailable'

const messages: Readonly<Record<CryptoErrorCode, string>> = {
  unsupported_version: 'Unsupported cryptographic format version.',
  invalid_format: 'Invalid cryptographic input format.',
  invalid_key_length: 'Invalid cryptographic key length.',
  kdf_failed: 'Key derivation failed.',
  decrypt_failed: 'Decryption or authentication failed.',
  runtime_unavailable: 'Cryptographic runtime is unavailable.',
}

export class CryptoError extends Error {
  readonly name = 'CryptoError'

  constructor(readonly code: CryptoErrorCode) {
    super(messages[code])
  }
}

export function isCryptoError(error: unknown): error is CryptoError {
  return error instanceof CryptoError
}
