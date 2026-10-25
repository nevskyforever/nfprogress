# MVP6.0.10 — isolated staging restore drill

**Date:** 2026-10-26 (Samara)

**Repository baseline:** `5b87250dad98b4fb6e46237ef1aee22d91429b42`

**VPS scope:** existing SpaceWeb staging only; no install, service start, network exposure, or live-database switch.

## Outcome

The restored copy matched the stopped staging database at PostgreSQL 16.15.
The active staging database was never modified. The backend unit stayed stopped
and disabled; SSH, PostgreSQL and Caddy stayed active. PostgreSQL and Caddy
remained loopback-only and only SSH remained publicly reachable.

The pre-MVP6.0.09 empty-database archive was present on the VPS with its
recorded SHA-256 `7b545f6b02727806e45756d1c6f9f635b2cc672e05495fb2c45f31d5a6aa5af3`;
the local retained copy had the same hash. The paired local blob-inventory copy
matched its recorded hash
`61e7555f5481f71c148610a133af605966bdb762be59a37ff07b1220140a0b13`; no such
inventory file was present in the VPS temporary directory. That earlier archive
represents the empty pre-migration state, so this drill captured a new matched
snapshot of the current migrated state instead of treating the older archive as
a current backup.

Before capture, `worta-staging.service` was inactive and disabled, the source DB
had no other connections, and the isolated blob root contained zero files. The
source had 18 tables at Alembic head `private_invitations`, zero users, zero
invitations, zero cloud projects and zero blob metadata; the registration mode
was `closed`. The database was 8,567,831 bytes.

The matched current-state artifacts remain on the VPS in this root-only
directory:

`/var/lib/worta/staging/tmp/mvp610-restore-20261025T202011Z`

| Artifact | Size | SHA-256 |
| --- | ---: | --- |
| `worta_stage.dump` | 54,352 bytes | `1cfb50f9df8fcc5ca73e73c546f60da48c030d147ba5bf13b6b165260ff4b49b` |
| `staging-blobs.tar` | 10,240 bytes | `f5f3f6532e13d67b2bf008723aa1b245a00e8730bbbdd5b91dc55ad65308029d` |

Both artifacts are mode `0600` inside a mode `0700` root-owned directory. The
blob archive is empty because the actual staging blob root was empty. The
restored blob directory also had zero files. These current-state artifacts were
not transferred off-host because no external backup destination was approved.

## Database restore verification

The custom-format archive passed `pg_restore -l` with 110 table-of-contents
entries. It was restored into a newly created database named
`worta_stage_restore_mvp610_20261025`, with the source UTF-8 and
`ru_RU.UTF-8` locale. The temporary database was separate from `worta_stage`.
The installed Alembic script tree reported the same single head,
`private_invitations`, without applying any migration.

Source and restored database both reported:

`private_invitations | 18 tables | 0 users | 0 invitations | 0 cloud projects | 0 encrypted blob rows | closed`

Exact row counts for all 18 tables matched. Structural inventories also
matched: 102 constraints, 29 indexes and 154 columns, with identical sorted
names/types/validity, index definitions, and column types/nullability. A raw
`pg_dump --schema-only` text hash differed because PostgreSQL re-rendered
several equivalent CHECK expressions with explicit casts and generated a new
per-dump `\\restrict` token; the catalog inventory checks above matched. A
synthetic reserved-username fixture was inserted, read back and removed only
in the temporary restore database. No user or invitation was created.

`pg_restore` completed in 0.14 seconds with 10,112 KiB peak process RSS. The
restore used no application worker or Argon2 operation. Point-in-time
`MemAvailable` samples were 639,700 KiB before capture, 657,162,240 bytes after
the restore, and 646,352 KiB after cleanup; swap was absent throughout. Root
free space was 6,683,795,456 bytes before capture, 6,680,678,400 bytes after
the restore, and 6,650,933,248 bytes at final inspection. Host readings can
fluctuate and were not attributed to the drill. These are point-in-time
observations, not a capacity or load acceptance.

## Blob restore and integrity checks

The actual staging blob archive and extracted copy both contained zero files;
there were no existing ciphertext objects to recover or exercise through a
client. The installed `backend/app/cloud/blob_store.py` SHA-256 matched the
repository file (`6d0872359f1d1c5b0b325206e623c5432adc5dba9948968c2310c594457c2489`).

Using that installed file-store implementation, a separate, temporary harness
generated 256 random opaque bytes (no encryption key), archived them and
restored the synthetic fixture twice. The verified ciphertext SHA-256 was
`d7741ee0eb16d9befd4383fbb877c5b21c7af0177c92faab36cf174828d78bea`; its
fixture-archive SHA-256 was
`76bbadf10ffb229cb2ab07eb9ceb290fc8aecd5de50d5f11ca8a829b5ff4d1c6`.
`read_verified` returned identical bytes after both restores and after a third
recovery extraction. A missing file raised `BlobMissing`; a same-length
corrupted file raised `BlobStoreError`. This validates the file-store
integrity/refusal path with synthetic bytes, not E2EE, a database-to-blob client
workflow, or recovery of a real staging blob.

## Cleanup and remaining acceptance

The temporary restore database and synthetic harness files were removed only
after recording the checks above and confirming their exact names and ownership.
The original `worta_stage` database, its `private_invitations` head, and its
blob directory were not modified. The matched current-state DB/blob archives
and empty restored-blob directory remain in the private evidence directory
above; the earlier pre-migration archive remains untouched.

The focused local `bash scripts/maintenance/run_cloud_restore_preflight.sh`
check passed (**1/1**, 1.84 seconds); it used a unique labeled PostgreSQL 16
container and left no container with the test label. Pytest emitted one
upstream Starlette deprecation warning. `git diff --check` passed. No Actions
workflow was queried. Static workflow inspection shows no expected CI for these
paths: Cloud backend tests include `docs/cloud/**`, while this task changed only
the checkpoint, MVP overview, and `docs/infra/**` protocol.

This is **not C23 acceptance**. C23 still needs an owner-approved independent
backup destination and retention/RPO/RTO, a matched off-host DB plus real
encrypted-blob copy, a restore into a fresh isolated target, and recovery on
paired real clients with their existing encryption keys. No key was stored on
the VPS. Keep the service stopped, tester access closed, public registration
CLOSED, and Note reader/writer/ACK gates disabled until C21/C22/C23 and the
separate access approvals are accepted. Web remains **89.36%** and public
release remains blocked.
