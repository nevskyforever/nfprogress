# C21.2.22 — authenticated full-history feasibility STOP

**IMPLEMENTATION STOP / NOT LOCAL COMPLETE.** Before production edits, clean
branch `6.0`, HEAD, `origin/6.0` and the actual remote branch matched
`779736d3122f11b8382ab1e046185b5d52e23802`; fetch confirmed that baseline.
Protected engine/game_data bytecode hashes matched the checkpoint.

C21.2.18 remains REMOTELY ACCEPTED at
`8df51fbe37624324a5b0831daf6da2f1d0a55ecd`, Cloud `39850013638`, SUCCESS6/6.
C21.2.19 and C21.2.21 remain AUDIT COMPLETE. C21.2.20 remains historical
IMPLEMENTATION STOP / NOT LOCAL COMPLETE. This result qualifies .21's proposed
replay design; it supplies no create acceptance.

## Mandatory feasibility result

The current server can return original Legacy Resolution ciphertext on its v3
endpoint. That positive transport result does not close the browser's complete
history/source contract. Two actual boundaries prevent the requested acceptance:

1. **Registered browser devices cannot fetch required Content history.**
   [SyncService.pull_encrypted][service] checks the whole account for any Note
   `operation=event` before selecting a page. If the requesting device fails
   `content_note_reader_ready`, every v3 pull fails with HTTP409
   `content_note_reader_required`, including `since=0,limit=1` when that first
   page would contain only old Legacy history. A new browser cannot qualify the
   required complete account history once subsequent Content ID0/ID1 exists.
   [BrowserDeviceRegistration][device] registers identity only;
   [BrowserReaderCapability.declare][reader] declares compression support only.
   [BrowserNoteReaderReadiness][readiness] deliberately reports
   `ready=false,declarationAllowed=false` with the unresolved full
   ordinary1/Resolution2 reader requirements. This task prohibits activating
   that capability. The predicate cannot be truthfully satisfied by declaring
   just the bounded private cohort.
2. **A fresh browser has no accepted raw Legacy Resolution-on-v3 producer and
   owner path.** After mode3 cutover, the v2 pull endpoint rejects even requests
   for old sequence ranges. V3 returns the original opaque Note/resolution
   object under a protocol3 page, without a per-event original-transport field.
   [syncDurability][durability] stores the page protocol on newly received rows.
   [BrowserResolutionPlanner.original][planner] accepts raw Legacy Resolution on
   protocol2; protocol3 requires `operation=event` and a framed Content
   Resolution2. The [historical verifier][authentication] makes the same codec
   distinction and binds original protocol in proof digests. A parsed v3 raw
   Resolution row therefore cannot be applied through that existing owner on a
   fresh device. Do not relabel it as protocol2 or fabricate its proof/source.

The first boundary alone blocks the required subsequent-Content and independent
new-browser replay matrix under the present task restrictions. The second
qualifies how the original F/source evidence could be obtained on a fresh
device. A device already retaining an authentic protocol2 F may potentially
compare that exact original descriptor/ciphertext against a v3 server re-fetch
and retain its actual F2 proof. That is a possible read-only join to review; it
is not evidence that current fresh v3 ingestion produces F2 history. No claim
is made that the server loses Legacy ciphertext or that every narrower
Legacy-only replay is impossible.

These trigger the task's sections2/12 STOP for insufficient mixed transport /
complete-history access in the required browser cohort. No private replay
capability, no-head pre-state exception, owner plan, create transition, K route,
cursor grant, reader declaration or fallback endpoint was added. Existing
`unsupported_create_baseline` remains intact. The real Metadata owner and all
accepted .17/.18 update/delete/source/prefix behavior are preserved.

## Demonstrated API and original-wire evidence

A temporary focused test used a disposable PostgreSQL16 container and the actual
FastAPI application, authentication, migrations, registry and sync endpoints.
It used server-opaque fixture envelopes, not genuine Metadata/Content AEAD, so
its result is transport/gate evidence only:

- A real authenticated user registered a device and an empty active bootstrap
  through the APIs, cut over to v2, pushed two opaque Legacy Note rows plus one
  Note/resolution row, declared generic v3 readiness and cut over to v3.
- A protocol3 Metadata descriptor was pushed. A newly registered device pulled
  from0 with `limit=1`. Four pages returned dense sequences1..4, exact event IDs,
  unchanged original nonce/ciphertext, correct `next_cursor`, `has_more`, and a
  v3 response containing the old `resolution` descriptor. No older row was
  silently filtered. V2 pull after cutover returned HTTP409
  `sync_transport_mode_incompatible`.
- The synthetic existing peers then declared the complete Note reader contract
  through the actual API so a writer could publish an opaque Content Note.
  This was fixture setup for capable peers, not a browser readiness result.
  A **fresh** registered browser identity received only the compression
  declaration currently issued by the browser. It received HTTP409
  `content_note_reader_required` for both `since=0,limit=1` and `since=4`.
  The registry still returned authenticated `current_cursor=5`; the capable
  writer could pull all five events. Thus current account/cursor authentication
  does not remove the device gate.

Four temporary Vitest cases used real encrypted `plannerFixture` Legacy F
payloads and actual Legacy parents for `choose_version`, `manual_merge`,
`delete`, and `keep_both`. Each actual protocol2 F prepared successfully and
left every durable fixture row unchanged. `parseV3Pull` accepted its same
original raw `resolution` item. In a negative diagnostic, changing only the
received row's page protocol to3 reproduced what current fresh v3 ingestion
would store; actual F preparation rejected with `invalid_resolution`, with no
further durable writes. No encryption bytes, payload or proof were changed to
make this pass. These four probes demonstrate the dispatch boundary; they are
not no-head create, F commit, restart, or second-device source acceptance.

## Retention, cursor and bounds

[SyncRepository][repository] selects all account rows after `since`, ordered by
server sequence. The encrypted pull service materializes the same original
envelopes, checks descriptor/object consistency and applies per-page limits;
unsupported material rejects rather than being silently removed. Mode selection
is account-wide and exclusive. The actual v3 router emits a v3 wrapper and omits
the service's high-water return value; authenticated registry GET is still the
separate source of H and would need revalidation around a future replay.

Current source has no sync-log compaction path. The unchanged real PostgreSQL
v2 historical-pull/ACK test also passed and retains rows after ACK; this is
bounded current implementation evidence, not a new perpetual retention promise.
Missing sequences, unsupported families, malformed original material and the
16,384-rows-per-store / 32-MiB complete inventory bounds must still block.
No complete replay proof or safe cursor-change snapshot rule was implemented,
so no full-history no-genesis permission is claimed by this stage.

## Checks actually executed

| Command / evidence | Actual result |
| --- | --- |
| Temporary API/PG feasibility test + existing `test_cloud_c18_content_note_gate.py::test_registered_account_capability_gate_and_downgrade` + `test_cloud_encrypted_sync_v2.py::test_c17_v2_opaque_resolution_replay_historical_pull_and_ack_without_pruning` | **3 PASS in6.34s**, no skips. Actual dedicated PostgreSQL16, migrations and HTTP routes. One existing Starlette/AnyIO deprecation warning. |
| Temporary four-strategy crypto probe + `encryptedSyncV3.spec.ts` + `noteReaderReadiness.spec.ts` | **40 PASS /3files in8.49s**. Four temporary probes and36 existing cases. |
| `privateMetadataHandoff.spec.ts -t 'unsupported no-head create baseline'` | **1 selected PASS in2.48s**, selected test1.44s.45 cases unselected by CLI filter; no test-source skip, retry or timeout change. |

Total **44 executed PASS**, zero failures:39 existing checks and5 removed
temporary probes. `PYTHONDONTWRITEBYTECODE=1` was used for Python checks. Both
temporary probe files were removed. The task-created PostgreSQL container was
stopped; `--rm` removed the container and its anonymous database volume. No
host user-data directory was mounted.

Typecheck, production/harness builds, actual Metadata genesis, Content ID0/ID1
crypto/source acceptance, owner/cursor commits, uncertain-commit postchecks,
native CAS/races, revocation, Chromium renderer crashes and full-browser/disk
restarts were **NOT RUN**: the mandatory feasibility gate failed before any
production implementation. No mocked restart or existing local fixture is
presented as equivalent. .19/.17/.18 historical results remain historical.

## Smallest prerequisite and CI effect

Propose **C21.2.23 — cross-transport history authentication and truthful browser
reader-gate contract audit**. Resolve the actual API/consumer boundary before
retrying create:

- Specify whether a private exact server-v3-item to **retained genuine F2**
  history join suffices for an explicitly restricted existing-device cohort,
  including every proof/source join and independent second-device evidence.
  Distinguish it from fresh raw-Legacy-on3 owner ingestion, whose known dispatch
  gap is still open in the checkpoint. Do not rewrite original protocol fields.
- Resolve access to full account history containing Content under the frozen
  full ordinary1/Resolution2 predicate. The current complete-reader prerequisite
  belongs to C21.2.08 and remains incomplete. If a different read-only history
  access policy/API is necessary, that is a **separate backend contract review**;
  it is not an existing endpoint or a permitted fallback in .22.

No backend/schema/wire/crypto alternative was chosen. No new stage weight or
release waiver is added. .23 is proposed only; do not start it automatically.

Permanent changes are this document, a .22 qualification in the .21 audit, and
the checkpoint record/two relevant Metadata gate rows. No production source,
test, dependency, migration or workflow changes remain. Added mandatory CI
workload is0; all six Cloud jobs and40-minute budgets remain unchanged. The
bounded probe durations above do not establish headroom for a future complete
implementation. No large complete-project suite was rerun. Cloud and SQLite
are NOT EXPECTED for these documentation paths under current filters; no
Actions dispatch, polling or waiting is performed.

Final `git diff --check` and exact changed-file checks PASS. The previous
checkpoint is byte-identical outside the new .22 record and the two relevant
Metadata gate rows. Both protected bytecode hashes are unchanged. No user
changes were present at preflight or replaced during this task.

C21/C21.2 IN PROGRESS; C21.2.22 NOT LOCAL COMPLETE; C21.2.21/C21.2.19 AUDIT
COMPLETE; C21.2.20 IMPLEMENTATION STOP; C21.2.18 REMOTELY ACCEPTED;
C21.2.11 historically PARTIALLY RESOLVED; C21.2.08 NOT CLOSED; C21.1.06 NOT LOCAL
COMPLETE. Web89.36%, `ready=false`, registration CLOSED, PUBLIC RELEASE BLOCKED.
VPS, landing, permanent CI/CD release policy, C22/C23/PF6.0/RC gates and all
existing stage weights are preserved.

[service]: ../../backend/app/cloud/services.py
[repository]: ../../backend/app/cloud/repositories.py
[device]: ../../frontend/src/platform/web/deviceRegistration.ts
[reader]: ../../frontend/src/platform/web/readerCapability.ts
[readiness]: ../../frontend/src/platform/web/noteReaderReadiness.ts
[durability]: ../../frontend/src/platform/web/syncDurability.ts
[planner]: ../../frontend/src/platform/web/resolutionPlanner.ts
[authentication]: ../../frontend/src/platform/web/resolutionAuthentication.ts
