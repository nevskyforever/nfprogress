# NFProgress — F8 release qualification

Дата: 2026-09-04. F8 audit baseline: `e490698`; F9 qualification baseline:
`e70ba022989d70d6ca4d8aaf4703486dad045999`.
F8 разделяет `Architecture complete` и `Production upgrade qualified`.

Итог F8 был **BLOCKED**. F7 доказал Python-free архитектуру и packaging
boundary для development runtime. F8 доказал локальные validation/recovery
primitives и обнаружил незакрытые production gates: нет упакованного полного
legacy helper-а, нет proof cross-generation updater/data activation и нет
production-signed artifact evidence.

## 1–12. Baseline, decisions and source matrix

1. Actual baseline HEAD: `e49069834793fe3151fcedf14e7308a577f37ea1`.
2. Baseline ancestry contains F1–F7; F7 is the parent architecture milestone.
3. Current production app metadata says version `5.3.9` (`engine.py`).
4. No user-facing release was published by F8.
5. `update_manifest.json` and `update_manifest_legacy.json` were not changed.
6. Complete source matrix: [`F8_MIGRATION_MATRIX.md`](F8_MIGRATION_MATRIX.md).
7. Direct seamless sources: fresh install; valid prepared v6 profile with all
   authorities already SQLite; valid restored profile after staged validation.
8. Helper-required sources: PKL-only, PKL + Gamer + documents, v3/v4 profiles,
   mixed-owner profiles, changed-source retry and ambiguous partial migration.
9. Bridge-required source: any PKL-backed production profile if a packaged
   helper is not delivered before Tauri.
10. Web-converter-required source: only users who explicitly choose the future
    service after local helper/manual recovery is unavailable.
11. Unsupported/manual source: corrupt DB/backup, conflicting markers, broken
    relations, unknown pickle classes or unproven downgrade.
12. Another Bridge Release: **CONDITIONAL**. It is required unless a separate,
    signed and rehearsed migration helper is shipped and invoked before Tauri.

## 13–23. Bridge, bundle and validation

13. Exact bridge requirements: [`BRIDGE_RELEASE_REQUIREMENTS.md`](BRIDGE_RELEASE_REQUIREMENTS.md).
14. The bridge is monotonic: legacy PKL/JSON → MigrationBundle v1 → SQLite v6.
15. PKL remains outside the Tauri runtime and is retained as recovery evidence.
16. Current MigrationBundle version: **v1** (`dto_version=1`).
17. Sections: `dto_version`, `projects`, `project_order`, `folders`,
    `project_metadata`, `root_extensions`, `source_manifest`, optional `game`,
    optional `documents`, optional `document_bindings`, optional
    `external_file_manifest`.
18. Settings and Notes are not bundle sections; their existing cutover APIs
    must be orchestrated and verified by the eventual full helper.
19. Bundle validation now rejects newer/unknown top-level fields, invalid or
    duplicate stable IDs, incomplete order, broken project/stage/folder/binding
    and document relations, invalid JSON, deep/oversized payloads and non-finite
    JSON constants.
20. SQLite validation checks header/open, singular schema marker, required v6
    tables, JSON payloads, contiguous project order, owner rows,
    `PRAGMA integrity_check` and `PRAGMA foreign_key_check`.
21. Unknown nested extension fields are retained; unknown top-level DTO fields
    are rejected so they cannot be silently lost.
22. Future bundle/schema versions are rejected without DB mutation.
23. Archive path traversal/symlink/ZIP limits are enforced by the existing
    updater/XMind/DOCX boundaries; the future bundle archive must apply the
    same policy before extraction.

## 24–40. Import, idempotency, corruption, backup and restore

24. Projects import boundary: validate → transactional replace of the Projects
    representation → semantic readback → guarded owner switch.
25. Failed import rolls back the SQLite transaction and leaves old owner state.
26. The same Projects bundle is idempotent: stable IDs and replacement avoid
    duplicate projects, stages, progress or bindings.
27. Source fingerprint: SHA-256 over sorted available `nfprogress.db`, PKL and
    `documents.json` names plus each file digest; changed source requires a new
    preview/rehearsal.
28. Stale PKL: ignored after the relevant SQLite owner is switched; it is never
    a runtime fallback after a SQLite error.
29. Stale `documents.json`: ignored after `documents_json_migration`; existing
    document rows win via `INSERT OR IGNORE`; file is retained.
30. SQLite v1→latest: PASS for a constructible empty schema chain; populated
    historical semantic coverage remains a rehearsal requirement.
31. SQLite v2→latest: PASS for the same constructible chain.
32. SQLite v3→latest: PASS; populated v3 preservation of settings/notes and
    owner state is covered by Rust/Python tests.
33. SQLite v4→latest: PASS for schema chain and current v4 tables.
34. SQLite v5→latest: PASS for schema chain and Game metadata migration.
35. SQLite v6→latest: PASS/no-op when valid; future/malformed state rejected.
36. Partial marker/table disagreement: rejected as `database_corrupt` by the
    qualified validator; native Rust open now rejects missing required tables.
37. Corrupt SQLite: explicit recovery state; no stale PKL fallback. Invalid
    header, invalid JSON, missing table and integrity/FK failures are tested.
38. Missing SQLite: fresh initialization if no legacy files; explicit helper if
    legacy files exist.
39. Interrupted migration: pre-migration backup plus source fingerprint makes
    retry deterministic; partial activation is never treated as success.
40. Backup before migration: `PickleRepository.create_backup()` now delegates
    to sealed application backup creation and keeps sources untouched.

41. Backup format: timestamped directory under `<data-root>/backups`, with
    `backup_manifest.json`, SQLite, selected legacy stores, `documents.json`
    and `external_file_manifest.json`.
42. Manifest fields: format version, kind, UTC creation time, app version,
    schema version, source fingerprint, file paths/sizes/SHA-256 and explicit
    `external_files_are_references=true`.
43. External files are not copied by application-state backup; paths, hashes,
    sync metadata and exists/missing status are recorded.
44. Backup creation is write-temp → fsync file/dir → atomic directory rename;
    no valid-looking half-written backup is exposed.
45. Existing backup directories are never overwritten; initial retention is
    conservative and cleanup is manual/release-owner controlled.
46. Valid backup restore: validate complete manifest and SQLite first, upgrade
    only in staging, verify again, atomically activate.
47. Corrupt backup: rejected before current profile is moved.
48. Failed restore activation: previous profile is restored from named rollback
    directory; rollback is retained after successful activation.
49. Old unsealed backup: accepted only with explicit limitation—file sizes can
    be checked, but old backups have no trustworthy checksums.
50. Full portable backup: **P2/post-F8**. Application-state restore is in scope;
    copying user-owned Word/Scrivener assets is not yet promised.

## 51–67. Runtime/update/platform qualification

51. Downgrade policy: unsupported after schema migration unless a matching
    pre-migration backup is restored first.
52. Rollback strategy: stop staged rollout, revert manifest, preserve data and
    restore the matching old-format backup before reinstalling the old app.
53. Old app identifier: no stable bundle/application identifier is declared in
    the Python app source/release metadata; this is not proven.
54. New app identifier: `app.nfprogress.tracker` in `frontend/src-tauri/tauri.conf.json`.
55. Old data directory: Windows `%APPDATA%\nfprogress` (with legacy discovery
    from `%USERPROFILE%\Documents\nfprogress`); macOS `~/Documents/nfprogress`;
    Linux `~/Documents/nfprogress` or `~/.local/share/nfprogress`.
56. New release data directory: same platform paths in `sqlite_data_root()`;
    debug builds append `test_data`, release builds do not.
57. Data discovery is deterministic and does not scan the home directory, but
    Windows legacy copy behavior lives in Python and is not in Tauri startup.
58. Reinstall retaining the data root: PASS for a valid existing v6 SQLite
    profile; it is reopened rather than treated as fresh.
59. Cross-generation updater: **BLOCKED**. The legacy Windows updater requires
    `nfprogress.exe`/`nfprogress-updater.exe`, while Tauri uses a different
    executable/package contract; continuity is not proven. macOS replacement
    accepts `.app`/DMG but has no signed cross-generation rehearsal.
60. Tauri updater configuration: **PASS WITH LIMITATION**. Windows release
    config creates signed updater artifacts and GitHub endpoint; the legacy
    hosting manifest is a separate shape and remains unchanged.
61. Updater signature readiness: CI configuration validates Tauri signing keys;
    no production secret was used in F8.
62. macOS signing/notarization: **NOT TESTED/NOT READY**. Local app evidence is
    ad-hoc (`Signature=adhoc`, no TeamIdentifier); notarization evidence absent.
63. macOS ARM: **PASS WITH LIMITATION**. The post-commit production DMG builds,
    verifies with `hdiutil`, and its ARM app smoke-created SQLite in an isolated
    data root; signing/notarization remain unproven.
64. macOS Intel: **PASS WITH LIMITATION**. The post-commit x86_64 production
    DMG builds and verifies; runtime execution on this ARM host is not proven.
65. Windows x64: **NOT TESTED locally**. CI workflow builds NSIS with
    `x86_64-pc-windows-msvc`, but a successful CI artifact/signature is required
    before release readiness.
66. Package inspection: the fresh ARM/Intel archives contain no Python,
    FastAPI, Nuitka, PKL parser or sidecar names; `SOURCE_CODE.txt` embeds the
    qualification commit.
67. Permissions: SQLite data path is deterministic; Word/Scrivener access under
    signed/notarized macOS sandbox/security-scoped bookmarks remains unproven.

## 68–80. Fixtures, services, rollout and remaining issues

68. Representative fixture: existing F1–F6 fixtures cover multiple projects,
    stages, order, progress, maps, notes, Game, folders, bindings, documents,
    Unicode and unknown extension fields; F8 backup/restore covers the same
    SQLite relations.
69. Large fixture: F8 adds a bounded 250-project migration validation profile;
    it is a qualification smoke fixture, not a millions-of-rows benchmark.
70. Unicode fixture: Cyrillic, emoji, non-Latin content and paths are preserved
    by JSON-safe bundle/backup handling and existing parity tests.
71. Date-boundary fixture: timestamps around midnight/week/month/year are
    persisted as source values; the known weekly oracle failure is isolated
    below and does not alter migration bytes or stable IDs.
72. Missing external files: internal document remains; binding is
    `missing_external` and rebindable.
73. Fresh install: PASS in Rust tests and F7 startup smoke.
74. Current SQLite reopen: PASS when the exact v6 authority precondition holds.
75. Repeated launch: PASS for owner guards, document marker and bundle import;
    no reimport or duplicate rewards/documents is expected.
76. Legacy Migration Service contract: upload → static inspect → isolated
    restricted converter → MigrationBundle v1 → preview → download/trusted
    import. No public deployment is part of F8.
77. Service security boundary: isolated worker/container; no production DB
    credentials, network, host filesystem, Docker socket, SSH credentials or
    cloud metadata; read-only root, ephemeral storage, CPU/RAM/process/time and
    upload/entity/depth limits, short retention and no raw content logging.
78. Personal real-data protocol and staged rollout are in
    [`F8_RELEASE_ROLLOUT_PLAN.md`](F8_RELEASE_ROLLOUT_PLAN.md) and
    [`F8_RECOVERY_RUNBOOK.md`](F8_RECOVERY_RUNBOOK.md).
79. F9 closes the migration-helper P0: a separate packaged PyInstaller helper
    now performs read-only detection, canonical Bundle v1 conversion and
    staging/verified activation. Remaining P0 blockers are cross-generation updater/installer and identifier continuity proof; Windows
    cross-generation updater/installer and identifier continuity proof; Windows
    CI artifact/signature; real signed/notarized macOS evidence.
80. P1 issues: populated v1/v2/v4/v5 historical fixtures, explicit startup
    recovery UI states, security-scoped bookmark qualification and bundle
    archive container/import preview. P2: portable external-asset backup and
    public Legacy Migration Service.

## Test evidence and baseline failures

- Python focused migration/recovery/authority/build-isolation suite: **85
  passed, 2 subtests**.
- Baseline full Python run at `e490698`: after `297 passed, 11 skipped` it was
  interrupted because the suite hung; it had reproduced the legacy
  accessibility and OpenAPI developer-response failures before interruption.
- Post-change full Python run: **560 passed, 3 failed, 15 skipped**. The three
  failures are the same known accessibility, OpenAPI developer-response and
  weekly-symbol date-boundary tests; no new failure appeared.
- Rust: `cargo fmt --check`, `cargo check`, `cargo test`: **32 passed**.
- Frontend post-F8 rerun: typecheck, **261 tests**, and build passed; only the
  existing sourcemap/dynamic-import/large-chunk warnings remain.
- Existing three Python failures: accessibility is legacy PySide-only and does
  not block Vue/Tauri; OpenAPI developer response is Web contract-only; weekly
  symbol date boundary is relevant to oracle parity but not persisted migration
  bytes/IDs, so it is P1 parity debt rather than an F8 storage blocker.

## Exact readiness and next action

Production readiness after F9: **BLOCKED — migration path qualified, release
engineering blockers remain**.

Before release, complete the P0 list, run the full matrix on copied real-data
fixtures, obtain fresh artifacts whose embedded revision equals the release
commit, pass Windows CI/signature and macOS signing/notarization, and add a
qualification gate before any publish workflow can update manifests. Recommended
F9 evidence is in [`F9_MIGRATION_HELPER.md`](F9_MIGRATION_HELPER.md) and
[`F9_BRIDGE_RELEASE_DECISION.md`](F9_BRIDGE_RELEASE_DECISION.md). Do not publish
the helper, bridge or Web converter from this milestone.
