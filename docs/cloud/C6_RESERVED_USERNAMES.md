# C6 — Reserved Usernames

C6 adds a PostgreSQL-backed public-registration policy namespace. A reservation is metadata, not a `User`: `reserved_usernames` stores only the canonical `username_normalized` primary key and `created_at`. It has no user ID, role, password, email, or account state, so reservations do not affect user counts, C4 `max_users`, account lists, authentication, or C5 cloud-resource limits.

Migration `c6_reserved_usernames` seeds exactly these normalized names: `admin`, `administrator`, `root`, `system`, `support`, `security`, `staff`, `moderator`, `official`, `api`, `www`, `nfprogress`, `wow`, and `worta`. `worta` is the current product/domain name; `wow` and `nfprogress` remain reserved historic or technical names.

The only normalization contract is the existing cloud repository contract: `value.strip().casefold()`. Matching is exact: `Admin` and ` admin ` match `admin`, while `admin2`, `myadmin`, `administrator2`, `worta-user`, and `wowwriter` do not. C6 intentionally adds no NFKC/NFC normalization, transliteration, confusable or homoglyph detection, fuzzy matching, substring blacklist, or regex blacklist.

For public `POST /api/v1/auth/register`, after C4's CLOSED and production-email-availability policy checks and C2's cheap password validation, a reserved username returns `409 {"detail":{"code":"username_reserved","message":"This username is reserved."}}`. The service checks again inside its creation transaction before it creates a user or verification token. Consequently, a rejected reservation creates no User, email-verification token, auth session, refresh token, or registration email. C4 duplicate ordinary-account behavior remains the generic `202 registration_request_accepted`; a reserved name may be disclosed as policy even when a legacy/internal User already owns it.

Reservations are not retroactive. An existing `Admin` account remains unchanged and can continue to log in; the reservation only prevents a new public registration. Trusted/internal account creation remains unchanged: C6 has no cross-table check, foreign key, or trigger on `users`.

There is no public availability or reservation-list endpoint, and C6 adds no admin API/UI. C7 may add list/add/remove management. At that time it must coordinate public registration and an administrator reserving the same normalized name in a race-safe PostgreSQL transaction; C6 does not add that future mutation coordination early.
