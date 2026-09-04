# NFProgress — F8 recovery runbook

Это manual/local runbook для release owner и поддержки. Он не удаляет legacy
файлы и не запускает публичный converter.

F9 adds the local helper commands:

```text
nfprogress-migration-helper detect --source <data-root>
nfprogress-migration-helper preview --source <data-root>
nfprogress-migration-helper prepare --source <data-root>
nfprogress-migration-helper verify --source <data-root>
```

`prepare` uses an invisible staging database and replaces the destination
SQLite file only after bundle, semantic, integrity and foreign-key checks.

## Before any migration

1. Close all NFProgress processes and copy the complete data directory to an
   offline archive. Never rehearse against the only live copy.
2. Record the exact source path, app version, file list and
   `source_fingerprint`.
3. Create an application-state backup. The F8 helper writes a temporary
   directory, verifies files, then atomically renames it under
   `<data-root>/backups/<UTC timestamp>`; an existing backup is never replaced.
4. Confirm that external Word/Scrivener paths are user-owned references. A
   normal application backup does not copy those files.

## Migration failure

The states exposed to a caller are:

```text
migration_required
migration_failed
database_corrupt
backup_available
restore_failed
unsupported_legacy_source
external_files_missing
```

Do not delete PKL, `documents.json` or the pre-migration backup. Read the
diagnostic and source fingerprint. If the source is unchanged, retry the same
helper. If it changed, make a new backup and preview; do not resume a partial
assumption. A failed verifier must leave the old authority and owner markers
unchanged.

## Corrupt or missing SQLite

- `missing_sqlite` with no legacy files is a normal fresh install.
- `missing_sqlite` with legacy files requires the explicit migration helper.
- Invalid header, truncated file, failed `PRAGMA integrity_check`, failed
  `PRAGMA foreign_key_check`, missing tables, invalid JSON or broken relations
  is `database_corrupt`.
- Never copy stale PKL over a failed SQLite open automatically.
- Choose a validated backup or explicitly select the legacy converter/helper.

## Restore

Restore flow is always:

```text
validate manifest and every checksum
→ validate SQLite without overwrite
→ copy to an invisible staging profile
→ apply supported schema upgrades there
→ run integrity/FK and semantic verification
→ move current profile to .<name>-restore-rollback-<UTC>
→ atomically activate staging profile
```

If activation fails, the previous profile is put back. The rollback directory
is retained after success until the owner confirms the restored profile. A
corrupt backup is rejected before the current profile is moved.

Older unsealed backups can be inspected and restored only with a documented
limitation: their files are size-checked but cannot be checksum-verified.

## Interrupted migration or update

After restart, inspect schema/owner markers and the backup directory. A
canonical completion marker plus matching source fingerprint means legacy files
are recovery-only and cannot overwrite SQLite. A partial marker/table mismatch
is not repaired opportunistically: restore the pre-upgrade backup or run the
helper from the unchanged source.

The Windows legacy updater has a tested filesystem rollback, but its archive
contract expects `nfprogress.exe` and `nfprogress-updater.exe`; it is not a
proven cross-generation installer for the Tauri executable. Use the signed
Tauri/NSIS package only after cross-generation qualification. Do not downgrade
an already migrated database blindly.

## External files

Restored internal document content remains available when Word/Scrivener files
are absent or moved. Bindings must report `missing_external` and remain
rebindable. Never interpret a missing external file as document deletion.

## Legacy users

PKL-only users need the local helper or, if they explicitly consent, the future
isolated Web Legacy Migration Service. The service returns a preview and a
MigrationBundle; it does not write an account database from pickle. No upload
is automatic.
