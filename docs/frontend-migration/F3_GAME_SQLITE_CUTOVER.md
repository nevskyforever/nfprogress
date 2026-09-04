# F3 — Game SQLite authority and deterministic event processing

Status: implemented from the F2 desktop cutover baseline. The current branch
HEAD used for this implementation is `29e064dceeb2fc4dae9f1eba88bdc34cc7ac6969`;
the requested F3 reference `9af7b0597d3f3a54adce23766057546e1c122d68` is not
the checked-out commit, so facts below describe the actual working tree.

## Ownership and cutover

F3 changes the local desktop Game owner from `pickle` to `sqlite` after a
verified, transactional import:

```text
gamer.pkl + data.pkl
    → GameMigrationBundle v1
    → game_state JSON + game_metadata
    → semantic readback verifier
    → storage_ownership.game = sqlite
```

If import or verification fails, the owner remains `pickle`. If the owner is
already `sqlite`, startup returns without reading either legacy Game file. The
legacy files are retained as recovery artifacts and are not authoritative.

The migration reads the full `Gamer.__dict__` (currently 46 fields), envelope
notifications/global-streak fields, project/stage streak markers, freeze
counters, and unknown root fields. JSON-safe unknown values are preserved in
the versioned payload; unknown object values retain a tagged `__legacy_type__`
and field map rather than being silently dropped.

## Canonical representation

The normalized/queried relational state remains in the existing Projects,
Settings and Notes tables. Game state is one versioned JSON aggregate because
quests, inventory definitions, buffs, bank products, sessions and forward-
compatible catalog extensions are nested and not independently queried.

| State | Legacy source | F3 representation | Derived? |
| --- | --- | --- | --- |
| level, XP, coins, health, inflation | `gamer.pkl` | `game_state.gamer` | No |
| skills and coefficients | `gamer.pkl` | `game_state.gamer` | Coefficients are recalculated for display |
| buffs/debuffs | `gamer.pkl` | typed JSON object tags | Remaining time is derived from timestamps |
| inventory/items/custom awards | `gamer.pkl` | `game_state.gamer` | Catalog price/effect is static code |
| bank credit/deposit | `gamer.pkl` | typed JSON object tags | Interest/status display is derived |
| quests and claim markers | `gamer.pkl` | `game_state.gamer` | Catalog definitions are static code |
| daily/weekly challenges | `gamer.pkl` | `game_state.gamer` | reset is lazy at the existing day boundary |
| sessions/history/shields | `gamer.pkl` | `game_state.gamer` | remaining seconds is wall-clock derived |
| specialization/mastery/effects | `gamer.pkl` | `game_state.gamer` | rank/passive values are derived |
| manuscript journeys/cabinet | `gamer.pkl` | `game_state.gamer` | unlocked sets are derived |
| notifications | `data.pkl` | `game_state.notifications` | no |
| global streak/status/markers | `data.pkl` | `game_state.global_streak` | length/status display is derived |
| project/stage streak markers | project objects in `data.pkl` | `game_state.project_game_state` keyed by stable ID | no |
| unknown Game/envelope values | both legacy stores | `gamer`/`extensions` JSON | no |
| catalog definitions | `game.py`, `game_data.py` | application code | yes/static |

The DTO is compatible with `MigrationBundle` v1 through its optional `game`
section. Existing Projects-only bundles serialize and import unchanged.

## Schema v5

Migration `005_game_authority.sql` keeps the existing `game_state` table and
adds `game_metadata(key,value_json)`. It extends F2 `domain_events` with:

```text
attempt_count INTEGER NOT NULL DEFAULT 0
last_error TEXT
failed_at TEXT
status TEXT NOT NULL DEFAULT 'pending'
```

The pending index is deterministic on `(consumer,status,processed_at,
created_at,event_id)`. The migration is version-gated and idempotent for fresh
databases and v4 databases. Existing Projects, Notes, Settings and event rows
are retained.

## Event processing

`GameEventConsumer` and the trusted Rust `game` module consume only
`consumer='game'` events in `(created_at,event_id)` order. The transition is:

```text
read pending event
→ validate context JSON/version
→ apply pure deterministic transition
→ write game_state
→ mark the same event processed
```

All steps use one SQLite transaction. A duplicate `event_id` is rejected by
the existing primary key and a processed row cannot apply again. A failed
attempt records a bounded error and increments `attempt_count`; after three
failures it becomes `status='failed'`, receives `failed_at`, and is excluded
from the startup loop without being deleted. Before that threshold it remains
pending for retry. A crash/rollback before commit leaves both Game state and
the event marker unchanged.

`ProgressAdded` grants the existing base positive-writing reward in the
deterministic core. `ProgressDeleted` is intentionally non-reversible, matching
the Python oracle: it records an audit marker and does not claw back XP/coins.
Completion events use stable project/stage keys and one-time completion guards;
project deletion preserves already-earned Game evidence. F2 progress events
now include the stable Game key and authoritative progress context. Completion
events include total symbols so their reward calculation does not depend on a
deleted Projects row.

Out-of-order processing is not allowed to depend on SQLite row order. The
explicit ordering above is used because lifecycle and reward markers are
ordered effects; idempotent deletion/status observations remain safe on retry.

## Time, streaks, quests and randomness

The legacy oracle continues to define effective writing-day semantics through
`engine.today_for_test()` and wall-clock session semantics through
`game.get_session_now()`. F3 does not introduce a second date boundary. Global
streak state is now in the Game aggregate; project/stage streak evidence is
keyed by stable Project/Stage IDs in the same aggregate, so the Projects
tables do not acquire a competing Game writer. Freeze state and daily/weekly
quest state are imported and round-tripped unchanged. No background reset
scheduler is added; existing lazy reset behavior remains.

Lottery/catalog definitions stay static in `game_data.py` for the current
compatibility façade. No new random event is introduced by F3, so no lottery
outcome semantics are changed; a future port must inject a deterministic RNG.

## Runtime and recovery boundary

`PickleRepository.read_gamer()` and `write_gamer()` route to SQLite after the
Game owner switch. `Gamer.save()` is guarded the same way and compatibility
service persistence is suppressed until the outer SQLite command commits.
Project reads used by the transitional Game service are reconstructed from
SQLite rows and Game-owned streak overlays. No normal Game operation writes
`gamer.pkl`; stale or inaccessible PKL cannot overwrite SQLite.

The present F2 desktop still has a Python sidecar for other transitional
features. Its Game HTTP façade uses the SQLite Game repository after cutover;
the Rust event processor is the trusted authoritative event boundary. Moving
all user-facing Game commands from the compatibility façade to direct typed
Tauri commands remains part of the Python-free runtime completion (F6), not a
new F4/F5 feature.

Backups continue to include `nfprogress.db` and retain legacy PKL snapshots
when present. After F3 the authoritative Game backup is SQLite; PKL is only a
recovery source. The long-term fallback remains:

```text
prepared SQLite → bridge-updated Python version → temporary migration helper
→ sandboxed Web Legacy Migration Service
```

The service must receive a canonical Game DTO/MigrationBundle, never mutate an
account database from a pickle decoder, and retain the F2 restrictions on
isolation, allowlists, limits, retention and credentials.

## Verification

`tests/test_f3_game_sqlite.py` covers failed-verifier ownership retention,
second-startup no-reimport, stale/inaccessible PKL, unknown fields, migration
readback, duplicate completion/progress effects, restart processing, retry and
poison events, and SQLite integrity checks. The Rust module has a matching
pure transition/idempotency test. Python legacy Game tests remain the
behavioral oracle; no pickle byte equality is used as a parity criterion.

## Production Bridge Release Strategy

Production Python releases continue to receive maintenance and bug fixes
during F3–F7. Additional monotonic bridge releases may normalize malformed
Game state, add stable IDs, materialize a SQLite mirror, or export a canonical
MigrationBundle. A bridge is not a hidden prerequisite: F7 must name the
minimum production version for seamless upgrade. A user below that version
uses the migration-only helper or the isolated Legacy Migration Service.

This distinguishes development readiness from production upgrade readiness:

```text
DEV Game SQLite cutover = implemented and tested
Production seamless upgrade = gated on the final importer/source matrix in F7
```
