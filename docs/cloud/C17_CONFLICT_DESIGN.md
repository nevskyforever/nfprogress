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
