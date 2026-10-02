# C18.4.07 structural / account catalog integration acceptance

Branch `6.0`; clean starting HEAD == local `origin/6.0` ==
`39022df6ff0f69cc7ec3f9a4b317e8c6eb6f8f39`.
Owner-supplied independent evidence: **C18.4.06 — REMOTELY ACCEPTED AS INTEGRATION AUDIT**:
[SQLite 36996342190](https://github.com/nevskyforever/nfprogress/actions/runs/36996342190)
and [Cloud 36996342235](https://github.com/nevskyforever/nfprogress/actions/runs/36996342235)
SUCCESS, including Python SQLite, Rust Windows, Frontend admin and PostgreSQL.
That audit intentionally kept C18.4 open for P1-02. Codex did not query Actions.

**Closure decision: C18.4 — LOCAL COMPLETE / REMOTE ACCEPTANCE PENDING.**
No P0 or remaining P1 found within this bounded integration matrix. P1-01 remains
fixed; P1-02 is resolved locally with causal recovery and complete preservation.
This is a closure candidate, not CLOSED or remotely accepted. C18 remains
IN PROGRESS; official progress exactly77.0%. No C18.5 implementation.

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
scenario. All native calls reopen distinct device database files. The former known-gap regression is now a positive recovery proof with an exact
legacy blocker, reopen, preserved O/R tips and a follow-on project Stage event.
The existing PostgreSQL scenario also exercises recovery with production TS crypto.

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
| F. Folder order | PASS locally | `account_catalog_stale_dependency_recovery_preserves_newer_resolution_and_shared_ack`; scoped ancestry over unchanged exact live IDs; PG frozen O → folder rename → newer R → O/R preservation → explicit R2 | No permanent stale-rename ACK hole |
| G. Membership | PASS locally | `account_catalog_membership_waits_for_reconciled_metadata_after_restart` retains P1-01; `account_catalog_project_order_and_membership_cover_causal_metadata_move_and_null` covers folder/metadata rename; live-set/tombstone regression preserves incompatible old relation without moving to deleted folder | Active metadata authority remains required |
| H. Project order | PASS locally | Causal metadata + move/null membership native regression and PG frozen order; `account_catalog_project_set_change_preserves_order_and_unproven_local_ids_block` covers C3, unproven C2, local-only, wrong bootstrap/account | Exact eligible IDs required for direct projection; known additions preserve conflict only |
| I. Local-only exclusion | PASS | `eligible` uses explicit same-account binding and metadata authority; `portable` filters before constructing payload/proofs; interleaved native test, PG L1 absence on B, binding count2 | No login/order/folder/current-selection path registers L1 |
| J. Dependencies/orphans | PASS locally | `account_catalog_dependency_conflict_restart_resolution_and_unrelated_history`; `account_catalog_ancestry_budget_cycle_and_missing_are_not_ack_proofs`; reader keyset fairness regression | Unknown/unproven/unrelated/over-budget remains blocked; proven safe successors recover |
| K. Shared ACK | PASS locally | Converted recovery regression uses real `prepare_note_sync_ack`:9 before recovery,12 after O10/R11/Stage12; PG exact common ACK candidate before user R2 plus confirmed server/local ACK; immutable-byte negative | No per-entity cursor or stored-only ACK |
| L. Conflicts/full-tip/stale resolution | PASS for admitted events | Native generic all-four-type A+B/R+C/R2, Stage/order full-tip and metadata stale decision proofs; exact local CAS; PG branch preservation and convergence | Recovered old events join causal tips without removing concurrent newer branches |
| M. Tombstones/destruction | PASS safety; DEFERRED BY FROZEN DESIGN cleanup | Folder relation/tip checks retain projects/memberships; Stage unconditional `tombstone_blocked` retains children/order and has no destructive ledger; metadata tombstone retains visible project/children | Metadata intent ACK authorizes preservation only, as frozen by accepted C18.3.04, never cleanup |
| N. Restart/replay | PASS locally | File-backed legacy blocker reopen/retry with exact ID/frame/nonce/ciphertext; conflict-resolution reopen regression; PG duplicate upload/apply and response-loss recovery | Same immutable old event receives durable existing outcome |
| O. Two-device integration | PASS locally | Extended `test_account_catalog_explicit_migration_two_native_devices_v2_postgresql`: accepted metadata/Stage/catalog graph plus frozen folder-order O/R conflict recovery, explicit R2, metadata rename + null membership → frozen project order; L1 only on A | One bounded real PostgreSQL scenario, production TS crypto, distinct reopened native devices |
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

## P1-02 — immutable stale dependency (resolved locally by C18.4.07)

Historical root cause: C18.4.06 required frozen dependency heads/proof maps to equal
current heads. O froze F1/F2; rename at9 advanced F1; O10 blocked; R11 applied;
reopen/retry left common ACK at9 permanently. Data retention was safe but eventual
progress was missing. The old deficiency test is replaced by
`account_catalog_stale_dependency_recovery_preserves_newer_resolution_and_shared_ack`.
It retains an exact legacy O10 blocker, applies R11 and real Stage12, reopens,
recovers O as `conflict_preserved`, verifies both O/R tips and visible R, and uses
real `prepare_note_sync_ack` to obtain12 without immediate user resolution.

The catalog-scoped iterative walker follows authenticated parent IDs, using a
cycle-safe visited set and deterministic retained history. Bounds:256 distinct
nodes per dependency unit and65,536 loads per complete event. Every frozen node
and traversed catalog node is same-account/type/entity and has exact `ack_proven`
ledger/frame/nonce/ciphertext/sequence evidence. Current dependency tips must be
single; unresolved branches block until explicit full-tip resolution. The resolved
single tip must cover every frozen reference. Unrelated history, missing/unproven
references and proof limits produce existing typed blockers, never ACK evidence.
Stage's accepted ancestry implementation is unchanged.

Entity semantics are explicit. Folder renames preserve identity/liveness. Folder
order still requires the exact portable live ID set for direct application.
Project proof requires the same explicit account/project/bootstrap, frozen applied
non-delete metadata, active current authority and scoped causal coverage. Membership
can survive folder/metadata rename. For project order a folder move or null relation
is not project removal: authenticated membership ancestry covers the frozen relation,
while exact eligible connected project IDs remain required. Local-only projects
never become proofs or implicit bindings.

Known added/deleted folder sets, proven folder tombstones, or added eligible project
sets are incompatible with direct projection. The event is fully conflict-preserved
with its immutable payload/dependencies and current local candidate; no invalid
permutation or deleted-folder assignment is materialized. Unknown history, unbound
or unproven projects, unresolved metadata authority and unrelated bootstrap continue
to block. Folder tombstones still cannot cascade or delete referenced children.

Existing `cloud_catalog_apply_ledger` outcomes suffice: `applied` and truthful
`conflict_preserved`, exact immutable event/frame/nonce/ciphertext/sequence, retained
authenticated dependency history, event tips and local conflict candidate, all
committed atomically. There is no ignore flag, synthetic replacement, new schema
or new ACK outcome. Causal admission removes only named parents, so late O cannot
roll back concurrent R. Explicit ordinary full-tip R2 can subsequently reconcile.
`ack_proven` remains unchanged; tampered bytes or foreign account never gain proof.

Account reader retains only a scoped ephemeral keyset scheduling position across
bounded cycles, then resets at end-of-list to retry old blockers. New successors
cannot be starved by a long blocked prefix; authentication epoch/scope changes reset
scheduling. This is not a transport/ACK cursor. Existing safe diagnostics codes and
friendly waiting/conflict/resource messages remain accurate; no new UI strings,
plaintext logging or telemetry.

## Local checks and CI disposition

Frontend: **53 PASS /9 files**, including catalog codec/runtime/reader fairness,
account-object/C11 vectors, mixed V3 cycle, Note runtime, diagnostics and desktop.
TypeScript typecheck and frontend build PASS; existing chunk/dynamic-import warnings.
Rust: **52 PASS** (catalog14, metadata acceptance4, Stage20, account transport4,
diagnostics5, developer/profile5); cargo check PASS with existing warnings.
Python SQLite/catalog/account subset: **64 PASS**. Extended real PostgreSQL two-device
scenario: **1 PASS, 0 skipped,258.56 seconds**. Affected Python syntax compiled in
memory without bytecode. No full legacy suite or full SQLite CI-equivalent claim.

Native regressions cover causal rename/move/null, unresolved branch then resolution,
unrelated/missing/cyclic/over-budget history, tombstone/live-set conflict preservation,
exact immutable byte checks, project addition/unproven/local-only/wrong scope proofs.
The PG extension reuses accepted account/bootstrap setup and production TS encryption;
all bridge calls reopen device databases. Confirmed shared server/local ACK converges;
a later deliberately blocked account event followed by applied Stage still blocks ACK.

Existing mandatory Cloud and SQLite Windows `account_catalog` filters cover the new
native tests; reader spec and PG integration module already run in required Cloud
checks. Changed paths trigger both workflows. No workflow or timeout change:
PostgreSQL stays40 minutes. Expected Actions: Cloud backend tests and SQLite sync
substrate tests. New remote CI is PENDING; after push Codex stops without polling.

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
