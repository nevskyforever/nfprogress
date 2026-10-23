# C21.2.08R — authenticated Legacy Resolution over v3: durable contract STOP

**IMPLEMENTATION STOP / NOT LOCAL COMPLETE — local durable schema semantics need
explicit contract review.** Starting clean branch `6.0`, local HEAD, `origin/6.0`
and actual remote ref matched `fe23a33e42e58f6ee3ba27924b946ad3cf5218bd`.
Protected engine/game-data bytecode hashes matched the established values.
No production component, durable variant, capability, workflow or dependency was
changed. Only this report and the checkpoint are permanent changes.

## Mandatory pre-write decision

The task explicitly requires: **“STOP for contract review if a new versioned
durable proof, schema, wire field or server contract is necessary.”** Its
publication rule requires only documented findings when mandatory authority or
storage prerequisites fail. The fresh-device durable form is outside the
accepted B5 schema; the stop applies before introducing partial A/B components.

The existing fields can physically store protocol3 plus a Legacy transport kind.
That does **not** mean this combination is accepted by the durable contract.
The exact B5 invariant allows only protocol2/Legacy and protocol3/Content.
Allowing protocol3/Legacy would extend the semantic schema even if no field,
store, index, record number or physical database version changed. This task does
not authorize that extension. A new record version or database migration has
**not** been proven necessary or selected; choosing same-version extension versus
new versions and compatibility barriers requires the separate review.

## Actual identity and proof boundary

| Surface | Existing accepted meaning | Required raw-Legacy/v3 meaning and result |
|---|---|---|
| New inbound row | `commitInboundPage` copies the actual page protocol into the received row and retains original item bytes. | An actual v3 page produces `protocol_version=3`, `operation='resolution'`, with original raw Legacy ciphertext. This receive succeeds. It must remain protocol3. |
| Resolution4 | B5 and `validateResolution4` allow exactly `(2, legacy_resolution_v2)` or `(3, content_note_resolution_v2)`. Protocol3 wire must use operation `event`. | `(3, legacy_resolution_v2)` is rejected. Relabeling it Content still fails the raw `resolution` descriptor. A third semantic combination requires reviewed durable authority. |
| ResolutionProof1 | Protocol3 requires `reference.operation='event'`; its outcome is explicitly `applied`, not merely decoded. | A protocol3 reference to raw `resolution` is rejected. Calling an AEAD/codec success an applied proof would omit actual parent/source/owner acceptance. |
| Inbox10 | Exact retained row/proof protocol, sequence, event and descriptor must agree. | The correct raw3 row cannot contain a currently accepted protocol3 Legacy applied proof. F2 proof reuse would misstate the actual receive identity. |
| Encrypted apply evidence | Exact public Resolution identity is authenticated inside evidence; `wrapper_payload_digest` and source validation follow the accepted transport/codec mapping. | Protocol3 currently implies a Content frame/wrapper and Content source validation. Supporting raw Legacy requires an explicit mapping for null wrapper digest, Legacy route limits, dependency rules and source semantics. |
| F prepare/apply | Protocol2 `resolution` opens with the Legacy codec; protocol3 `event` opens with the Content frame decoder. Producer and historical reader use the same mapping. | Current F rejects the correct raw3 received row with `invalid_resolution`, before any owner/source write. Changing only that branch would leave durable readers unable to reopen the result. |
| H/G/Q/J/K consumers | Historical authentication reopens original AEAD and applies the same codec/proof rules. J additionally requires retained row protocol to equal the page protocol. | An exact existing F2→v3 re-fetch join remains a separately possible read-only route; it cannot create the fresh-device proof missing above. Downstream consumers must not silently reinterpret a new durable variant. |

Source anchors: [B5 exact durable contract](C21_BROWSER_CONTENT_OUTBOUND_DESIGN.md#b5-proposed-exact-durable-extension-not-implemented),
[F accepted apply contract](C21_BROWSER_PERSISTENCE.md#c21208f--browser-resolution-v2-atomic-protected-apply--dormant),
`resolutionRecords.ts` lines 92–140, `resolutionPlanner.ts` lines 103–128 and
313–335, `resolutionAuthentication.ts` lines 134–153 and 216, and
`v10Transport.ts` lines 60–81. The historical design heading remains verbatim;
the later C/F records identify its implemented and accepted scope.

## Two distinct device cases

**A — retained genuine F2 evidence:** the old protocol2 row, Resolution4,
ResolutionProof1, source witnesses and immutable wire remain valid and can be
reauthenticated. A future exact read-only join can compare canonical scope,
device/project/bootstrap, event/sequence, full descriptor and encrypted object
against that authenticated inventory without rewriting its protocol or digests.
Current J still rejects cross-page protocol equality, and no new join was shipped
in R. Missing/corrupt F2 evidence must remain a rejection. Existing disk restart
acceptance is historical component evidence; no new cross-transport persistent
restart claim is made.

**B — fresh raw3 receive:** actual inbound retention can preserve protocol3 and
the exact original encrypted item. Direct AEAD open plus the strict Legacy
Resolution decoder succeeds for genuine Legacy payloads; the Content frame
decoder rejects those bytes. This proves codec feasibility, not complete fresh
F apply or durable authority. New F preparation fails under the current mapping,
and the correct raw3 applied form fails existing durable validators. No F2 proof
was forged, no original submission protocol inferred, and no new decoder/proof
component was shipped.

This qualifies .23's conditional recommendation: its existing-device versus
fresh-device distinction and AUDIT COMPLETE status remain valid, but avoiding a
physical migration is insufficient to establish compatibility with the exact
current B5 semantic schema. The required local schema/owner review is now
concrete. No backend field or server endpoint is established as necessary.

## Focused evidence and limitations

One temporary Node/Vitest probe file ran four cases, one per strategy:
`choose_version`, `manual_merge`, `delete`, `keep_both`. Each used real encrypted
Legacy parent producers and actual F plan/prepare/atomic commit, then:

- Reauthenticated the genuine F2 owner/history and validated its Resolution4,
  ResolutionProof1 and inbox10 using the accepted readers.
- Wrapped the identical descriptor/encrypted object in a v3 page and validated
  that page without changing the original wire or claiming a network fetch.
- Opened actual AEAD and decoded the exact Legacy payload; verified that the
  Content frame decoder rejects it.
- Confirmed that illustrative protocol3/Legacy Resolution4, protocol3/raw-reference
  Proof1 and inbox10 candidates fail structural validation. These candidates are
  deliberate negative inputs, **not** re-signed or accepted new proofs.
- Reconciled genuine F2 with no extra writes and unchanged complete fixture state.
- Used an independent genuine Legacy fixture and the actual inbound owner to
  receive its raw event through a v3 page. The resulting row was protocol3.
  F prepare rejected it with `invalid_resolution`; complete state was unchanged
  after that rejection. Expected initial F2/apply and receive writes are not
  counted as unauthorized writes.

Executed once from `frontend/`:

```text
npx vitest run src/platform/web/c21_2_08r_contract_probe.spec.ts src/platform/web/resolutionReaders.spec.ts src/platform/web/resolutionApply.spec.ts src/platform/web/v10Transport.spec.ts
```

**178 PASS / 4 files in 12.42s wall time; 0 failures, 0 skips.**
174 existing cases plus 4 temporary probes. Existing F2 and framed Content3
four-strategy apply/reconcile, proof validation, corruption, scope/lifecycle,
transaction rollback, exact same-protocol replay and mixed-history negative
coverage remain intact. The temporary probe was removed before commit; no
permanent tests or workflow checks were added.

No new cross-transport join, private-token boundary, fresh applied proof, native
CAS integration or complete new security matrix was implemented. Typecheck,
build, real persistent Chromium/process/disk restart, migration and live server
multi-device/revocation tests were **NOT RUN** after the mandatory pre-write
STOP. Scheduling-fixture tests are not presented as persistent Chromium evidence.
No Note capability PUT, transport-mode activation, ACK, Metadata creation,
publication, live pull, uploader or production orchestration was performed.

## Required review and next smallest slice

Propose **C21.2.08S — Legacy-v3 durable identity contract and compatibility design**,
DESIGN ONLY, not started. Acceptance must choose and independently review:

1. The supported tuple of receiving transport, authenticated codec and actual wire
   descriptor; original submission protocol remains unknown when not retained.
2. Whether to extend the existing semantic variants or introduce explicit new
   record/proof versions. Specify old-reader rejection, upgrade/rollback and
   migration behavior before enabling any durable producer. No version selected
   here.
3. Exact digest domains, wrapper/null semantics, encrypted evidence identity,
   Legacy source limits, real parent/publication/bootstrap checks, owner/CAS and
   replay rules. Preserve all existing F2 and Content3 bytes and proof domains.
4. The consumer inventory: strict records/DAG, planner/apply, historical and source
   readers, H/G/Q, J/K and private Metadata dependencies. Every consumer must
   either explicitly support the new form or reject it before mutation/ACK.
5. Separate acceptance for retained-F2 exact join and fresh raw3 codec/owner
   authority: all four strategies, framed Content separation, deterministic wire
   tampering, missing/corrupt source/proof, real persistent restart/migration,
   stale/revoked scope, duplicate/conflicting sequence and no unauthorized writes.
   Use the existing six Cloud jobs/40-minute budgets or review a partition before
   adding workload. Do not infer headroom from the current local focused run.

After independent contract acceptance, a separately authorized implementation can
resume these bounded paths. Full C21.2.08 reader/capability remains later work;
R cannot bypass the server Content-bearing-account gate. Metadata no-head create
stays at `unsupported_create_baseline` and is not the next slice.

## Publication and unchanged release state

CI increment **0**; only checkpoint and `docs/web/` paths change. Existing Cloud
and SQLite filters select neither file, so both are NOT EXPECTED. No Actions
polling, waiting or dispatch. `git diff --check`, exact changed-file scope,
temporary-file removal and protected bytecode checks are publication gates.

C21.2.18 REMOTELY ACCEPTED, Cloud `39850013638` SUCCESS6/6; .19/.21 AUDIT COMPLETE;
.20/.22 IMPLEMENTATION STOP; .23 AUDIT COMPLETE; .11 PARTIALLY RESOLVED;
.08 NOT CLOSED; C21.1.06 NOT LOCAL COMPLETE; C21/C21.2 IN PROGRESS.
Web89.36%, `ready=false`, `declarationAllowed=false`, `writerAuthorized=false`,
registration CLOSED, PUBLIC RELEASE BLOCKED. VPS, landing, permanent CI/CD policy,
C22/C23/PF6.0/RC, security and owner release requirements remain mandatory.
