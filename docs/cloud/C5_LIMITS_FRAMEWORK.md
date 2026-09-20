# C5 — Limits Framework

C5 adds the PostgreSQL-backed policy foundation for future per-user cloud-resource limits. It stores no project usage and does not create cloud projects, sync, a cloud toggle, Admin API/UI, Desktop/Tauri behavior, local SQLite state, or cryptography.

## Current limit and authority

`global_limits` is a singleton (`id = 1`) with typed PostgreSQL columns. C5 seeds `max_cloud_projects = 20`; it is non-null and constrained to zero or greater. `user_limit_overrides` is an optional one-to-one row keyed by `user_id`, with a cascading foreign key to `users`. Its nullable `max_cloud_projects_override` is also constrained to zero or greater when present.

The effective value is:

`effective_limit = user_override ?? global_default`

Thus both a missing override row and `NULL` override inherit the current global value. `0` is a real zero-project limit, not inheritance; there are no negative or “unlimited” sentinels. New users do not receive an override row, so later global changes affect them immediately. An override affects only that user, and clearing it to `NULL` returns to inheritance.

PostgreSQL is the sole authority. There is no environment setting, frontend authority, or local fallback. A missing `global_limits` singleton is a misconfigured/corrupt server state: `LimitsService` raises `LimitsUnavailableError`, and the authenticated API returns sanitized `503 limits_unavailable` without database details.

## Current API

Authenticated active users can read only their own effective value through `GET /api/v1/account/limits`:

```json
{"max_cloud_projects": 20}
```

The route derives the user exclusively from the C2 authentication context. It neither accepts a client user ID nor exposes the global value, override state/value, another user’s limits, or C4 `max_users`.

`registration_settings.max_users` remains C4’s separate system-wide registration/activation capacity policy. It is not a cloud-resource limit and is not copied into C5.

## Future project contract

Local Desktop/Android projects remain unlimited and never depend on this quota. In C8, only projects explicitly enabled as “На всех устройствах” will count. The server will atomically allow enablement only when `cloud_project_count < effective max_cloud_projects`; a rejected extra enablement will use the stable lowercase API code `cloud_project_limit_reached`. No fake counter or enforcement exists in C5.

If a limit is lowered below existing cloud-enabled use, future behavior preserves all existing projects and sync data: nothing is deleted, archived, or converted to local-only. The user simply cannot enable additional cloud projects until usage falls below the effective limit.

Later migrations may add typed global and override columns for storage or devices. C7 will add administrative mutation endpoints; C5 intentionally provides none.
