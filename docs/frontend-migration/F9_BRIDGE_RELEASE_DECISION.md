# NFProgress — F9 Bridge Release decision

## Decision

Bridge Release required for the default rollout: **NO**.

F9 selects the separate, explicit migration helper as the default path. It is
packaged independently with PyInstaller, runs once against a deterministic
legacy data root, writes only a verified canonical SQLite destination, and is
not a Tauri sidecar. A Bridge Release remains a fallback for users whose OS
cannot run the helper artifact or whose installed updater cannot deliver it.

## Comparison

| Strategy | Strengths | Risks/limits | F9 decision |
| --- | --- | --- | --- |
| A — Python Bridge Release | Uses the existing packaged Python runtime; can normalize old data before the Tauri upgrade; familiar rollback channel | Requires another production release and updater continuity; old Python UI can continue writing legacy files after preparation unless every old write path is changed; cross-generation updater is still unqualified | fallback only |
| B — standalone helper | One-shot, removable boundary; no Python in normal Tauri; explicit preview/verification; same Bundle v1 can serve future converters | Needs signed ARM/Intel/Windows artifacts and a delivery/invocation UX; current F9 proves ARM only | default |

## Exact behavior

```text
legacy source
  → read-only detect/fingerprint
  → preview
  → restricted legacy decode
  → MigrationBundle v1 + checksum
  → strict trusted validation
  → staging SQLite v6
  → integrity/FK/semantic verification
  → atomic activation and prepared marker
```

The helper creates a destination backup, never copies external user files,
retains legacy files and produces a concise metadata-only report. A failure
leaves the active destination and source unchanged. A repeated unchanged run is
safe; a changed fingerprint requires a new plan. `merge into non-empty
workspace = not qualified` unless the user explicitly selects replace after
backup.

The marker is stored in existing SQLite metadata (`game_metadata` plus the
existing document marker) and is written only after all domains pass. The
native Tauri gate recognizes only a complete marker/owner/integrity condition.
It returns `migration_required` for `data.pkl` without prepared SQLite instead
of creating an empty workspace. No authority switch happens on detection,
preview, decode or failed staging validation.

## Bridge fallback requirements

If a future Bridge Release is needed, it must invoke the same helper/converter
and trusted importer, create a pre-preparation backup, retain all legacy
sources, record the same fingerprint/checksums/readiness marker, and continue
to support the old application. F9 does not claim that old Python writes and
SQLite authority have been fully reconciled; therefore the bridge is not the
regular rollout path. Bridge preparation must be explicit and idempotent, not a
silent startup action.

Fallback order is:

```text
separate packaged helper → explicit Python Bridge Release
→ isolated opt-in Web Legacy Migration Service → manual validated backup
```

The future Web service may reuse the decoder/converters conceptually, but only
inside an isolated worker. It must never expose pickle decoding as a direct
FastAPI request or grant the decoder production database access.

F9 status remains **BLOCKED** for production because updater continuity,
Windows artifact/signature and macOS production signing/notarization are still
open release-engineering blockers. F10 selects a hybrid explicit helper plus
signed installer handoff; it does not make the old updater replace itself with
a Tauri bundle. Production manifests remain untouched.
