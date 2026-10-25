# C21.2.08Z1 — Authoritative source baseline feasibility

**DECISION A — EXISTING SOURCE SUFFICIENT, WITH REPLAY ELIGIBILITY GATES.**
Documentation-only audit at baseline `d9879b904e762f852d947bf595de2bfe6e00d4f2`,
branch `6.0`; preflight found a clean worktree and `HEAD == origin/6.0`. No
production code, tests, schema, protocol, cryptography, or readiness settings
changed. The result narrows Z's DB10-only finding: current browser stores alone
do not prove B's baseline, but existing authenticated bootstrap + full encrypted
event history can reconstruct one on a fresh device.

## Existing source chain

The source is a bounded replay composition, not a single snapshot endpoint:

1. **Project origin and initial Note producer.**
   `frontend/src/cloud/projectBootstrap.ts::CloudProjectBootstrapCoordinator.run`
   registers a project bootstrap, calls the captured initial Note cohort owner,
   uploads that exact cohort, then completes registration with its accepted count
   and maximum server sequence. `frontend/src/platform/web/initialNoteCapture.ts`
   derives the cohort from the encrypted local source snapshot. Its
   `deriveInitialLegacyCohort()` rechecks the exact captured ordinal interval,
   project membership, unique Note/event IDs, accepted receipts, count and max
   sequence. These initial events are genuine revision-1 Note creates. Backend
   `CloudProjectService.register_bootstrap()` refuses a new bootstrap when
   project event history already exists and binds it to one origin device.

2. **Durable registry anchor.** `GET /api/v1/cloud/projects/bootstrap`, served by
   `backend/app/cloud/projects_router.py::list_cloud_project_bootstraps`, returns
   the project/bootstrap ID, origin device, active state, initial Note event
   count, maximum initial Note sequence and current account cursor. The backing
   `CloudProject` row keeps completed bootstrap fields immutable;
   `CloudProjectService.complete_bootstrap()` checks the origin's accepted
   project-event count and sequence before activation. The count/max tuple is a
   cohort boundary, not by itself proof of membership; replay must verify it
   against actual events and ciphertext.

3. **Complete history transport.** The existing authenticated encrypted pull
   endpoints accept `since=0` and page the account log by server sequence.
   `SyncRepository.pull()` / `pull_encrypted_descriptors()` query every retained
   `SyncEvent` above the cursor in ascending order, with no project filter;
   `SyncService.pull_encrypted()` materializes the matching opaque encrypted
   objects. `sync_events` has a unique `(user_id, server_sequence)` key. The
   audited application has no event-pruning/deletion path for a live account;
   project removal deletes only its registry row, and an account deletion
   cascades account data. The caller compares the completed replay cursor with
   the registry's current account cursor. V2/V3 parsers reject malformed pages;
   the Web inventory/prefix owners require a dense account sequence from 1
   through `pull_cursor`, rejecting any missing row. A fresh profile starts at
   cursor zero. If any historical event or encrypted object is unavailable,
   replay stops without lowering a cursor or rewriting evidence.

4. **Independent content authentication.** Event descriptors provide routing
   and sequence only. Note and project Metadata contents remain ciphertext at
   the server. The client opens Notes with the account master key and validates
   the original wire/header against account, project, Note, operation and
   revision. `ProjectMetadataEvent` carries its own project/bootstrap/device
   lineage and is opened through the existing Metadata owner. Thus the server
   supplies no Note or project plaintext. The existing authenticated registry
   and server sequence remain the transport/order authority, consistent with
   the current WORTA threat model; this is not a cryptographic proof against a
   malicious server that equivocates about its own cursor.

5. **Derived B source baseline.** On a clean imported project, authenticate its
   Metadata genesis for the same project/bootstrap and bind its sender to the
   actual event descriptor through the Metadata owner. The initial Note cohort
   separately binds to the bootstrap origin device.
   Metadata carries the supported shared project fields, while current code has
   no direct Metadata-to-`NativeLocalProject` converter. Z2 must define a
   deterministic mapping for the restricted cloud projection (empty unsupported
   local payload, timestamps derived from authenticated Metadata history, and
   exact supported fields); if that mapping cannot be established, fail closed.
   Require an active bootstrap and exactly
   `initial_event_count` Note events from its origin at or before
   `initial_max_server_sequence`, with that maximum equal to the cohort's last
   Note sequence. Open every event and require a unique initial create; any
   extra/missing Note, wrong origin/project, non-create, unsupported project
   field, missing Metadata genesis, or mismatched bootstrap fails closed. Start
   `BrowserLocalAuthority.initialize()` from the empty project at its defined
   local source revision 1, then feed the authenticated initial Notes through
   the real inbound apply owners in server order. This yields the new device's
   own source revision chain and membership; it does not claim to reproduce the
   source device's private local counter or unuploaded local-only Notes.
   Subsequent B events continue through their real Legacy2/Content3 owners.

6. **Join to Q.** Replay and authenticate the complete account stream, including
   accepted Metadata/Stage/StageOrder dependencies, and enforce one account-wide
   owner for each Note ID. Project B gets its own derived baseline and source
   fold; project A continues to use only F's authenticated `source_after`/R0.
   Q may qualify only the exact dense prefix supported by those owners and the
   accepted F/H/O evidence. Its commit remains cursor-only; no ACK follows.

This establishes a supported synchronized cloud baseline for a new device; it
does not copy arbitrary local-only project state or initial tombstones that were
never uploaded. A pre-existing local project with independent edits is not a
clean import and cannot be silently replaced or joined to this replay.

## Why a new witness format is not required

The authenticated bootstrap tuple plus actual initial Note ciphertexts provides
the initial synchronized Note set; full ordered event replay derives every
subsequent local source transition. The Metadata genesis authenticates supported
project fields. Existing AEAD, project/bootstrap bindings, Note owners, account
sequence, and DB10 records remain the evidence; no new server plaintext, event
field, proof version, IndexedDB store, PostgreSQL column, migration, or crypto
format is needed. Imported bindings currently omit the registry count/max, so
the future replay owner must re-fetch and revalidate the authenticated registry
descriptor when preparing after restart rather than treating the local binding
alone as source authority. Offline preparation without that registry evidence
stays blocked.

## C21.2.08Z2 implementation contract

Implement a client-only, dormant source-replay owner that:

- takes a freshly authenticated registry snapshot and complete `since=0` pages;
- verifies dense sequence coverage to the snapshot cursor and the exact
  bootstrap initial Note count/max/origin cohort described above;
- authenticates Metadata genesis, then materializes only supported empty-project
  fields and applies real Note producers in global server order;
- recomputes after restart from persisted inbox/history plus a newly authenticated
  registry snapshot; never treats current `localProjects`/`localNotes` alone as
  historical evidence;
- uses an isolated clean import target, full inventory/lifecycle checks and
  existing transaction/CAS owners; unsupported or already-populated conflicting
  projects stop without writes;
- passes its independently authenticated B fold to Q only through a private
  owner capability. Q preserves the A F/H/O fold and its own cursor-only commit.

No schema or protocol migration is proposed. If implementation finds bootstrap
metadata, project Metadata genesis, or retained full history missing for a target,
that target remains blocked. Do not synthesize its baseline. Revisit a new
durable-witness proposal only if production-shaped replay cannot establish this
contract from existing sources.

## Future acceptance matrix

| Case | Required result |
| --- | --- |
| Project A genuine F/H/O plus project B genuine Legacy2 and Content3 Note histories | Fresh project B baseline and both histories authenticate through actual bootstrap, Metadata, inbound apply and Q owners; account/project isolation holds. |
| New browser with no local history; browser restart and replay | Pull from 0, verify every sequence through registry cursor, persist ciphertext, restart, re-fetch descriptor and reproduce the same B membership/source fold. |
| Missing sequence/object or incomplete initial cohort | Reject/block before writes; preserve all received ciphertext and cursor. |
| Substituted bootstrap, origin, project, Metadata genesis or corrupt ciphertext | Reject; no fallback to current local source. |
| Revoked auth/key/device during replay | Abort transaction and prevent stale Q commit. |
| Same Note ID in two projects | Reject account-wide identity collision. |
| Older client without this replay owner | Remain blocked at the existing earliest Note sequence; no durable-record modification. |
| Successful Q | Exact cursor-only `proven_prefix` commit; no ACK, Note upload, writer activation or reader declaration. |

Positive cases must use the real bootstrap and event producers. No fabricated
proofs or mocked authenticated event source can establish acceptance.

## Boundary and next action

Decision A removes the need for a new witness protocol, but does not implement
cross-project Q admission. The smallest next slice is **C21.2.08Z2 — client-only
authenticated second-project full-history replay and Q composition**, GPT-6 Luna
/ High: it is a bounded but multi-owner client integration. Keep it dormant until
its focused real-producer and persistent-browser acceptance passes.

MVP6.0.12 Cloud `40236767686` remains pending owner confirmation. Localization
debt remains 27 historical untranslated keys per target language (47 at its
baseline). C21 truthful reader gate remains `ready=false`,
`declarationAllowed=false`, `writerAuthorized=false`; cloud Note upload/writer/ACK
remain disabled. Registration stays CLOSED, PUBLIC RELEASE BLOCKED, Web progress
89.36%, and C22/C23/PF6.0/RC remain mandatory.
