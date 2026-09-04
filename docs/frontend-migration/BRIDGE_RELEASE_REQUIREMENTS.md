# NFProgress — Bridge Release Requirements

Решение F8: `CONDITIONAL`.

Текущий репозиторий содержит migration-only Python primitives, но не содержит
отдельно упакованного и автоматически запускаемого перед Tauri полного
multi-domain helper-а. Пока такой helper не входит в release package и не
прошёл rehearsal на копиях реальных профилей, Python bridge release является
обязательным безопасным вариантом для PKL-backed пользователей.

Bridge release не должен быть скрытой частью Tauri runtime и не должен
переводить authority через несколько временных форматов:

```text
legacy PKL/JSON → canonical MigrationBundle v1 → SQLite v6
```

## Source states it must fix

- current Python production profiles with `data.pkl`, `settings.pkl`,
  `gamer.pkl` and/or `documents.json`;
- schema v3/v4 profiles whose SQLite mirror omits envelope fields or bindings;
- profiles with missing stable IDs that can be deterministically repaired;
- stale but readable mirrors, provided PKL/SQLite parity is proven;
- old Windows data copied from `%USERPROFILE%\Documents\nfprogress` into the
  canonical `%APPDATA%\nfprogress` root.

It must stop with a diagnostic, not guess, for corrupt PKL, conflicting
authorities, broken parent relations, duplicate IDs, partial writes or an
unreadable source.

## Required normalization and markers

The bridge must:

1. create stable project, stage, progress, note, document and binding IDs where
   they are absent, using deterministic scope-based rules;
2. preserve existing IDs, order, dates, Unicode, maps, unknown JSON-safe
   extensions, Game state, settings, notes, documents and binding metadata;
3. export MigrationBundle v1 plus the source manifest, individual SHA-256
   checksums and the aggregate source fingerprint;
4. prepare SQLite schema v6 and verify `PRAGMA integrity_check` and
   `PRAGMA foreign_key_check`;
5. write explicit migration metadata only after semantic verification:
   `source_fingerprint`, source file checksums, bundle version, importer
   version, schema version, completed domains and completion timestamp;
6. leave `data.pkl`, `gamer.pkl`, `settings.pkl` and `documents.json` untouched;
7. retain the pre-upgrade application-state backup until a release owner
   explicitly approves cleanup.

No marker may mean merely “legacy file no longer exists”. A retry with the same
source fingerprint must be a no-op or reproduce the same verified result. A
changed source fingerprint after a failed attempt must require a fresh preview
and must not resume assumptions from the previous attempt.

## Why this is safer than a Rust compatibility branch

The Rust desktop must not learn to deserialize pickle. The existing Python
classes are the compatibility boundary for historical class paths, while Rust
is the trusted importer of a bounded JSON DTO. Keeping those concerns separate
avoids shipping a second pickle implementation, avoids arbitrary object
construction in the desktop, and makes the one-shot conversion auditable and
removable after rollout.

## Idempotency and rollback

The helper must use this boundary:

```text
lock source → snapshot all available inputs → inspect/preview
→ decode in migration-only process → validate bundle
→ write a temporary SQLite profile → semantic verify
→ atomically activate → mark completion
```

Failure before activation leaves the old profile usable. Failure after a
filesystem activation keeps the previous profile in a named rollback location.
The helper must never delete the only backup and must never activate a partial
database. A second run must not duplicate projects, notes, rewards, documents
or bindings.

## Required tests before shipping

- PKL-only, PKL + Gamer + documents, prepared v3/v4/v5/v6 and mixed-owner
  profiles;
- fresh, repeated launch, changed-source retry and interrupted phases;
- duplicate IDs, broken relations, invalid dates/numbers, unknown extensions,
  Unicode and boundary dates;
- malformed/corrupt pickle rejection after static opcode inspection;
- MigrationBundle duplicate IDs, path traversal, oversized JSON, unsupported
  future version and failed-verifier rollback;
- application backup checksums, corrupt backup rejection and failed restore
  rollback;
- semantic parity for projects/stages/order/progress/settings/notes/Game/maps,
  documents and bindings, not only row counts.

The bridge release is not approved by this document alone. It needs a packaged
artifact, signed distribution plan, manual real-data rehearsal and a release
owner decision that the source matrix is complete.
