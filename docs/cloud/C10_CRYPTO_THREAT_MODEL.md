# C10 — Crypto Threat Model

## Decision and scope

C10 fixes the cryptographic architecture before C11. It is documentation-only: it
does not implement crypto, server/schema changes, upload, trusted devices,
Recovery Key, browser storage, WebAuthn, or a project switch.

WORTA's E2EE invariant is deliberately narrow:

> The WORTA server, PostgreSQL, blob storage, backups, and an ordinary server
> administrator must not have the technical ability to decrypt protected project
> content from server-side stored data.

This is not a claim that the server knows nothing. It knows account/auth metadata
and sees selected routing/sync metadata, timing, and sizes. E2EE does not protect
a device or browser that is already compromised while unlocked.

## Audited current boundary

| Area | Current state | C10 consequence |
| --- | --- | --- |
| C2 auth | Account password reaches FastAPI over TLS; PostgreSQL has its Argon2id hash. Short-lived access tokens and refresh sessions exist. | It is not crypto material. |
| C7 admin | Access/refresh tokens are runtime-memory only, not browser storage/cookies/IndexedDB/URLs. | Admin gets no decrypt/read-project endpoint or AMK. |
| C8 | `cloud_projects` is only a registry of stable cloud-enabled IDs; it has no content. | `encryptedInitialUpload` remains `false`. |
| C9 | v1 exposes event/device/project/entity IDs, type, operation, revision, timestamps, cursor; no payload/ciphertext. | This metadata is not secret; C10 does not change it. |
| Local state | SQLite/C9 outbox are local-first state, not encrypted-at-rest E2EE storage. | Do not claim local SQLite encryption. |
| Tauri | CSP includes `script-src 'self'`; style permits `'unsafe-inline'`; no secure-key-storage capability/plugin. | Native secure AMK storage is unimplemented. |
| Web | local/session storage holds non-secret UI state; production CSP is not a proven crypto boundary. | Keys may not use those stores. |
| Capacitor | No secure-storage/Keystore integration is selected. | Mobile protected storage is deferred. |
| Dependencies | No selected C11 frontend crypto dependency or cross-runtime crypto module. | C11 must select and validate one. |

Prerequisites: C11/C12 crypto implementation/tests; C13 encrypted server schema;
C16/C20 native secure storage/sync; C21 trusted-Web storage, CSP/XSS/auth-cookie
boundary; C22 deployment/supply-chain hardening; C23 failure/disaster/security
regressions. C10 implements none.

## Independent passwords and lifecycles

The **account password** authenticates the cloud account/API. It reaches the
server over TLS and is verified against C2's Argon2id hash. Email recovery may
reset it. It is never an E2EE root key, KEK, Recovery Key, or AMK input. Reset
must not decrypt old cloud data.

The **master encryption password/passphrase** unlocks protected content locally.
It is never sent to FastAPI, logged, stored plaintext, placed in a cookie,
localStorage, or sessionStorage. The server stores no hash/verifier of it. Even
if a user chooses identical strings, implementation must not reuse C2's server
hash or derive encryption material from it. Access token, refresh cookie, admin
role, account reset, and server session are not crypto unlocks.

Authentication answers “who may access account/API?” E2EE unlock answers “can
this client obtain plaintext AMK?” Thus session revocation/device revocation
blocks future server access, not guaranteed deletion of downloaded plaintext or
local data.

## Key hierarchy

**Account Master Key (AMK)** is a client-CSPRNG-generated random 256-bit secret,
the E2EE account root. It is never derived from account password, sent plaintext,
or disclosed plaintext to the server.

```text
master passphrase --Argon2id--> KEK --AEAD wrap/unwrap--> AMK
```

Each password-wrapping record has unique random salt, versioned KDF algorithm and
parameters, wrapping version, nonce, and encrypted AMK. Salt/parameters/version
are non-secret metadata and support upgrades. C11 must benchmark supported
Desktop/Mobile/Web devices, select no less than a reasonable modern baseline, and
never silently lower cost for a weak device. This Argon2id is independent of C2
server-side password hashing.

There is no server-held random Project/Object Key per object:

```text
Object Key = HKDF(AMK, versioned, domain-separated canonical context)
```

Context includes crypto protocol/version, stable account/user ID, stable project
ID, stable object/entity ID, and object/entity type. Canonical binary encoding is
a fixed ASCII domain label, format-version bytes, and fixed-order length-prefixed
UTF-8 or raw-ID bytes. Ambiguous concatenation is forbidden. Titles/display names
and mutable project names are never key input; stable IDs are identity.

## AEAD, nonce, AAD, and envelope

C11's fixed AEAD is **XChaCha20-Poly1305-IETF** through a vetted
libsodium-compatible implementation: authenticated encryption, a 192-bit nonce,
and portable random-nonce use after cross-runtime validation. Never handwrite
ChaCha/Poly1305; never use raw stream cipher or unauthenticated encryption.

Every encryption operation receives a fresh random nonce. It is non-secret and
stored with ciphertext, but must never intentionally repeat with the same key.
Reuse is release-blocking. If C11 cannot establish cross-platform XChaCha
compatibility, it must stop for an architecture decision, not silently replace it.

AAD has fixed length-prefixed binary serialization of protocol domain label,
crypto format version, account/user ID, project ID, object/entity ID, and object/
entity type. Its own version is documented; malformed/duplicate fields reject.
Revision/schema version is intentionally not mandatory AAD: binding mutable
revision requires normal re-encryption and must be designed with C13/C17 sync
semantics. The binding detects cross-user/project/object/type/format substitution.

A future object envelope logically has `crypto_version`, `nonce`,
`ciphertext`, and authenticated canonical context. Password AMK wrapping has
wrapping version, KDF version, salt, KDF parameters, nonce, encrypted AMK.
Recovery wrapping has a separate record/context. This is not a C13 schema.

## Data classification and server storage

| Class | Treatment | Server visibility |
| --- | --- | --- |
| Protected project content | Client-encrypt before future C13+ upload: title/name/description; stages/sources names/text; manuscripts/documents; notes; maps; game/project user content; custom rewards; user metadata; covers; attachments; imports; integration-related content; future arbitrary user-authored fields. | Ciphertext, nonce, format/version, size/blob reference only. |
| Filenames/MIME | User-authored filenames are protected. MIME/type is plaintext only for concrete protocol need. | Minimize; never expose for convenience. |
| Account/auth metadata | Not E2EE. | User UUID, username, email, role/status, account timestamps, auth/session state, registration/limits metadata. |
| Sync/storage metadata | Open minimal routing data. | Opaque project/object IDs, device ID, entity type if required plaintext, operation/tombstone, revision, server sequence/cursor, timestamps, crypto format/version, nonce, ciphertext size/blob reference, encrypted bytes. |

This is the exhaustive C10 plaintext-server allowlist—no vague “and other.”
It can reveal project/object counts, types, activity/frequency/time, approximate
sizes, and intra-account object relations. C9 metadata is openly visible; future
minimization is optional hardening, not C10 transport redesign.

The server may store wrapped/encrypted AMK, salt/KDF parameters/version, crypto
version, Recovery-Key-wrapped AMK, device/trust metadata, ciphertext/nonces,
allowlisted metadata, and encrypted blobs. Correctly AEAD-wrapped
`encrypted_master_key` is not plaintext AMK and need not itself be secret. It
must never store master passphrase, server-side passphrase verifier, plaintext
AMK/Recovery Key/KEK/Object Keys, or protected plaintext.

Covers and attachments are protected; sensitive user-authored filenames are too.
Large objects need a later safe chunk/blob pipeline and must not be put in C9
events.

## Recovery Key and trusted devices

A future **Recovery Key** is random high-entropy client-generated secret. It is
not either password, is never sent plaintext, and independently wraps/unwraps the
same AMK. Server may hold only Recovery-Key-wrapped AMK plus public metadata; the
user saves it outside WORTA. Email cannot recover it.

If master passphrase, Recovery Key, and every trusted device that can unlock AMK
are lost, encrypted cloud data are cryptographically unrecoverable. Email can
recover the account, not old E2EE data. This is an intentional UX/security tradeoff.

“Запомнить это устройство” never stores master passphrase. After unlock it may
store only protected AMK recovery material: macOS Keychain, Windows OS-protected/
DPAPI-backed design, iOS Keychain, Android Keystore-backed design. C11/C20 must
choose/verify a supported implementation; none is selected. Server trusted-device
records contain no plaintext AMK.

For untrusted/shared Web, remember-device is off: AMK/KEK only in runtime memory;
logout clears available key material; tab/browser close ends unlock state; no
plaintext key in localStorage/sessionStorage/cookies. Future trusted personal Web
(C21) may use protected wrapping such as non-extractable WebCrypto `CryptoKey`,
IndexedDB only for wrapped material/non-extractable handles, or practical
passkey-assisted wrapping. C10 chooses none. C21 must prove cross-browser
properties. Never store master password, plaintext AMK/KEK, or E2EE keys in
browser storage/auth cookies.

## Local-first, deletion, and admin

WORTA remains local-first: projects exist independently of cloud; C8 OFF is
local-only; future C8 ON retains local working copy and syncs encrypted; sync
failure must not destroy the only local copy. This is not local SQLite encryption.

| Operation | What it does not prove |
| --- | --- |
| Logout | Does not delete downloaded plaintext/local data. |
| Revoke auth session | Blocks future session use, not local deletion. |
| Revoke trusted device | Blocks future authenticated access/sync and possibly future wrapped-key retrieval, not remote wipe. |
| Disable cloud project | Alters cloud participation, not local copies. |
| Delete cloud ciphertext | Removes server data subject to backup/retention, not other devices' copies. |
| Delete local project | Affects only that copy under local deletion semantics. |
| Remote wipe | Must not be claimed unless downloaded data can demonstrably be erased; C10 defines none. |

C7 Admin must never receive `decrypt`, `open`, or `read project`. It sees
administrative/minimal operational metadata only. No root/admin gets AMK. No
escrow/admin-recovery key or universal server master decryption key may exist.

## Threat matrix

| Scenario | Required outcome / honest limit |
| --- | --- |
| Stolen PostgreSQL dump, blob storage, backup | Protected plaintext is not disclosed from encrypted stored data. |
| Curious/compromised server administrator | Cannot decrypt DB/blob/filesystem data without an unlocked client/key. |
| Network attacker | TLS is mandatory; E2EE does not replace HTTPS. |
| Stolen locked native device | Cloud E2EE differs from unclaimed local-disk encryption; trusted material needs future OS secure storage. |
| Stolen unlocked device or malware | Out of E2EE storage guarantee: plaintext/keys may be accessible after unlock. |
| Account-password compromise | Account/API access alone cannot decrypt without crypto unlock. |
| Email compromise + account reset | Can seize auth and perhaps delete/change encrypted data; cannot automatically obtain AMK. |
| Recovery Key compromise | High-severity secret: with needed wrapped material/cloud access it can recover AMK. |
| Master-passphrase compromise | Offline guessing of wrapped AMK is possible; Argon2id and strong passphrase reduce risk. |
| Malicious backend, signed native client | Server-side data still yields no keys; signed-update/supply-chain security matters. |
| Malicious Web deployment/supply chain | Server-delivered malicious JS at unlock can steal passphrase, AMK, plaintext; Web is not signed-native equivalent. |
| XSS/privileged malicious extension | Critical while unlocked; sufficient page privileges can read plaintext/key material. |
| Rollback/replay of valid ciphertext | AEAD authenticates bytes, not freshness; C9 revisions/sequences and C17 conflict layer decide ordering. |
| Ciphertext swapping | Canonical AAD detects cross-user/project/object/type/format substitution. |
| Nonce reuse | Forbidden under a key; random fresh nonce every operation. |
| Logs/crash/telemetry/support | Never include passphrases, keys, protected plaintext. First release assumes no analytics/ads/tracking. |

Web mitigations reduce, not remove, the deployment threat: strict CSP, no arbitrary
third-party JS or analytics on crypto surface, dependency pinning/audit, protected
build/deploy pipeline, review, XSS sanitization, minimal dynamic loading, and
future reproducible/static delivery where practical.

E2EE provides confidentiality and ciphertext integrity when correctly implemented,
not availability. A malicious server can delete/withhold/replay valid data, block
sync, destroy account, or alter open metadata. Freshness/rollback need sync/version
logic and potentially later cryptographic mechanisms.

## Versioning, rotation, fail closed

Crypto format, KDF version/parameters, wrapping version, and object-encryption
version are distinct and explicit. Master-passphrase change unlocks AMK via old
method, derives new KEK, re-wraps same AMK, and does not re-encrypt objects.
Recovery Key regeneration is analogous. AMK rotation is separate/heavy and can
require object re-keying. Algorithm migration handles a supported old version or
fails closed; no silent downgrade.

For unknown crypto/KDF version, unsupported KDF, malformed nonce/AAD, invalid
tag, corrupt wrapped AMK, wrong master password, or wrong Recovery Key: issue a
typed crypto error; no partial plaintext; do not overwrite valid local copy; do
not repair ciphertext; do not log secrets. Auth and crypto failures remain
distinct internal states, but UI must not become a sensitive oracle. Zeroize
secret buffers where runtime/library permits; GC Web runtimes cannot promise
absolute memory erasure.

## Product wording boundary

Product may say protected cloud-project content is encrypted on-device before
upload, the server stores ciphertext, and it receives neither master encryption
password nor plaintext encryption keys. It must not promise server ignorance,
anonymity, protection from every compromise, impossibility of access under all
conditions, identical Web/native trust, or encrypted local SQLite before it exists.

## C11 implementation contract

- AMK: client CSPRNG, exactly 256 random bits.
- Password KDF: Argon2id; versioned salt/parameters benchmarked before final costs.
- AEAD: XChaCha20-Poly1305-IETF via vetted libsodium-compatible primitive.
- Object keys: HKDF with the canonical domain-separated context above.
- Every operation: random nonce, canonical AAD, versioned object/wrapping format.
- No secret plaintext server-side; typed errors and practical secret zeroization.
- Cross-runtime test vectors/compatibility required; never handwrite crypto primitives.

## C12 mandatory security tests

C12 must test encrypt/decrypt roundtrip; wrong master password/Recovery Key;
tampered ciphertext/tag/AAD; wrong user/project/object/type; nonce-uniqueness
path; deterministic object-key derivation; separation of users/projects/types;
crypto/KDF version rejection; corrupt wrapped AMK; master-password rewrap preserves
AMK; Recovery-Key rewrap; no secrets in network requests/localStorage/sessionStorage/
cookies/logs/errors; cross-platform vectors; corrupt cloud object never overwrites
sole valid local copy.

## Explicit open implementation questions

Open only: exact benchmarked Argon2id costs; vetted JS/WASM/native package; native
secure-storage integration; trusted-browser protected wrapping; attachment chunk/
blob format; possible later C9 metadata minimization. Closed: server-side plaintext
and escrow are forbidden; account password cannot be AMK; master passphrase is never
sent to server; unauthenticated encryption and plaintext browser-stored keys are
forbidden.
