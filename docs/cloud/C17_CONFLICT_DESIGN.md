# C17 conflict design freeze

## Pass 1 boundary

C17 Pass 1 implements only durable Note conflict preservation and ACK fairness.
It does not add resolution events, protocol v2, conflict UI, or HTML merge.
User-selected resolution, including manual composition, belongs to later C17
passes. Automatic HTML merge is excluded.

The existing E2EE design, AMK handling, `crypto_version=1`, and `aad_version=1`
remain unchanged. A future resolution-event design reserves Note plaintext v2
and encrypted sync protocol v2. Before the first public release, client and
server may make one coordinated hard cutover, but a v1 client must reject an
incompatible protocol fail-closed. The server never reads plaintext and never
chooses a winning Note version.

## Preservation and causality

Every causally proven competing Note tip is retained in the local encrypted
client database as an immutable full snapshot or tombstone. A conflict group
records account/project/entity scope, a proven common parent, tip revision,
known tips, generation, and lifecycle. Server sequence and receipt time are
transport facts only; neither is causal evidence.

The first implemented proof is a remote tip and a local unsealed outbox tip
with the same non-null parent and revision. The transaction copies the local
outbox identity, intent snapshot/tombstone, and mutation generation before it
marks the inbox event preserved. This protects that exact local branch from
later intent coalescing. Further remote tips may extend the same open group only
when they prove the same common parent and revision.

Every remote Note successfully applied under schema 17 also records immutable
causal history (parent, revision, operation, sequence, and full snapshot or
tombstone) in its apply transaction. A later remote sibling can therefore
preserve the already displayed remote tip without guessing its ancestry.
Pre-17 applied events without that proof remain fail-closed.

A revision-1 Note-ID collision, an unbound project, or any event without proven
shared history is not promoted to a resolvable conflict. Unknown parents,
orphans, rejected payloads, and incomplete preservation remain unacknowledgeable.

## Atomicity and ACK meaning

The native apply boundary rechecks account/device/project binding, inbox and
encrypted-object identity, plaintext metadata, current Note state, causal
parent, and durable local intent inside one `BEGIN IMMEDIATE`. It then inserts
the remote version, snapshots the local unsealed version when opening a group,
updates tips/generation, and transitions the inbox row to
`conflict_preserved`. Any failure rolls back all of those writes and never
changes the displayed Note.

An exact event replay is idempotent. Reuse of an event ID with different
metadata, envelope, plaintext snapshot, or tombstone is rejected. ACK means
durable receipt, not user resolution: `applied` and transactionally proven
`conflict_preserved` rows may advance the contiguous prefix. `received`,
`conflict`, `orphan`, `rejected`, and unknown entities may not. One unresolved
sequence blocks every later event, while an independently applied Note may
continue after a correctly preserved conflict.

No server-side pruning may rely only on ACK until a separate future contract
defines retention of all conflicting encrypted versions. Project-name and
project-metadata conflicts remain C18 scope.

## IPC contract and deferred boundaries

The protected Rust apply command continues to return `conflict` after a
successful atomic preservation. That value describes an unresolved
user-visible conflict, not an apply error and not a claim that the conflict has
been resolved. TypeScript must still invoke native ACK. Only the native ACK
transaction distinguishes a proven `conflict_preserved` inbox row from an
ordinary `conflict` and may advance the contiguous prefix.

Pass 1 intentionally remains fail-closed for pre-017 applied histories that do
not contain the required causal snapshot. It also does not claim complete
preservation for a sealed local delete branch when no plaintext tombstone was
durably retained, or automatically capture a newer coalesced local generation
created after the conflict's initial preservation. Those cases require an
explicit follow-up contract before ACK eligibility can be broadened.

Resolution events remain future C17 work and require Note plaintext v2 plus
encrypted sync protocol v2. Any pre-release hard cutover must be coordinated
between client and server, with incompatible older clients failing closed.

## Pass 2A freeze: Note plaintext v2 resolution event

This section freezes the payload for a future implementation; it does not add
a parser, an IPC command, a schema migration, or a protocol cutover.  V1
payloads and their codec stay byte-for-byte and semantically unchanged.

### Root and header

A v2 resolution payload has exactly these root keys:
`version`, `header`, `mutation`, `resolution`, and `result`.  `version` is the
number `2` and `mutation` is the string `resolution`.  No unknown root or
nested keys are permitted.

`header` has exactly these keys:
`event_id`, `parent_event_id`, `additional_parent_event_ids`, `project_id`,
`entity_id`, `entity_type`, `operation`, `revision`, and `updated_at`.

* `event_id`, `parent_event_id`, every additional parent, every resolved event,
  and `conflict_group_id` are lowercase canonical UUIDs.  `event_id` must not
  occur in any parent or resolved-event list.
* `parent_event_id` is the primary parent.  It is the lexicographically smallest
  UUID in `resolved_event_ids`; it is not a user-selected winner.
  `additional_parent_event_ids` is the remaining parent UUIDs in strictly
  ascending byte/ASCII lexical order.
* `project_id` and `entity_id` are non-empty strings, `entity_type` is `note`,
  `operation` is `resolution`, `revision` is a safe integer at least `2`, and
  `updated_at` is the existing canonical six-fractional-digit UTC timestamp.

`resolved_event_ids` is the complete conflict-tip set the user saw: from two
to 64 distinct canonical UUIDs, in strictly ascending byte/ASCII lexical
order.  It must equal `[parent_event_id, ...additional_parent_event_ids]`
exactly.  This canonical parent ordering makes independently encoded
resolutions deterministic even when their chosen version differs.

### Resolution and result variants

`resolution` always has `conflict_group_id`, `conflict_generation`,
`resolved_event_ids`, and `strategy`.  `conflict_generation` is a safe integer
at least `1`.  Variant keys are exact:

| `strategy` | Additional `resolution` keys | `result` |
| --- | --- | --- |
| `choose_version` | `selected_event_id` | `{ operation: "upsert"|"delete", note: NoteSyncRecord|NoteSyncTombstone }` |
| `manual_merge` | none | `{ operation: "upsert", note: NoteSyncRecord }` |
| `keep_both` | `selected_event_id`, `retained_event_id`, `retained_note` | `{ operation: "upsert", note: NoteSyncRecord }` |
| `delete` | none | `{ operation: "delete", note: NoteSyncTombstone }` |

`result` has exactly `operation` and `note`.  Its `note` uses the existing v1
record or tombstone shape, except that its timestamps describe the resulting
snapshot rather than the resolution event's `updated_at`.  Its route must have
the header's project/entity identity; a tombstone is required only for
`operation: delete`.  Thus choosing a version can carry its immutable historical
snapshot without forging a new timestamp.

For `choose_version`, `selected_event_id` is one member of
`resolved_event_ids`, and native history must prove that `result.note` is its
exact immutable snapshot and that `result.operation` is its operation.  For
`manual_merge`, the user supplies a complete upsert record; automatic HTML
merge remains forbidden.  For `delete`, no version is selected: the complete
observed tip set is deliberately replaced by the supplied tombstone.

`keep_both` is deliberately limited to exactly two upsert tips.  The selected
tip remains the original Note through `result`; `retained_event_id` is the
other member of `resolved_event_ids`; and `retained_note` is a complete new
`NoteSyncRecord` in the same project with an `id` distinct from the original
`entity_id`.  Native history must prove it is a clone of `retained_event_id`'s
record with only the route `id` and creation/update timestamps changed to form
the new Note.  A delete/edit group cannot use `keep_both`; it must use
`choose_version`, `manual_merge`, or `delete`.

### Causal and freshness rules

The codec performs only local structural checks: exact keys; canonical UUID,
timestamp, safe-integer, list length/order/uniqueness, variant shape, root and
route identity, and obvious self-reference.  It cannot establish causal truth.

Inside one future native SQLite transaction, local causal history must prove
that the group is open, account/project/entity-scoped, and that its current
generation exactly equals `conflict_generation`.  It must prove that the
sorted current tip event IDs exactly equal `resolved_event_ids`, that every
parent belongs to that group and identity, and that all selected/retained
snapshots match their immutable history.  The resolution revision must be
`max(tip revisions) + 1`, not an increment from an arbitrary selected parent;
this is the rule for branches of unequal depth.  The transaction re-reads the
group generation and tips while committing, so an unknown parent, stale
generation, changed tip set, or new competing edit fails closed and receives
no ACK as a resolution.

The preceding equality rule is strict for a resolution prepared and applied on
the same device: that writer must CAS its own local `conflict_group_id` and
`conflict_generation`.  In an authenticated inbound resolution, however,
those two payload fields identify the sender's conflict group and sender-local
generation.  Conflict-group UUIDs are generated locally and are not expected
to match independently generated receiver UUIDs; discovery order may likewise
make the numeric generations differ.  A receiving device therefore maps the
sender evidence to an existing local group only by exact account/project/entity
scope, common parent, complete sorted tip set, immutable tip snapshots and
revisions.  It then performs an independent CAS against that local group's ID,
generation and current tips.  It must not invent a local group when this proof
is absent.  The applied-resolution ledger retains both sender and local group
IDs and both generations together with the full parent proof, so replay never
depends on current Note contents or UUID equality.  This clarification changes
no v2 payload key or encoding.

Pre-017 history without sufficient immutable causal evidence remains
unresolvable.  The deferred sealed-local-delete and post-preservation coalesced
generation cases from Pass 1 also remain fail-closed until their explicit
contracts exist.

### Encryption and cutover

Note plaintext v2 is encrypted under the existing AMK with the existing
`crypto_version=1` and `aad_version=1`; the server stores and transports only
opaque encrypted bytes and learns neither plaintext nor the parent DAG.  The
future encrypted sync protocol v2 is a coordinated pre-public-release hard
cutover: client and server must be deployed together, and a protocol-v1 client
must reject v2 envelopes/events fail-closed.  No mixed v1/v2 apply, downgrade,
or server-side winner selection is permitted.  Existing v1 events continue to
be decoded and applied only by the v1 path; v2 resolution events require the
new v2 path and the local schema-17 conflict evidence.  Until Pass 2F-E
coordinates activation, clients implementing the clarified sender-scoped
group semantics must not participate as uncoordinated protocol-v2 writers or
readers; capability version alone is not semantic-cutover authorization.
