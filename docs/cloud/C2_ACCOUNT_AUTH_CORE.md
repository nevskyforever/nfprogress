# C2 — Account & Authentication Core

C2 adds the first account-owned PostgreSQL boundary. It is server-only and
separate from legacy `/api` compatibility routes and Desktop local SQLite.

## Schema and ownership

Migration `c2_account_auth_core` follows `c1_postgresql_foundation` and creates
only `users`, `auth_sessions`, and `auth_refresh_tokens`.

`users` uses UUID primary keys, preserved display names plus canonical
`username_normalized` and `email_normalized`, Argon2id hashes, account role and
status, and UTC-aware timestamps. Both normalized columns are unique. Username
normalization is exactly `strip().casefold()` and login accepts username only;
email is not a login identifier.

Cloud repositories must derive ownership from the validated access token's
`current_user.id`. They must never accept a client-provided `user_id` as an
authorization source. C2's `/api/v1/account/me` demonstrates that invariant.

## Passwords and accounts

`pwdlib[argon2]` supplies its recommended Argon2id PHC implementation. New
account passwords require 15–1024 Unicode characters; spaces and Unicode are
allowed, no composition rules apply, and passwords are never silently
truncated. `PasswordService` supports verify-and-update for future parameter
rehashing. Passwords, hashes, and authentication secrets are never returned by
API DTOs or logged.

C2 intentionally exposes no registration route. `AccountService.create_user`
is a repository/service primitive for tests and later C3 verification-led
registration. Only `active` users may obtain or use sessions.

## Tokens and sessions

`NFPROGRESS_AUTH_SECRET` is a server-only secret, hidden from `RuntimeConfig`
repr and required in production along with PostgreSQL. Generate it from at
least 256 cryptographically random bits, for example:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

Access tokens are HS256 JWTs with a 15-minute lifetime. Decode requires the
fixed `nfprogress-cloud` issuer, `nfprogress-api` audience and HS256 algorithm;
the required claims are `sub`, `sid`, `iss`, `aud`, `iat`, `nbf`, `exp`, and
`jti`. They contain no profile, password, encryption, or project data. Each
request additionally loads the user and auth session from PostgreSQL and checks
active status, session ownership, expiry, and revocation.

An auth session has an absolute 30-day lifetime from login. Refresh tokens are
opaque `rt1.<token-id>.<random-secret>` values. The secret has 256 bits of
entropy and only its SHA-256 verifier is stored; token comparison is
constant-time. A refresh rotates atomically under PostgreSQL row locks: the old
token becomes used/revoked, points to its replacement, and the replacement
retains the original session expiry. Reuse of an already rotated token revokes
the entire session and all active refresh tokens; no replacement is issued.
Logout likewise revokes the current session and its refresh tokens.

## API

- `POST /api/v1/auth/login` — username/password; returns bearer access and
  refresh tokens.
- `POST /api/v1/auth/refresh` — rotates an opaque refresh token.
- `POST /api/v1/auth/logout` — Bearer-authenticated; revokes the current
  server-side session.
- `GET /api/v1/account/me` — Bearer-authenticated safe account DTO.

Invalid credentials use one public `invalid_credentials` contract for unknown
usernames and bad passwords; an unknown username performs dummy Argon2
verification. Standard `Authorization` is enabled for `/api/v1`; legacy
`X-NFProgress-Token` remains separate and unchanged for `/api`.

## Deliberately deferred

C2 contains no public registration, email/SMPP/reset flow, registration policy,
reserved names, quotas/admin/project/sync/device/object-storage work, frontend
or desktop token storage, or encryption material. The account password is only
an authentication password: it is not an encryption passphrase, KEK, master
key, recovery key, or part of the future zero-knowledge architecture.
