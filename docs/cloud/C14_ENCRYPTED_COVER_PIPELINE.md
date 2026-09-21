# C14 — Encrypted Cover / Blob Pipeline

C14 creates and tests a separate client-encrypted transport for project covers.
It does **not** enable a project Sync Engine or make a cloud project fully
synchronised: C8 `encryptedInitialUpload` remains `false`, C9 remains protocol
v1 metadata-only, C13 `encrypted_objects` is unchanged, and C15 is the first
real encrypted object sync.

## Client boundary

The editor accepts JPEG/PNG/WebP inputs up to 20 MiB, keeps its 2:3 crop/zoom
workflow, and prepares a JPEG no larger than 1000×1500. Encoding starts at that
resolution and reduces JPEG quality, then resolution if necessary, based on raw
`Blob.size`; prepared plaintext is at most 2 MiB. Local `cover_image` remains a
Data URL for compatibility and C14 does not upload it automatically.

For a later explicit upload, the client generates a UUID `blobId` once and
retains it for retry. C11 encrypts prepared bytes with context
`{ userId, projectId, entityId: blobId, entityType: "project_cover" }`.
`blobId` gives every cover version an identity and binds HKDF/AAD, so a server
cannot swap a ciphertext from another cover version. The server receives neither
plaintext cover, AMK, KEK, Object Key, master passphrase, nor a decrypt request.

## Transport and storage

`PUT` and `GET /api/v1/cloud/projects/{project_id}/covers/{blob_id}` use raw
`application/octet-stream`. Metadata is carried in `X-WORTA-Crypto-Version`,
`X-WORTA-AAD-Version`, and canonical unpadded Base64URL `X-WORTA-Nonce` headers.
Current versions are 1; a nonce is 24 bytes. Ciphertext maximum is
2 MiB + 16-byte XChaCha tag (2,097,168 bytes). GET returns no-store/nosniff
headers and raw ciphertext only.

PostgreSQL `encrypted_blobs` contains only `(user_id, blob_id)`, project ID,
kind, crypto/AAD versions, nonce, ciphertext size, SHA-256 of ciphertext, and
time. It does not contain a Base64 blob, large ciphertext, plaintext hash,
filename, MIME, image dimensions, or keys. This differs from C13
`encrypted_objects`, which is a small encrypted-object sidecar stored in
PostgreSQL; C14 ciphertext files are external binary blobs.

The stdlib filesystem store is optional via `NFPROGRESS_CLOUD_BLOB_DIR`. If it
is absent, only C14 endpoints return `blob_storage_unavailable`; application
startup remains available. Files are `<root>/<user UUID hex>/<blob UUID hex>.blob`
and contain raw ciphertext only, never JSON/Base64/plaintext. IDs are validated
UUIDs; project IDs and filenames are never paths.

Writes use a same-directory temporary file, flush/fsync, then `link` publication
that cannot overwrite an existing final file. PostgreSQL advisory locks serialize
one `(user_id, blob_id)` upload. Exact metadata and bytes retry verifies storage
integrity and returns duplicate success, even after C8 disable. Any difference
conflicts. New uploads require an enabled C8 project; existing owned downloads
also remain available after disable. There is no cloud-project FK cascade and no
DELETE endpoint: project→current-cover reference, replacement/GC and lifecycle
are not designed yet.

Filesystem and PostgreSQL are not one ACID transaction. A newly created file is
best-effort removed when its DB transaction fails; a crash between publication
and commit may leave an orphan ciphertext file. Orphan cleanup, account physical
blob cleanup, production object storage/hardening, disaster/corruption/deletion
semantics are deferred to C22/C23. C18 defines project/blob references and full
lifecycle. Admin receives no blob API, content, preview, path, or decrypt
capability. SHA-256 is solely ciphertext integrity/idempotency metadata, never
cross-user deduplication or a plaintext hash.
