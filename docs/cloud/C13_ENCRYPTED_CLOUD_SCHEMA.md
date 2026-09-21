# C13 — Encrypted Cloud Schema

## Scope

C13 creates PostgreSQL storage foundations for client-encrypted material. It adds
`user_crypto` and `encrypted_objects`, plus future-facing DTO validation. It does
not add a production endpoint, upload, Sync Engine, server cryptography, or
decryption capability.

> C13 creates server storage schema capable of holding only client-encrypted
> protected content; production encrypted sync is not yet connected.

## Storage boundary

`user_crypto` has at most one row per account. It stores a password-wrapped AMK
record as typed columns: protocol/wrapping/KDF versions, public `argon2id13`
metadata, salt, KDF limits, nonce, and wrapped AMK. It may additionally store a
Recovery-Key-wrapped AMK record. Recovery columns are all NULL or all present;
the Recovery Key itself is never stored.

PostgreSQL stores the byte fields as `BYTEA`. Salt, nonce, versions, KDF
algorithm and KDF limits are server-visible public crypto metadata. The server
never stores a master passphrase, passphrase verifier, plaintext AMK, Recovery
Key, KEK, Object Key, Project Key, plaintext project data, escrow key, or
universal master key.

`encrypted_objects` stores an immutable ciphertext version under the C9 identity
`(user_id, event_id)`. It contains only crypto version, AAD version, nonce,
ciphertext and storage time. Every row references the matching composite C9
`sync_events(user_id, event_id)` key. This lets concurrent versions retain
different event IDs without mutable ciphertext overwrite.

C8 `cloud_projects` remains only a cloud-slot registry. C9 remains metadata-only:
ciphertext is deliberately not placed in `sync_events`, preserving its v1
transport contract, cursor/ack semantics, and retry identity. C8's
`encryptedInitialUpload` capability remains `false`.

## Future wire contract

Future C15/C21 APIs use unpadded, canonical Base64URL strings for every binary
field. Padding, invalid alphabet, malformed forms, alternative non-canonical
representations, and incorrect decoded lengths reject. The password DTO mirrors
the C11 record with nested KDF data; Recovery and object-envelope DTOs mirror
their C11 records. DTOs contain no decrypt operation or secret plaintext field.

## Lifecycle and deferred work

The FK follows C9 accepted-event lifecycle: deleting an event removes its
ciphertext sidecar, and deleting an account cascades through its events and
crypto configuration. C13 intentionally does not decide cloud-disable/delete
ciphertext lifecycle, because C9 retains accepted history after C8 disable.

C14 separately designs encrypted covers/blob storage and size policy. C15 is the
first real encrypted object sync and must define transactional idempotency. C17
will define conflict handling. Native secure storage, trusted Web storage, and
C23 deletion/disaster/failure semantics remain deferred.
