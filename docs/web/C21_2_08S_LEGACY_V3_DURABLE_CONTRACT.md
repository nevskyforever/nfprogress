# C21.2.08S — Legacy-v3 durable identity contract

**DESIGN COMPLETE / RECOMMENDED CONTRACT, NOT OWNER-APPROVED FOR IMPLEMENTATION.**
Baseline: clean branch `6.0`, HEAD, `origin/6.0` and actual remote ref all
`b5bd63be42225a2df17f282211deec39b64c5d4f`. Documentation only; no producer,
validator, migration, capability or workflow change is made by this stage.

**Recommendation: Option A**, the explicit third semantic variant of
Resolution4 / ResolutionProof1 / inbox10. Retain IndexedDB10, its twelve stores
and indexes, Head2 and GroupTransition2. No new backend endpoint, wire field,
encryption format or submitting-protocol claim is needed for this bounded local
contract. This does not solve the frozen server Note reader gate.

## Evidence and authority

Reviewed [R's implementation STOP](C21_2_08R_LEGACY_V3_DURABLE_CONTRACT_STOP.md),
[.23's cross-transport audit](C21_2_23_CROSS_TRANSPORT_READER_GATE_AUDIT.md),
[B5's exact durable contract](C21_BROWSER_CONTENT_OUTBOUND_DESIGN.md#b5-proposed-exact-durable-extension-not-implemented),
and the accepted F/H/G/J/K/Q sections of
[browser persistence](C21_BROWSER_PERSISTENCE.md). Those historical records remain
unchanged. R correctly stopped: B5 currently admits only F2 and Content3.
Physical representability was never authorization to extend that semantic schema.

Source review at the baseline, rather than documentation alone, establishes:

- `resolutionRecords.ts`: exact field sets, two allowed transport/codec pairs,
  protocol3 proof references restricted to `event`, and full row/proof equality.
- `resolutionPlanner.ts`: protocol-driven decoding, clone reservations, protected
  apply, encrypted evidence, ten-store CAS, predicted-state authentication and
  reconciliation. **There is no production `resolutionApply.ts`**; the apply
  runtime is in the planner. `resolutionApply.spec.ts` is its test file.
- `localAuthority.ts`: `prepareProtectedResolutionApply` currently selects source
  validation from `authority.protocol===3`; that assumption must also change.
- `resolutionAuthentication.ts` and `resolutionHistorical.ts`: original wire
  reopening, historical source/output verification and dependency authentication
  also assume protocol3 means Content.
- `syncDurability.ts`: actual protocol3 receive already retains raw Resolution
  descriptors/ciphertext. `v10Transport.ts` J replay requires exact retained
  protocol/page equality; it is not an existing-F2 cross-transport join.
- `resolutionDag.ts`, H/G/Q, K/O/mixed/private Metadata consumers and migration
  dispatch are accounted for in the matrix below; sharing an authenticator must
  not implicitly widen a previously accepted owner route.

R's four genuine encrypted probes established codec feasibility and current
rejection, not new owner or restart acceptance. Its 178 passing tests are
historical evidence only; S runs no implementation tests.

## 1. Exactly two designs

| Decision | Option A — explicit semantic extension (preferred) | Option B — new versioned variant (alternative) |
|---|---|---|
| Durable identifiers | Resolution4, Proof1, inbox10; add exactly `(3, legacy_resolution_v2, resolution)`. | Propose **Resolution5**, **ResolutionProof2**, **inbox11** exclusively for that tuple. Versions are scoped by history kind / proof owner / inbox store; these are proposed identifiers, not allocated by this task. |
| Fields | Existing exact sets suffice. No new optional field or origin flag. | Reuse every corresponding Resolution4 / Proof1 / inbox10 field, with new `record_version` literals. `owner_kind='note_resolution'`, `outcome='applied'`, `state='note_resolution_proven'` unchanged. No additional field is necessary. |
| Identity separation | Protocol, codec, original descriptor and all digests are already included in encrypted evidence/public record identity. Proof reference operation distinguishes raw3 from framed3 and binds the Resolution digest. | Same identity, with Resolution5 and Proof2 version literals also committed. Head2 and Transition2 references still bind the new Resolution digest; evidence format1 carries identity with record_version5. |
| Digest domains | Existing formulas below, with actual values. Existing F2/Content3 domains and bytes untouched. | Same canonical SHA-256 formulas below. New Resolution record/evidence identity includes version5; proof outcome includes version2; dependency preimage still contains received1, not inbox11. Wire/payload domains stay transport/payload based. No synthetic prefix is added to old formulas. |
| Validators | Extend exact tuple/reference checks, replace codec inference in producer/readers, require all cross-record equalities. Reject every other pairing. | Separate strict validators and dispatcher cases for history5/proof2/inbox11; retain old validators unchanged. New leaves only accept raw3. Reject cross-version row/proof substitutions. Update unions, DAG/authentication and consumers. |
| Existing data / upgrade | No conversion or digest rewrite. New bundle reads accepted old records unchanged; only newly authorized owner applies can produce the third tuple. | No conversion of existing F2/Content3. New bundle reads both old and new variants; received raw3 remains received1 until new owner commits inbox11. |
| Old readers | Old v10 opens physical DB10, but exact tuple/reference validators reject raw3 applied records before protected consumption. This is a semantic, not an open-time, barrier. | Old v10 rejects history version5 and unknown inbox11; also a semantic barrier if physical DB stays10. A new record number alone does not prevent opening the DB. |
| Physical migration | None required by field/store/index layout. Keep existing 9→10 validation. | None demonstrated necessary: stores/indexes already fit. Keep DB10; version5/proof2/inbox11 are record versions, not database versions. An opening barrier would require separately justified physical version work, not an automatic consequence of choosing B. |
| Rollback | Old bundle may retain bytes but cannot consume new applied form. Preserve database; restore compatible bundle. No downgrade to F2, deletion or forced reset. | Same preservation/compatible-bundle recovery. Never relabel new versions as old. A future physical upgrade, if separately required, would additionally cause old opens to fail with VersionError. |
| Cost and risk | Smallest semantic change, but same-version extension must be explicitly reviewed and every protocol-based consumer covered. | More unions/validators/test combinations and mixed-version dispatch, without extra authenticity or an open-time barrier. Distinct numbers improve discoverability but do not eliminate codec/source/routing work. |

### Versioning decision and security review

Existing frozen B5 does **not** already license A. This document proposes a narrow
amendment to its allowed-value rule, preserving exact fields, meaning of all
previously accepted values, digest algorithms, rejection of unknown fields and
all existing owner prerequisites. That is consistent with a structural record
version remaining stable **only after explicit acceptance of this semantic
extension**. It is not evidence that arbitrary future variants may reuse versions.
If the owner requires a new record number for every semantic expansion, A cannot
be implemented under that policy; B is the fully specified alternative above.

A is preferred because no previously valid record acquires a different meaning,
the current identity already commits the new distinction, and it avoids adding
parallel record families and cross-version substitutions to the security surface.
B supplies no additional cryptographic binding and no stronger DB-open barrier
under the existing physical schema. Neither design permits an old reader to
apply the new form. **Old-bundle execution against real newly committed data is
mandatory before accepting a producer**, not replaced by this source inspection.
This is a source-based security design review, not independent security approval.

## 2. Exact identity contract (Option A)

The only accepted Resolution combinations after explicit authorization are:

| Retained received protocol | Authenticated `transport_kind` | Original descriptor `operation` | Wrapper digest |
|---|---|---|---|
| 2 | `legacy_resolution_v2` | `resolution` | `null` |
| 3 | `content_note_resolution_v2` | `event` | Digest of authenticated Content wrapper |
| 3 | `legacy_resolution_v2` | `resolution` | **`null`** |

Everything else rejects, including protocol2 Content, raw bytes described as
`event`, framed Content described as `resolution`, an unknown codec, and a
descriptor/payload mismatch. Descriptor operation chooses exactly one permitted
decoder after actual AEAD open; decoder failure never triggers another decoder.
Only successful strict decoding and binding make `transport_kind` authenticated.

| Identity component | Frozen meaning / required check |
|---|---|
| 1. Received page protocol | Actual validated page protocol, copied to received1, Resolution4, Proof1 and inbox10. Raw3 is always3. No cast or synthetic protocol2 receive. |
| 2. Actual wire descriptor | Preserve original parsed `event` and encrypted `object`, including event/device/sequence/project/entity/type/operation/revision/timestamps and crypto/AAD/nonce/ciphertext. Scope is also bound by local record and crypto context. Never reconstruct descriptor fields from plaintext to replace the received descriptor. |
| 3. Authenticated codec | Strict Legacy Resolution v2 for raw `resolution`; strict Content Note frame containing Resolution v2 for `event`. Persist existing transport_kind literals; do not infer codec solely from transport protocol. |
| 4. Original submitting protocol | **UNKNOWN** unless independently attested outside this contract. The wire has no such field. No new field is proposed. F2 proves retained protocol2 context, not independently attested original submission endpoint; raw operation/Legacy codec cannot prove submission2 because v3 can carry/submit it. |
| 5. Durable Resolution identity | All fields returned by `resolutionIdentity(r)`: every Resolution4 field except evidence_envelope and record_digest. Includes local account/device/bootstrap, remote source_device_id, project/note/event, actual protocol, codec, sequence, header, original wire string, wire/payload/dependency digests, group identities/generations/digest, parents, strategy and output role/retained ID. Exact set unchanged. |
| 6. Original wire digest | `D({protocol_version: received.protocol_version, item: JSON.parse(received.wire_item)})`. Fresh raw3 hashes3. Genuine F2 continues hashing2. No byte rewrite or cross-protocol digest comparison pretending equality. |
| 7. Payload digest | `D(strictlyDecodedResolutionV2)`, excluding Content wrapper. Equal logical payloads may have equal payload digests; that does not equate their transport, scope or applied identity. |
| 8. Dependency digest | Existing preimage below, with real received1 row and captured complete owners/bindings. Raw3 uses dependencies:null, never an invented Metadata/Stage dependency. Null wrapper dependencies do not waive bootstrap, publication, parent or source authority. |
| 9. Evidence and wrapper | Existing encrypted resolution_format1/kind resolution_apply with exact identity, payload digests, parents/group/head/source-before/source-after. wire_frame_digest hashes original decrypted bytes; raw Legacy wrapper_payload_digest is literal null; resolution_payload_digest equals r.payload_digest. |
| 10. Applied outcome | Real atomic owner commit produces Resolution4 + Transition2 + original Head2 (+ retained Head2) + inbox10/Proof1 and encrypted sources. Proof1 protocol3/reference.operation resolution binds Resolution/transition/output digests. Successful decoding, a read-only join or a structurally valid record is never an applied outcome. |

`D(x)` is the existing `noteProofDigest`: lowercase hex SHA-256 of UTF-8
`immutableWireIdentity(x)` canonical JSON. `B(bytes)` is existing
`resolutionBytesDigest` over exact bytes. No new domain prefix is introduced.
Resolution4's exact field set is:

```text
record_version, account_id, device_id, project_id, note_id, bootstrap_id,
record_kind, record_id, event_id, source_device_id, protocol_version,
transport_kind, server_sequence, header, wire_item, wire_digest, payload_digest,
dependency_digest, remote_group_id, remote_generation, local_group_id,
local_generation, group_digest, parent_event_ids, strategy, result_operation,
retained_note_id, evidence_envelope, record_digest
```

Full dependency preimage (field names and values unchanged):

```text
D({scope: s, bootstrap_id: group.bootstrap_id,
   project_id: h.project_id, note_id: h.entity_id, event_id: h.event_id,
   transport: receivedRow,
   dependencies: authenticatedContentWrapper?.dependencies ?? null,
   owners: capturedInventory.owners, bindings: capturedInventory.bindings})
```

Historical authentication binds this digest through the exact encrypted evidence
identity and proof, and authenticates the applicable historical dependencies.
It must not recompute it from later current owner heads or rewrite old evidence
when Metadata evolves. Existing parent/dependency historical rules remain in force.

`record_digest = D(Resolution excluding record_digest)`, including its encrypted
evidence envelope. `transition_digest = D(Transition excluding record_digest)`.
Head references contain the exact Resolution digest. Proof output digests hash
the actual encrypted original/retained Note records (`retained=null` when absent).
`outcome_digest = D(Proof excluding outcome_digest)`. Proof exact fields remain
record_version/owner_kind/outcome/account_id/bootstrap_id/protocol_version/
reference/server_sequence/header/wire_digest/payload_digest/dependency_digest/
resolution_digest/transition_digest/output_digests/outcome_digest. Inbox exact
fields remain record_version/state/account_id/device_id/event_id/server_sequence/
protocol_version/wire_item/resolution_proof. There is no unattested codec field
in Proof1: reference operation plus the authenticated Resolution digest binds it.

### Descriptor, crypto and Legacy source checks

Raw3 wire reference is the exact received event with fields
`event_id, device_id, server_sequence, project_id, entity_id, entity_type,
operation, revision, updated_at, deleted_at`. Require note/resolution,
deleted_at=null (including delete strategy), peer source device, valid original
sequence/IDs, crypto_version1/aad_version1 and valid canonical encodings/bounds.
AEAD uses the existing canonical user/project/note/entity-type context. Match
payload event/project/entity/revision and canonical timestamp to the original
descriptor; bind source device in durable identity, not an invented raw payload
field. Payload operation remains resolution; parent IDs are canonical, sorted,
unique, complete and non-self. Existing strategy/revision/group rules apply.

Legacy original and retained outputs must have `stage_id=null`,
`source_type='project'`, `source_map_id=null`, `source_node_id=null`,
`content_format='html'`, and pass the strict Legacy local-source validator and
current resource limits. Tombstones obey the same route constraints. Parent
routes must match the output route, published parents must be genuinely
authenticated in their own codec, and selected/retained content must equal the
declared parent under existing strategy rules. Mixed Legacy/Content ancestry is
eligible only where these existing parent/source/dependency rules accept it;
Content parents do not become Legacy parents and do not lose dependencies.

Authenticate actual import/bootstrap binding, full parent ciphertexts/publication
evidence, group/head, source membership/revision and historical source-before/
source-after. A local unsealed parent needs genuine accepted publication and
frozen-version evidence; no synthetic self-echo. Existing first-F constraint
remains account-wide: pre-F inventory must satisfy v9 validators; any additional
Resolution after an applied F, including another project, stays unsupported.
Keep clone reservations/collisions across all three tuples, including pending
raw3 keep_both. No extra Resolution generation, resurrection, missing parent,
unsupported route or provenance shortcut is enabled.
Retain existing bounds: at most16,384 rows per store, the complete planner's
32MiB inventory budget, 64MiB evidence and 128MiB per-record serialization
ceilings, plus the existing historical-material and local-source limits. These
are simultaneous limits, not permission to exceed the smaller inventory budget.
Reject oversized predicted state before committing; never truncate to fit.

## 3. Complete consumer matrix and partial upgrade barrier

Paths below are relative to `frontend/src/platform/web/` unless stated otherwise.
Classification describes work for the proposed **bounded T slice**, not current
acceptance of Legacy3. “Already supports” means the algorithm is independent of
the new tuple after its strict record/auth dependency is updated; a regression
case is still required. “Must explicitly reject” means retain accepted F2/Content3
behavior and add a new-root guard if shared authentication would widen it.

| Consumer / file | Classification | Exact required handling |
|---|---|---|
| `resolutionRecords.ts` | Requires implementation | Extend Resolution4 tuple/descriptor and Proof1 reference rules by the table; inbox10 preserves full protocol/sequence/reference equality. Validate Resolution codec against proof reference during authenticated cross-record join. No permissive protocol3 catch-all. |
| `resolutionPlanner.ts` original/plan | Requires implementation | Descriptor-selected single decoder; preserve actual received protocol; Legacy limits by authenticated codec; real parent/dependency/source checks unchanged. Extend all pending Resolution clone-reservation paths, including raw3. |
| `resolutionApply.ts` | Not applicable | No such production file. `BrowserResolutionApplyRuntime` in `resolutionPlanner.ts` is the actual owner requiring changes. |
| `resolutionPlanner.ts` apply/reconcile | Requires implementation | Carry authenticated codec in private preparation; evidence wrapper null by codec; generate new tuple using original row; authenticate predicted inventory before atomic commit; reconciliation reopens original evidence/source without reapply. |
| `localAuthority.ts` protected F hook | Requires implementation | `verifiedResolutionForLocal` exposes the privately authenticated codec, not an authorizing caller flag. Use that codec for source validator selection; retain lease/source revision/clone/CAS checks. Do not globally change ordinary source hooks. |
| `resolutionAuthentication.ts` core | Requires implementation | Reopen original wire by tuple, bind all proof/evidence identities, validate raw3 source_after as Legacy, retain parent/dependency authentication. Structural hashes alone confer no authority. |
| `resolutionDag.ts` | Already supports structurally | Existing event/role/revision/parent/bootstrap/clone uniqueness algorithms work after strict leaf validator extension. Never make DAG success an AEAD/apply/prefix certificate. |
| `syncDurability.ts` receive | Already supports retention | Actual v3 raw receive retains protocol3 and wire. Leave general legacy applied readers strict; do not extend commitInboundPage replay by accepting F2/page3 equality. Receipt/pull retention is not application. |
| `v10Transport.ts` J inspect/replay | Requires implementation/acceptance | Core auth must support raw3; replay still requires retained protocol=page protocol, exact interval/cursor/count/descriptor/object and fresh inventory. Raw3 proof replay is3→3. Add a separate read-only F2 join entry; never weaken ordinary replay equality. |
| `resolutionHistorical.ts` root reopening | Requires implementation | Decode authenticated root by transport_kind, preserve role/source lineage and historical dependencies. Needed for safe source reauthentication; does not itself authorize H or G. |
| `resolutionContinuation.ts` H | Must explicitly reject | For T, reject any Legacy3 root before continuation preparation/source mutation. Existing ordinary child2 Legacy / child3 Content mapping remains; no blanket “protocol3 can be Legacy” replacement for child routes. |
| `resolutionPrefix.ts` G and Q mixed prefix | Must explicitly reject | Reject Legacy3 roots before issuing prefix certificate or committing localproven_prefix. Existing G/Q F2/Content3 acceptance unchanged. Later positive acceptance must count keep_both once and authenticate complete historical/source coverage. |
| `v10Recovery.ts` K | Must explicitly reject | Fresh protocol3/resolution currently classifies unsupported; keep that. Explicitly reject a persisted Legacy3 root before J/H/G orchestration if shared J starts accepting it. No automatic fresh F routing in T. |
| `v10MixedRecovery.ts` mixed K / post-F Metadata routing | Must explicitly reject | Reject new root and pending additional Resolution before any routing/owner/prefix mutation. Keep existing supported mixed histories. No inferred private Metadata authorization. |
| `v10OrdinaryApply.ts` O | Must explicitly reject | Guard Legacy3 roots before ordinary owner preparation; otherwise shared historical auth could silently permit them. Existing F2/Content3 paths remain. |
| `mixedSourceValidation.ts` | Must explicitly reject at owner/witness route | Reject Legacy3 root for mixed continuation/ordinary/private Metadata authority in T. Pending Resolution still unsupported_generation. Never treat a readable new root as permission for unrelated owner application. |
| `historicalContentAuthentication.ts`, `historicalMetadataDependency.ts` | Requires compatibility checks; must reject unsupported route | Preserve genuine Content parent dependencies in core F authentication. These higher-level mixed/private paths must explicitly reject Legacy3 roots until separately accepted; historical current-head substitution remains forbidden. |
| Specialized terminal/handoff auth in `resolutionAuthentication.ts`, private historical variants in `resolutionHistorical.ts` | Must explicitly reject | Shared core may read raw3 for F/J; specialized Metadata entry points must not inherit authority for raw3. Retain no-head/create and source restrictions. |
| `privateMetadataPrefix.ts` | Must explicitly reject | No new raw3 root prefix authority or F2/page3 replay relaxation. `privateMetadataAuthentication.spec.ts` covers implementation in `mixedSourceValidation.ts`; there is no same-named production module to edit. |
| `provenPrefix.ts`, existing ACK/write/upload gates | Must explicitly reject | Old validators already reject Resolution leaves. Do not grant ACK, upload, writer or current cursor authority from new proof or read-only join. T adds no positive prefix route. |
| `noteReaderReadiness.ts` I | Already supports negative gate | Preserve ready=false, declarationAllowed=false, writerAuthorized=false; no capability PUT. Readability of this tuple cannot satisfy the complete frozen predicate. |
| `persistence.ts`, `indexedDbV9Migration.ts` | Already supports physical storage; strict migration rejection retained | DB10/twelve stores/indexes unchanged. Keyless 9→10 validation cannot authenticate or admit applied future leaves; genuine old data migrates as before, forged/new leaves in v9 reject atomically. Reopen10 alone is not record authentication. |
| Restart / lifecycle across F,J and local source | Requires acceptance | Reconstruct scope, binding, lease and full disk inventory, then AEAD/authenticate sources/proofs again. No reusable in-memory planner/join token survives logout/restart/key/device/account change. |

No producer may be reachable before the required readers and explicit guards are
installed in the same accepted build. A stale tab/old v10 bundle may physically
open DB10, but its strict records reject new applied data (`corrupt_record` or
the existing boundary error) before protected source/history/proof/prefix use.
Do not claim old v10 gets VersionError: only the existing older physical-version
barrier does that. Nor claim every ancillary operation is globally disabled:
byte retention or unrelated bookkeeping may still be possible. Such operations
must not overwrite the new leaves or advance application/ACK authority across
them. Test old public routes as well as leaf validators; if any route bypasses
this barrier, producer acceptance fails and that barrier must be repaired first.

During partial upgrade, preserve encrypted rows and old evidence exactly, surface
the existing unsupported/corrupt boundary, and resume only with a compatible
bundle. Never drop unsupported rows, truncate an account inventory, recreate the
database, rewrite protocol/version fields or fall back to a different codec.

## 4. Separate existing-F2 exact join

Recommend implementing this **alongside the bounded fresh-F slice**, with
independent positive/negative acceptance. It reuses the complete authenticated
read boundary but has a separate API/result; it is not J interval replay and
must not produce an apply token. A small separately accepted join would be
possible, but would not satisfy fresh-device acceptance or unblock full replay.

1. Take current authenticated account/canonical-user/local-device/key/registration
   context and a validated v3 re-fetch item. The join itself performs no HTTP,
   mode switch or server-gate bypass. Require a genuine note/resolution descriptor.
2. Load the complete bounded account inventory in a readonly transaction. Require
   existing F2 Resolution4, genuine protocol2 Proof1/inbox10, matching bootstrap,
   original parents/publications/group/transition/heads and encrypted source
   witnesses. Missing, duplicate, cross-scope or corrupt evidence rejects.
3. Reauthenticate the original F2 wire, encrypted evidence, full historical owner
   chain and actual applicable source state with current keys/lease. Existing
   accepted descendants may be folded by their accepted historical readers;
   unsupported descendants reject. Do not compare an old output to a newer
   source as if history had not advanced. No digest-only or cache-only shortcut.
4. Match event ID, source device, sequence, project/note/type/operation/revision,
   updated_at/deleted_at and **every original encrypted-object field**, using the
   existing exact parsed identity after page validation. Account/canonical user,
   local device/profile and bootstrap must match retained authority. Reject even
   valid re-encryption with a different nonce/ciphertext. Ignore neither descriptor
   fields nor byte encodings. Equivalent JSON whitespace is not wire replacement:
   retained wire strings remain untouched.
5. Keep F2 wire digest in domain2 and the refetch's receiving context3 separately.
   Never recompute/update F2 as3, copy F2 proof into a raw3 row, or “repair” a
   missing proof. The result means only “this re-fetched item exactly matches
   authenticated retained F2 application.” It claims no original submission
   endpoint and no new applied result.
6. Recheck lifecycle and full snapshot before returning a bounded read-only result.
   No applied/source/history/inbox/receipt/outbox/binding/owner/cursor/ACK writes,
   no prefix certificate, and no call into commitInboundPage. A later restart
   reruns this operation from durable evidence; no in-memory-only join token is
   a prerequisite or durable authority.

A fresh device missing F2 evidence **rejects this join**. Its distinct path is
genuine received3 plus the real F planner/owner below. A server that refuses the
v3 page because of the Note gate cannot be bypassed by either local path.

## 5. Mandatory implementation acceptance

Use the existing fixtures/harness and extend focused parameterizations; do not
create a second redundant broad suite. Every rejection compares the complete
durable inventory before/after, including encrypted wire strings, not just one
count. Initial authorized receive is allowed to retain its row/pull state;
subsequent rejected application/join/replay must preserve that state. Successful
F application changes only its authorized sources/history/inbox atomically,
never prefix/ACK/outbox or capabilities.

| Mandatory case family | Required evidence / oracle |
|---|---|
| Four strategies | Genuine choose_version, manual_merge, delete, keep_both fixtures. Real Legacy producer ciphertext, actual v3 inbound retention, real F prepare/protected source prepare/native atomic commit. Assert raw3 tuple, all digests, transitioned group, source membership and heads; keep_both has two output roles and one event/sequence. |
| Codec and AEAD | Open with actual current AMK/AAD context; strict raw decoder succeeds and Content frame fails. Wrong descriptor route, raw-as-event, framed-as-resolution, unknown format and failed AEAD reject with no decoder fallback. |
| F2 / Content3 preservation | Existing strategy tests unchanged, original records/digests byte-preserved on reopen/reconcile. New branch must not change old hash preimages, wrapper semantics or source acceptance. |
| Source, parents, bootstrap | Full parent ciphertext/publication/receipt/frozen-version checks, genuine binding/bootstrap, correct source-before/after. Missing parents, forged import origin, unpublished local version, wrong project/bootstrap, staged/map/non-html Legacy output, clone collisions and unsupported second F reject. |
| New applied proof | Validate real owner-produced Resolution4, Proof1 and inbox10; reopen encrypted evidence and verify transition/output digests. Hand-edited protocol2 proof or rehashed structural fixture is not positive evidence. |
| Replay / duplicates | J exact3→3 current-interval replay and F reconcile after commit cause zero extra writes. Altered interval/sequence/item/protocol, duplicate event/sequence, wrong receipt and conflicting object reject. Existing F2→page3 J replay still rejects; only separate exact join accepts its own read-only result. |
| F2 join | All four retained F2 strategies with genuine v3 refetch item, full original evidence and current source history. Missing/corrupt/cross-device/bootstrap/parent proof or changed ciphertext rejects. Verify zero writes, and repeat after full process restart. |
| Persistent Chromium | Reuse production harness/native IDB, persistent user-data directory. Commit, close entire browser process, relaunch same profile and reauthenticate all four strategy results, J replay and F2 join. Reload/in-memory adapter is insufficient. Verify no token retained and complete encrypted state persists. |
| Migration where applicable | Existing genuine9→10 and existing10 disk reopen; F2/Content3 stay intact, raw3 received row remains3. Applied new tuple placed illegally in9 rejects migration atomically. No 10→11 migration is required or to be fabricated for A. |
| Tamper matrix | Mutate each identity axis independently: ciphertext/nonce/AAD/crypto, descriptor IDs/device/sequence/revision/time/operation, protocol/codec/header/parent set, dependency/evidence/wrapper/group/transition/output/proof digests and retained role. Rehashing public fields must not defeat encrypted-evidence checks. Unknown fields/versions, truncation and resource exhaustion reject. |
| Lifecycle | Logout/account switch/session expiry/device mismatch or revoked current authorization/key-lock or replacement/profile change during every async boundary invalidates prepare/read/commit. Late callback cannot commit with a stale lease. No new live server capability claim from local tests. |
| CAS and uncertain completion | Race source/inbox/history/group/owner/binding/cursor snapshot changes; abort transaction; crash before/after commit. Native transaction all-or-nothing. Lost completion result triggers disk reauthentication/reconciliation; no second clone/revision/proof. A committed complete result may exist after interruption; verify it rather than falsely require rollback after commit. |
| Actual old reader | Open a real new-profile copy with baseline old v10 bundle; invoke relevant F/J/H/G/Q/K/old-prefix routes. Require rejection before protected mutations/ACK, exact data preservation, then recover with new bundle. Old v9 physical opening barrier remains. Leaf validator negatives alone do not satisfy this row. |
| Mixed history and explicit barriers | Genuine supported Legacy/Content parents retain their own proofs/dependencies; accepted F2/Content3 mixed histories still work. New Legacy3 root through H/G/Q/K/O/private Metadata routes rejects before writes/certificates. Unsupported ancestry/source routes, another Resolution, missing historical dependency, pending work or partial inventory reject. |
| Capability / release boundaries | ready=false, declarationAllowed=false, writerAuthorized=false; no capability PUT, ACK, uploader, transport-mode activation, Metadata no-head creation or production orchestration. Full-account server gate unchanged. |

Optional diagnostics: additional fuzz campaigns, heap profiling and wider
cross-browser permutations. These do not replace mandatory tamper/resource,
native transaction, persistent restart and actual old-reader cases. Independent
review must verify the implementation against this matrix and remote required
coverage before local completion is promoted to accepted status.

## 6. CI feasibility and placement proposal

Inspected actual `.github/workflows/cloud-backend-tests.yml`: **six mandatory
jobs, all timeout40 minutes**: PostgreSQL mandatory foundation, content-action,
complete-project; PostgreSQL cloud and legacy regressions; Frontend admin;
Android compression packaging. Preserve all six, their coverage and limits.

Frontend admin already owns typecheck, production harness build, pinned Chromium,
F/H/G/I/J/K native runs, ordinary/mixed owner/prefix cases and the large persistence
contract command. It is already heavily loaded; do not simply append another
full suite there. Complete-project already installs frontend dependencies,
builds/serves a production Chromium harness, runs isolated historical/private/
post-F Metadata tests (`--maxWorkers=1`), disk acceptance and native/backend work.
It has reusable infrastructure, **not demonstrated spare capacity**.

Proposed placement for separately authorized implementation: parameterize existing
F/J tests for cheap existing-code regressions; isolate the new Legacy3 matrix and
one persistent browser acceptance invocation in complete-project, sharing its
existing build/preview/Chromium. Avoid rerunning every original browser script
merely to exercise the new tuple. Keep old-reader bundle as a pinned baseline
test artifact/profile copy; include its build/start cost in the estimate.
If isolation needs a new spec/script, add only that narrow module and explicit
workflow step/path selection under separate CI review, not a seventh job.

**Measured headroom and incremental CI duration: UNKNOWN.** R's local 178 tests
in12.42s contain no new native restart/old-bundle matrix and cannot estimate this
addition. Before CI placement acceptance, measure per-job and new-step wall time
on representative runners, including dependency/browser/build/native costs and
repeat-run variance. Proposed admission budget: observed maximum job duration
plus measured increment plus a five-minute reserve must stay below40 minutes;
the reserve is this recommendation, not a claim about existing policy. If that
cannot be demonstrated, explicitly review redistribution of complete unchanged
test families among the existing six jobs before accepting the new load. No
coverage deletion, timeout increase or silent skip. CI placement remains an
acceptance requirement, not permission to expand crowded jobs now.

For S, only docs-web/checkpoint change: neither Cloud (`docs/cloud/**` only for
docs) nor SQLite path filters match. No Cloud/SQLite run is expected; no Actions
polling. Future `frontend/src/**` changes select Cloud. SQLite is selected only
if the actual final diff matches its enumerated paths; this browser-only plan
does not itself require SQLite. Reevaluate filters against the actual next diff.

## 7. Minimal next implementation sequence and affected files

Propose **C21.2.08T — dormant Legacy3 F owner/proof and exact retained-F2 join**,
only upon explicit authorization adopting A and this bounded consumer policy.

1. Install strict tuple validation and a single codec discriminator shared by
   the F producer/historical readers. Install explicit new-root barriers in all
   higher-level routes above. Preserve existing record/digest/version behavior.
2. Complete read-side encrypted history/source/J replay support, the protected
   source hook and pending clone checks before making the producer reachable.
3. Implement real F prepare/apply/reconcile with unchanged transaction stores,
   lifecycle guards and CAS. Keep it dormant and directly invoked by the bounded
   acceptance harness; K/production orchestration remains blocked for raw3.
4. Add the separate read-only F2 join and independently accept it. Run the focused
   matrix, persistent native restart/old-bundle cases, typecheck/harness build,
   then reviewed CI placement and all selected mandatory jobs. No public gate
   promotion from a local pass.
5. A later separately authorized slice may positively accept Legacy3 H/G/Q/K and
   mixed/private consumers. It must include their full owner/prefix/history tests;
   do not advertise complete authenticated account replay after T alone.

The smallest accepted producer slice is **steps1–4 together**, with explicit
negative guards for deferred consumers. A read-only preparatory commit is useful
internally but not fresh-owner completion. This resolves the known durable
format choice before coding; no repeat of R's semantic ambiguity is necessary
once A is explicitly authorized. It does not pre-authorize unexpected new scope.

Expected production edit set for T (all under `frontend/src/platform/web/`):
`resolutionRecords.ts`, `resolutionPlanner.ts`, `localAuthority.ts`,
`resolutionAuthentication.ts`, `resolutionHistorical.ts`, `v10Transport.ts`,
`resolutionContinuation.ts`, `resolutionPrefix.ts`, `v10Recovery.ts`,
`v10MixedRecovery.ts`, `v10OrdinaryApply.ts`, `mixedSourceValidation.ts`,
`privateMetadataPrefix.ts`; route-local guards in
`historicalContentAuthentication.ts` / `historicalMetadataDependency.ts` only
where their entry points can bypass the guarded shared boundary. Prefer one
explicit shared guard with verified callers over duplicated inconsistent guards.
No production `resolutionApply.ts` or `privateMetadataAuthentication.ts` exists.
No change is expected to syncDurability receive, DAG algorithm, persistence
layout, migration, wire codecs, crypto, readiness, backend, Rust or Python.

Expected acceptance files: extend existing `resolutionReaders.spec.ts`,
`resolutionPlanner.spec.ts`, `resolutionApply.spec.ts`, `v10Transport.spec.ts`,
`localAuthority.spec.ts` and relevant H/G/Q/K/mixed/private boundary specs in the
matrix; reuse `resolution.testFixture.ts`,
`frontend/scripts/browser-persistence-harness.ts` and existing browser acceptance
infrastructure. If isolated CI placement is approved, proposed narrowly scoped
additions are `frontend/src/platform/web/legacyV3Resolution.spec.ts` and
`frontend/scripts/browser-legacy-v3-resolution-acceptance.mjs`, plus explicit
Cloud step/filter edits. Do not duplicate the entire existing suite in them.
Update the accepted contract/checkpoint at that implementation's real status.

Contract-review risks remain: same-version semantic policy approval; actual old
reader routes that might bypass validators; missed protocol-as-codec inference;
shared Metadata/historical consumers accidentally widening authority; and
unmeasured CI capacity. All have explicit acceptance barriers above. New versions
or a DB migration are not established remedies for unrelated source/reader gaps.

## 8. S validation, publication and unchanged status

S changes exactly this document and `docs/WORTA_CHECKPOINT.md`. Required checks:
`git diff --check`, exact changed-file scope and protected bytecode SHA-256
integrity. Expected unchanged hashes:

```text
__pycache__/engine.cpython-312.pyc
a256bcf08940a513a98f6551e314511cf6961bf298b88b294fd6d9c133d4bec5
__pycache__/game_data.cpython-312.pyc
8bd116c0b5b284f4f4b80551d10199e20d3c4546fe8caac22c07ff2973d568d2
```

No implementation tests, builds, browser runs, migrations or live multi-device
experiments are run in S. Publish a docs-only commit to origin/6.0, without
polling/waiting for Actions or starting T. Publication SHA is recorded in the
task result; no self-referential commit hash is fabricated here.

C21/C21.2 IN PROGRESS; C21.2.08 NOT CLOSED; .08R IMPLEMENTATION STOP;
.11 PARTIALLY RESOLVED; C21.1.06 NOT LOCAL COMPLETE; .18 REMOTELY ACCEPTED,
Cloud `39850013638` SUCCESS6/6; .19/.21/.23 AUDIT COMPLETE;
.20/.22 IMPLEMENTATION STOP. Web89.36%, ready=false,
declarationAllowed=false, registration CLOSED, PUBLIC RELEASE BLOCKED.
VPS, landing, permanent CI/CD release policy, C22/C23/PF6.0/RC and all security
and owner gates are preserved. Design completion is not owner approval,
implementation completion, full-reader acceptance or release readiness.
