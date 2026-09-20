# C3 — Email verification and account recovery

C3 adds cloud-only email verification and password recovery on PostgreSQL. It
does not add registration, account policy controls, frontend pages, Desktop
storage, or any zero-knowledge material.

## Tokens and verification

Verification links use `ev1.<UUID>.<secret>` and expire after 24 hours. Password
reset links use `pr1.<UUID>.<secret>` and expire after one hour. The random
secret has at least 256 bits of entropy. PostgreSQL stores only its SHA-256
verifier, never a raw token, secret, or full link. Both token types are
single-use and retain used/revoked history for audit semantics.

`POST /api/v1/account/email/verification/request` requires a normal C2 bearer
session. It returns an idempotent accepted result for already verified users.
`POST /api/v1/auth/email/verify` is intentionally unauthenticated, so a future
pending C4 registrant can verify before normal login. Verification requires the
current normalized user email to match the token email, and sets only
`email_verified`; **email verification is not account activation**.

New verification issuance revokes outstanding verification tokens for the same
user and email. New reset issuance revokes outstanding reset tokens for that
user. PostgreSQL row locking makes concurrent token consumption allow only one
success.

## Password recovery

`POST /api/v1/auth/password-reset/request` always returns the same 202 response.
Only `active` accounts receive a token; pending, blocked, rejected, unknown and
malformed email inputs stay externally indistinguishable. This prevents reset
from bypassing future verification/approval policy.

`POST /api/v1/auth/password-reset/confirm` accepts only token plus new password.
It reuses C2 `PasswordService` Argon2id and its 15–1024 Unicode character policy.
On success, one database transaction updates the hash, consumes the token,
revokes all other reset tokens, every auth session, and every active refresh
token. No session is issued: the user performs normal username/password login.
The successful reset schedules a separate password-changed notification.

The account password remains an authentication credential; it is **not an
encryption passphrase**, KEK, Account Master Key, or Recovery Key.

## Delivery and configuration

Business services depend on the `EmailSender` boundary. `SmtpEmailSender` uses
only standard-library `smtplib`, `EmailMessage`, and a default TLS context with
a 10 second timeout. Supported secure modes are `starttls` and `implicit_tls`;
plaintext SMTP is rejected. Tests use `RecordingEmailSender`.

Configuration is server-only:

- `NFPROGRESS_PUBLIC_WEB_URL` — trusted HTTPS base URL for links.
- `NFPROGRESS_SMTP_HOST`, `NFPROGRESS_SMTP_PORT`, `NFPROGRESS_SMTP_USERNAME`,
  `NFPROGRESS_SMTP_PASSWORD`, `NFPROGRESS_SMTP_FROM_EMAIL`,
  `NFPROGRESS_SMTP_FROM_NAME`, `NFPROGRESS_SMTP_SECURITY`.

Any enabled SMTP configuration must be complete and use HTTPS public URL plus a
secure TLS mode. Passwords are excluded from configuration repr and logs.
Links are built only from this configured base URL, never request host headers.

FastAPI `BackgroundTasks` run delivery only after the DB transaction commits;
they receive immutable email data, not request sessions or ORM objects. They are
not a durable queue: a durable outbox may be added later without storing raw
tokens in PostgreSQL. SMTP errors do not roll back a completed action. Logs do
not contain passwords, token material, full links, SMTP credentials, or full
email addresses.

## Abuse controls and C4 boundary

Token history supplies PostgreSQL-backed shared-worker throttling: at most one
issue per 60 seconds and five per hour per existing eligible account/purpose.
Public reset responses remain generic. Deployment should additionally apply
reverse-proxy IP limits; C3 deliberately adds no CAPTCHA or distributed queue.

C4 may call this verification service when it introduces registration controls.
It remains responsible for OPEN/APPROVAL/CLOSED policy and deciding activation;
C3 adds none of those controls.
