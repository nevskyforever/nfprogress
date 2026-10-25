# WORTA 6.0 MVP — desktop + Web + encrypted cloud sync

**Owner priority:** restricted Web + desktop encrypted writing; frozen C21 reader,
security, backup/restore, CI, and public-release gates remain.

**Current practical browser milestone: MVP6.0.02.** A development Web account
session now composes normal-user login, existing account-key lookup, durable
IndexedDB account/device identity, exact binding, and client-side AMK unlock.
It supports lock, logout and same-profile reopen. Web Note sync is still disabled.
The card requires a Vite development build and a Web backend that reports
developer mode; the normal Web bootstrap still uses the plaintext compatibility API.

**MVP6.0.03 private access preparation.** The existing administrator authority
now has a one-time interactive bootstrap guard and private, expiring, single-use
email invitations for pending user accounts. Recipients set their own passwords.
The invited-account path is separate from public `/auth/register`, which remains
CLOSED. The additive PostgreSQL migration and backend are local code only; no
production database or VPS service was changed. The `landing/worta` site now
labels its status as closed testing and explains future invitation-only access
without publishing a registration form. It does not assert that the test Web
backend is deployed or that Note synchronization is ready.
The owner reports independent Cloud acceptance for MVP6.0.02
(`40180686691`, 6/6 SUCCESS), MVP6.0.03 (`40183219901`, 6/6 SUCCESS),
and MVP6.0.05 (`40206456558`, 6/6 SUCCESS).
The owner reports MVP6.0.06 Cloud `40212021756`, 6/6 SUCCESS.
MVP6.0.04 did not query GitHub Actions.

## Exact MVP

One existing authorized account can sign in on a Mac desktop client and in a
browser, unlock the same account encryption key with the cloud password, enable
cloud sync for two isolated test projects, and write Notes on either client.
After reconnect/restart, each client shows the other client’s accepted edit.
The server stores authenticated opaque ciphertext; it never receives manuscript
plaintext or encryption keys. Local saves remain durable while offline. A conflict
retains both versions or stops safely with a clear recovery action.
This is **restricted MVP staging**, not public release. Support only accepted
Note formats/histories; unsupported legacy, mixed-family, dependency or conflict
history stops with data preserved and a diagnostic. Reader readiness still
requires every registered device to truthfully satisfy the frozen Note predicate.

## Current state: components vs user flow

| Area | Existing tested component | Connected working user flow |
| --- | --- | --- |
| Desktop Notes | Native SQLite Notes and durable encrypted sync capture/seal/upload/pull/apply/ACK owners; bounded restart/conflict evidence | Desktop cloud session is Tauri-only; no accepted real backend + Web + desktop writing round trip |
| Browser writing | Vue Web runtime, HTTP compatibility repositories, browser-safe editor and browser IndexedDB persistence/migration substrate | Local Web API is plaintext compatibility storage; it is not encrypted offline project/Note persistence |
| Account and keys | Cloud auth, device identity, E2EE provisioning/unlock, account binding and project bootstrap owners exist for desktop | MVP6.0.02 composes a development Web account/key session; browser Note/project sync and production Web connection remain absent |
| Private account access | Existing administrator role checks and MVP6.0.03 invite issuance/acceptance, revocation and expiry have local PostgreSQL/browser evidence | No production backend deployment, live invitation delivery or owner-authorized tester onboarding |
| Encrypted transport | Authenticated v2/v3 APIs, opaque event storage, PostgreSQL backend and guarded reader/write endpoints have focused acceptance | No deployed production-shaped endpoint is connected to a browser Note writer and accepted inbound reader |
| Note readers | Bounded F/H/G/Q/J/K/O owners and ordinary Legacy/Content readers have local evidence; Y is published, remote acceptance pending | No full v10 production dispatch/replay/recovery path; readiness is deliberately negative |
| Project isolation | Per-account/project ownership and bootstrap contracts, encrypted envelopes, isolation tests | Two-project end-to-end desktop↔Web isolation has not been accepted against a real deployment |
| Recovery and conflicts | Durable outbox/inbox, atomic apply, replay, conflict preservation and backup/restore code/tests exist in bounded scopes | Full offline/retry/restart/conflict/backup-restore user workflow is not accepted across real clients and backend |
Existing tests prove bounded components, not a connected product. `Run Web.sh`
uses a local plaintext API and synthetic profile; it does not prove encrypted
cloud sync or justify describing Web persistence as cloud synchronization.

## Current critical path

| User goal | Already works | Missing | Exact blocker | Next action |
| --- | --- | --- | --- | --- |
| Desktop local writing | Existing Tauri editor and SQLite | MVP smoke evidence on selected build | No MVP-specific baseline evidence in current records | Record exact build/profile and local-save restart result |
| Browser local encrypted project/Note storage | IndexedDB persistence and migration owners | Production Web repositories, account-key use, UI wiring | Web repositories still use HTTP compatibility APIs; no browser cloud runtime composition | Build one browser durable repository slice against existing contracts |
| Account login and encryption | Backend auth, desktop key owners and MVP6.0.02 development Web login/unlock | Production Web bootstrap and sync composition | `cloudSession` remains Tauri-only; test Web card runs behind the development boundary | Keep account session isolated; connect durable Note path only after reader acceptance |
| Private tester provisioning | One-time admin bootstrap guard, pending user creation, server-email invitation, single-use claim and admin status/revocation | Deployment, configured SMTP, isolated staging verification and administrator action | Production schema/backend are not deployed; invite link cannot be issued to real testers yet | Review additive migration and mail configuration in authorized staging; retain CLOSED public registration |
| Browser cloud upload and inbound apply | Encrypted APIs and bounded browser reader/apply owners | Production routing, complete reader lifecycle | Note gate requires all six fields; production dispatch/replay and histories incomplete | Implement the next accepted C21.2.08 reader slice; keep declaration off |
| Desktop↔Web bidirectional Notes | Desktop production router and browser v10 slices | Connected durable writer/reader cycle in both clients | Browser client is not connected to the desktop-equivalent production sync runtime | After browser composition, prove one Note each direction |
| Project isolation | Server ownership checks and local owner tests | Real account with two end-to-end projects | No accepted deployed E2E evidence | Include two project IDs in restricted staging acceptance |
| Restart and retry | Durable local stores, idempotent receipts and restart tests | Cross-client/backend interruption proof | No production-shaped end-to-end run | Inject lost reply/offline/reopen and verify exact replay |
| Minimum conflict safety | Keep-both and atomic conflict owners in bounded tests | User-visible Web/desktop conflict recovery round trip | Production composition and real client evidence absent | Preserve both versions or stop; never overwrite silently |
| Note reader gate | Server predicate and negative-only readiness | Truthful full cohort declaration | Legacy v3/F2 join, complete route/replay/recovery and lifecycle evidence remain incomplete | Resolve the historical reader-gate dependency; no capability bypass |
| VPS backend and PostgreSQL | Fresh MVP6.0.07 read-only SSH: PostgreSQL 16/Caddy active, loopback-only; .05/.06 owner-reported CI accepted; local non-superuser migration passes | VPS staging DB/role/HBA, backend install, native loaded RAM gate | C21/C22/C23 and real service/restore evidence remain; no backend installed | Review C21/C22 installation boundary, then request an isolated technical install; C23 before testers |
| Real E2E acceptance | Component suites and disposable PostgreSQL CI | Real HTTPS/production-shaped clients and backend run | Backend not deployed; HTTPS/DNS inactive; no accepted connected run | First loopback-only restricted staging after all gates |
| Backup/restore | Reproducible **local** PostgreSQL dump plus opaque blob restore and failure checks pass; provider snapshot service reported active | VPS/off-host matched backup and restored-client C23 acceptance | Live backup integrity and RPO/RTO are not verified | Complete approved off-host restore drill before staging user data |
| Core UI defects | No reproducible MVP P0/P1 UI defect is identified in inspected current records | User-reported/reproducible issue list | No issue evidence in these records; avoid inventing bugs | Capture repros during first end-to-end smoke and triage by impact |

## Prioritized backlog

**P0 — integrity and access.** Keep reader declaration, ACK, and content writer
gates closed until contracts pass. Complete the truthful Note reader path; prove
encrypted browser persistence, isolation, atomic apply, conflict retention,
retry/restart, auth/key lock and restore. Unknown/unsupported history remains
unapplied and visible.
No confirmed production data-loss defect is recorded; this is an acceptance gap.
**P1 — first usable sync.** Compose Web login/key unlock and device identity with
durable browser project/Note repositories; wire explicit project enablement,
outbound sealing/upload, inbound accepted-reader dispatch, and status/retry UI.
Connect desktop and Web to the same staging account only after the server and
reader gates are ready. No confirmed P1 application bug is evidenced in the
inspected records.
**P2 — usability.** Improve first-run setup, understandable blocker messages,
sync status, and recovery guidance using issues observed in the restricted run.
Do not treat unverified UX concerns as release blockers or invent bugs.
**Deferred, safe-stop required.** Rare historical codecs, unsupported mixed
families, later resolution generations, tombstone resurrection, post-resolution
local authorship, cold/orphan dependency repair and broad multi-device revocation
may be excluded from the initial supported cohort only if unsupported histories
are detected before writes/ACK, retained intact, and reported for recovery. If
the frozen global reader predicate cannot be met without one of these cases, it
is not deferrable: restricted sync stays blocked until the predicate is met.

## Small implementation slices

1. **MVP6.0.02 browser account/key session.** Development Web sign-in, existing
   AMK unlock, lock/logout and persistent browser identity are implemented with
   no Note reader declaration, ACK, writer or sync activation. Record its exact
   implementation SHA and independent CI outcome before claiming remote acceptance.
2. **Resolve the remaining Legacy v3/F2 reader dependency.** The historical
   C21.2.08R identifier belongs to its STOP/audit record and is not a new task
   name. A future authorized slice must strictly authenticate the v3 wrapper and
   original F2 proof without relabeling protocol or inventing a receipt. Missing
   or corrupt proof stops; restart and no-duplicate-write evidence is required.
   C21.2.08Y still needs its independent Cloud acceptance; no gate is waived.
3. **Finish the smallest remaining Note-reader slices.** Production route
   dispatch, replay/received scan, dependency stop and only required supported
   lifecycle cases; retain full inventory checks. Each slice needs focused native
   and browser evidence plus the existing mandatory CI gate. Unsupported cases
   fail closed; the six-field account-wide declaration remains unchanged.
4. **Compose the durable browser Note path.** Extend the bounded Web session
   with IndexedDB-backed repositories, then wire explicit project enable,
   encrypted upload and accepted inbound apply. Show locked, offline, blocked,
   conflict and retry states. Do not use localStorage or HTTP plaintext APIs as
   sync success.
5. **Prepare isolated staging and run paired-client acceptance.** Only after
   C21/C22 authorization: recheck VPS, install the prepared backend bundle into
   isolated service/data paths, create a separate test DB/role, and use loopback
   tunnel access first. Prove two projects, both edit directions, restart,
   interruption, conflict retention and restore before considering any external
   test access.

## MVP6.0.07 — isolated staging and restore readiness (2026-10-25)

**Preflight only; deployment blocked.** Read-only SSH succeeded using the
previously verified `worta-admin` account, explicit existing key and strict
host-key checking. No SSH alias or new key was needed. On the VPS, Ubuntu
24.04.5, WORTA Python 3.13.17, PostgreSQL 16.15 and Caddy 2.6.2 are present.
The snapshot has 679,018,496 bytes available RAM (~647.6 MiB), zero swap and
6,955,671,552 bytes available on root (~6.48 GiB). PostgreSQL and Caddy use
about 18.2 and 7.2 MB service memory at idle. PostgreSQL allows 20 connections
(3 reserved for superusers), currently 6 including the audit query; the
MVP6.0.06 backend pool budget is 2 with no overflow and one intended worker.
That is plausible connection headroom, **not proof of RAM capacity under native
Argon2/sync load**. PostgreSQL listens on loopback; existing loopback HBA is
`reject`. Caddy listens on loopback:8080 and returned 404 for the three closed
site hosts. No WORTA database/role, backend unit, source/venv or state/env root
exists on the VPS. No VPS configuration or data was changed.

The new opt-in local [restore preflight script](../scripts/maintenance/run_cloud_restore_preflight.sh)
starts a labeled, disposable PostgreSQL 16 container, creates a random
non-superuser role and two isolated databases, applies Alembic head to the
empty source, saves a `pg_dump` custom archive and a copy of synthetic opaque
blob files, then restores into the separate target. It verifies schema version,
record counts, hashes, production-shaped login/ready/CLOSED registration,
cloud-only routing, and blob download. Missing and corrupted restored blobs
return sanitized 503 without plaintext fallback; restoring the blob recovers
access. The script removes its container, databases and role. This **local
fixture is not C23**, an off-host VPS backup, or a paired-client restore.
The Cloud backend workflow runs this bounded drill independently.

The inactive [staging Caddy example](../deploy/vps/Caddyfile.staging-https.example)
uses `https://test.worta.ru` as a separate same-origin Web/API endpoint, with
documentation-only TEST-NET IP allowlists that admit no actual testers until
replaced. It gates `/admin` and admin API to the administrator CIDR, permits
only cloud API namespaces for approved tester CIDRs, blocks registration and
legacy `/api`, serves `/invite` through the reviewed SPA artifact, and has no
access-log directive. The final service must retain `--no-access-log` and the
effective proxy logging policy must be reviewed for token secrecy. The template
passed read-only `caddy adapt` on the installed
VPS binary; it is **not active**. HTTPS certificates, open public ports, exact
tester CIDRs, reviewed Web artifact, runtime origin, SMTP and service limits
remain unproven. The landing at `worta.ru` was not changed.

For an approved later **loopback-only technical** staging install, the owner
must authorize that specific VPS change and approve the C21/C22 installation
boundary while keeping reader declarations, writer and tester access off.
The owner also selects tester/admin access CIDRs and an external backup
destination/RPO/RTO, and provides trusted private SMTP/DNS/TLS decisions. The
operator then creates a separate non-superuser `worta_stage` role and empty
database, changes only a reviewed loopback HBA rule to SCRAM, configures one
backend worker with the existing two-connection pool and measured memory/task
limits, creates private data/blob roots, and applies migrations **only to that
new database** after an approved backup. The frontend build must set
`VITE_API_BASE_URL=https://test.worta.ru`; the backend uses only the corresponding
allowed origin and `NFPROGRESS_PUBLIC_WEB_URL=https://test.worta.ru`. The
existing `python -m backend.app.admin_cli create` is then run interactively on
the trusted server terminal: the owner enters a unique username, separate email
and password there. No credentials enter Codex, chat, Git or command arguments;
the command refuses a second administrator. Test CLOSED registration, 401/403
admin boundaries, HTTPS `/invite`, delivery to an owner-controlled mailbox,
resource ceiling and consistent off-host DB/blob restore before admitting
testers. C21 truthful reader/writer acceptance, C22 live security review and
C23 restored-client acceptance remain required before tester data; the C23
drill itself needs an isolated installed target. No real administrator or
invitation was created in this stage.

Staging remains **BLOCKED**; Web stays **89.36%** with C21/C22/C23, Note
reader/writer/ACK/E2EE and public release gates unchanged.

## MVP6.0.06 — resource limits and invitation delivery (2026-10-25)

**Owner-reported Cloud acceptance: `40212021756`, 6/6 SUCCESS.** `CloudDatabase` now caps
each backend process at two pooled PostgreSQL connections, zero overflow, a
three-second pool wait and a five-second connect timeout. Request sessions still
close on all outcomes; pool exhaustion yields a sanitized 503 and recovery is
tested after connections return. The intended small-VPS profile uses **one
backend worker**, so the application connection budget is two; PostgreSQL,
Alembic and other processes need their own separate capacity allowance.

Server password Argon2id remains `PasswordHash.recommended()` with unchanged
hash format and verification. A process-wide semaphore permits one concurrent
Argon2 operation with a two-second bounded wait; overload returns a sanitized
503 with `Retry-After`. The dummy verification hash is shared rather than
recomputed for every service instance. This does not change client AMK/E2EE
key derivation or user-key unlock. The server process memory and worker count
must still be measured and constrained at service deployment.

SMTP STARTTLS and implicit TLS use the existing ten-second socket timeout and
TLS context. An SMTP failure now raises a sanitized delivery error. The private
admin invitation route waits for SMTP transport acceptance; on a reported
failure it revokes the committed token and returns 503, allowing a safe reissue.
This is **transport acceptance, not mailbox delivery proof**; a response lost
after SMTP acceptance may leave a revoked link in a mailbox. Invitation links
use a validated HTTPS URL without credentials, query or fragment; existing
72-hour expiry, single use, revocation, username/email separation, admin role
checks and CLOSED public registration remain in force. Only controlled SMTP
and disposable PostgreSQL tests ran; no real email or invitation was sent.

Staging remains **blocked** by C21 truthful reader/writer acceptance, C22
security, C23 consistent DB/blob restore and client recovery, a fresh read-only
VPS audit, isolated staging DB/role and roots, measured host RAM/connection
headroom and service limits, a private HTTPS `/invite` application, and an
owner-authorized SMTP delivery smoke check. No VPS, production database,
account, Caddy, DNS, release gate or Web progress changed. Web remains 89.36%.

## MVP6.0.05 — backend security and runtime configuration (2026-10-25)

**LOCAL IMPLEMENTATION / CLOUD CI PENDING / VPS UNCHANGED.** The production Web
profile (`NFPROGRESS_ENV=production`, `NFPROGRESS_PLATFORM=web`) now constructs
only the cloud backend. It does not instantiate `PickleRepository`, resolve a
legacy data directory, run local SQLite cutovers, or register the plaintext
`/api` routers. Those paths are absent both at runtime and from OpenAPI. Cloud
auth, admin checks and registration policy use their existing PostgreSQL routes.
Development Web and Desktop/Tauri retain the legacy API and its existing local
session-token behavior. Production desktop requires its session token; unsupported
production platform, production cloud developer mode, legacy session token and
local-file access fail at configuration validation. The CLI rejects non-loopback
legacy/development binds even with `--allow-remote`, and rejects production
development-data options before copying local data.

The CLI now derives its effective settings with `dataclasses.replace` from the
validated environment configuration. SMTP host/port/credentials/TLS, HTTPS
invitation URL, encrypted blob root, PostgreSQL URL, auth secret and origins reach
the real ASGI app without appearing in diagnostics. Invalid SMTP/PostgreSQL
ports are reported without echoing raw values; the session token and SMTP
username are redacted from config representation. No migration or cloud authorization
contract changed. Local tests cover the actual CLI listener, route inventory,
OpenAPI, no-plaintext-store construction, CLI configuration and profile rejection,
plus disposable PostgreSQL login/admin and legacy compatibility. The exact test
counts and SHA are recorded in the checkpoint. This closes the two **code P0**
findings from MVP6.0.04; the owner reports Cloud run `40206456558` 6/6 SUCCESS.

At the .05 baseline, staging remained **blocked** by C21 truthful reader/writer
acceptance, C22 security, C23 DB/blob restore, resource limits, isolated host
DB/role, private HTTPS invitation frontend, reliable SMTP delivery and a fresh
read-only VPS preflight. Registration stays CLOSED; reader declaration, ACK and E2EE gates
remain unchanged. No backend was deployed.

## MVP6.0.04 — safe staging preflight (2026-10-25; historical baseline)

**Decision: STOP before deployment or account provisioning.** At baseline
`d70d438ddcea45881a4e0f832c35c2c7dc22a74c`, the local repo and
`origin/6.0` matched. This is a code/document audit, not fresh VPS acceptance:
the requested `worta-admin` alias did not resolve in this execution environment
because `~/.ssh/config` is absent. No server commands completed. The host facts
below remain the dated 2026-10-22 report until a read-only SSH preflight succeeds.

| Priority | Boundary | Confirmed code state / staging consequence |
| --- | --- | --- |
| P0 | Legacy `/api` | `create_app()` mounts plaintext `PickleRepository` routes alongside cloud routes. `require_session()` allows requests when `NFPROGRESS_SESSION_TOKEN` is unset; the backend CLI rejects a non-loopback bind with a token. A cloud-capable staging process has no proved safe network path for this mixed API. Isolate/disable the legacy routes through a reviewed runtime boundary before any reachable staging listener. |
| P0 | RuntimeConfig and invitations | `RuntimeConfig.from_env()` reads SMTP, `NFPROGRESS_PUBLIC_WEB_URL` and `NFPROGRESS_CLOUD_BLOB_DIR`, but `backend.app.__main__.main()` reconstructs a config without these fields. Its normal CLI launch therefore disables SMTP and blob storage, so invitation issuance returns 503. Repair config propagation and test the actual CLI entry point before installation. |
| P0 | C21 reader gate | Bounded native/browser reader owners exist; the full six-field truthful declaration, production dispatch/replay and remaining histories are not accepted. Keep Note sync, writer authorization and declaration closed. |
| P0 | C22 security | Server-side account/role/ownership checks and closed registration exist, with bounded tests. An independent staging security review of the mixed API, secrets, limits, TLS and service isolation is not accepted. Do not treat component authorization tests as C22 completion. |
| P0 | C23 restore | Bounded client recovery code/tests and reported provider snapshots exist. An independent, consistent staging DB-plus-encrypted-blob backup restored into an empty target and verified with clients is not recorded. Do not admit real tester data until that drill passes. |
| P1 | Resources and isolation | `CloudDatabase` uses SQLAlchemy's implicit pool defaults; there is no explicit pool/overflow budget or Argon2 concurrency limit in this runtime. A separate PostgreSQL role/database, dedicated legacy-data and blob roots, service RAM/process limits and connection budget are design requirements, not verified host state. |
| P1 | Invitation delivery and HTTPS | SMTP TLS and complete env validation exist, but SMTP send failures are logged and swallowed after a pending invitation is committed; 201 cannot prove delivery. The invitation page is a Vue `/invite` route and `NFPROGRESS_PUBLIC_WEB_URL` must be HTTPS. The published landing is not an invitation application endpoint. Prove a private HTTPS frontend and monitored mail delivery before inviting testers. |
| P1 | Live VPS state | The SSH alias was unavailable here. Versions, free RAM/disk, interface bindings, permissions, current services, PostgreSQL policy and Caddy status cannot be claimed fresh. |

The one-time `backend.app.admin_cli create` path reads username/email with
`input()` and password/confirmation with `getpass`, uses a PostgreSQL advisory
transaction lock, and refuses creation if any admin exists. Admin API routes use
server-side `get_current_admin`; public registration policy updates reject any
mode other than CLOSED. Invitation acceptance locks and rechecks a token hash,
expiry, revocation, account state and capacity. Login still selects by normalized
**username**; `username` and `email` remain distinct unique fields. The admin
bootstrap and invitation tests used disposable PostgreSQL in MVP6.0.03; this
task created no real administrator or staging database.

### Authorized deployment sequence after the P0 gates close

1. Repeat a **read-only** `worta-admin` inventory: UTC/OS/Python/PostgreSQL/Caddy
   versions, `pg_isready`, service states, RAM/swap/disk, interface/listening
   addresses, and owner/mode of intended paths. Do not print environment files,
   credentials, process environments or user data. Compare host capacity with a
   measured single-worker Argon2 and DB pool budget. Record the exact SSH profile
   and host fingerprint through the owner's trusted channel.
2. Review the actual backend entry point and a cloud-only route boundary; prove
   legacy `/api` unreachable, CLOSED public registration, admin 401/403 checks,
   no broad CORS, and dedicated empty data/blob directories. Set a bounded DB
   pool/overflow and authentication concurrency plus service memory/task limits.
   Use a separate non-superuser staging DB/role; never reuse production data or
   credentials. This task creates none of them.
3. Review Alembic head and PostgreSQL 16 compatibility on a disposable database,
   including the additive `private_invitations` migration and policy row. Before
   any authorized migration, capture an independent consistent DB dump and
   encrypted-blob snapshot with inventory/checksums. Do not use automatic
   downgrade after invitations exist; its guard intentionally refuses data loss.
4. Keep the backend bound to loopback with SSH tunnel access only. Configure a
   private HTTPS app endpoint for `/invite` and server-generated links before
   sending invitations; the existing public landing and DNS remain unchanged.
   Provide `NFPROGRESS_ENV=production`, `NFPROGRESS_DATABASE_URL`,
   `NFPROGRESS_AUTH_SECRET`, `NFPROGRESS_DATA_DIR`,
   `NFPROGRESS_CLOUD_BLOB_DIR`, exact `NFPROGRESS_ALLOWED_ORIGINS`,
   `NFPROGRESS_PUBLIC_WEB_URL`, and complete `NFPROGRESS_SMTP_HOST`,
   `NFPROGRESS_SMTP_PORT`, `NFPROGRESS_SMTP_USERNAME`,
   `NFPROGRESS_SMTP_PASSWORD`, `NFPROGRESS_SMTP_FROM_EMAIL`,
   `NFPROGRESS_SMTP_SECURITY` values through a root-controlled environment file
   (mode 0600), never Git, chat, command arguments or logs. Validate SMTP
   delivery to an owner-controlled
   mailbox and failure reporting without sending a real tester invitation.
5. After owner authorization, run the existing `python -m backend.app.admin_cli
   create` **interactively on the trusted server terminal** with the staging env
   loaded locally. The owner types a unique username, separate email and strong
   password directly into that terminal. No password is supplied to Codex. Verify
   only role/status through an authorized session; no duplicate bootstrap.
6. Run restricted smoke checks: `/ready`, unauthorized/admin access, CLOSED
   registration, invitation issue/expiry/revoke/replay, username login, project
   isolation, ciphertext-only storage, and negative reader/writer gates. Admit
   no real users until C21/C22/C23 and paired-client acceptance authorize it.
7. Rehearse restore into **another** disposable database/blob root and verify
   counts, checksums, auth/session revocation assumptions and client recovery.
   Rollback a bad rollout by stopping its isolated service, retaining evidence,
   restoring the matched DB/blob snapshot into an empty isolated target and
   restoring the prior reviewed backend image. Never overwrite the source or
   downgrade populated invitation history in place.

No backend, role, database, migration, account, DNS, firewall, Caddy or public
listener was changed during this preflight.

## VPS readiness and staging boundary

Latest read-only VPS status is **prepared / deployment blocked** (2026-10-25;
MVP6.0.07 SSH SUCCESS): Ubuntu 24.04.5, Python 3.13.17, PostgreSQL 16.15
and Caddy 2.6.2. PostgreSQL is loopback-only with TCP rejected and no WORTA
DB/role; Caddy serves closed 404s on loopback `127.0.0.1:8080`. Available
RAM is about 647.6 MiB with no swap; free root disk is about 6.48 GiB. The
backend bundle and production dependency lock remain uninstalled, and no
WORTA service, state root or active HTTPS site exists. Public 80/443 are not
listening; apex/www remain on their existing hosting. Provider snapshots are
reported active but restore is unverified. MVP6.0.05 cloud isolation and CLI
config, and MVP6.0.06 pool/Argon2 limits, have owner-reported Cloud acceptance.
The new local dump/blob restore drill and inactive Caddy staging example reduce
preparation work but do not satisfy C21/C22/C23 or native VPS service limits.
Before any approved isolated install, review separate data/blob roots,
staging DB/role and loopback HBA, service RAM/task limits and C21/C22
installation boundaries. C23 matched restore and client recovery require the
isolated target and must pass before tester data. Keep registration CLOSED,
reader/writer gates off and access restricted; do not open public listeners
in this stage.

## Acceptance checklist — restricted MVP

- [ ] Existing authorized account signs in on desktop and browser; both unlock
      the same E2EE account key without sending plaintext or keys to the server.
- [ ] Each client registers its own supported device; the live account gate shows
      every registered device ready and writer mode 3 before Note sync starts.
- [ ] Two test projects are enabled independently; data never crosses projects.
- [ ] Desktop Note save seals locally, uploads ciphertext, and Web applies the
      authenticated Note; Web edit then appears on desktop.
- [ ] Offline save survives close/restart; reconnect retries idempotently and a
      lost reply does not duplicate writes or advance an unproven cursor.
- [ ] Conflict keeps both versions or stops before mutation with a usable
      recovery path; corrupt/unknown/unsupported history remains intact.
- [ ] Server/PostgreSQL inspection confirms only opaque encrypted content and no
      keys/plaintext; auth, ownership, limits and registration policy are tested.
- [ ] Isolated backup of database and encrypted blobs is restored and verified;
      client recovery after restore is exercised before test data is retained.
- [ ] Record exact client/backend SHA, profile, gate values, acceptance evidence,
      and any unsupported cases. Label each state accurately.

## Release states and preserved gates

1. **Development:** local API/browser and component tests; not cloud sync.
2. **Restricted MVP staging:** isolated backend and allowlisted testers only,
   after C21/C22 authorization and a truthful Note gate; registration stays CLOSED.
3. **Private MVP accepted:** paired-client and restore checklist passes with
   owner acceptance; still private, with no public registration.
4. **Public Web release:** separately blocked on C21/C22/C23, VPS hardening and
   independent security review, policy/license/release checks, permanent CI/CD,
   backup/disaster acceptance, owner stabilization and explicit release approval.

At this document’s baseline Web progress remains **89.36%**;
`ready=false`, `declarationAllowed=false`, `writerAuthorized=false`; public
registration is **CLOSED** and **PUBLIC RELEASE BLOCKED**. C21/C21.2 remain in
progress and the .08 reader gate is not closed. C22, C23, PF6.0, RC, VPS security,
landing and all existing release criteria are preserved. This priority document
does not award roadmap points, alter scoring, or report unverified deployment,
CI, readiness, restore, or end-to-end results as complete.
