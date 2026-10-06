# C18.6.02 — local external integration acceptance

## Audited current-state map

Baseline `5b4d54d3ae4de8bf801683f36f01dbdedb6612a1`, branch6.0,
HEAD=origin/6.0, clean preflight. C18.6.01 independently accepted: SQLite
37372599703 attempt2 SUCCESS (Python/Rust); Cloud37372599817 attempt4 SUCCESS
(frontend/foundation/content-action/regressions). Progress stays77.0%.

| Authority/state | Class | Actual implementation |
| --- | --- | --- |
| Portable Document | A | codec10/v1, native document_sync + documents SQLite |
| Document Word binding | C | native documents.rs / document_bindings |
| Project Word/Scrivener source | C | native documents.rs also uses document_bindings; legacy project_bindings/synch mirrors stay local |
| Legacy local document integration | C | Python DocumentService documents.json, desktop-local guard |
| Progress | portable frozen authority | codec11 / progress_sync; source path/hash excluded |

Frontend useDocumentSync.link immediately writes selected existing file on
baseline. Native bind lacks semantic comparison; native accept already checks
fresh file hash/parser and editor CAS, but marks binding synced before self-echo.
Native project run_sync immediately records source-derived progress; background
joins only configured local bindings. Existing fs writer uses fsync+replace.
Existing bindings payload_json/expected_external_hash are sufficient for durable
local comparison/proposal evidence: schema stays38, no backend migration or
portable codec/capability changes. Web local integration APIs are desktop-gated.

The baseline audit above precedes implementation; completed local evidence follows.
No local developer paths are included in this document.

## Implemented boundary

Schema remains38; no new SQLite or Alembic migration, cloud capability, entity,
codec, crypto or ACK cursor. The accepted cover implementation is unchanged.
Metadata/Stage migration recognizes the already-frozen local `synch` and
`last_synch` keys as C, retaining their raw source snapshots locally and excluding
them from canonical portable fields. Unknown portable extensions still block.

Native cloud-project progress sources now use existing `project_bindings`,
separate from manuscript `document_bindings`. Existing legacy rows are retained;
without authenticated comparison evidence they require explicit revalidation.
Local-only native progress integrations retain their prior local behavior.
The Python documents.json service remains a legacy/local adapter; Web views
exclude binding fields and external read/write/import endpoints reject Web
filesystem ownership before repository/filesystem access.

### Actual local evidence

* Document binding: binding_type, external_path, source_id, last_external_hash,
  last_synced_revision/hash/at, sync_state, expected_external_hash, payload_json.
* `payload_json.reattach_v1`: exact compared Document snapshot/tips, external raw
  hash, parsed-content digest, action and optional intended output hash. This is
  local evidence, not Document extensions. Unknown local metadata stays intact.
* Project binding: project/stage identity, type, path, source_id, content_hash,
  last_synced_at and local proposal/baseline/pending evidence in payload_json.
* Progress comparison requires an applied causal tip and apply ledger, active
  migration and matching authenticated chain. Authored/unsealed local tips are
  insufficient; duplicate confirmation before self-echo is blocked.
* Document comparison requires the active single authenticated projection head
  and exact current canonical snapshot. Pending drafts/conflicts require review.

### First output versus existing-file reattachment

| Action | File effect | Portable effect |
| --- | --- | --- |
| Explicit export/copy | Existing save-dialog/export path produces a chosen output | None |
| Reattach existing Word | Read/hash/parse/compare only | None |
| Semantically equal | Establish local hash/head baseline, no normalization write | None |
| Different Word | Durable local proposal and read-only preview | None |
| Use WORTA | Recheck selected canonical binding, hash and head; guarded atomic write | None |
| Import Word | Reread/validate/hash/head CAS; ordinary Document writer | Existing causal Doc event |
| Keep copy | Explicit export; original selected Word stays untouched until a separate choice | None |
| Unlink | Remove local binding only | None |

Semantic comparison ignores equivalent adjacent styled-run segmentation and
empty attributes; it preserves meaningful styles and never rewrites either
source or historical canonical bytes. Raw DOCX ZIP identity is not semantic
identity. Explicit import preserves the parser output and existing title/scope.

### Durable states and restart

Existing-file selection can leave a local binding requiring comparison; it
cannot enable an unguarded write. Comparison persists atomically. A proposal
survives reopen, retaining its old head/hash until an explicit comparison.

Import and its pending binding evidence share the ordinary writer transaction.
The binding does not claim synchronized authority until authenticated self-echo.
A lost response reuses the existing durable Document outbox. Polling can prove
completion, but never imports or writes.

WORTA-to-Word persists intended output hash before filesystem mutation. It holds
SQLite head protection during the guarded write; after temp-file fsync it checks
the expected source hash again immediately before atomic replace. If replacement
completed before binding commit, reopen hashes actual bytes and recognizes the
exact intended output; it does not blindly rewrite it.

| Restart boundary | Recovery rule |
| --- | --- |
| Selected, not compared | Revalidation required, no overwrite |
| Read/hash before comparison commit | Reread; no partially accepted baseline |
| Proposal committed | Frozen head/hash retained; explicit refresh |
| Import decision before writer commit | Transaction rollback preserves proposal and file |
| Writer durable, response/echo pending | Existing exact event/outbox; pending local state |
| Write intent before replace | Explicit retry with current hash/head checks |
| Replace before binding commit | Exact intended output detected by hash |
| Missing/moved source | Local blocker; no portable tombstone or zero progress |

## Word/Scrivener progress sources

Path selection creates only a local project binding. The existing source parser
reads Word or explicitly selected live Scrivener binder item. Same count records
a local authenticated baseline without a Progress event. Different count creates
a local proposal; explicit confirmation rechecks binding/hash/applied head and
uses the ordinary Progress writer. A pending authored tip cannot be mistaken for
accepted cloud authority. Missing content and removed/unknown binder items fail
closed; no zero/reset or mtime arbitration. Paths, binder trees and source IDs
remain local.

Background enumeration includes only explicitly configured source rows, never
filename/disk guessing or manuscript binding reuse. An imported sync-method
project with no source performs zero filesystem reads and emits no Progress
change. A configured source may create a local proposal, never choose a winner.

## Path-leak matrix

Sentinels cover POSIX/macOS/Linux paths, Windows drive/UNC paths, file URI,
Scrivener path and `SOURCE-ID-C18-LOCAL-ONLY`.

| Boundary | Evidence |
| --- | --- |
| Metadata/Stage migration | Known C details excluded; raw local snapshot retained |
| Document canonical content/save/move/conflict/resolution/delete | Strict vectors and existing two-device scenarios; binding not enumerated |
| Progress canonical append/rebase/tombstone | Strict vectors; actual source action frame excludes path/hash/source ID |
| HTTP before transmission | Generated push requests exclude sentinels |
| Before encryption | Canonical native/TS frame assertions exclude binding sentinels |
| PostgreSQL | sync_events, encrypted_objects, sync_devices, cloud_projects and cover rows inspected |
| Other device | A/B bindings never transported; own explicit paths only |
| Web | Binding-free document view; desktop filesystem actions rejected |
| Diagnostics | Existing allowlisted operations/codes only; no args/content/hash/path logging added |

Portable text remains ordinary user content; binding/provenance is never injected
into it. No backend binding table/API, cloud attachment or file watcher exists.

## Acceptance and commands

Commands below assume isolated test profiles and the dedicated real PostgreSQL
URL in NFPROGRESS_TEST_DATABASE_URL; PYTHONDONTWRITEBYTECODE=1 protects artifacts.

* `python -m pytest -q tests/test_cloud_c18_document_acceptance.py`: real PostgreSQL,
  production TS crypto, two distinct file-backed native SQLite DBs, same-content
  different containers, explicit import/echo/convergence, cloud overwrite without
  event, stale cloud/file races, local unlink and file preservation, paths absent
  across devices/frames/requests/server rows. Passed in the full content shard.
* `python -m pytest -q tests/test_cloud_c18_external_progress_acceptance.py
  tests/test_cloud_c18_progress_acceptance.py`: 2 passed,113.85s after exact
  fixture/contract corrections; Word count comparison, explicit confirmation,
  pending-tip rejection/dedup, both-device convergence, live/stale Scrivener and
  missing source, real server blindness. Original causal/rebase/delete assertions
  retained and strengthened with no event before confirmation.
* `cargo test --lib`: 384 passed,1 existing ignored headless hook (executed by
  PostgreSQL bridge acceptance). Added semantic test subsequently included in
  `cargo test --lib external_reattach`: 5 passed. Current unique native union385.
* Metadata C retention/path test:1 passed; documents focused group14 passed.
* Frontend workflow selection:645 tests covered by 395 initial passes + exact
  admin retest5 passes + remaining groups201/48. The admin issue was local Node26
  Web Storage; `NODE_OPTIONS=--no-experimental-webstorage` passes with unchanged
  assertions, while CI stays Node20. Added local panel3 tests pass; current union648.
* Focused frontend document/API/source/UI group26 passed; final presentation6
  passed. Chromium actual panel: all six locales, six clicks per explicit action,
  preview present, no untranslated non-Russian UI or implicit choice.
* SQLite workflow:483 passed,119.32s; new Web guards3 passed separately. Current
  union486. Schema38 fresh/prefix/reopen tests unchanged, no migration needed.
* Legacy Word/Scrivener/method family19 passed (13 unrelated deselected),64.65s;
  affected Web/legacy document family7 passed; localization19 and help11 passed.
  An earlier broad legacy run was bounded/interrupted; isolated focused coverage
  completed. No required test was skipped.
* Typecheck/build, cargo check, affected Python syntax, generated content check,
  YAML/symmetric path filters and git diff --check pass. Protected pyc unchanged.

### Cloud coverage union / budget

| Group | Before | After | Bounded local evidence |
| --- | --- | --- | --- |
| Foundation |34 tests |34 unchanged |34 passed,612.55s |
| Content-action |22 tests |23, adding external source acceptance |21 passed initially; two exact corrected retests pass |
| Cloud/legacy regressions |194 tests |197, adding Web ownership guards |197 passed,110.25s |

Union250 →254, no unique family removed, no weakened assertion, no new skip/xfail.
Keep all four parallel Cloud jobs, independent PostgreSQL services and existing
40-minute limits. Windows/native validation remains, including the new explicit
external_reattach filter. Both workflows react to native module, local service,
acceptance and workflow changes. No Actions polling occurs after push.

C18.6.02 LOCAL COMPLETE / REMOTE CI PENDING; C18.6/C18 IN PROGRESS; official77.0%.
Independent remote platform acceptance remains required. Release gate, terminology
audit and C21 local-Web-first preserved. C18.7/compression not implemented.
