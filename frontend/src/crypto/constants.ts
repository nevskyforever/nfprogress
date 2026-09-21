export const CRYPTO_VERSION = 1 as const
export const CONTEXT_VERSION = 1 as const
export const AAD_VERSION = 1 as const
export const KDF_VERSION = 1 as const
export const PASSWORD_WRAPPING_VERSION = 1 as const
export const RECOVERY_WRAPPING_VERSION = 1 as const

export const KEY_BYTES = 32 as const
export const XCHACHA20POLY1305_NONCE_BYTES = 24 as const
export const ARGON2ID_SALT_BYTES = 16 as const
export const ARGON2ID13 = 'argon2id13' as const

/** libsodium's v1 interactive profile; calibration is a pre-production decision. */
export const C11_ARGON2ID_OPSLIMIT = 2 as const
export const C11_ARGON2ID_MEMLIMIT = 67_108_864 as const

export const OBJECT_KEY_HKDF_SALT = 'worta/hkdf/object-key/salt/v1'
export const OBJECT_KEY_CONTEXT_DOMAIN = 'worta/object-key/v1'
export const OBJECT_AAD_DOMAIN = 'worta/object-aad/v1'
export const PASSWORD_WRAP_AAD_DOMAIN = 'worta/amk/password-wrap/v1'
export const RECOVERY_WRAP_AAD_DOMAIN = 'worta/amk/recovery-wrap/v1'

export const MAX_IDENTIFIER_BYTES = 512
export const MAX_ENTITY_TYPE_BYTES = 128
