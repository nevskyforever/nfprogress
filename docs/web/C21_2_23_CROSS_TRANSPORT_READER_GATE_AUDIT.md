# C21.2.23 — cross-transport history and truthful reader-gate audit

**Status: AUDIT COMPLETE — implementation remains blocked at the C21.2.08 reader gate.**
Starting branch `6.0` was clean at `d6d78eb040558d676713ca9984fbd44009211391`,
matching `origin/6.0`. No application behavior, server predicate, declaration,
protocol, schema, proof, or CI workflow was changed. C21.2.22 remains an
IMPLEMENTATION STOP / NOT LOCAL COMPLETE; its `unsupported_create_baseline`
boundary is retained.

## Findings: original Legacy Resolution through a v3 page

| Layer | Current evidence and boundary |
|---|---|
| Original producer | The accepted Legacy F path seals raw Legacy Resolution-v2 history through the v2 transport. The accepted Content path uses a v3 `event` whose decrypted object is a framed Content Note event. |
| Persisted server event | `SyncEvent` retains the event descriptor, sequence, device, and encrypted object. V3 pull preserves `event_id`, `device_id`, `server_sequence`, project/entity fields, `operation`, revision/timestamps, crypto/AAD versions, nonce, and ciphertext. Its top-level `protocol_version` and `encrypted_sync_version` are both 3. It carries no separate original submission-protocol field or per-device import receipt. The v3 push contract also permits `operation='resolution'`; therefore operation alone does not prove which transport accepted the row. |
| Original format signal | The authenticated descriptor's operation and the AEAD-opened, strictly parsed payload format distinguish the current raw Legacy Resolution representation from a framed Content Resolution representation. The current F owner selects its decoder from the received row protocol before opening the payload: protocol 2 accepts raw `resolution`; protocol 3 accepts `event` plus Content frame/version 2. The v3 parser preserves raw `resolution`, but F does not currently accept that combination. A decoder must authenticate first and use an exact codec parser; trying codecs until one happens to parse is not an accepted contract. |
| Existing genuine F2 identity | An accepted device retains `protocol_version=2` in its durable inbox row and in the genuine Resolution4 / ResolutionProof1 evidence and dependent historical proof/certificate digests. The evidence is authenticated against the original wire and source history by F/H/G readers. This retained record is durable IndexedDB state and is reauthenticated after a full browser restart. |
| Proof domains | F binds `protocol_version` into the original wire digest and Resolution4 / ResolutionProof1 evidence. Historical authentication recomputes the same digest from the retained protocol and original item. It cannot be changed from 2 to 3 or 3 to 2 without changing the proof domain. |
| New v3 receive | `commitInboundPage` stores the page protocol on a new received row. `BrowserV10Transport.replayInboundPage` requires the stored row protocol to equal the page protocol, then compares exact event/wire identity. `resolutionPlanner.ts` and `resolutionAuthentication.ts` also branch on the row protocol. No accepted owner joins a newly received v3 wrapper to old protocol2 F evidence today. |

### Cases

| Device/history case | Safe conclusion under current code |
|---|---|
| Existing device with authentic persisted F2 proof | It can reauthenticate its retained protocol2 row/proof after restart. A v3 re-fetch has the same original descriptor and ciphertext, so an exact join by event ID, sequence, full descriptor, nonce/ciphertext, and independently reauthenticated F2 proof is technically useful. No current J/F owner implements or accepts this cross-page join; it must preserve the retained protocol2 proof and must not relabel the v3 page as protocol2. |
| Existing device with missing, corrupt, or mismatching F2 proof | Fail closed. The server re-fetch can confirm bytes but cannot recreate the missing F2 application/source proof. It must not synthesize a proof or use payload shape as evidence that F had already accepted the event. |
| Fresh registered device with no retained Legacy history | It has no F2 owner history to join. Once account Content events exist, the current v3 pull is blocked until the device truthfully meets the frozen Note gate. After that gate is independently satisfied, it still needs a new authenticated raw-Legacy-on-v3 decode/apply/proof contract. Current F rejects it. |
| Browser database migration | The accepted v9→v10 migration is structural and preserves accepted leaves; it grants no missing protocol identity, proof, or readiness. Retained genuine F2 evidence can still be reauthenticated if present and valid. Migration cannot recover erased or malformed proof rows. |
| Full browser restart with database retained | Existing F2 row/proof can be freshly reauthenticated; no in-memory cache is needed. A proposed exact join must have the same property and make no duplicate source/history writes. A cleared or lost database is the fresh-device case. |
| Mixed Legacy and Content account | V3 transports both historical families as protocol3 pages. Legacy raw Resolution and framed Content Resolution remain distinct codec/owner routes. Full history cannot be claimed until both routes and their source/dependency lifecycles are accepted. |
| Earlier event received through v3 with original bytes unchanged | Byte equality proves the encrypted object is unchanged. It does not itself prove the original submission protocol or a prior local F application. Retained genuine F2 evidence can prove the latter for that device; a fresh decoder needs its own explicitly versioned proof domain recording the v3 receive and authenticated Legacy format. |

**Answer to the origin question:** the v3 response preserves enough authenticated event and encrypted-object material to recognize and strictly decode the current Legacy versus framed Content wire formats after AEAD verification. It does not explicitly preserve the endpoint/submission protocol. Existing genuine F2 evidence supplies that original protocol identity on that device. For a fresh device, no accepted evidence supplies it. The operation field cannot substitute because v3 also accepts `resolution`. A new browser owner/decoder and local proof contract is required to support raw Legacy carried by a v3 page without casting the page to protocol2. Current evidence does not require a backend field or wire change if that contract binds the actual v3 page, exact descriptor/ciphertext, and strict authenticated Legacy codec. If future requirements demand proof of the original submitting endpoint rather than authenticated event format, that provenance is unavailable in the current v3 response and needs separate contract review.

This is not a server cryptographic proof that a client consumed the event. The server stores opaque ciphertext and cannot attest to local apply, source ownership, or proof completeness.

## Frozen Note gate and readiness inventory

The server predicate in `services.py::content_note_reader_ready` requires each device to have all six values:

| Field | Required value | Browser status |
|---|---:|---|
| `reader_transport_version` | 3 | Registration is identity-only; no Note declaration is made. |
| `note_frame_version` | 1 | No accepted full production reader declaration. |
| `note_codec_version` | 1 | No accepted full production reader declaration. |
| `note_compression_zero` | `true` | Browser's current v3 capability call declares compression support only. |
| `note_ordinary_reader_version` | 1 | Bounded Legacy/Content ordinary readers exist; full v10 route integration and lifecycle acceptance remain incomplete. |
| `note_resolution_reader_version` | 2 | Bounded F/H/G readers exist; full raw-Legacy-on-v3 dispatch, complete recovery, author/source chains, and lifecycle acceptance remain incomplete. |

The account gate additionally requires at least one registered device, every
registered device to satisfy that predicate (`missing_devices=0`), and authoritative
writer transport mode 3. V3 pull applies the per-device Note predicate when any
account Note `event` exists, before pagination; the check is not limited to the
requested page. Map, Document, and Progress v3 gates also build on the Note reader
predicate. The server cannot verify these declarations against E2EE plaintext.

| Requirement family | Classification | Current accepted boundary / remaining work |
|---|---|---|
| F/H/G/Q/J/K component readers and local evidence | **Already independently accepted, bounded and dormant** | Genuine F/H/G evidence, Q prefix, J page replay/received scan, and K manual recovery cover explicit subsets. They are not production dispatch or full ordinary1/Resolution2 lifecycle acceptance. |
| Existing ordinary Legacy and Content readers | **Partially implemented / bounded accepted** | Legacy protocol2 and Content ordinary-v1 owners exist. Full v10 inbound page replay, received scanning, dependency ordering, route dispatch, and mixed-history recovery are not composed into normal browser sync. |
| Cross-transport raw Legacy Resolution | **Not implemented as an accepted owner path** | V3 preserves the bytes and parser accepts the descriptor. Current F requires protocol2 for raw Legacy; v3 branch requires framed Content. Exact retained-F2 join is not implemented. |
| Production dispatch and transport replay | **Implemented in isolated dormant slices; production composition incomplete** | J and K are manual/read-only or dormant routes. Current production browser orchestration does not route every received event through accepted v10 owners and replay checks. |
| Missing/cold dependency and orphan recovery | **Partially implemented; full behavior not accepted** | K reports missing dependencies/sequences and retries manually. It does not fetch all dependencies or safely recover every cold/orphan history in production. |
| Mixed source ownership, full project/family routing | **Partially implemented / dependent** | O/P/Q and .09 have bounded mixed-source paths. L's source-authority STOP and unsupported Stage/StageOrder, unrelated Note, and other family histories remain. Full coverage needs each actual owner, dependency, source revision, and complete inventory proof. |
| Tombstone resurrection | **Not implemented / not accepted** | Implicit resurrection is rejected; a separately specified lineage and source contract plus genuine lifecycle tests are required. |
| Further Resolution generations/open groups | **Partially implemented / not accepted for full lifecycle** | H can preserve a bounded fork and K stops at unsupported later generations. A genuine next producer, closure, current-source chain, and restart/replay acceptance are missing. |
| Own Content self-echo and own Resolution author chain | **Not implemented / not qualified** | Format readers do not prove producer, durable receipt, local publication, self-echo, or author-chain ownership. Genuine producer and consumer evidence is required. |
| Local author after Resolution | **Not accepted** | Existing source validators reject later own author children; requires exact source/CAS and author-chain contract and acceptance. |
| Multi-device production orchestration and remote revocation | **Partially implemented locally / full claim not proven** | Native real-profile tests cover bounded restart, tabs, and locally observable revocation. Complete live server multi-device discovery/recovery, offline/reopen/lost reply and authoritative remote revocation behavior are not accepted. |
| Readiness inspector and declaration client | **Implemented but deliberately dormant/negative-only** | `noteReaderReadiness` always returns `ready=false`, `declarationAllowed=false`, `writerAuthorized=false`; it has no capability HTTP surface. `readerCapability.ts` declares compression only. |
| Note declaration, account gate and ACK activation | **Not activated** | No Note capability PUT is authorized by this audit. Resolution ACK and Content writer/sealing/upload remain separate later gates. |

### Exact conditions for a truthful positive readiness result

`ready=true` and `declarationAllowed=true` can be considered only after all of the
following are independently accepted:

1. Every supported ordinary and Resolution family has a strict authenticated
   decoder, durable identity/proof, owner, source/dependency route, and exact
   restart/replay behavior. This includes raw Legacy Resolution on v3 pages and
   framed Content Resolution without protocol casts or ambiguous fallback.
2. Version-aware page replay and received scanning retain exact original wire and
   event identity, reject gaps/conflicts/corruption, survive full disk/browser
   restart, and do not duplicate apply/source/proof writes.
3. Full production dispatch and dependency/orphan recovery route each event to its
   real accepted owner in account sequence order, stop at the earliest blocker,
   and preserve unrelated-project and mixed-source ownership.
4. Every lifecycle included in the frozen claim has genuine positive and negative
   evidence: deletion/resurrection rules, further Resolution/open-conflict
   generations, source changes, own Content receipt/self-echo, own Resolution
   author chains, local authoring after Resolution, key/profile/device revocation,
   and multi-device offline/reopen/recovery. Unsupported cases remain explicit
   blockers unless the owner changes the scope.
5. The actual production browser orchestration uses those accepted routes. Tests
   cover registered devices, real server history, all supported event families,
   crash/restart, competing tabs, unknown/corrupt events and revocation. A bounded
   F or G history pass alone is insufficient.
6. Only after code and evidence pass may each registered device truthfully declare
   the frozen six-field tuple. A fresh authenticated gate read must show
   `ready=true`, `missing_devices=0`, and writer mode3 for the same current account
   and device set. No cached flag or local inspector result substitutes for it.

Partial implementation must keep readiness blocked for raw Legacy-on-v3 gaps,
unsupported families/generations, missing dependencies, tombstone resurrection,
own-authorship/self-echo gaps, mixed-source uncertainty, unproven multi-device
recovery, any registered device without all six fields, any lifecycle revocation,
and any nonzero/missing server gate result.

## Strategy and implementation order

| Strategy | Assessment |
|---|---|
| **A — Complete C21.2.08 first** | **Preferred.** It resolves the shared prerequisite for truthful Note capability, fresh complete-history replay, dependent Note/map/document/progress reads, and the later Metadata no-head path. Implement and independently accept reader compatibility and lifecycle coverage before any declaration or Metadata-create attempt. |
| **B — Existing-device authenticated F2 join** | Useful as a small dormant compatibility improvement, if separately scoped. Join only when the current v3 descriptor/object exactly match a retained, freshly reauthenticated F2 row and proof. Missing/corrupt F2 evidence still blocks. It does not establish fresh-device history, clear the Content gate, or close C21.2.08; it must not invoke a Note capability declaration. |
| **C — New read-only history endpoint** | Not technically required for the recommended A path: once a complete reader implementation is independently accepted, that truthful device can declare and use the existing v3 endpoint. A separate endpoint would be needed only if policy requires unready devices to read account history before they can declare. It would need the same account/device authorization, bounded ordered pagination, stable high-water snapshot, exact no-omission retention, revocation and cursor semantics, rate/resource limits, encrypted-byte preservation, and no ACK/write authority. This changes the backend contract and needs explicit owner review. It must not weaken registration, mode, capability, or device gates. |

### Minimal ordered plan

1. **C21.2.08R — authenticated Legacy Resolution identity across v3 pages**
   (proposed, not started): define a local owner/proof contract that preserves the
   received page protocol3 and strictly authenticates the raw Legacy codec. In
   the same bounded slice, support exact re-fetch join for an existing authentic
   F2 proof without rewriting its identity. Test four F strategies, genuine
   Legacy producers, v3 wrapper identity, tampered descriptor/ciphertext, absent
   or corrupt F2 proof, browser database migration, full restart, no duplicate
   writes, and framed Content discrimination. No declaration, scheduler, ACK, or
   fresh-device readiness activation. No backend/schema/wire change unless the
   explicit proof-origin review shows the current descriptor and AEAD inputs
   cannot support this local contract.
2. Independently accept R, then continue the smallest unresolved C21.2.08 slices
   through version-aware transport replay/received scan, route-aware full recovery,
   and the missing lifecycle/author/source cases. Preserve per-event atomicity,
   complete inventory checks, explicit blockers, and existing CI job budgets.
3. Compose the accepted routes into actual browser orchestration and complete the
   registered-device, account-wide Note gate matrix. Submit Note declarations
   only after independent review confirms the implementation satisfies every
   frozen field. Verify the live gate for every device and authoritative mode3.
4. Only after C21.2.08 is independently accepted, reopen the C21.2.22 Metadata
   no-head feasibility/create task. Recheck full-history replay, Content ID0/ID1,
   source ownership, ten-store CAS, restart and race acceptance. Keep
   `unsupported_create_baseline` until then.

If R finds that authenticated event plus codec cannot support the required proof
domain, stop and request an explicit owner/contract review for a versioned local
proof origin or server provenance field. Do not cast v3 rows to2, weaken the
server predicate, or invent a fresh-device import receipt. Strategy C is not a
fallback unless separately approved.

## Release and validation record

This work is inside the existing mandatory C21.2.08 full reader/recovery and
C21.1.06 all-family browser coverage requirements. It does not make raw Legacy
history optional and does not change .11's partial status. C21.2.18 remains
REMOTELY ACCEPTED, Cloud `39850013638` SUCCESS6/6; C21.2.19 and .21 remain AUDIT
COMPLETE; .20 and .22 remain IMPLEMENTATION STOP / NOT LOCAL COMPLETE; .11 remains
PARTIALLY RESOLVED; .08 remains NOT CLOSED; C21.1.06 remains NOT LOCAL COMPLETE.

Inspection only; no tests or probes were run. `git diff --check` is required for
this documentation task. No Actions were dispatched or polled. Checkpoint and
this `docs/web/` document are not selected by current Cloud/SQLite source filters;
no CI run is expected. Web progress stays 89.36%, `ready=false`, registration
CLOSED, PUBLIC RELEASE BLOCKED. VPS, landing, permanent CI/CD policy, C22/C23,
PF6.0/RC, security, and owner release requirements remain unchanged.

## Source map

- [C21.2.22 feasibility STOP](C21_2_22_AUTHENTICATED_HISTORY_FEASIBILITY_STOP.md)
- [C21.2.21 trusted import-origin audit](C21_2_21_TRUSTED_IMPORT_ORIGIN_CONTRACT_AUDIT.md)
- [C21.2.18 private Metadata routing](C21_POST_F_METADATA_ROUTING.md)
- [C21 browser persistence history and C21.2.08 acceptance inventory](C21_BROWSER_PERSISTENCE.md)
- `frontend/src/api/encryptedSyncV3.ts`, `frontend/src/platform/web/syncDurability.ts`, `v10Transport.ts`, `resolutionPlanner.ts`, `resolutionAuthentication.ts`, `noteReaderReadiness.ts`, `readerCapability.ts`, and `deviceRegistration.ts`
- `backend/app/cloud/services.py::content_note_reader_ready`, `content_note_gate`, `declare_content_note_reader`, `pull_encrypted`, and `pull_encrypted_v3`; `backend/app/cloud/sync_v3_router.py::encrypted_pull`
