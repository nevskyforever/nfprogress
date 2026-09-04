# NFProgress — F11 transition rehearsal

Дата: 2026-09-05. Source baseline: `3b3980d`. The rehearsal uses copied test
data only; no live personal profile was opened or modified.

## Current transition contract

```text
legacy source
→ backup
→ helper detect
→ preview
→ prepare
→ verify READY_FOR_TAURI
→ close/block legacy writer
→ install platform Tauri package
→ startup gate
→ first launch
→ close/restart
→ verify persistence
```

The old Python updater must not unpack a Tauri NSIS/app bundle. The chosen
transition remains an explicit standalone helper plus platform installer;
Tauri updater signatures are for subsequent Tauri releases. A minimal
transitional Python release is still required for delivery to legacy users,
but it has not been implemented or qualified at this HEAD.

The explicit qualification version boundary is: last Python transition
release `5.3.10`, first Tauri release `6.0.0`. The boundary is SemVer-ordered
and keeps the legacy numeric updater channel separate from Tauri's
`latest.json` channel. These are qualification values from the F10 fixture,
not a publication command.

The initial platform set for this rehearsal is macOS ARM64 and Windows x64.
macOS Intel remains build-supported but is **DEFERRED / NOT IN INITIAL RELEASE
SCOPE**. The dedicated manual workflow
`.github/workflows/f11-windows-qualification.yml` checks out the dispatch ref,
builds the x86_64 NSIS package and standalone helper, records exact SHA-256 and
checkout provenance, and runs on `windows-latest`. It has no publish step and
uses unsigned qualification mode unless optional signing inputs are explicitly
enabled.

## ARM helper fixture

The copied fixture included Unicode project data, one project, one stage, two
progress entries, two notes including `#карта`, one map, Game state, two
documents, an existing Word path, a missing Scrivener path, settings, and
unknown extension fields. The packaged arm64 helper produced:

| Command | Result |
| --- | --- |
| `detect` | `D_pkl_game_documents`, supported, read-only |
| `preview` | 1 project / 1 stage / 2 progress / 2 notes / 1 map / 2 documents / 3 external bindings |
| `prepare` | `migration_verified`; atomic activation; backup created |
| SQLite checks | `integrity_check=ok`, `foreign_key_check=ok` |
| `verify` | `READY_FOR_TAURI` |
| source files | retained byte-for-byte; external files remained references |
| parity inspection | existing Word binding and missing Scrivener binding retained |

The helper binary was built with PyInstaller on the ARM host and passed
`file`/Mach-O inspection. It is ad-hoc signed, which is an accepted `P1`
trust limitation under the current policy.

## Uncompleted P0 stages

The Tauri install/first-launch/restart leg was not completed. The local
qualification app could not become the active single instance because an
already-running `/Applications/nfprogress.app` process owns the product
identity; it was not safe to terminate that unverified user process. Intel and
Windows were not available. Intel is deferred rather than a current P0.
Windows remains a current P0 and requires the manual runner evidence before
the initial two-platform transition can be called qualified. Therefore this is
helper PASS plus transition BLOCKED, not a full transition PASS.

The following failure cases remain required evidence:

| Interruption | Required recovery proof | F11 result |
| --- | --- | --- |
| helper cancelled/failed | source and prior authority unchanged; retry from same fingerprint | helper unit coverage exists; packaged platform rehearsal not run |
| after prepare before install | backup and `READY_FOR_TAURI` remain deterministic | not run with installer |
| installer download/install failure | old app/source or prepared backup remains recoverable | not run |
| first Tauri launch failure | pre-migration backup and diagnostic path remain available | not run |
| restart/reinstall | same SQLite opens with no reimport/duplication | not run |

## Coexistence policy

Concurrent writers are unsupported. Once preparation starts, the legacy app
must be closed and remain closed until transition completion. The Tauri startup
gate must open the prepared SQLite only when its marker, owners, schema, and
integrity checks agree; legacy PKL/JSON files must remain recovery-only. A
transitional release must enforce this explicitly in its handoff UI/lock and
must never let old Python writes race with SQLite authority.

## Personal-data protocol

Before any real-user rehearsal, make two offline copies of the complete data
root, record app versions and fingerprints, and use one copy for migration and
one untouched comparison copy. Compare IDs, counts, ordering, text/content,
Game balances and streak/freeze state, documents, bindings, maps, notes and
note links. Close the old app before `prepare`; after first launch close the
new app fully and reopen it. Keep the backup until the owner accepts the
comparison. Never use the only live copy and never copy external Word or
Scrivener files into the application backup.
