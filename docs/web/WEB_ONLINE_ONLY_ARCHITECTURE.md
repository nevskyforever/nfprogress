# WORTA Web Online-Only Architecture

**Approved by the project owner: 2026-10-27.** This document supersedes earlier
product requirements for full offline Web parity. It does not supersede the
LOCAL-FIRST development/testing policy in `AGENTS.md`.

## Runtime ownership

- **Desktop:** offline-first, SQLite is the local source of truth, cloud sync is
  optional.
- **Web:** online-only; the server is authoritative for persistent user data.
  Browser E2EE encrypts/decrypts content. The server stores opaque ciphertext and
  only the minimal metadata required by the established protocol.
- **Compatibility:** Desktop and Web use the same accepted cloud formats and
  protocol. Do not create a second Web sync engine or send plaintext/AMK.

Web does not require a persistent IndexedDB copy of user content, offline queue,
background sync, or restart recovery from the browser. Existing `worta-web` v12
and its local developer-only workspace remain intact for legacy tests and any
existing local data. They are not the target online flow. Never auto-import,
merge, delete or promote those records without a separately approved migration.

## Save and connectivity semantics

A local in-memory edit, encryption operation, IndexedDB write or queued event is
not a server save. The UI reports **Saved** only after the authoritative server
has acknowledged the accepted protocol operation and required revision/security
checks have passed. With no connection, report the failure and retain the
current unsaved input in memory when possible. Do not promise recovery after
refresh or browser restart. Never fall back to legacy plaintext `/api` for E2EE
entities.

## Online-only milestones

1. **WEB.ONLINE.01:** authenticated server cloud-project catalog. The current
   endpoint returns project IDs/count/limit only; an ID is not a decrypted name
   or evidence that content is synchronized.
2. **WEB.ONLINE.02:** E2EE server read and in-memory restoration after C21
   reader/security/recovery gates.
3. **WEB.ONLINE.03:** existing Tiptap document editing through accepted
   ciphertext writer protocol and verified server confirmation.
4. **WEB.ONLINE.04:** Notes, Maps and Stages through accepted compatible owners.
5. **WEB.ONLINE.05:** Progress, Game Mode and Settings.
6. **WEB.ONLINE.06:** Desktop ↔ Web compatibility, conflict and recovery
   acceptance.

The exact sequence may be refined based on frozen C21/C22/C23 contracts. No
milestone may bypass reader declaration, writer authorization, ACK, recovery,
PF6.0 or release gates.

## WEB.ONLINE.01 catalog contract

Use the ordinary authenticated account session and legal acceptance gate, then
call existing `GET /api/v1/cloud/projects`. The result is shown in memory in a
separate **Cloud projects** section. It is not persisted in IndexedDB and is
never populated from `localProjects` or another browser store. Show server
count/limit, a truthful empty state, manual refresh, and connection errors.
Discard visible catalog state on logout or auth-context change. Do not expose a
raw access token to Vue components. The endpoint is metadata-only and does not
authorize content reads, writes, bootstrap, ACK, or synchronization.

The existing developer-only encrypted local workspace remains explicitly
labeled as local, unsynchronized test data and is not merged with the server
catalog. Public registration remains closed.

## Release invariants

Official Web progress stays **89.36%** until formally recalculated.
`ready=false`, `declarationAllowed=false`, `writerAuthorized=false`,
Registration CLOSED, PUBLIC RELEASE BLOCKED. C21/C22/C23/PF6.0/RC remain
mandatory. LEGAL.ACCEPTANCE.02 remains required, and final legal-text approval
is a separate owner decision.
