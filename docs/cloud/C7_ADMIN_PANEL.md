# C7 — Admin Panel

C7 adds a server-side administrative surface under `/api/v1/admin`. Administrators use the normal C2 username/password login and normal JWT/rotating-refresh authentication; authority is only an active `users.role == "admin"` account. Every endpoint independently applies the backend dependency, returning `401 invalid_token` for invalid authentication and `403 admin_required` for a non-admin. The Vue guard is UX only.

The user list exposes account metadata only (never hashes, tokens, sessions, or project content), with stable `created_at, id` ordering, pagination, filters and exact normalized username/email substring search. Web lifecycle actions are explicit: approve activates verified pending/rejected users only when C4 active-only capacity permits it; reject only changes pending users; block revokes all sessions and refresh tokens; unblock requires verified email and capacity and never restores revoked credentials. Admin accounts are protected from all Web lifecycle changes. Session revocation alone leaves an active account able to log in again.

Registration policy (`open`, `approval`, `closed`, nullable `max_users`) and the C5 global project limit are persisted authorities. Zero is a real limit and `null` means unlimited only for `max_users`. Lowering a registration cap does not disable existing active accounts; it blocks later activation until capacity exists. Per-user cloud-project overrides use `override ?? global`: `0` is an override and `null` deletes the sparse row to inherit. C8 project state/enforcement is not implemented; future lowering must block only new cloud-enable operations, never delete or archive existing projects.

Reserved usernames are listed, added and removed for administrators only. Canonicalization remains exactly `strip().casefold()`. Adding a new reservation for an existing user returns `username_in_use`, while legacy user/reservation collisions remain non-retroactive. Public registration and add/remove reservation take the same PostgreSQL transaction-scoped advisory lock, keyed by normalized username, after Argon2 for registration. Thus a concurrent new registration/reservation serializes to exactly one namespace claim.

Bootstrap is server-side only:

```text
python -m backend.app.admin_cli create
python -m backend.app.admin_cli promote USERNAME
python -m backend.app.admin_cli restore USERNAME
```

`create` interactively reads password and confirmation with `getpass`; no password command-line argument exists. It creates an active, email-verified admin and may use a reserved name. `promote` is idempotent and changes only role. `restore` activates only an existing admin. There is no Web role elevation, admin-specific password, admin table, admin token, secret URL, or project-content/crypto bypass.

The Web panel is directly reachable at `/admin/login` and `/admin`, outside ordinary AppShell/workspace bootstrap and absent from desktop/mobile navigation. It retains access and refresh tokens only in runtime memory; reload requires login. Refresh replaces both in-memory token values, logout clears them, and a failed refresh returns to login. Tokens are never written to browser storage, cookies, or URLs.
