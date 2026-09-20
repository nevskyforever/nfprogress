# C4 — Registration Controls

C4 adds a cloud-backend-only public registration foundation on PostgreSQL. It does not add a registration or verification frontend, Desktop/Tauri behavior, an Admin Panel, approval endpoints, general C5 quotas, projects, or any zero-knowledge cryptography.

## Policy and schema

`registration_settings` is a PostgreSQL singleton (`id = 1`) and is the authoritative registration policy. Its validated modes are `open`, `approval`, and `closed`; `max_users` is either `NULL` (unlimited) or a non-negative integer. C4 migration `c4_registration_controls` seeds it as **`closed` with `max_users = NULL`**. A deployment therefore never opens public registration merely by applying the migration.

`GET /api/v1/auth/registration` is intentionally public and returns only the mode plus `registration_enabled` and `requires_approval`. It never exposes capacity, user counts, or remaining slots.

`POST /api/v1/auth/register` accepts only username, email, and password. Its strict schema rejects role, status, verification, and policy marker fields. New public accounts are always `user` / `pending` / unverified, use C2's Argon2id 15–1024 Unicode-character password policy, and save the C2 normalized username/email forms. Email syntax uses the maintained `email-validator` library; identity comparison remains the existing `strip().casefold()` policy, without provider-specific Gmail transformations.

For syntactically valid accepted or duplicate requests the response is the same: `202 {"code":"registration_request_accepted"}`. Duplicates create neither a second user nor another initial email. `closed` returns the public policy response `403 registration_closed` and creates no user.

## Signup snapshot, verification, and activation

Each public signup receives server-owned `registration_mode_at_signup` of `open` or `approval`. `NULL` remains the meaning for old/internal accounts. This snapshot controls the completed registration flow even if the global policy changes before verification: OPEN signups remain OPEN after a later CLOSED/APPROVAL change; APPROVAL signups remain pending after a later OPEN/CLOSED change. Existing/internal pending accounts retain C3 verification semantics.

C3's `ev1` token format, SHA-256-only PostgreSQL verifier, expiry, rotation, single-use behavior, trusted public URL construction, and PostgreSQL row locks are reused. Verification and the C4 activation decision occur in one database transaction, so a consumed token cannot leave a public OPEN signup in a partially decided state.

`POST /api/v1/auth/email/verify` returns `email_verified` with typed `account_status` and `activation`:

- OPEN becomes active when capacity permits (`active` / `active`).
- APPROVAL remains pending (`pending` / `approval_required`).
- An OPEN signup at capacity remains pending but verified (`pending` / `capacity_reached`).
- Non-C4 accounts retain their current status (`unchanged`).

Thus **`email_verified = true` does not necessarily mean `status = active`**. Verification never issues a session; an active user later performs normal C2 username/password login.

`max_users` counts only `active` users. Pending, rejected, and blocked users do not count. Lowering it below current active use leaves existing active users unchanged, while blocking later activation transitions. OPEN activation locks the singleton policy row (`SELECT ... FOR UPDATE`), counts active users, and changes the user status in the same transaction. This is the shared-worker, PostgreSQL concurrency boundary that prevents two last-slot verifications from exceeding capacity.

## Delivery and public resend

Production OPEN/APPROVAL registration fails closed with `503 registration_unavailable` if SMTP delivery configuration is absent. No account or token is created in that case. Normal post-commit SMTP failure still does not roll back an already correct account/token transaction, preserving C3's delivery boundary. SMTP credentials and token material are not logged.

`POST /api/v1/auth/email/verification/request` accepts an email without authentication and always returns `202 {"code":"verification_request_accepted"}`. It sends only to a C4 public, pending, unverified registrant. Unknown, verified, active, blocked, rejected, internal, and throttled accounts all receive the same public response and no inappropriate mail. It reuses C3's PostgreSQL per-account 60-second / five-per-hour throttle and row-lock serialization.

Public deployments still need reverse-proxy/WAF signup velocity limits, especially per-IP. C4 intentionally adds no CAPTCHA, phone verification, client-IP storage, Redis, or third-party anti-bot product.

## Deferred boundaries

C7 will add administrative policy changes and approval/rejection actions; C4 adds neither API nor UI for them. C5 will provide broader project, storage, device, and per-user quota frameworks; C4 supplies only `max_users` because it is directly part of activation policy. The account password remains only an authentication credential, never an encryption passphrase, KEK, Account Master Key, or Recovery Key.
