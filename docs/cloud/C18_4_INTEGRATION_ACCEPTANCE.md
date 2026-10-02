# C18.4.06 structural / account catalog integration acceptance

Branch `6.0`; clean preflight in `/Users/romankisockin/Desktop/nfprogress/ts_migration`.
HEAD and local `origin/6.0` both `d95e4c0d8612783e13950bd1aac8cfded318b44b`.
The independent evidence supplied by the owner accepts C18.4.05: SQLite run
[36992277299](https://github.com/nevskyforever/nfprogress/actions/runs/36992277299)
and Cloud run [36992277357](https://github.com/nevskyforever/nfprogress/actions/runs/36992277357)
SUCCESS; Python SQLite, Rust Windows, Frontend admin and PostgreSQL all green.
Codex did not query Actions. Baseline evidence remains valid; this review does
not declare the new commit remotely accepted.

**Closure decision: C18.4 remains IN PROGRESS.** No P0 found. One bounded P1 is
fixed here; one P1 remains and requires C18.4.07. C18 remains IN PROGRESS and
official progress is exactly 77.0%. No C18.5 implementation.

## Audit method and production wiring

Reviewed the frozen C18 design and C18.3/.4 checkpoint evidence against production
code: `noteSyncRuntime.ts::composeSync` installs metadata, Stage and catalog
runtimes; `noteSyncV3Cycle.ts::runOnce` persists the common mixed stream, runs
separate project/account readers and prepares one ACK only after apply.
`accountObjectReader.ts` authenticates 2/2, checks outer/inner identities and
calls registered `apply_account_catalog`; project readers use C11 1/1.
`lib.rs` registers native catalog commands and routes ordinary folder/member/
order writers into `account_catalog::normal`; Stage commands route into
`stage_sync`. `account_catalog::apply`, Stage apply and metadata apply commit
projection/history/inbox/proof together. `note_sync::contiguous_applied_ack_prefix`
requires the appropriate ledger in the common account sequence.

The audit uses independently accepted existing proofs plus focused regressions.
The accepted PostgreSQL catalog test is extended with the missing Stage graph;
its account/bootstrap setup is reused, not duplicated into another expensive
scenario. All native calls reopen distinct device database files. The separate
known-gap regression deliberately documents failed progress; its green result
does **not** establish acceptance of that requirement.

## Acceptance matrix

Evidence paths are repository-relative. Native names refer to tests/functions in
`frontend/src-tauri/src/`; TS names refer to `frontend/src/`.

| Area | Classification | Evidence / production boundary | Closure impact |
| --- | --- | --- | --- |
| A. Metadata | PASS | `project_metadata_sync.rs` authority, exact full-tip decisions, 12-field allowlist, causal writers and preservation; four `project_metadata_acceptance_*` regressions; independently accepted C18.3.04 | No regression found |
| B. Stage | PASS | `stage_sync::dependency`, explicit `begin`, `normal_edit`, immutable frames/receipts; `stage_sync_explicit_migration_frozen_restart_receipts_and_order`, normal-writer and delete/edit tests | Required non-destructive paths covered |
| C. Stage order | PASS | Exact live set and scoped bounded causal ancestry proof; `stage_sync_frozen_order_reference_survives_rename_but_not_unknown_or_delete`, concurrent/stale order tests | Rename ancestry is already handled for Stage order |
| D. Account-object v2 | PASS | `account_sync` golden vector; TS account crypto/C11 vectors; `tests/test_cloud_c18_account.py` closed descriptor, ownership, replay and shared stream; no project slot/fallback | Accepted 2/2 contract unchanged |
| E. Folder | PASS | Strict codec, retained history/tips/projection, explicit migration, normal writer, immutable retries; native generic conflict/tombstone suite and PG rename conflict | Physical deletion remains disabled |
| F. Folder order | GAP-P1 | `proof_ready` / `dependencies_ready` require current folder heads byte-for-byte; new `account_catalog_audit_stale_dependency_cannot_resume_after_new_resolution` | Ordinary folder rename can permanently strand a received order and global ACK |
| G. Membership | PASS after bounded P1 fix; recovery affected by F | New `account_catalog_membership_waits_for_reconciled_metadata_after_restart`; current metadata must be `active`, not merely have a historical ledger; PG move/remove conflict | Authority admission fixed; stale folder-head dependency recovery remains in C18.4.07 scope |
| H. Project order | GAP-P1 recovery; otherwise PASS | Exact eligible project set and membership proofs, generic conflicts/full-tip/stale decisions; `dependencies_ready` compares metadata proof maps and current membership heads exactly | Same stale-dependency recovery mechanism is absent; no claim of complete recovery |
| I. Local-only exclusion | PASS | `eligible` uses explicit same-account binding and metadata authority; `portable` filters before constructing payload/proofs; interleaved native test, PG L1 absence on B, binding count2 | No login/order/folder/current-selection path registers L1 |
| J. Dependencies/orphans | GAP-P1 recovery; safety PASS | Unknown dependency retains exact inbox bytes and blocks ACK; typed blockers persist; new known-gap reopen/retry proof | Missing dependency can retry; superseded immutable dependency has no completion protocol |
| K. Shared ACK | PASS safety; GAP-P1 eventual progress | `ack_proven` matches frame/nonce/ciphertext/sequence/outcome; extended PG proves blocked account event followed by applied Stage cannot advance ACK; known-gap shows newer resolution cannot fill earlier hole | No per-entity bypass; closure blocked by recovery |
| L. Conflicts/full-tip/stale resolution | PASS for admitted events | Native generic all-four-type A+B/R+C/R2, Stage/order full-tip and metadata stale decision proofs; exact local CAS; PG branch preservation and convergence | Dependency-blocked events are not admitted tips; the gap is classified separately |
| M. Tombstones/destruction | PASS safety; DEFERRED BY FROZEN DESIGN cleanup | Folder relation/tip checks retain projects/memberships; Stage unconditional `tombstone_blocked` retains children/order and has no destructive ledger; metadata tombstone retains visible project/children | Metadata intent ACK authorizes preservation only, as frozen by accepted C18.3.04, never cleanup |
| N. Restart/replay | PASS durability; GAP-P1 eventual progress | File-backed native reopen, exact IDs/frames/sealed nonce/ciphertext, PG response-loss duplicate replay; typed blocker reopen regression | Stored data survives; permanent stale-dependency blocker remains |
| O. Two-device integration | PASS for bounded graph; not full closure | Extended `test_account_catalog_explicit_migration_two_native_devices_v2_postgresql`: metadata → two Stages → Stage order; folder/order → membership → project order; L1 only on A; explicit conflict resolution, confirmed common ACK and later blocked-account/applied-Stage sequence | Tests normal integrated graph, not a workaround for the reproduced P1 |
| P. Security isolation/readers | PASS | Metadata account/project/foreign-parent negatives; Stage foreign-stage/unknown-frame tests; account crypto wrong user/type/scope/version vectors; catalog exact inner/outer pair checks and binding joins; runtime auth/key lease/epoch guards | No downgrade or cross-account/project borrowing found |
| Q. Diagnostics/UX | PASS; graphical shell P2 | Mirrored safe allowlists, `diagnostics.spec.ts`/`desktop.spec.ts`, prior native privacy/queue/reopen proofs; friendly status maps/fallbacks for dependencies/limits/formats; separate metadata/Stage/catalog controls | Clear → reproduce → correlated copy/export supported locally; no telemetry |
| R. Future children | DEFERRED BY FROZEN DESIGN | Stage tombstone blocks regardless of whether current known children appear empty; unknown maps/documents/progress/game cannot prove completeness; project physical cleanup absent | Notes/maps/documents/progress/covers/game manifests belong to later C18; not a closure gap by themselves |

## P1-01 — historical metadata proof is not current authority (fixed)

Before the fix, catalog `dependencies_ready` accepted a project's historical
nondeleted metadata apply ledger, even if the visible local metadata no longer
matched the authenticated authority. The new regression removes C1 membership
while C1 has an unreconciled local rename: baseline returned `applied` where
`catalog_project_unproven` was required. The bounded fix checks the referenced
project's current `metadata::authority_view().state == active` inside the same
catalog preparation/apply transaction. Conflict, pending resolution, local
divergence and tombstone states cannot authorize membership/order application.
After reopening and reconciling the existing metadata, the **same** retained
membership frame applies and receives ACK proof. No new ID or ciphertext is issued.
Existing friendly waiting/help text already describes this dependency; no new
UI text, localization, protocol, schema or dependency is introduced.

## P1-02 — immutable stale dependency has no safe recovery (unresolved)

Exact reproducible sequence in the new native known-gap test:

1. Explicitly migrate the catalog (metadata sequences1–2, catalog3–8).
2. Capture and seal folder-order O over the current live F1/F2 heads.
3. Apply another device's ordinary F1 rename at sequence9. Folder IDs/live membership do not change.
4. Receive O at sequence10. Its proven old F1 head differs from current tips:
   `catalog_membership_changed`; no ledger or ACK proof is written.
5. Explicitly publish/apply R over the exact current folder-order tips and fresh
   dependency heads at sequence11. R has valid proof; O was never admitted as a tip.
6. Reopen the database and retry the exact immutable O: the same blocker remains;
   `ack_proven(10)` is false even though `ack_proven(11)` is true. The real common
   ACK candidate remains9; O's exact sealed nonce/ciphertext are retained.

`proof_ready` accepts only current heads; `decide` can resolve current causal tips,
not a dependency-blocked event outside that tip set. There is no bounded ancestry
admission or complete conflict-preservation proof for this old operation. New R
therefore cannot repair the contiguous hole. A Stage rename already has a bounded
ancestry rule for Stage order, which makes this difference observable rather than
a hypothetical concern. Project-order proof-map equality has the same recovery
boundary when metadata or membership heads advance.

This is P1, not P0: exact source/history/children remain retained and ACK correctly
stops. It is not a later-content manifest requirement and not a harmless P2 cap.
A simple skip, fabricated ledger, changed ciphertext under the same ID, or weakened
current-head comparison would be unsafe. Generic recovery affects frozen immutable
dependencies, resolution admission and complete-preservation ACK semantics for
several catalog types; it deserves corrective **C18.4.07 — CATALOG STALE DEPENDENCY
RECOVERY / SHARED ACK PROOF**. Freeze a scoped bounded ancestry/reconciliation rule,
preserve all changed-membership conflicts, and prove old-event completion plus
two-device contiguous ACK recovery. Do not start C18.5 or close C18.4 first.

## Local checks and CI disposition

Focused frontend checks: **38 PASS** across8 files (account-object/C11 vectors,
catalog codec/runtime/reader, mixed V3 cycle, diagnostics and desktop support).
Native: **37 PASS** (catalog9 including two new audit/regression tests,
metadata acceptance4, Stage20, account transport/vector4); cargo check PASS with
existing warnings. Python SQLite/catalog/account subset: **64 PASS**. One extended
real PostgreSQL two-device scenario: **1 PASS, 0 skipped, 99.49 seconds**, including
confirmed server/local cursor convergence before the intentional account blocker
and an applied Stage afterward. Affected Python files compile in memory without
bytecode. No full legacy green-suite rerun or full SQLite CI-equivalent claim.

No TS/Vue, build, schema, dependency or workflow change: typecheck/frontend build
were not rerun; independently accepted C18.4.05 evidence is retained. Existing
mandatory Cloud command includes all three affected PG modules; existing native
catalog filters include the new tests on Cloud Linux and SQLite Windows. Both
workflow triggers cover `account_catalog.rs`; PostgreSQL timeout remains40 minutes.
Expected Actions: Cloud backend tests and SQLite sync substrate tests. New remote
CI is PENDING; after the authorized push Codex stops without polling/watching it.

## Deferred/P2 and permanent rules

Full graphical Tauri/Windows E2E and broader manual device runs are P2 release
hardening (C22/C23/PF6.0). Accepted Windows native evidence is retained; the new
native tests match the existing mandatory Windows `account_catalog` filter.
Physical child/history cleanup, compression and new content/game entities remain
later frozen scope, with current fail-closed boundaries retained.

Registration remains CLOSED until the owner completes stabilization/dogfooding,
reviews/fixes release blockers and diagnostics, performs the final terminology
audit and critical manual tests, and explicitly opens it. PF6.0/RC does not open
registration automatically. C22/PF6.0 final terminology audit remains required.
C21 order is local browser build → Tauri dependency audit → browser adapters →
stable local Web → VPS/production. No telemetry or production deployment here.
