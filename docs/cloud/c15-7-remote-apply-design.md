# C15.7 remote Note apply design gate

## C15.7A boundary

The durable inbox remains the only pending-remote-event source.  C15.7A reads
only `state='received'`, `entity_type='note'` rows for a binding-validated
local account and its registered pulling device, ordered by `server_sequence`.
It has no SQL that writes `notes`, `cloud_sync_entities`, inbox state, cursors,
outbox, or receipts.  Decryption uses the existing C11/C15.3
`openNoteSyncEvent()` inside `AuthoritativeKeyContextLease.use()`; plaintext is
passed only to an internal callback and the public pass result is metadata.

## Why migration 010 cannot be bypassed

The three `notes_require_sync_intent_*` triggers correctly require a matching
unsealed local outbox intent for every mutation in a cloud-bound project.
Remote apply has no such local intent by design: manufacturing one would echo a
received event back to the server.  Disabling triggers, toggling a connection
pragma, or modifying migration 010 would remove the protection for ordinary
local mutations and is not acceptable.

## Exact C15.7B migration 015 scope

Migration 015 must be forward-only and limited to remote-apply authorization:

1. Add `cloud_sync_remote_apply_authorizations`, keyed by `event_id`, with
   `account_id`, `project_id`, `entity_id`, `entity_type`, `operation`,
   `revision`, `parent_event_id`, `payload_json`, and a per-transaction random
   capability.  Add checks for canonical IDs, supported Note operations, and
   exact account/project/entity identity.  The row is ephemeral: it is created
   and consumed in the same transaction and must never survive commit.
2. Replace only the three migration-010 Notes triggers with semantically
   identical local-intent branches plus an explicit remote branch.  The remote
   branch requires one authorization row whose account is the project binding,
   whose entity/operation/payload exactly match the pending Notes mutation, and
   whose capability is supplied only by the C15.7B Rust command.  An `AFTER`
   trigger consumes it; the command asserts exactly one authorization row was
   consumed before commit.
3. Do not change legacy/local intent semantics, inbox states, cursors, or the
   C11/C15.3 cryptographic schema.

## C15.7B apply transaction

After the protected decrypt callback validates the plaintext/header binding,
C15.7B will pass the typed payload directly to one private Rust apply command.
That command starts `BEGIN IMMEDIATE`, rechecks account binding, project and
entity scope, rereads the received inbox row/object identity, and validates the
following before creating its one-use authorization:

* the inbox event is still received and exact metadata matches;
* project exists and is bound to the same account; absence is a retained
  dependency/orphan classification, not corrupt ciphertext;
* no unsealed local Note intent exists for the entity; this is retained as a
  conflict, never last-write-wins;
* revision one has no parent; later revisions name the expected durable head;
* any already-applied identical head is a self-echo/idempotent result; a
  different head, missing parent, or locally dirty head is retained for
  dependency/conflict handling.

The command then installs the authorization, changes `notes`, advances the
entity head and inbox state together, consumes the authorization, and commits.
It does not create an outbox event or modify acknowledgement cursors.  A
rollback leaves all evidence intact.

## Tombstones and conflicts

Delete applies a tombstone head before deleting the local note.  Later upserts
must name that delete event as their parent; an older or unrelated upsert cannot
resurrect it.  A missing project, unsupported route/content format, missing
revision parent, local unsealed change, malformed ciphertext/payload, and true
head conflict have separate durable classifications in C15.7B.  Corrupt data
is retained for inspection; it is never silently deleted.  Full conflict
resolution remains C17.

## Race boundary

`BEGIN IMMEDIATE` serializes the remote decision with local Notes writes.
Local writers continue to prepare their intent before changing Notes.  If a
local unsealed intent wins first, remote apply records/retains conflict; if the
remote transaction wins, a subsequent local writer observes the new head and
creates its normal local successor.  Key/logout races are handled outside SQL:
no decrypt starts without a current lease, while an already-started lease drains
before lock/logout completes.
