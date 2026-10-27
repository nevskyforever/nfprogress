# WORTA 6.0 — Web Online-Only roadmap

**Owner decision, 2026-10-27: WEB ONLINE-ONLY / SERVER-AUTHORITATIVE.** Desktop
remains offline-first on SQLite with optional cloud sync. Web requires server
connectivity. E2EE remains client-side; the server is authoritative for
persistent user data and stores opaque ciphertext plus required protocol
metadata. LOCAL-FIRST is still mandatory for Codex development and acceptance;
it does not require offline-first runtime behavior in Web.

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
