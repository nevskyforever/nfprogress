# NFProgress — F9 migration helper qualification

Дата: 2026-09-04. Baseline: `e70ba022989d70d6ca4d8aaf4703486dad045999`.
F9 closes the first F8 production blocker only. Cross-generation updating,
Windows production artifacts, and signing/notarization remain blocked.

## Boundary and source profiles

The helper is an explicit one-shot CLI/API. It is not imported by Tauri startup
and never writes PKL, `gamer.pkl`, `settings.pkl`, `documents.json`, or external
Word/Scrivener files. The caller supplies one deterministic data root. The
release discovery list is macOS `~/Documents/nfprogress`, Windows
`%APPDATA%/nfprogress` plus the known historical `%USERPROFILE%/Documents/nfprogress`
location, and Linux `~/Documents/nfprogress` or `~/.local/share/nfprogress`.
The helper does not scan home.

Audited profiles:

| Profile | Detection | F9 result |
| --- | --- | --- |
| A PKL-only | `data.pkl` | supported |
| B PKL + `gamer.pkl` | data and Game pickle | supported |
| C PKL + `documents.json` | data and document JSON | supported |
| D PKL + Game + Documents | all legacy stores | supported |
| E SQLite v3 + PKL authority | v3 marker plus data pickle | supported from PKL authority |
| F SQLite v4 mixed | v4 marker plus legacy source | supported after strict validation |
| G SQLite v5 incomplete Game | v5 marker plus legacy source | supported after full rebuild |
| H SQLite v6 incomplete ownership | v6 marker/owners not ready | supported only when SQLite is healthy and source ownership is unambiguous |
| I prepared v6 | v6, four SQLite owners, complete document marker | `READY_FOR_TAURI` |
| J corrupt/ambiguous | unreadable DB, bad marker, broken relations | explicit unsupported/manual recovery |

`detect` returns `source_profile`, `source_version`, files, SQLite tables,
ownership, migration markers, warnings, support status and a stable fingerprint.
Detection has no write side effects. `preview` reports Projects, Stages,
Progress entries, Notes, Game, Maps, Documents, external bindings and warnings.

## Decoder and canonical conversion

`LegacyDecoder` performs bounded static `pickletools` inspection before loading.
It rejects oversized/truncated streams, unsupported opcodes, persistent IDs and
unexpected globals. The allowlist is explicit: `engine.Project`, `engine.Stage`,
`engine.Note`, `engine.Notification`, `game.Gamer`, `game.Quest`,
`game_data.Buff`, `Item`, `FuncItem`, `BankAccount`, `Credit`, `Deposit`, and
the required safe date/decimal/UUID/ordered-dictionary globals. Unknown classes
return `unsupported_legacy_object`; there is no unrestricted fallback.

The restricted unpickler reduces the attack surface but is not a sandbox. A
future Web Legacy Migration Service must run the decoder in an isolated,
resource-limited worker/container with no production credentials or filesystem.

Every domain is converted to the existing canonical MigrationBundle v1:

- Projects, Stages and Progress preserve stable IDs, order, folders, maps,
  bindings, timestamps and JSON-safe extension fields. Missing IDs use UUID5
  scope derivation and never Python hash randomization.
- Settings are an optional full-profile object and retain unknown JSON-safe keys.
- Notes use the existing canonical Notes converter, including tags, `#карта`,
  `source_map_id`, `source_node_id`, ownership and ordering.
- Game stores the existing F3 JSON aggregate, including Gamer fields,
  notifications, streaks, rewards and unknown extensions.
- Documents retain stable IDs, project/stage links, Tiptap JSON, revisions and
  extensions. External bindings become metadata manifests; missing paths are
  `missing_external` warnings and do not block internal migration.

The bundle manifest contains bundle/helper versions, source profile and
fingerprint, creation time, entity counts, per-source SHA-256 checksums and a
canonical bundle checksum. Strict validation rejects unknown top-level fields,
future versions, duplicate IDs, broken relations, invalid document content,
oversized/deep JSON and checksum mismatch.

## Apply and recovery

The qualified flow is:

```text
detect → snapshot source → preview/decode → validate bundle
      → import staging SQLite v6 → integrity_check + foreign_key_check
      → semantic verifier → atomic SQLite activation → READY_FOR_TAURI
```

The destination is empty/new or requires explicit `--replace`. An existing
destination is backed up before import. The staging database is never exposed
as the active profile. Activation keeps a named rollback database and restores
it if the second filesystem rename fails. Source fingerprints are rechecked
before activation; a changed source starts a new attempt. Same-source retries
are idempotent, while a prepared profile ignores stale PKL/JSON recovery files.
Dry-run builds and validates in a temporary directory and makes no source or
destination changes.

The independent `verify` command returns `READY_FOR_TAURI` only for schema v6,
healthy integrity/FKs, four SQLite owners, complete document migration and the
explicit prepared marker. Tauri itself performs only the minimal native gate:
legacy files without that marker return `migration_required`; a fresh directory
is initialized normally; a prepared v6 profile opens normally. Tauri never
decodes pickle or spawns Python.

## Artifact and evidence

`scripts/build-migration-helper.py` builds a separate one-file PyInstaller
executable and includes the shared SQL migration files. The ARM artifact was
actually executed against a copied PKL fixture and produced a verified v6
profile. Intel and Windows builds are not claimed by F9. No helper, bridge,
release or production manifest was published.

Focused F9/F8/F1/F3 tests: **45 passed**. The complete representative fixture
covers Unicode, multiple progress/stage/note/document records, map payload,
Game extension, bindings, missing external file, backup, retry, stale source,
corrupt source, invalid documents and partial SQLite. A large 250-project
fixture remains in the existing recovery qualification suite.
