# NFProgress — fast-track migration plan

Baseline for F4: `aad08cdd34cd5bc9a10c28e862c2f8aa6860da7c`.

This plan targets the Python-free Tauri desktop only. FastAPI/Python may remain
as a separately deployed Web/cloud backend. The plan is intentionally not
production-safe at every intermediate commit; every milestone is nevertheless
testable, data-preserving and committed separately.

The detailed evidence and data inventory are in
[`FAST_TRACK_AUDIT.md`](FAST_TRACK_AUDIT.md). It is part of this plan, not an
optional appendix.

## Current baseline

```text
projects/stages/progress = PKL authoritative
settings                 = SQLite authoritative
notes                    = SQLite authoritative
game                     = PKL authoritative
```

F2 and F3 are ancestors of the F4 starting HEAD. Their effective current
ownership is therefore SQLite for Projects, Settings, Notes and Game; the
legacy table above is retained as historical context for the original plan.

The v3 SQLite database was a useful shadow/read model. F1 adds schema v4 as a
lossless-capable Projects substrate: project envelope extensions, folders,
actual sync bindings, stable progress ordering and Notes-safe foreign keys.
The v3 database is still not by itself a complete migration source for
`documents.json`, external files, Game state, or legacy PKL fields outside the
Projects aggregate. Rust now runs the shared migration files; ownership is
unchanged until F2.

## Fast-track principles

- One ownership switch per coarse domain, with no hidden second writer.
- Projects means projects, stages, progress, order, folders and project-local
  binding metadata; do not create unnecessary micro-domains.
- Global streaks and notifications move with Game/event state, not into a new
  permanent ownership subsystem.
- Use TypeScript for pure calculations, domain models and testable use-cases;
  use Rust for SQLite, transactions, filesystem, OS integrations and trusted
  desktop validation.
- Keep the Python implementation as a behavioral oracle and migration/recovery
  source until parity and upgrade tests pass. It is not a desktop runtime
  bridge after cutover.
- A one-shot legacy importer is mandatory. Recommended implementation is a
  separately tested Rust importer; a separately packaged migration-only
  Python helper is an explicit fallback. If neither exists, an additional
  bridge release is required.

## Remaining milestones

There are eight meaningful milestones including final release qualification;
F1–F7 are implementation milestones and F8 is the release gate. F4 is an
inserted Game-runtime-completion milestone exposed by the F3 audit; each
milestone gets its own commit boundary.

### F1 — final storage contract and legacy migration substrate

**Goal:** make the final SQLite schema, Rust migration runner and one-shot
legacy importer capable of representing all supported existing-user data.

**Authoritative state:** unchanged; no ownership switch. This milestone is
implemented by the F1 storage audit and repository foundation; the runtime
still uses PKL for Projects.

**Work:**

- define a versioned canonical DTO for the full Projects aggregate;
- add Rust schema upgrade/open checks and shared SQL migration source;
- import the legacy Projects aggregate and the current v3 mirror profile;
- recover omitted project envelope fields and sync bindings; preserve unknown
  JSON metadata and keep Documents migration as its F6 concern;
- make the importer idempotent and leave all source files untouched;
- create Python-oracle fixtures for IDs, dates, writing-day boundaries,
  ordering, maps, game state and external-file manifests.

**Python dependencies:** remain for the current desktop and oracle; no new
desktop bridge is introduced.

**Migration requirement:** source matrix and ambiguous/corrupt-source refusal
must be completed around the migration-only helper before F2.

**Tests / exit criteria:** Rust/TS compile and typecheck; schema upgrades from
all supported versions; importer fixtures pass twice; JSON and semantic parity
passes; no source is rewritten; incomplete DB never silently wins over a
complete legacy source.

**Pre-existing failures:** may remain only if separately recorded and unrelated
to importer/storage invariants. Any failure touching migration fixtures blocks.

**Risk:** Very High. **Codex:** Luna High; Sol only for pickle-format/parser
design or cross-platform migration review.

### F2 — Projects/Stages/Progress SQLite-authoritative cutover

**Goal:** switch the complete Projects aggregate from PKL to SQLite with one
controlled ownership transaction.

**Authoritative state:** `projects`, `stages`, `progress_entries`,
`project_order`, folders and project-local integration bindings become SQLite.

**Work:**

- finish Rust repositories and typed Tauri commands for create/update/delete,
  stage lifecycle, archive/complete/reopen, conversion, ordering and all
  progress mutations;
- preserve stable IDs, legacy list order, units, effective writing days,
  totals, deadlines, status and complete payloads;
- make project/stage deletion clean SQLite Notes and document relations;
- record progress/lifecycle effects in an idempotent Game event/outbox contract;
- remove all desktop Project writes to PKL and all write fallback paths;
- keep Python ProjectService available for Web/oracle only, isolated from the
  desktop data root.

**Python dependencies:** game effects may still be Python in the Web/oracle;
Python no longer owns or writes desktop Projects after the cutover.

**Migration requirement:** run F1 importer, verify PKL/projection parity, back
up, switch ownership, and record the cutover manifest. Never switch on an
unhealthy or incomplete order/parent relation.

**Tests / exit criteria:** full Projects repository/use-case tests; lifecycle
and cross-table transaction tests; Notes/document relation cleanup; progress
rounding/date parity; concurrent-writer rejection; retry/idempotency tests;
Python oracle fixtures; no PKL modification under a desktop test run.

**Pre-existing failures:** date/oracle failures in the known list block if
they affect progress/lifecycle semantics; obsolete UI-only failures do not.

**Risk:** Very High. **Codex:** Luna High, with Sol only for transactional
boundary or data-loss review.

### F3 — Game state and progress-event cutover — complete in development

**Goal:** move Game from `gamer.pkl` plus `data.pkl` side effects to SQLite and
the F2 event contract.

**Authoritative state:** Gamer state, quests, streak/reward markers,
notifications, global streak state, sessions, inventory, bank, cabinet and
achievement evidence become SQLite/event authoritative.

**Work:**

- port pure catalogs/rules and canonical Russian keys to TypeScript Core;
- port orchestration to TS/Rust commands with trusted Rust persistence;
- consume each project progress/lifecycle event once and apply rewards
  transactionally or via an idempotent journal;
- preserve writing-session wall-clock behavior, challenge variants, streaks,
  rewards, quests, mastery, cabinet and inventory limits;
- use Python `game.py`/`game_data.py` only as the oracle until parity closes.

**Implementation:** schema v5 adds Game metadata and retry/poison-event
columns; `GameMigrationBundle` imports and verifies known Gamer state,
Game-owned envelope fields and unknown extensions; SQLite repository methods
block normal Game PKL access after the owner switch; and deterministic
Python/Rust consumers apply F2 events with the processed marker atomically.
The existing HTTP façade remains over SQLite for Web/compatibility; F4 direct
Tauri commands remove it from normal desktop Game use.

**Python dependencies:** no desktop Game runtime; Python remains available to
Web and reference tests.

**Migration requirement:** import `game_state.payload_json` plus any required
`data.pkl` notification/global-streak fields; compare against `gamer.pkl` and
the legacy envelope before switch.

**Tests / exit criteria:** full Game command/state fixtures; reward
idempotency; progress-to-game event parity; daily/timezone/DST tests; all
legacy game tests relevant to supported desktop behavior; SQLite corruption
and retry tests.

**Pre-existing failures:** game/progress/date failures must be fixed or
explicitly retired with replacement tests before F4. Unrelated accessibility
failure may remain outside this gate.

**F3 evidence:** `tests/test_f3_game_sqlite.py` covers migration, failed
verification, no reimport, stale/inaccessible PKL, unknown fields, duplicate
effects, restart, retry/poison behavior and SQLite integrity. Development
authority is complete; production seamless upgrade remains an F8 source
matrix and Legacy Migration Service gate.

**Risk:** Very High. **Codex:** Luna High; Sol for reward-transaction design
or difficult parity failures only.

### F4 — Python-free desktop Game runtime — complete in development

**Goal:** remove Python, FastAPI and the sidecar from normal desktop Game
reads, mutations and event processing.

**Implementation:** Vue now selects a storage-neutral Game repository adapter:
Tauri uses explicit typed commands and Web retains the existing FastAPI
adapter. Rust `GameApplicationService` validates strict DTOs, runs atomic
SQLite transitions, preserves tagged/unknown state, applies F2 events and
provides injectable RNG-backed lottery rules. Economy, XP/level, health and
resources, skills, inventory, buffs, bank, sessions, daily/weekly challenges,
specialization effects and streak protection are native Game operations.

**Python boundary:** `game.py`, `game_data.py` and `GameService` remain for Web,
behavioral-oracle, migration and recovery use. No normal desktop Game path
uses them, pickle, or localhost Game HTTP. Documents and integrations still
use the sidecar and are explicitly outside F4.

**Exit evidence:** native adapter tests, Rust deterministic/idempotency tests,
strict DTOs, catalog parity fixture, SQLite restart/unknown-field coverage and
sidecar-unavailable Game smoke coverage. Production migration readiness and
the bridge-release matrix remain separate F8 work.

### F5 — Mind Elixir maps and XMind import

**Goal:** remove Python from map normalization, map persistence,
reconciliation and local XMind import.

**Authoritative state:** canonical map payloads and map-note relations live in
SQLite under the Projects/Notes contract.

**Work:**

- port `normalize_mindmap_data`, combined-map compose/split and note
  reconciliation to TS pure functions;
- keep the existing JavaScript Mind Elixir editor and adapter;
- implement bounded XMind ZIP/JSON/XML parsing, stable tree mapping and errors
  in Rust; map results through the TS adapter;
- preserve map IDs, node IDs, map metadata and note text exactly.

**Python dependencies:** map/XMind Python API paths remain only for Web or
legacy import until parity is accepted; not in desktop runtime.

**Migration requirement:** F1/F2/F3 map payloads and derived map notes must be
verified before old map writes stop.

**Tests / exit criteria:** TS normalizer/reconciliation parity; JSON/XML XMind
fixtures, limits and malformed archives; multi-stage combined-map round trips;
map-note update/delete/recreate tests; no API call in Tauri map workflows.

**Pre-existing failures:** only map-related failures block; obsolete Qt tests
are not a reason to retain Python desktop runtime.

**Risk:** High. **Codex:** Luna Medium, Luna High for combined-map parity.

### F6 — Documents, Word/Scrivener and background synchronization

**Goal:** move remaining local filesystem behavior out of the Python sidecar.

**Authoritative state:** document records/content and binding metadata are
SQLite-authoritative; external manuscript files remain user-owned filesystem
state referenced by validated paths/hashes.

**Work:**

- migrate `documents.json` records to SQLite and include them in snapshots;
- preserve structured Tiptap JSON with a versioned content format;
- implement Rust local file access, atomic writes, SHA-256 hashes, snapshots
  and change-during-read checks;
- port the supported Scrivener binder/XML/RTF read/count boundary to Rust;
- implement native polling with bounded per-source failures, hash-based
  coalescing and self-write suppression; a native event watcher is not added
  because the audited product behavior is polling;
- explicitly define which remote upload workflows remain Web-only.

**Python dependencies:** no desktop document/integration worker; Python may
remain for remote FastAPI upload endpoints.

**Migration requirement:** preserve document content, paths, hashes, source
item IDs and missing-file bindings; backup must include records and manifest,
not external files implicitly.

**F6 result:** completed for the development desktop path. Typed commands are
`list_documents`, `get_document`, `save_document`, `record_document_progress`,
`rename_document`, `delete_document`, `bind_document_file`,
`read_document_external`, `accept_document_external`,
`parse_word_document`, `import_word_document`, `export_word_document`,
`configure_document_sync`, `get_document_sync`, `get_project_document_syncs`,
`remove_document_sync`, `run_document_sync`, and
`run_all_document_sync`. DOCX limits, XML/archive traversal protection,
Scrivener symlink/size protection, stable IDs, conflict states, and external
file ownership are covered by Rust tests and the existing Python oracle suite.
The external path manifest is included in transitional backups. F8 still owns
full restore and cross-platform release qualification.

**Pre-existing failures:** integration/document failures block; unrelated
legacy UI failures may remain only if retired from desktop scope.

**Risk:** High. **Codex:** Luna Medium for isolated ports, Luna High for
filesystem watcher/sync semantics.

### F7 — Python-free desktop sidecar and packaging cutover

**Status:** Complete for the development desktop runtime. The implementation
is recorded in [`F7_PYTHON_SIDECAR_REMOVAL.md`](F7_PYTHON_SIDECAR_REMOVAL.md).
F8 release qualification remains pending.

**Goal:** make the normal Tauri desktop path direct Vue/TS → typed Tauri →
Rust/SQLite, with no sidecar or runtime PKL.

**Authoritative state:** all desktop runtime domains are SQLite/external-file
authoritative.

**Work:**

- replace sidecar bootstrap with direct Rust DB open, schema upgrade and
  migration status;
- delete `backend_connection`, loopback/token readiness, sidecar child/watchdog
  state and API transport from desktop runtime;
- remove `externalBin` and `nfprogress-backend` startup/configuration;
- remove desktop Nuitka sidecar build scripts and target-specific sidecar
  packaging; retain only a separately documented migration/recovery tool if
  still needed;
- stop normal PKL reads/writes and mirror rebuilds; leave legacy importer and
  recovery tooling isolated;
- preserve Web/Capacitor remote API configuration independently.

**Migration requirement:** first launch runs or invokes the one-shot importer
before opening the profile; failure is diagnostic and recoverable, never a
silent fallback.

**Tests / exit criteria:** run desktop with Python absent; inspect bundle for
mandatory Python/FastAPI/Nuitka sidecar; verify startup, shutdown, update,
settings, notes, projects, game, maps, documents and integrations; prove no
PKL access in normal runtime.

**Pre-existing failures:** no known failure may remain if it covers a desktop
runtime path or a migration invariant. Explicitly retired legacy-only tests
must be listed.

**Risk:** High. **Codex:** Luna Medium for mechanical removal, Luna High for
startup/packaging and release isolation.

### F8 — migration, backup/restore and release qualification

**Goal:** qualify the first publishable Python-free desktop release.

**Work:**

- execute the existing-user matrix on supported source states;
- backup current SQLite plus documents/metadata and external-file manifest;
- restore into a clean profile, upgrade schema, validate, and test rollback;
- test corruption, incomplete migration, missing external files and legacy
  backup recovery;
- run complete Python oracle/parity suite where legacy reference is required,
  full frontend tests/typecheck/build, full Rust checks, and desktop smoke
  tests;
- build macOS ARM, macOS Intel and Windows artifacts on their supported hosts;
- record known failures only if they are explicitly retired and replaced or
  formally accepted as out-of-scope.

**Python dependencies:** migration/recovery helper may remain separate; no
normal desktop process starts it.

**Exit:** all release gates in this document and the audit pass. This is the
only milestone that creates a publishable desktop release.

**Risk:** Very High. **Codex:** Luna High; Sol for cross-platform packaging,
upgrade failures or data-integrity review.

## What changed from P4–P9

| Old stage | Fast-track disposition |
| --- | --- |
| P1 read model | Already complete; retained as F2 input, not a milestone. |
| P2 metadata/order boundary | Already complete transitional work; absorbed into F2 and replaced by direct Rust writes. |
| P3 progress/calculation boundary | Already complete parity foundation; absorbed into F2. Its Python sidecar path is removed by F2/F6. |
| P4 lifecycle/cross-domain effects | Absorbed into F2, with Game effects represented by an event contract rather than blocking storage cutover. |
| P5 filesystem/document boundary | Split by dependency: maps/XMind become F5; documents/Word/Scrivener/sync become F6. |
| P6 pure Game rules | Combined with Game persistence/orchestration in F4 after the F3 event contract. |
| P7 Game persistence/events | F3 storage/event authority, completed for desktop runtime in F4. |
| P8 Python-free runtime | F7 after integrations have direct paths; Game runtime is complete in F4. |
| P9 recovery/legacy retirement | Importer substrate in F1; final recovery and release qualification in F8. |

## Critical path

```text
F1 importer/schema contract
  → F2 Projects authority + event contract
  → F3 Game authority
  → F4 Game runtime completion
  → F5 maps/imports and F6 documents/files/sync (parallel after their inputs)
  → F7 sidecar/PKL/Nuitka removal
  → F8 migration + release qualification
```

The true blockers for Python removal are F1, F2, F3, F4, F5 and F6 only insofar
as the corresponding desktop feature remains supported. Settings and ordinary
Notes CRUD are already cut over. Pure TS calculations, Web backend work,
localization, UI polish, and server-only upload features can proceed in
parallel or later and must not be placed on the critical path.

## Release gates

The Python-free Desktop Release Candidate is ready only when:

- normal desktop startup does not launch Python, FastAPI or a sidecar;
- the desktop bundle has no mandatory Python executable, Nuitka sidecar or
  `externalBin` backend;
- SQLite is authoritative for Projects/Stages/Progress, Settings, Notes,
  Game, maps and Documents;
- PKL is not read or written in normal runtime and mirror rebuild is not part
  of startup or ordinary writes;
- legacy migration succeeds for every supported source matrix, with no silent
  data loss and originals preserved for recovery;
- Notes, Projects, Progress and Game work without Python;
- supported integrations work without Python or are explicitly server-only;
- backup/restore includes DB, document records, metadata and external-file
  verification, and rollback/corruption paths are tested;
- full frontend, Rust and relevant Python oracle/parity suites pass, or every
  remaining failure is explicitly retired and recorded;
- clean install, upgrade, restored backup and missing/corrupt source tests
  pass;
- macOS ARM, macOS Intel and Windows supported desktop targets build and
  complete smoke/signing/update qualification.

## F2 completed scope

F2 is the controlled Projects/Stages/Progress SQLite cutover: verified
MigrationBundle import, owner guard, idempotent startup, typed Tauri CRUD and
progress commands, explicit Notes cleanup, durable idempotent Game events,
preservation of extensions/maps/bindings/folders/references, and SQLite-aware
backup/recovery documentation. F3 adds Game SQLite authority and deterministic
event consumption. F4 completes the exposed Game runtime façade; the next
milestones are F5/F6 integration work; no next milestone is
started by this change.

## Long-Term Legacy Migration Service

The future web mechanism is a separate service/worker architecture: untrusted
upload, static validation, isolated restricted decoder, canonical versioned
MigrationBundle, schema/semantic validation and preview, followed by
download-only conversion or a normal authenticated import API. It must never
unpickle uploads in the production process or let a decoder write production
data. Worker isolation, allowlisted classes/opcodes, resource/archive/path
limits, privacy/retention, authentication, CSRF, quotas and rate limits are
mandatory. No public endpoint is part of F2; details are in
`F2_PROJECTS_SQLITE_CUTOVER.md`.

## F5 Mind Elixir/XMind

F5 is complete for the development desktop path. Mind Elixir load/save and
map-linked Note mutations use typed Tauri commands and SQLite. The existing
opaque `mindmap` section remains nested in Project/Stage payloads, so no
duplicated `mind_maps` authority or schema migration is introduced. Structural
XMind import is bounded and performed in Rust from ZIP `content.json` or
`content.xml`; Vue explicitly selects among multiple sheets. Python remains
the Web adapter, oracle and legacy migration path. Documents, Word, Scrivener,
watchers and global sidecar removal remain F6/F7 scope.
