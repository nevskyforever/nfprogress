# MVP6.0.09 — first loopback backend deployment

## Preflight and rollback record (before VPS changes, 2026-10-25)

The clean `6.0` checkout, local `origin/6.0`, and remote `origin/6.0` all
matched `f3f0e59b682e680a7cbc1cdc33a2793ef23e311b`. The owner supplied
independent MVP6.0.07 Cloud run `40215702912`, 6/6 SUCCESS; Codex did not
query Actions. SSH as the previously verified `worta-admin` succeeded to
SpaceWeb `195.208.60.94`.

The host had Ubuntu 24.04, PostgreSQL 16.15, Caddy 2.6.2, and WORTA CPython
3.13.17. SSH, `postgresql@16-main` and Caddy were active. Only SSH listened
on public IPv4/IPv6; PostgreSQL bound `127.0.0.1:5432` and Caddy bound
`127.0.0.1:8080`, returning 404 for the three closed WORTA hosts. UFW
allowed inbound TCP/22 only. No port 8000 listener, staging service or
enabled unit existed. Available RAM was 691,290,112 bytes (~659 MiB), swap
was absent, and free root disk was 6,947,487,744 bytes (~6.47 GiB).

MVP6.0.08 resources were intact: `worta_stage` is a locked-shell OS account;
the PostgreSQL role is passwordless peer-auth, non-superuser, no CREATEDB or
CREATEROLE, with a two-connection limit. Its database is owned by `postgres`,
has zero user tables and no Alembic version; the role has CONNECT/USAGE but
no database or schema CREATE. Application, data, blob and temporary
directories were empty. The venv had no pip or backend dependencies. The
root-only `staging.env` was mode 0600; its secret was not read or printed.

Baseline SHA-256 values: PostgreSQL HBA
`b67a064b18dd0af7ce20f97c2c044110b2a40e746d723ccecb6dfee659970039`,
PostgreSQL config
`a8917323495057fe87f0a222ee997da43a0b468f1ffbf9ca754716d6ca027bc7`,
Caddyfile
`97e39ff74abf7d6bc15c3ff7630c26d55e5a188c7395001ef0230989208408c9`,
`sshd_config`
`7962003fec1be865b919f3e48185b0a80905774e888e081f530ce1ffa9a22f16`,
inactive unit template
`4c6874361b9e41c19097f8bf1f2b9e890fb74d38a9a19dd10a6b4efab653c0c3`.

The new backend source archive is generated from the exact Git SHA above;
its SHA-256 is
`73deccc30652f4690e229afbf623f01271d90832a1a3d876853f77aa019f4b5e`.
Its unchanged production requirements match the previously verified Python
3.13.17/Linux amd64 lock of 39 wheels, SHA-256
`b3e76eede1f2d7602e1a6b9bf2801718244d39e403029ef212fb84e6d8f4e1fe`.
The assembled transfer bundle SHA-256 is
`10c8d952f05dcf8ecff5d607d05d9a6b4a7a4236fd34bd6356166856c5956855`.
It contains no user data or secrets. The local bundle is retained outside Git
under `.codex/artifacts/worta-mvp609-f3f0e59`.

Before migration, capture the empty database with `pg_dump` and the empty
blob inventory, verify their checksums off-host, and retain them. Later
rollback must stop the staging service, preserve the current DB/blob state,
restore the matched pre-migration dump into a **new empty database** if
needed, and switch only the isolated staging target after verification. Never
downgrade a populated invitation history or overwrite the only DB/blob copy.
If no data has been admitted, the installation can be stopped and removed
after a complete path/role inventory; no automatic deletion is allowed.
PostgreSQL, Caddy, SSH, UFW, DNS and provider snapshots are outside this
stage's rollback boundary.

## Execution record (2026-10-25–26)

The final Linux amd64 bundle is
`/Users/romankisockin/.codex/artifacts/worta-mvp609-f3f0e59/worta-backend-mvp609-f3f0e59-linux-amd64-v2.tar.gz`.
It contains 143 tracked source files and 39 hash-locked production wheels.
The bundle SHA and every listed wheel were verified on the VPS. All 143
installed source files under `/opt/worta/staging/app` matched the archive.
The staging venv was populated offline with bundled pip and
`--no-index --require-hashes`; `pip check` and production imports passed.
No development dependency or system Python setting was changed. Final source
size was 3,064,141 bytes; the venv was 90,121,557 bytes.

Two earlier local packaging attempts were rejected: a macOS tar carried
AppleDouble metadata, and a clean archive omitted tracked
`translations_catalog.py`. The first Alembic invocation with a test profile
hit an import-time legacy data-path error before touching the DB. The final
bundle and migration used production/web configuration with a process-only
synthetic authentication secret; neither the real secret nor a user profile
was read. No backend business logic was changed.

Before migration, an empty DB archive was captured with `pg_dump -Fc` at
`/var/lib/worta/staging/tmp/worta_stage_pre_mvp609.dump`, root:root 0600,
SHA-256 `7b545f6b02727806e45756d1c6f9f635b2cc672e05495fb2c45f31d5a6aa5af3`.
`pg_restore -l` succeeded. A matching copy with the same hash is retained
off-host at
`/Users/romankisockin/.codex/artifacts/worta-mvp609-f3f0e59/worta_stage_pre_mvp609.dump`
(0600). The empty blob inventory is retained at the same artifact root as
`pre_mvp609_blob_inventory.txt`, SHA-256
`61e7555f5481f71c148610a133af605966bdb762be59a37ff07b1220140a0b13`.
These are technical rollback artifacts, not a tested provider restore.

Migration used a separate locked-shell OS account and matching peer-auth
PostgreSQL role, `worta_stage_migrate`, with temporary CONNECT and schema
USAGE/CREATE only on `worta_stage`. `alembic heads` showed the single
`private_invitations` head. `alembic current` and the explicit
`alembic upgrade head` succeeded: 23 revisions, peak migration process RSS
149,268 KiB, 4.60 seconds. The result has 18 user tables, 2 sequences and
an 8,510,487-byte DB at migration inventory. The policy row is `closed`.
The migrator's temporary grants were revoked and its DB role set NOLOGIN.
Runtime `worta_stage` has DML on required application tables, read-only
`registration_settings`, sequence USAGE/SELECT and no schema/database CREATE.
Privilege checks returned database CREATE false, schema CREATE false, policy
SELECT true, policy UPDATE false. No HBA edit or other DB migration occurred.

The reviewed template was installed as `/etc/systemd/system/worta-staging.service`
with the same SHA-256 as above. `systemd-analyze verify` passed. The unit ran
as unprivileged `worta_stage`, one worker, `127.0.0.1:8000` only, disabled at
boot, with bounded restart, `MemoryHigh=320M`, `MemoryMax=384M`,
`TasksMax=32` and access logs off. No SMTP or invitation flow was activated.

| Actual local HTTP check on the VPS | Result |
| --- | --- |
| `GET /health` | 200, application 5.3.9 |
| `GET /ready` | 200, database ready |
| `GET /api/v1/auth/registration` | 200, mode `closed`, registration disabled |
| `POST /api/v1/auth/register` with synthetic input | 403, `registration_closed` |
| Anonymous `GET /api/v1/cloud/projects` | 401 |
| Anonymous `GET /api/v1/admin/users` | 401 |
| Legacy `GET /api/projects` | 404 |
| Three WORTA Host headers to Caddy loopback 8080 | 404 each |
| 10 sequential local `/health`/`/ready` requests | 10/10 passed in 0.039 s |

The first registration probe with a syntactically invalid email returned
422 validation error; the corrected synthetic probe above reached the CLOSED
policy. After the checks the DB still had zero users and zero invitations,
Alembic head `private_invitations`, and the isolated data/blob roots had zero
files. No plaintext user store or test profile was populated. The ready
checks used two PostgreSQL connections including the inspection connection;
this was not a concurrency or Argon2 load test.

During the running sample, the unit had `MemoryCurrent=93,757,440` bytes,
`MemoryPeak=134,012,928` bytes and six tasks. Available RAM was 585,031,680
bytes and root disk free 6,683,820,032 bytes. This measured one idle worker
plus bounded local requests; it does not prove full-load capacity on 1 GiB
RAM. No swap exists.

After smoke checks, `worta-staging.service` was **stopped** and remains
**disabled**, preserving memory and preventing accidental serving before
tester authorization. Port 8000 is closed. SSH, PostgreSQL and Caddy remain
active; PostgreSQL and Caddy still bind loopback only, and UFW still allows
only SSH inbound. PostgreSQL HBA/config, Caddyfile and `sshd_config` hashes
match the before-state values above. Final available RAM was 663,584,768
bytes, root disk free 6,683,832,320 bytes, no swap. Installed app, venv,
unit, DB schema and backup artifacts remain for the next reviewed stage.

Immediate rollback is `systemctl stop worta-staging.service` (already done)
and leave it disabled. For a schema rollback, first preserve the current
isolated DB/blob state, restore the matched pre-migration dump into a **new
empty** staging target, verify the restore and blob inventory, then switch
only that target after separate authorization. Do not downgrade a populated
invitation history in place or overwrite the sole DB/blob copy. Removal of
the isolated app, unit, migration role or database requires a complete
inventory and a separate decision; no automatic deletion was performed.
This stage did not touch DNS, public Caddy/HTTPS, SSH, UFW, system Python,
provider snapshots, other databases or the existing landing site.

The backend is technically installed and its loopback smoke test passed.
It is **not** approved for real users, invitations, account creation, public
HTTPS or sync. C21/C22/C23 and truthful reader/writer capabilities remain
open; backup restoration and client recovery are untested. The next stage
should review the matched DB/blob restore, SMTP/private HTTPS and account
bootstrap plan, then run a separate owner-authorized private acceptance after
the application gates close. Keep public registration CLOSED and Web progress
at **89.36%**. Expected automatic CI for this docs-only commit: none under
the current workflow path filters. This is a static expectation, not a
queried run.
