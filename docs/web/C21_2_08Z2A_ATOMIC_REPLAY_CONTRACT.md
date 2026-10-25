# C21.2.08Z2A — bounded atomic second-project replay contract

**Decision A — BOUNDED ATOMIC REPLAY FEASIBLE as an implementation contract; not implemented.**
Design-only review on clean `6.0` baseline
`964d3632c81ad5d28d2384ee010c4c166050d118`. MVP6.0.12 Cloud run
`40236767686` was independently checked: all six mandatory jobs succeeded.
The earlier Z2 implementation STOP remains historical and correct for the
current per-event APIs. This contract specifies the additional private owner
seam needed before Z2 can write project B.

## Exact supported cohort and starting state

- One already accepted project A with genuine Legacy3 F/H/O evidence and one
  **clean** imported project B. B has an active `import_remote` binding for the
  same account/device, with no `localProjects`, `localNotes`, Note history,
  Note intents or outbound Note records for B. A's F `source_after`/R0 remains
  authority for A alone. Third-project Note history, independent B edits,
  unresolved forks, self echoes and unsupported generations stop this slice.
- The existing authenticated receiver has retained a dense ciphertext inbox
  through the registry snapshot cursor. Receiving ciphertext before this
  operation is transport staging, not project initialization. The Z2A
  **prepare** itself performs only authenticated read-only HTTP from `since=0`
  and IndexedDB reads. It compares each returned original event, protocol,
  server sequence and encrypted object with the retained inbox row, regardless
  of that row's local proof state. A missing row/object, mismatch, gap, event
  beyond the fixed cursor, or changing registry snapshot stops before writes.
  A fresh profile may receive its encrypted inbox first through the existing
  transport; the B project remains absent until the atomic import commit.
- The existing Metadata, Stage and StageOrder owners must already have applied
  every structural dependency needed by B Notes, including B's coverless
  Metadata `create` genesis. Their original ciphertext, proofs and heads are
  reauthenticated in prepare, retained under the full inventory CAS, and not
  rewritten by this owner. Pending/unsupported structural dependencies stop
  before B writes. This is a deliberate eligibility limit that avoids building
  a second structural apply engine. Y's independent cross-project structural
  qualification is retained.
- The fresh active bootstrap descriptor must match B's project/bootstrap and
  origin device. Check its initial count/max against **actual** Legacy2 Note
  ciphertexts at or before that maximum: exactly the claimed number, each a
  unique origin-authored revision-1 create with null parent, and the last
  initial Note's server sequence equal to the claimed maximum. A zero count
  requires a zero maximum. No extra B Note in that interval is admitted.
  Authenticate Metadata genesis and sender through the existing Metadata owner
  and its original descriptor. Reject deletion, non-genesis, foreign bootstrap,
  foreign origin or unsupported cover/material. Track Note IDs across the
  complete account history and local inventory; one ID cannot belong to A and B.
- Construct the local **empty** B source at revision 1 from authenticated
  Metadata genesis: `id=project_id`, `name`, `goal`, `infinite`, `unit`,
  `status` from its supported fields, `created_at=updated_at` from its canonical
  genesis timestamp, and `payload={}`. No stage, document, cover, game or other
  absent local fields are inferred. Reject any event whose required local
  projection cannot be represented by this mapping. Later Metadata/Stage
  history remains under its separate structural owners; it does not silently
  mutate this Note source baseline.
- Replay initial and later eligible Legacy2/Content3 create, linear update and
  delete Notes in **global server order** through the same Note decoding,
  prerequisite, causal, candidate, proof and source-transition kernels used by
  the current inbound owners. Each accepted B Note transition raises the new
  device's project source revision by one. Tombstones remain authenticated
  members as required by `BrowserLocalAuthority`; source-device private
  revisions and unuploaded Notes are never claimed. Unsupported mixed history
  stops without a fallback.

## One private owner, two phases

Introduce a dormant `BrowserSecondProjectReplayOwner` with only these
owner-specific operations (names are the implementation contract, not an
existing API):

```text
prepareInitial(scope, projectB): Promise<VerifiedAtomicBReplay>
commitInitial(token): Promise<'applied'>
reconcileInitial(scope, projectB): Promise<'already_applied' | 'not_imported'>
prepareQ(scope, projectB, qRuntime): Promise<VerifiedResolutionPrefix>
```

`VerifiedAtomicBReplay` and the Q handoff are frozen, one-use objects whose
data live only in module-private `WeakMap`s. The owner binds them to its runtime,
the exact account/device, auth epoch, AMK lease, browser profile, immutable
bootstrap snapshot and complete ten-store inventory. No caller supplies an
authenticated fold, proof row, capability boolean or source revision. Tokens
are consumed on commit attempt, failure or revocation. A later attempt prepares
again from fresh evidence.

### PREPARE — no durable changes

1. Fetch and validate a fresh registry snapshot. Read complete encrypted
   account history from `since=0` through its fixed cursor using the existing
   authenticated pull parsers. Compare it to the complete local inbox and
   current cursor, then load the bounded ten-store inventory. Require exact
   account/device/key/profile currentness throughout. Recheck the registry
   descriptor and cursor before minting the token; a changed snapshot restarts
   preparation.
2. Reuse the Metadata/Stage/StageOrder owners to authenticate the already
   applied dependencies and B genesis. Open each B Note with the existing
   `openNoteTransport`/canonical readers. Verify bootstrap cohort, causal
   lineage, project membership, route, global Note identity and existing Note
   proof/history absence. Check the rest of the account stream through the
   cursor; an unrelated unsupported Note blocks Q at its earliest sequence.
3. Extract a **private pure planning kernel** from the existing
   `BrowserLegacyNoteApplyRuntime.prepareRoute()` and
   `BrowserLocalAuthorityRuntime.preparePeerSource()`. Their normal one-event
   paths must call the same kernel. The batch entry receives only an
   owner-created virtual empty B source and evolving owner-private inventory.
   It calls the existing Legacy2/Content3 prerequisite, Note causal, candidate,
   proof digest, local source validation and encryption helpers. After each
   eligible event it advances only that virtual state; no `initializeProject()`
   or per-event `commit()` occurs. Content3 uses its existing authenticated
   Metadata/Stage prerequisite over the pinned applied inventory. This seam is
   essential: copying a proof DTO or running a second causal algorithm would
   not meet the contract.
4. Produce exact future rows for B: one final encrypted `localProjects` row;
   one latest encrypted `localNotes` row per B Note, including tombstones; all
   genuine candidate/head records in `legacyNoteHistory`, with each event's
   encrypted projection/source revision; and the matching proven `inbox` rows.
   Keep each original `wire_item` unchanged. Compute the complete expected
   post-inventory and authenticate its internal history and membership before
   commit. Do not prepare conflicts or other unsupported outcomes as success.

Existing `prepareRoute()` currently reads a **durable** local source and its
`commit()` opens a separate transaction for one Note. It cannot be called in a
loop to satisfy this plan. The implementation must extract the shared private
planning kernel and add a batch-only synchronous write scheduler; the accepted
one-event behavior and proof formats stay unchanged. The current Metadata
private handoff explicitly rejects a no-head create, so B genesis is prepared
by the existing imported Metadata `create` owner before this operation and is
only reauthenticated here.

### COMMIT — one IndexedDB transaction

Immediately before opening the transaction, refetch and require the same
authenticated bootstrap descriptor and snapshot cursor; a mismatch discards
the one-use plan. Use one `BrowserSyncTransaction` `readwrite` call with
`resolutionInventoryStores`: `inbox`, `outbox`, `receipts`,
`projectBindings`, `ownerHeads`, `legacyNoteHistory`, `legacyNoteIntents`,
`localProjects`, `localNotes`, `cursors`. The persistence wrapper includes
`identities` and `accountBindings` in that **same physical DB10 transaction**
and checks account/device identity before scheduling. It requests strict
durability and resolves success only on transaction completion.

Within the transaction, synchronously load the complete account inventory
using `scheduleResolutionInventory`, then compare it by the existing exact
immutable-record equality (including each ciphertext and original wire string)
with the prepared expected-old inventory. Recheck lifecycle and the exact active B
binding, zero B local project/Notes/history/intents/outbox, original inbox rows,
owner heads, account cursor and cross-project Note-ID index. Any drift aborts.
Check expected writes against the precomputed post-inventory and existing
record validators; then schedule `add` for B project and new Note identities,
and the exact prepared history and inbox proof rows. All `add`/`put` requests
and their success callbacks check lifecycle and abort on failure. No HTTP,
decryption, hashing, key use or other `await` occurs inside the transaction.
The only writable stores are `localProjects`, `localNotes`,
`legacyNoteHistory`, and `inbox`. `ownerHeads`, binding, cursors, outbox,
receipts and intents are CAS/read-only. In particular, neither `pull_cursor`
nor `proven_prefix` is advanced by this import. The existing Content3 transport
candidate is written as its original owner-produced history row, with the
same pinned owner-head/binding checks its single-event hook requires.

The owner subscribes to auth/key invalidation and holds the verified device and
profile predicate until completion. Any request failure, tab closure,
key/auth/device/profile invalidation, concurrent writer change or quota error
aborts the **entire** transaction.
`runBrowserTransaction()` reports success after `oncomplete`, so no local
project or Note is reported saved early. The existing browser Web Lock excludes
a second writer to the same profile; the full CAS still checks for stale data.
Only the prepared ciphertext and proof rows are persisted; decrypted Notes,
passwords and AMK material remain out of IndexedDB and localStorage.
No partial B source is observable: before commit B has no local project; after
commit it has the complete authenticated fold and proofs in one DB10 state.

If the transaction may have completed but its response was lost, do not retry
its writes or compare new random-nonce ciphertext byte-for-byte. Fetch a fresh
registry/full history, reopen the exact durable rows through the existing
crypto and Note history owners, verify every B event/projection/source revision
and the final membership, and return `already_applied` only for the **complete**
authenticated result with no extra local edit. Otherwise return a blocker;
never overwrite. A browser restart follows this same reconciliation path.

## Capacity and unsupported history

For the first implementation, admit at most **256 B Note events**, at most
**256 distinct B Note identities**, and at most **8 MiB of prepared B write
rows**. Also enforce the existing `MAX_LOCAL_NOTES=4000`, local source
8 MiB limit, and the complete expected-old **and** expected-new inventory
limits of `MAX_PLANNER_ROWS=16384` per store and
`MAX_PLANNER_INVENTORY_BYTES=32 MiB` in aggregate. Budget during network
paging and planning, before retaining unbounded data. Clear temporary
plaintext and key-derived buffers promptly. A limit or unsupported family
returns `resource_limit`/a specific blocker **before B writes**; it does not
split the import into several transactions or silently truncate history.
These are deliberately conservative initial limits, not a claimed global
maximum for WORTA. Expanding them requires separate capacity evidence.

## Independent B source in dormant Q

After a successful commit or full lost-response reconciliation,
`prepareQ()` fetches a **new** registry snapshot, rechecks complete `since=0`
history and reopens the durable B project, Note rows and candidate/proof chain.
It produces a one-use, owner-bound B history capability in a private `WeakMap`.
The Q runtime consumes that capability only in its existing explicitly dormant
`bindMixedSources()` path. Q independently reauthenticates A's F/H/O source and
B's Metadata genesis, initial cohort, every B ordinary Note transition,
source revision 1→N, membership, account-wide Note-ID ownership and the exact
dense account sequence. The capability carries no public authorization flag
and cannot substitute B's current projection for history. A missing/unproven
row blocks at the earliest sequence. A's F/R0 is never applied to B.

Q binds its certificate to the same ten-store inventory and current auth/key/
device/profile and fresh registry snapshot; its unchanged CAS commit can write
only `cursors.proven_prefix`. A partial, stale or unrecognized B import cannot
mint a capability. After restart or inventory change, prepare a new one. The
existing Y Q may still qualify B Metadata/Stage/StageOrder through their own
owners, but it must continue to block B Note sequences until this independent
B proof is present. ACK, Note writer, reader declarations and production
routing remain unavailable.

## Required implementation acceptance

| Evidence | Required result |
| --- | --- |
| Actual A Legacy3 F/H/O producer and B bootstrap/Metadata/Legacy2/Content3 create-update-delete producers, interleaved structural events | B import has the exact derived source/membership; Q qualifies only the complete independently verified dense prefix. |
| Pre-transaction interruption; wrong/missing registry, sequence, event, Metadata, cohort count/max, origin/project, corrupt ciphertext or over-budget history | Zero B source/history/proof writes; ciphertext and previous A evidence preserved. |
| Forced abort while scheduling each writable store group; key/logout/device change and second-tab writer conflict | Whole B transaction rolls back; Q gets no B capability. |
| Commit completed but reply lost; browser process restart; repeat full replay | Fresh registry/crypto reconciliation returns `already_applied` with zero duplicate or overwritten records. |
| Existing B project/Note/edit or same Note ID in another project | Reject before writes; no merge or fallback. |
| Pinned Y old client on a closed copy, then new client on that copy | Old Q cannot qualify B Notes and makes no destructive write; new owner can reauthenticate the preserved data. Never run both builds concurrently. |
| Q commit abort or stale complete inventory | Cursor unchanged; full B/A data unchanged. Success changes only `proven_prefix`; ACK/declaration/writer stay disabled. |

Positive acceptance must run genuine producers and persistent-profile Chromium,
plus focused Vitest, typecheck and production build. Place new tests after
checking the six Cloud job budgets; retain all mandatory jobs and their
40-minute limits. This document is a design decision and makes **no claim**
that those tests or Z2 implementation have passed.

## Next implementation boundary

The smallest next stage is **C21.2.08Z2B — dormant bounded atomic B replay and
private Q source composition**, GPT-6 Luna / High for a scoped multi-owner
implementation. Escalate to Sol / Medium if extraction of the shared Note
planning kernel exposes a new architecture conflict. Preserve Z/Z1 findings,
the Z2 STOP, Y's accepted behavior, and all C21/C22/C23/PF6.0/RC gates.
Official Web progress stays **89.36%**; `ready=false`,
`declarationAllowed=false`, `writerAuthorized=false`, registration CLOSED,
PUBLIC RELEASE BLOCKED.
