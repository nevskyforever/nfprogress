# C12 — Crypto Security / Regression Tests

## Scope

C12 turns C11's isolated client crypto module into a regression-tested security
contract. It adds no cloud ciphertext schema, HTTP upload, key storage, unlock
UI, trusted-device implementation, Sync Engine, or C13 DTO. C8 remains gated:
`encryptedInitialUpload` is `false`. C9 remains metadata-only.

The suite covers 256-bit AMK/Recovery-Key generation; password and Recovery AMK
wrapping; empty, binary, Unicode, and bounded large object roundtrips; fresh
XChaCha20-Poly1305-IETF nonces; and caller-buffer non-mutation. It verifies that
authentication failure returns no plaintext. This is the strongest presently
available corrupt-object invariant. The end-to-end requirement that a corrupt
cloud object must not overwrite the sole valid local copy is an obligatory C15,
then C23, integration test once the real sync apply path exists.

## Compatibility vectors v1

`frontend/src/crypto/c11-compatibility-vectors.v1.json` is the stable,
machine-readable C11 v1 contract. Byte values are lowercase hex; XChaCha
`ciphertext` is combined ciphertext followed by its 16-byte authentication tag.
It fixes deterministic inputs/outputs for:

- HKDF-SHA-256 Object Key derivation, including canonical context bytes;
- XChaCha20-Poly1305-IETF key/nonce/plaintext/AAD/ciphertext;
- Argon2id13 passphrase, 16-byte salt, opslimit, memlimit, and 32-byte KEK;
- password-wrap and Recovery-wrap primitive AAD, nonce, and combined ciphertext.

The test verifies these using Web Crypto for the production HKDF path and the
vetted libsodium primitive for AEAD/Argon2id. Future Rust, Desktop, Android, iOS,
and Web implementations must pass the same vectors. They do not exist yet, so
C12 makes no claim to have tested a native implementation.

## Fail-closed and separation checks

Tests corrupt object ciphertext body/tag, nonce, crypto version, and AAD version;
and substitute each user/project/entity/type identity. Authentication failures are
`decrypt_failed`; malformed structures are `invalid_format`; unknown versions are
`unsupported_version`. Canonical UTF-8 length-prefix encoding has vectors for
Unicode/multibyte inputs and rejects empty, unpaired-surrogate, and byte-limit
violations without ambiguous concatenation.

The KDF record requires explicit Argon2id13/version, a 16-byte salt, and finite
safe positive integer parameters. It rejects malformed and out-of-libsodium-bound
values before an allocation. Stored parameters are used exactly; no weaker retry
or silent downgrade exists. Final product calibration across Desktop/Android/Web
is still an open decision, not a C12 product maximum.

Password passphrase rewrap and Recovery-Key regeneration are compositionally
tested: they produce a new record, preserve the same AMK, invalidate the old
unlocking secret for the replacement record, and require no object re-encryption.
Object HKDF context, object AAD, password-wrap AAD, and Recovery-wrap AAD are
separate domains; wrappers cannot be substituted even when the underlying
32-byte material is deliberately equal.

## Leakage and build boundary

Runtime guards assert crypto operations do not invoke fetch or console APIs, and
a focused source-boundary guard excludes network/browser-storage/cookie/URL
globals from the isolated crypto module. Typed errors are checked not to contain
passphrases, Recovery Keys, AMK/KEK/Object Key material, plaintext, or ciphertext.
The code retains C11's best-effort `memzero` design; JavaScript/WASM cannot prove
absolute GC-memory erasure without test-only internal hooks.

Frontend CI now runs the focused C7/C8/C9/C11/C12 tests and `npm run build`, so a
Vite/libsodium ESM/WASM bundle regression is caught. The runtime remains locally
bundled—there is no CDN fallback or external crypto origin.

## Explicit limits and deferred work

C12 does not mean local SQLite encryption. It also does not protect an unlocked
browser against malicious served JavaScript, XSS, or privileged extensions; those
remain outside storage-E2EE guarantees until the later trusted-Web/CSP work.

Deferred: final Argon2 calibration; native secure storage; native consumption of
these vectors; encrypted server schema/DTO (C13, not started); real encrypted
object sync (C15); trusted Web storage/CSP (C21); and corrupt-cloud-object/local-
copy integration testing in C15/C23.
