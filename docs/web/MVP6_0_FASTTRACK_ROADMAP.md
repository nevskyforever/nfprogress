# WORTA 6.0 — Web Online-Only roadmap

**Owner decision, 2026-10-27: WEB ONLINE-ONLY / SERVER-AUTHORITATIVE.** Desktop
remains offline-first on SQLite with optional cloud sync. Web requires server
connectivity. E2EE remains client-side; the server is authoritative for
persistent user data and stores opaque ciphertext plus required protocol
metadata. LOCAL-FIRST is still mandatory for Codex development and acceptance;
it does not require offline-first runtime behavior in Web.

## 2026-10-28 — WEB.ONLINE.02A production reader audit / STOP

Baseline `3ef704c5f4353fcfdf4d0921739ce2213fd052de` was independently accepted
by Cloud run `40578946929` (**6/6 SUCCESS**, owner-reported). WEB.CLOUD.READ.01
is present and accepted as a bounded **Metadata-only preview**: it validates the
whole bounded account v3 sequence, canonical AEAD, bootstrap/descriptor joins,
Metadata history and registry/transport stability. This is not full project
opening, project-content restoration, or C21 apply/recovery.

WEB.ONLINE.02A stopped before implementation because the existing C21 owners
are not composable with live server pull as a read-only Online-Only projection.
`BrowserV10Recovery`/`BrowserV10Transport`, Stage/StageOrder apply and Note
recovery are bound to a complete durable local inbox/source inventory and
atomically record owner/applied proofs. The Online-Only catalog/read path must
not promote the v12 developer workspace to project authority, nor invent
ephemeral proofs in place of owner evidence. Adding codec dispatch alone would
not authenticate dependencies, history, conflicts or applied state.

| Scope | Existing support | Web production-read gap |
| --- | --- | --- |
| Metadata | Shared codec/reducer, AEAD, account-wide cursor and active bootstrap validation; bounded preview only | Not a complete project. Cover material, non-Metadata families and unresolved/deleted heads fail closed. |
| Stage / StageOrder | Codecs and durable local apply owners check Metadata/Stage dependencies, history, tombstones, self-echo and owner-head CAS | Owners require IDB inbox and durable proofs; no online-only server projection/recovery path. |
| Legacy/Content Notes and Resolution | Codecs, causal apply, mixed-source/recovery owners and historical transport join exist | Production server-page dispatch/replay, complete dependency/source coverage and truthful readiness are unfinished; Note readiness remains negative-only. |
| Maps / Documents / Progress / Game | Canonical codecs and protected sync runtimes exist | Runtimes use durable protocol state and capability gates; not connected as production read-only owners. |
| Folder/catalog account events | Canonical account crypto decoder exists | No composed account-history owner; account events cannot be removed before validating the shared cursor. |
| Mixed history / transport | v3 pull, account registry and server-side ID0/ID1, family/device gates exist | Existing v10 recovery consumes persisted inbox; all-device readiness is not proved by Metadata preview. No capability PUT or ACK is permitted here. |

Specific boundaries: Legacy-v2 and Content-v3 Note histories have distinct
authenticated owners; mixed replay is not a production dispatcher. A Legacy
Resolution carried by v3 has an exact retained-identity join only against
persisted inbox evidence. Missing/dependent/orphan events are owner barriers,
not skippable pages. Multi-project account ordering and sequence continuity are
checked by Metadata preview, but no project can be projected past an unsupported
account event. Source device/header and AEAD identities are checked by existing
owners; this does not establish all-device readiness. ID0/ID1 support and
compression-reader gates remain server-controlled. Unknown versions/families,
deletions, conflicts and unsupported histories fail closed in their respective
owners; there is no uniform production project reducer. Read cancellation,
logout and AMK lock clear/abort the current Metadata preview, while the dormant
v10 lifecycle applies to persisted inbox work, not a live cloud session.

**Next minimum step:** settle a C21-compatible online source/proof contract for
replaying complete server history through the existing owners, including restart,
all-device/capability gates, mixed account ordering and safe refusal. Then
implement only the bounded production dispatcher/page replay slice authorized
by that contract (recommended model: GPT-6 Sol / High). No project-open UI or
readiness claim until complete family and recovery requirements are met.
Desktop offline-first/SQLite and Web
online-only/server-authoritative remain unchanged. `ready=false`,
`declarationAllowed=false`, `writerAuthorized=false`, Registration CLOSED,
PUBLIC RELEASE BLOCKED, C21/C22/C23/PF6.0/RC mandatory; Web progress remains
**89.36%**.

**MVP target: full Desktop feature parity in Web is mandatory.** Reuse the
existing shared Vue/TypeScript screens, Tiptap and Mind Elixir, business rules,
models, codecs and E2EE cloud protocol. The required user actions include
projects/folders, project organization and archive, ordered/completable stages,
project/stage text editing, Notes and their properties, mind maps and Note links,
writing goals, progress/statistics/history, the full Game Mode, settings and
personalization, and browser-supported import/export. Only genuine native-API
differences may use browser equivalents; Web Lite is not an MVP substitute.

**SUPERSEDED BY WEB ONLINE-ONLY DECISION:** the earlier plan for full offline Web
parity, durable IndexedDB copies of all user data, offline queues/retry, and
browser-only manuscript recovery. Historical acceptance records remain valid as
evidence of the existing developer-only workspace; they are not the target
product contract. IndexedDB v12 and its data are retained without automatic
cleanup or import. The local workspace remains a clearly labeled legacy
developer/test tool and is never merged into the cloud catalog.

Previous baseline SHA `6011d0d04cb1e7b75372c778de4e5cc2e615e931` was independently
accepted by run `40541798752` (**6/6 SUCCESS**). LEGAL.ACCEPTANCE.02 and M1.02
remain historically accepted. MVP6.0.M1.03 was cancelled by owner decision before
commit: **CANCELLED / OBSOLETE BY OWNER DECISION**; its partial uncommitted
v13/local map experiment was discarded explicitly and no v13 schema was
published.

## Feature matrix

Web status dimensions are separate: **user action**, **server path**, **server
storage**, **E2EE**, **Desktop format compatibility**, and **gate status**.
`PARTIAL` means only a bounded component exists; it is not an accepted user flow.

| Capability | User action in Web | Server path | Server stores data | E2EE verified | Desktop format compatible | Status / next work |
| --- | --- | --- | --- | --- | --- | --- |
| Cloud project catalog | IMPLEMENTED in developer account flow; IDs/count/limit, empty state, refresh, network error | `GET /api/v1/cloud/projects`, authenticated ordinary-user token via session | Server-owned catalog; no catalog persistence in IndexedDB | N/A: IDs and limits only | IDs are not names/content | Local fixture acceptance added; verify backend regression in prepush |
| Project names/content | NOT IMPLEMENTED in target online flow | Existing opaque event/metadata owners, not composed into UI | Existing server protocol only | Components exist; end-to-end Web read not accepted | Existing codecs provide candidate formats | FASTTRACK.01 blocked by C21 reader/recovery gates below |
| Stages and structure | NOT IMPLEMENTED in target online flow; legacy local CRUD remains dev-only | No Web cloud product flow | Not confirmed by this slice | Not verified in Web flow | Existing codecs/owners only | ONLINE.04 after accepted read path |
| Project/stage documents | Editor component exists; server flow NOT IMPLEMENTED | No writer connected | No Web document write in this slice | Existing local M1.02 is not cloud E2EE acceptance | Desktop codec exists; cross-client Web flow unverified | ONLINE.03 after writer gates |
| Notes and maps | Legacy/local developer experiences only | No cloud Note/Map writer connected | No Web write in this slice | Not verified as server flow | Existing codecs exist; Web compatibility unaccepted | ONLINE.04; keep C21 gates frozen |
| Progress and Game Mode | UI paths exist but are not target server-authoritative flow | Legacy plaintext routes are not permitted for E2EE data | Not verified | Not verified | Desktop models/codecs exist | ONLINE.05; no plaintext fallback |
| Account and legal access | IMPLEMENTED bounded login, legal acceptance and account key setup in developer flow | Auth/legal APIs | Server-owned identity/legal records | Key remains in client; no key sent with catalog request | N/A | Keep public registration CLOSED |

## Online critical path

### FASTTRACK.01 — next user action: open a server project

**Status: BLOCKED; no project-open code or mock success was added.** The
existing `GET /api/v3/sync/encrypted/pull` is the correct opaque transport, but
requires a registered device and negotiated v3 transport; if retained history
requires compressed ID1 frames, compression-reader support is also required.
The server also rejects pull when the account history includes
families for which that device lacks the corresponding accepted capability.
Because the feed has one account-wide sequence, filtering to a selected project
before validating earlier events and dependencies would violate the existing
source/history contract. `BrowserV10Recovery` is an isolated manual consumer of
already persisted inbox pages, not an online Web reader; the normal session does
not compose the production v10 dispatcher, page replay, dependency fetching,
family readers or lifecycle orchestration. `BrowserNoteReaderReadiness` remains
negative-only. The next concrete prerequisite is truthful C21.2.08 production
reader/recovery orchestration with complete required-family coverage and
accepted all-device readiness. Until that contract passes, do not declare reader
capability, ACK, or show a project ID as an opened project.

The backend's real API and security gates were exercised locally by the isolated
PostgreSQL 16 backend acceptance (261 tests plus encrypted-blob backup/restore);
those tests do not establish a browser-to-server project-open E2E.

1. **WEB.ONLINE.01 — architecture and server catalog.** Bind the developer-only
   Web account flow to the authenticated server catalog. Keep local test projects
   visibly separate. No content read or write is implied by an ID.
2. **WEB.ONLINE.02 — encrypted server read.** Retrieve opaque E2EE events and
   restore supported content in browser memory only after accepted reader,
   security and recovery gates. Reject unsupported histories without mutation.
3. **WEB.ONLINE.03 — encrypted document save.** Reuse Tiptap and existing codecs;
   send ciphertext through an accepted writer protocol. Show saved only after
   verified server confirmation and revision/protocol checks.
4. **WEB.ONLINE.04 — Notes, Maps and Stages.** Compose existing UI/codecs with
   accepted cloud owners. Preserve map-note links and stage dependencies; no
   plaintext API fallback.
5. **WEB.ONLINE.05 — Progress, Game Mode and Settings.** Add only supported
   server-authoritative encrypted flows with safe rejection of unsupported data.
6. **WEB.ONLINE.06 — Desktop ↔ Web acceptance.** Verify format compatibility,
   conflicts, recovery, authorization and cross-client preservation against
   isolated backend and PostgreSQL fixtures.

These stages may be refined after checking frozen C21/C22/C23 contracts. They
must not activate reader declaration, writer authorization, ACK, auto-bootstrap
or background synchronization before their exact gates pass.

## Safety and release boundary

- Desktop offline-first and SQLite behavior remain unchanged.
- The ordinary plaintext compatibility `/api` routes are not an E2EE fallback.
- `localProjects`, `localStages`, `localNotes`, `localDocuments` and the v12
  schema remain for existing data and developer tests. No automatic import,
  promotion, cleanup or cloud-catalog substitution is allowed.
- On network loss, show an error and retain current unsaved input in memory where
  possible. Do not claim persistence or restart recovery.
- LEGAL.ACCEPTANCE.02 remains required; legal text approval is separate.
- Official Web progress remains **89.36%** pending formal reassessment.
  `ready=false`, `declarationAllowed=false`, `writerAuthorized=false`,
  Registration CLOSED, PUBLIC RELEASE BLOCKED. C21/C22/C23/PF6.0/RC remain
  mandatory. No production VPS/database changes are authorized by this roadmap.

See [WEB ONLINE-ONLY architecture](WEB_ONLINE_ONLY_ARCHITECTURE.md) and the
current [checkpoint](../WORTA_CHECKPOINT.md).
