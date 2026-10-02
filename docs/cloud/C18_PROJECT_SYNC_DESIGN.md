# C18 Complete Project Sync — contract freeze (C18.1)

**Status:** locally frozen design; no production implementation, migration, dependency, or account-format activation. C18 remains open and WORTA ROADMAP SCORING v1.0 remains 77.0%.

This contract is based on the current `engine.Project`/`Stage`, the SQLite migrations through 024, the desktop project/document/Notes services, the C15–C17 sync path, and the C17 conflict design. It defines what C18 must prove, not a claim that any C18 entity already syncs. The C11 `crypto_version=1` and `aad_version=1` derivation/AAD, historical Note plaintext v1 and resolution v2, protocol-v1 objects, and the irreversible transport-v2 cutover remain unchanged and readable. The server remains blind to all project plaintext and metadata. Local-only projects never acquire a cloud binding through discovery or background reconciliation.

## 1. Vocabulary and invariant boundary

The classifications below are exclusive:

- **A — synced canonical entity:** an independently identified, E2EE cloud authority with causal history.
- **B — synced derived/dependent data:** travels within or is rebuilt atomically from an A/E authority; it has no second cloud writer or independently ACK-able event.
- **C — local device-specific state:** never send raw values or use them to decide a cloud winner.
- **D — rebuildable projection/cache:** recompute from canonical inputs; never publish as a competing authority.
- **E — account-scoped portable entity:** E2EE canonical account catalog/game fact, not attached to an invented project slot.
- **F — explicitly deferred:** no safe portable codec or ownership proof exists. Retain locally, report an exact blocker for an affected connected project/account, and do not claim complete sync for it. F is not permission to omit user data silently.

An event is **ACK-eligible** only after an atomic, durable, verified apply, exact self-echo reconciliation, or durable preservation of every conflicting version under a defined entity contract. ACK still advances a single contiguous account sequence; “yes” in the matrix means an event may establish its own proof, not that it bypasses an earlier unproven sequence. Dependencies may turn an otherwise valid event into an orphan. Server sequence, wall-clock timestamps, device ID, upload order, and local SQLite revision never choose a content winner.

## 2. Authoritative entity matrix

Abbreviations: P = project ID, S = stage ID, A/c = authenticated account ID, `→` = dependency. “Causal” means a new immutable event, parent proof, conflict preservation, and exact replay. “Txn” means one SQLite transaction with dependent materialized rows. Text/JSON is a compression candidate only after the versioned frame gate in section 9. Every A/E row is client-side E2EE.

| Current datum; class | Authority, stable identity, scope and dependencies | Mutation, conflict unit, tombstone, ordering, ACK | Compression; migration; portable/local boundary |
| --- | --- | --- | --- |
| Project name, rename, goal/infinite/unit, deadline, status, personal goal, auto-freeze, streak enablement, work method, stage enablement and combine-map setting — **A: project metadata** | `projects`/`engine.Project`, P within A/c; cloud binding and metadata genesis required. Only allowlisted user choices travel. Stage/total-dependent changes validate child state. | Causal create/update/tombstone; whole mutually constrained metadata record is one conflict unit. Concurrent rename/edit/delete preserves versions. No independent field LWW. No implied reordering. ACK yes after proof. | Text/JSON yes; migrate `projects.payload_json` and model fields. `work_method` is portable preference, while external `synch` details are C. `updated_at` is evidence, not precedence. |
| Project cover reference/removal — **B** | Allowlisted field of the project metadata authority, P → immutable encrypted cover blob ID. | Reference changes conflict as metadata; removal is an explicit null reference, not deletion of blob history. Txn apply only after blob availability/proof; ACK with metadata. | Tiny metadata; migrate local `cover_image` to new blob plus reference; no raw data URL in the metadata event. |
| Encrypted cover bytes — **A: cover blob** | Immutable blob ID, P within A/c, existing `project_cover` E2EE context; metadata reference depends on it. | Upload immutable exact bytes before publishing reference; same ID/different bytes rejects. No mutable blob overwrite. Old blobs retained across conflicts; eventual physical cleanup requires a separate retention contract. The blob API has no sync-sequence ACK; its referring metadata event is ACK-eligible only after blob availability and authentication proof. | JPEG is normally `none`; source is local `cover_image`. Server knows kind/size and opaque IDs, never image content. |
| Stage record, name, goals/status/settings — **A: stage** | `stages`/`engine.Stage`, S within P/A/c; parent project metadata must be applied. | Causal create/update/tombstone; stage record conflict unit. Delete vs edit is a preserved conflict. No cascade without child proof. ACK yes after parent and child constraints. | Text/JSON yes; migrate `stages.payload_json`; `parent_project_name` is D from current project name. External source details are C. |
| Stage order — **A: project stage-order entity** | `stage_order`, stable identity `(P, stage_order)` within A/c, referring only to live S IDs of P. | Causal full permutation with exact membership/head CAS; concurrent reorder is a conflict, never timestamp sorting. Removal requires stage tombstone proof. Txn with structural apply; ACK yes after all references are proven. | Small JSON; migrate `stage_order`. |
| Progress entry facts — **A: progress entry** | `progress_entries`/`engine.Note`, `entry_id`, P or P/S; input includes absolute new total, delta, unit and writing time, plus proven preceding progress head/base. | Causal add/correction/tombstone; conflict unit is the progress chain segment, not an independently writable scalar total. Concurrent absolute totals or delete with descendants preserve branches and require explicit rebase/resolution; no summation or LWW. `progress_order` follows proven chain/order. ACK yes only when base and descendants remain valid. | Numeric/JSON modest; migrate rows plus `progress_order`; local timestamps are facts, not arbitration. |
| Progress order positions — **B** | `progress_order`, materialized order of the proven P/S progress chain. | Updated atomically with entry/chain resolution; no independent reorder writer, tombstone or ACK. | Small derived relation; migrate and verify against entry order. |
| Current total, percent, remaining, today goal, planning date, `project_plan`, added today and displayed statistics — **D** | Derived from ordered progress entries, goal/unit, deadline, settings and writing-day rules. | Recompute in the same apply transaction or deterministically after it; never receive an independent total event. ACK belongs to source event. | No cloud payload; migrate by recomputation, retaining legacy source snapshots until verified. |
| Project HTML Notes — **A: Note** | `notes`, Note ID within P/A/c; current C15/C17 codec applies only to project HTML Notes. | Existing v1 ordinary / v2 resolution histories stay readable. New C18 writer uses a gated codec; causal Note upsert/delete, sort order and full Note metadata remain a single Note conflict unit. ACK via existing proven rules. | HTML/JSON yes; existing SQLite rows and encrypted history are migration sources. No rewrite of old objects. |
| Stage Notes and project/stage plain Notes that are not map-derived — **A: Note** | Same `notes` table and ID, with authenticated P/S and content/source type. Stage must exist. | New gated route and codec; causal upsert/delete/order. Delete vs edit conflict. Txn with stage FK and native guard; ACK yes after stage proof. | Text/JSON yes; migrate current `source_type=project` rows including `content_format=plain`; unsupported rows stay blocked until codec exists. |
| Map-derived Notes, including node text and Note annotations — **B** | `notes.source_type=mindmap` is a materialized view of the owning project/stage map. Node ID and map owner form identity; user-editable title/checklist/color/pin/archive/tags/order/metadata associated with such a Note move into the map authority, rather than a second Note event. | Note-editor text changes update the map node; annotation changes update map-owned annotations. Delete removes the node under map rules. Map and derived Note rows change in one Txn. No independent Note cloud event or ACK. | Map JSON yes; migrate node text plus existing map-derived Note annotations once, checking identity/collisions. Missing node/annotation proof blocks. |
| Project mind map — **A: map** | `projects.payload_json`/`engine.Project.mindmap_data`, identity `(P, map)`, node IDs inside one tree. | Causal full-map version initially; graph/text/annotation conflict unit is the map. Delete is explicit map tombstone. Combined view is not an extra map. ACK after atomic map + derived Notes apply. | Structured JSON yes; migrate map and `mindmap_updated_at` without using timestamp as winner. Bound nodes/depth/references. |
| Stage mind map — **A: map** | `stages.payload_json`/`Stage.mindmap_data`, identity `(P,S,map)`; requires stage. | Same map contract; combined editing may update project and several stage maps in one Txn with all expected heads, or preserve all on failure. ACK only for each completely proven event, never partial combined apply. | Structured JSON yes; migrate each stage map. |
| Combined map display — **D** | Rebuilt by `compose_project_mindmap`/`split_combined_project_mindmap` from the project and stage map authorities. | No independent event, tombstone or ACK. | No separate cloud payload. |
| WORTA document content/title/scope — **A: document** | `documents`, stable document ID and unique scope `(P,S-or-project)`; owner project/stage required. `content_json` is Tiptap JSON and `content_format` is explicit. | Causal create/update/title/scope move/tombstone. Document including title/content is one conflict unit; scope move locks old/new relation in one Txn. External file edits become explicit local import proposals, not silent cloud writes. ACK after document + relation proof. | Structured text/JSON yes; migrate SQLite, and `documents.json` only through its existing one-time migration marker. Validate editor schema, depth and references. |
| Known document extension keys — **F until codec admission** | `documents.extensions_json` currently permits arbitrary keys; `legacy_flag` in a migration test is not a supported portable field. | Preserve verbatim locally. Any nonempty unsupported extension on a connected document blocks complete sync and mutation capture rather than being dropped. No ACK for an incomplete document. | No blind compression/upload; source `extensions_json` and legacy `documents.json`. New key admission requires a versioned allowlist and migration proof. |
| Local Word/Scrivener binding, path, source ID, hash, dirty/sync state — **C** | `document_bindings`, `project_bindings`, `synch`, `last_synch`; device filesystem ownership. | Reattach per device by explicit user action. External change versus cloud document produces a local conflict/import proposal; never overwrite either source automatically. No cloud tombstone or ACK for a raw binding. | Never upload paths or raw binding payloads. Migrated only within that device. |
| Project folders and folder order — **E: account catalog folder** | `project_folders`, folder ID within A/c; not a project slot. | Causal create/rename/tombstone and order-permutation; concurrent edits preserve versions. Folder delete cannot silently remove membership. ACK after account scope and affected relation proof. | Small text/JSON; migrate folders and positions. |
| Folder membership — **E: account catalog relation** | `project_folder_members`, identity P within A/c, referring to an existing folder and a project bound to the same account. | Causal set/remove (null tombstone). Conflict on concurrent moves or folder delete. Apply relation and affected folder/project checks in one Txn; ACK after both ends exist. | Small JSON; migrate `folder_id`/membership, detecting mismatch. |
| Project order — **E: account catalog order** | `project_order`, account-scoped ordered list of explicitly cloud-connected P IDs. Local-only P positions remain local. | Causal exact-list/permutation with membership CAS; concurrent reorder is a conflict. Project add/remove must update catalog relation atomically. ACK after all referenced cloud projects have valid lineage. | Small JSON; migrate only connected IDs, preserving local-only ordering locally. |
| Positions of local-only projects — **C** | Local part of `project_order`; these P IDs have no cloud binding. | Reorder locally; no cloud event or ACK. | Never upload or turn such a project into a cloud project implicitly. |
| `project_last` and current selection/navigation — **C** | `project_metadata.project_last`/root `last`; current device UI context. | No cloud event/ACK; reconstructed locally on import if needed. | Never upload. |
| Project/stage streak and game transition facts — **A: project game action ledger** | New immutable E2EE action IDs with P/S, source progress/completion ID where applicable, effective writing day and rule version. Current `game_state.project_game_state`, entity streak fields and `domain_events` supply legacy candidates. | Causal append/correction/compensating event; no mutable aggregate overwrite. Concurrent noncommutative actions require preserved conflict and explicit resolution. Delete of source progress cannot silently erase awarded effects. ACK after referenced action/progress and atomic projection apply. | Small JSON; legacy snapshot must become an explicit authenticated genesis candidate before subsequent actions. |
| Account-wide game balances, rewards, inventory and global streak facts affected by projects — **E: account game ledger** | Immutable E2EE account action IDs, referencing project actions when earned. `game_state.gamer`, global streak and notifications are migration sources; account-scoped transport required. | Append/compensate with idempotent reward IDs; concurrent spend or noncommutative changes need causal conflict, no duplicated reward. ACK after referenced project action and one Txn that updates projections. | JSON candidate; only portable user-visible game facts, not execution attempts or diagnostic fields. |
| Streak counts/status/freezes, `project_game_state`, game balances and materialized reward views — **D** | Rebuild from versioned game ledgers and canonical progress/settings. Current state alone is **not** deterministically derivable from progress: freezes, manual enablement, bonuses, rewards and other game actions are separate inputs. | No independent mutable-aggregate event/ACK. Legacy snapshot is a migration input, not permission to publish current state as a forever-replacing aggregate. | No separate cloud payload. |
| Game event processing attempts, local notifications/read state, domain-consumer diagnostics — **C** | `domain_events` status/attempt/error and local notification UI. | Per-device execution state; no raw cloud event/ACK. Portable rewards are E ledger facts instead. | Never send diagnostics. |
| Unknown project/root/progress extensions — **F** | `project_extensions`, `project_metadata.root_extensions`, arbitrary legacy object attributes. | Preserve locally. Unknown nonempty content on a connected entity is a typed complete-sync blocker until field ownership, codec and migration are defined. No partial ACK representing a lossy copy. | No blind upload; distinguish from known device provenance below. |
| Unrecovered document migration payloads — **F** | `document_migration_orphans`, keyed by source record and retained locally until owner/scope/content can be proven. | No cloud event or ACK while orphaned. Blocks an affected document's complete migration; recovery requires an explicit, lossless document admission path. | Never blind-upload the recovery JSON or erase it during migration. |
| Migration, app/version and transport provenance — **C** | `migration_sources`, `document_metadata.documents_json_migration`, `application_metadata`, `mirror_state`, `storage_ownership`, cloud cursors/bindings/receipts and local diagnostics. | Remain local durable evidence; never interpreted as portable user content, never sent raw. | No cloud compression; do not erase during migration. |

Project/stage `created_at`, completion date and writing timestamps are portable historical facts when admitted by the owning codec. They do not establish causal authority. User settings outside project/account-game/catalog scope remain outside C18; an entity dependent on such a setting must carry a stable rule version or fail closed if its result cannot be reproduced.

## 3. Single-source-of-truth and transactional rules

**Maps and map Notes.** Current `ProjectNotesService` writes map-derived text back into `mindmap_data` and `_sync_map_notes` refreshes Note rows from map nodes. Therefore the map tree owns node text. C18 also places map-derived Note annotations in a map-owned versioned annotation collection, migrating existing Note fields exactly once. A Note row is a local query/editor projection. Map apply or local map-Note edit must atomically update map payload, annotation collection, derived Note rows, causal head, inbox state and conflict evidence. A structural conflict preserves complete maps and annotations; no automatic tree merge. A combined map edit touching multiple owners is all-or-nothing locally and may only publish after each expected map head is proven.

**Progress.** `progress_entries` are the durable user action history; `total`, percent, plan and statistics are projections. Because an entry records an absolute new total as well as a delta, two devices' entries are not safely commutative. The cloud event records its prior progress head/base and resulting entry. On a divergent head, preserve both branches. Deleting an entry with descendants requires an explicit resolution/rebase covering affected descendants, not silent recomputation that changes historical actions.

**Documents and external files.** `documents` owns portable WORTA text and title. `document_bindings`/`project_bindings` and external files are device-specific peers. Reattachment checks a local file hash and the authenticated document head, then offers an explicit import/conflict action. Neither a file modification time nor a cloud timestamp wins. The cloud never receives an absolute path, local file ID, or raw binding JSON.

**Game.** The current `game_state.project_game_state` snapshot cannot be reconstructed from progress alone. C18 therefore requires immutable project and account game action facts, including a one-time legacy genesis candidate, before it can claim cross-device convergence of game effects. Materialized `Gamer`/streak state is rebuilt from these facts under a fixed rules version. Applying a progress event and its resulting reward facts, projection, and deduplication evidence is one local transaction. A side-effect replay never grants the same reward twice.

## 4. Metadata genesis for C16-connected projects

The durable state machine is per `(account_id, project_id, device_id)` and is separate from an entity's later causal head:

```text
legacy_local -> metadata_candidate -> genesis_published
                                   \-> genesis_conflict -> resolved -> normal_causal_history
genesis_published -------------------------------> normal_causal_history
```

`legacy_local` means the C16 binding is verified but no authenticated metadata ancestor is known. An imported shell's user-entered name is a local candidate, not a server value. `metadata_candidate` is an immutable, locally durable snapshot of **all allowlisted metadata**, the source project row identity, account/project/bootstrap/device lineage, and an explicit unsupported-field preflight. It is created before network work. An existing candidate is reused on restart; a new local edit becomes a new local generation and cannot silently replace a candidate already being published.

A genesis event uses a fresh canonical event UUID, `entity_type=project_metadata`, entity ID P, account/project/device binding, logical revision 1, generation 1, `parents=[]`, transport operation `upsert`, payload operation `create`, and the authenticated candidate snapshot. Its outbox/event-object identity and bytes are immutable after sealing. Retry uses exactly the same event ID, metadata and ciphertext; changed bytes under that ID reject. A self echo proves its local candidate/outbox/receipt/inbox match, records an applied genesis head, and never overwrites the local project a second time.

Two independent legacy candidates may both publish revision-1 events with `parents=[]`. This is a **migration-genesis conflict**, not ordinary C17 siblings with a fabricated common parent. The receiver durably preserves every full candidate and tombstone, its own local candidate, source lineage, immutable object and exact tip set. A distinct local value cannot be replaced by the first remote genesis. Even equal names do not prove identical full metadata or shared history. A versioned genesis-resolution event lists the complete sorted genesis event set as parents, carries the selected or manually composed full metadata result, and uses `revision=max(parent revisions)+1`. The user explicitly chooses or composes the result. C17's immutable tip, exact-set CAS, publication, ledger, self-echo and ACK principles are reused with new metadata-specific validation and a distinct genesis-group kind; Note-only C17 tables/codec are not repurposed.

An inbound genesis enters the durable inbox before decryption. AEAD, frame, codec, account/project/device/registration/bootstrap lineage, project ID and candidate provenance are checked before apply. Its inbox becomes `applied` only after the local metadata row, head/history and evidence commit together; a fully preserved genesis conflict may become `conflict_preserved`. `received`, missing lineage, unknown parent, malformed or unresolved preservation evidence remain ACK-blocking. A later event with parents not yet present is an orphan, retained for fair bounded retry. Resolution is ACK-able only after exact local tip-set/generation proof and complete apply ledger. Sender-local group ID/generation are never equated to a receiver's local IDs.

Second-device import creates a shell and candidate under verified remote lineage. It pulls and authenticates metadata before treating any remote name as authoritative; conflicting local values are preserved. Following a resolved genesis, ordinary rename/update events require the current authenticated parent head and monotonic causal revision. Concurrent renames or delete/edit events preserve separate versions, with no timestamp or upload-order winner. A metadata tombstone represents explicit project deletion intent and cannot physically delete children while unresolved or unapplied descendants exist. Loss of HTTP response, restart at every state, and duplicate pull/upload must converge by immutable replay, never by issuing a replacement event ID.

## 5. General C18 causal event and scope contract

New C18 codecs require three distinct proofs:

1. **Transport/envelope:** authenticated account, registered device, exact project or account scope, immutable event UUID, server sequence, operation, bounded revision, crypto/AAD versions, nonce/ciphertext, receipt and cursor. Existing C9/C15 metadata remains opaque. A new account-scope route is required for E entities; it must identify the authenticated account directly, not invent a `project_id` or bypass project registry checks for project entities. Project-scoped objects retain the C11 object context. Account-scoped E objects require the **new domain-separated, versioned account-object key/AAD context** specified below, with account/entity identity and no fake project ID; it must be implemented and independently tested before C18.4 emits account events. Historical C11 derivation/AAD remains byte-for-byte unchanged.
2. **Entity payload:** inside AEAD, exact canonical type and stable ID, `entity_codec_version`, project/account scope, event ID, operation (`create`, `update`, `tombstone`, or explicitly typed resolution), sorted unique causal parent IDs, logical revision/generation, dependency IDs/heads, and allowlisted portable payload. Every field that duplicates the transport descriptor must match it exactly or by an explicitly frozen canonical equivalence rule. Unknown versions/keys reject.
3. **Transactional apply:** entity-specific schema and relational validation, local causal head/tip proof, immutable replay check, conflict preservation or exact mutation, dependent projections, receipt/self-echo evidence and inbox transition in one `BEGIN IMMEDIATE` transaction. No renderer-only apply, unguarded SQLite write, or ACK on mere decrypt.

Ordinary single-parent event revision is parent revision plus one; genesis has no parent and revision 1. A conflict resolution names the full sorted current tip set and uses `max(tip revisions)+1`; its group generation is a CAS proof local to the device. A migration-genesis resolution is explicitly typed and may have parentless generation-1 tips. Entity IDs never change on rename. A scope move is an authenticated relation change, not an ID rewrite. C17 Note-v1/v2 bytes and their multi-parent resolution rules remain untouched; new Note writes after the C18 gate use a new codec rather than reinterpret the historical payload.

### Account-object E2EE namespace

For E entities, the account-object context version is 2 and the envelope advertises `crypto_version=2`, `aad_version=2`. It retains XChaCha20-Poly1305-IETF, a fresh 24-byte nonce and the account AMK, but it **does not reuse** C11 project-object HKDF/AAD bytes. Its identity tuple is `(canonical authenticated server user UUID, literal scope kind "account", entity ID, entity type)`; each field is a nonempty Unicode-scalar UTF-8 string with the C11 bounds (user/entity ID 512 bytes, type 128 bytes), and scope kind is exactly `account`. Encode the tuple in that order as four-byte unsigned big-endian length plus bytes per field. The object-key HKDF uses SHA-256, AMK IKM, UTF-8 salt `worta/hkdf/account-object-key/salt/v1`, and info `worta/account-object-key/v1` followed by `0x02,0x02` and the encoded tuple. AAD is `worta/account-object-aad/v1` followed by `0x02,0x02` and the same tuple. Account/project cross-scope decryption is therefore impossible by construction; the authenticated user UUID must also match the server scope and local account binding. This is a **new** namespace, not a change to C11 version 1 or an approved production implementation. C18.4 must add independent cross-language vectors and backend envelope acceptance before first E writer activation.

## 6. Dependency graph, orphan retry and ACK

```text
authenticated account + registered device + explicit project binding
  -> project metadata genesis/head -> stage head -> stage Notes/maps/documents/progress
                            |          -> stage order
                            -> project Notes/maps/documents/progress
                            -> cover blob -> metadata cover reference
account catalog folder + authenticated bound project -> membership -> account project order
progress/completion action -> project game fact -> account reward fact -> projections
portable document head <-> explicit local external-file import proposal (local only)
```

An event whose authenticated parent, project/stage, blob, folder or action dependency is absent is a durable `orphan`, not an empty object or implicit create. The inbox and opaque object remain unchanged; bounded keyset pagination retries orphans fairly beside new events. An unsupported entity/frame is retained with a typed blocker, not skipped to advance ACK. The contiguous ACK prefix advances only across applied or completely preserved conflicts. No multi-entity operation may partially apply: parent removal plus child tombstones; map plus derived Notes; combined map owner changes; document scope move; folder deletion plus membership outcomes; progress plus dependent game facts; cover reference plus availability proof; and resolution plus all heads/ledgers are each atomic locally. Network publication may span objects, but each durable object is immutable and dependent events wait for their predecessors.

## 7. Tombstones, conflicts and retention

Every canonical deletion is an authenticated causal tombstone with event ID, parents, scope, revision and the minimum prior identity/reference proof. A tombstone is retained in encrypted history. Delete versus concurrent edit creates a preserved conflict; neither branch physically erases the other. Note deletion keeps C17 semantics for old history and extends only under a new codec for new routes. Document and map deletes remove their visible projection only after their own exact-head proof. Progress-entry deletion preserves descendants until an explicit rebase/resolution. Cover removal changes a metadata reference and does not delete an immutable blob. Folder deletion must resolve membership explicitly; membership removal is a relation tombstone. Stage/project tombstones require a complete, causally closed child manifest or equivalent per-child tombstone proof, including Notes, maps, documents, progress, covers and game references. Unknown/unapplied child events or unresolved conflicts block physical cleanup and ACK of the destructive parent operation. Local physical cleanup is permitted only after durable tombstone apply, complete child proof, conflict resolution, and a separately defined retention/restore policy. C18 does not introduce server history pruning or encrypted-object compaction.

## 8. Portable-field admission and migration

The v1 C18 allowlist consists of the typed user-visible fields assigned to A/E in section 2, including Note tags/checklist/color/pin/archive/order/metadata only under a validated Note codec, map nodes/annotations, Tiptap document title/content/format, cover reference, stage/project choices, catalog organization, progress facts and game action facts. Computed `today_goal`, `remaining`, plan, statistics and `parent_project_name` are D. `synch`, `last_synch`, external paths/hashes, `project_last`, cursors/attempts/errors, migration markers/sources and application-version data are C; unrecovered document migration payloads are F. `project_extensions`, `root_extensions`, `progress` extras and `documents.extensions_json` have no general portable allowlist today: nonempty unknown values are F and block the affected cloud migration until reviewed. A known diagnostic key can be excluded only by an explicit versioned rule with a lossless local retention test. A new portable key requires its own exact codec version, limits, migration and cross-device test. Blind serialization of permissive JSON is forbidden.

The migration copies no entity into cloud before full local preflight, source-authority check, lineage check and durable candidate capture. Existing C15/C17 encrypted Note history is preserved byte-for-byte. Historical document `documents.json` import uses its one-time local marker and keeps migration orphans inspectable. An unsupported item blocks “complete” for its project rather than presenting a partial project as fully synced.

## 9. Authenticated content frame and compression gate

The **new C18 frame version 1** is plaintext *inside* authenticated encryption: the existing C11 AEAD envelope for project-scoped objects and the separately versioned account-object context above for E entities. An explicit authenticated event-format/codec route selects legacy decoding or framed decoding; the frame has an unambiguous domain-separated magic, checked only after AEAD authentication. No first-byte sniffing decides the route. The frame contains exact `frame_version`, `entity_codec_id/version`, `compression_id`, declared uncompressed byte count, bounded payload byte count and payload bytes. `compression_id=0` means `none`; IDs 1–255 are reserved for separately frozen future algorithms, with no guessed fallback. The complete frame is authenticated by AEAD. A legacy event's historical codec/version route continues directly to its frozen decoder. New framed Note events use a new codec identity; legacy Note-v1 and resolution-v2 remain directly readable. A frame does not redefine C11 `crypto_version=1`, `aad_version=1`, object-key derivation, AAD, or protocol-v1.

The sender validates and canonicalizes an entity payload, optionally compresses those exact bytes, frames them, then encrypts. The receiver authenticates, parses exact frame fields and permitted codec/algorithm, verifies declared lengths, incrementally decompresses under an entity-specific maximum output and aggregate memory/time/work budget, then parses bounded-depth/count canonical structured data and revalidates all duplicated identities and dependencies. Decoder limits include output bytes, input bytes, expansion ratio, allocation, frame count, and algorithm window/dictionary where applicable; unknown dictionary or concatenated/trailing frames reject unless later explicitly versioned. Malformed/truncated/oversized data fail closed with a durable typed blocker and no ACK. Already-compressed JPEG/DOCX-like media default to `none` unless measured savings exceed framing and resource cost. Compression of attacker-influenced content beside secrets requires a ciphertext-length side-channel review.

No algorithm or package is selected here. **EXTERNAL LICENSE VERIFICATION REQUIRED** for the exact runtime/build/test package versions, transitive tree, GPLv3 compatibility, notices and Desktop/Web/Android distribution obligations before any new dependency is admitted.

## 10. Capability and compatibility gate

The existing account transport-v2 cutover is irreversible. It cannot silently start delivering new account-scope descriptors or framed C18 entities to older v2 clients. C18 requires a **new explicit account writer/read-format gate** (conceptually mode 3) with server/client capability negotiation for the descriptor route, entity codec set and frame/compression set. Project-scoped events still require an explicit cloud project slot and binding; account entities use a separately authenticated account route. The server validates only opaque descriptor/version/size/lineage, not plaintext. No automatic upgrade occurs in C18.1. Before activation, every participating device must demonstrate reader support for all retained old history and the new formats, or be explicitly retired under a separately approved workflow. Old writers/readers fail closed against the new mode; there is no downgrade-on-failure. Mode 3 readers retain legacy protocol-v1 Note objects, transport-v2 Note v1/v2 objects and their exact crypto/AAD contracts. New event types or frames are not emitted until the mode is safely activated. Unsupported objects stay durable and ACK-blocking.

## 11. Implementation sequence (one C18 stage, +7.0 only on closure)

Each completed implementation slice may receive a factual local checkpoint update. None receives separate roadmap points or `CLOSED` without independently verified remote acceptance. “Both Actions” means Cloud backend tests and SQLite sync substrate tests, with changed path filters and curated test commands extended before claiming coverage.

| Slice / prerequisite | Exact scope and production layers | Focused proof; expected Actions |
| --- | --- | --- |
| **C18.2 Metadata durable substrate** / this contract | Forward-only SQLite candidate/history/intent/conflict/ledger and protected native metadata apply; versioned metadata codec and frame-v1 with `compression_id=none`; opaque backend descriptor allowlist and dormant gate. No UI activation. | C16 populated upgrade/reopen, exact replay, rollback, scope/AAD/tamper, two parentless genesis candidates, framed/legacy dispatch, no silent winner; **both Actions**. |
| **C18.3 Metadata migration/integration** / C18.2 | Explicit candidate capture, first upload, second-device shell import, self echo, rename/tombstone/resolution UI and bounded runtime under gated mode. | Two-device divergent names, lost responses, restart, deletion guard, ACK fairness, account switch; **both Actions**. |
| **C18.4 Structural/catalog entities** / metadata head + account route | Stage/structural events, stage order, project folders/membership/order, parent dependency and delete manifest; implement the frozen separate account-object key/AAD contract before account E writers activate. | Concurrent rename/reorder/delete, local-only ID exclusion, unknown child orphan, account lineage, account/project crypto-context separation; **both Actions**. |
| **C18.5 Content/action entities** / C18.4 | Stage/plain Notes, map with derived Note annotations, documents, progress chain and project/account game action ledgers, each with protected transactional apply. | Cross-language codecs, map atomicity, document scope, progress divergence/rebase, reward once, legacy migration and unknown extension blockers; **both Actions**. |
| **C18.6 Blob/local integration boundary** / metadata + documents | Encrypted cover blob/reference lifecycle, missing blob orphan, local external-file reattachment/import conflicts, no raw path transport. | Blob exact replay/replace, missing bytes, crash, Word/Scrivener conflict and path-leak assertions; **both Actions** where code changes. |
| **C18.7 Compression implementation** / frame-v1 + mode gate + codec set | Add an algorithm ID to the already deployed versioned frame only after benchmark/license gate; cross-platform bounded decoders and compression policy. | Legacy golden history, Desktop/Web/Android vectors, bombs/truncation/window/memory limits, no ACK on failure; **both Actions**, relevant platform jobs. |
| **C18.8 Complete-project acceptance** / all above | Real two-/three-device PostgreSQL and distinct file-backed SQLite project with metadata, stages/order, all Note routes, maps, documents, progress/game, cover and account catalog; conflicts, tombstones, restart and lost responses. | Exact supported-entity convergence and retained conflict evidence, mandatory no-skip headless suite, both workflows on published SHA; **both Actions**. |

## 12. Contract consistency check

All initial-audit categories appear exactly once in the matrix; logical map text, totals, documents and game projections have one canonical owner. Every A/E deletion has a tombstone/dependency rule. C16 genesis has a distinct parentless migration conflict and cannot choose a winner implicitly. Paths and diagnostics are C, not cloud metadata. Unknown extensions are F and block a false “complete” claim. Old Note histories and crypto/AAD contracts remain readable, while new formats require an explicit gate. No implementation-blocking **OPEN DESIGN BLOCKER** remains at the contract level; package choice, exact byte encoding and numeric resource caps are deliberately required gates for their respective bounded implementation slices and must be frozen before writers activate.


## 13. C18.4.02 additive structural integration freeze

This addition activates only explicitly requested project-scoped Stage migration; section 10's mode-3 gate, C11 project crypto/AAD v1 and the opaque backend remain unchanged. Account-object v2/catalog and C18.5 content are not activated.

Stage/order ordinary events retain codec v1; full-tip decisions use codec v2 with exact sorted unique 1..64 parents and max(parent revision/generation)+1. Outer `WORTA-C1` frame remains v1, compression none, codec IDs2/3; byte10 and payload version must both equal1 or2. Historical v1 goldens remain readable. Remote decisions require bounded authenticated parent-lineage evidence for the visible local snapshot; unrelated local candidates remain preserved pending a local explicit decision. Native prepare CAS requires every current tip and exact local decision evidence; later C makes R(A,B) a preserved stale branch, requiring another explicit full-tip decision.

Schema029 stores immutable per-project migration generations, exact candidate/source/event identities and order header/permutation, local-order import evidence, later-creation companion intents and decision local snapshots. Only explicit begin captures source structure (≤32 Stages). Existing local mutations stay local before activation. All migration Stage genesis intents commit atomically; order is prepared only after original Stage ledger evidence plus current reconciled live projection proof. Order dependency references freeze on first prepare; sealed bytes never mutate. Later Stage creation preserves a companion order intent and uses the existing metadata writer transactionally if `stages_enabled` must change.

The production mode-3 cycle durably pulls opaque descriptors/ciphertext, authenticates/dispatches Notes, metadata, then Stage/order, and finally requests the shared contiguous ACK. Invalid scope/crypto/frame or missing dependency remains durable and ACK-blocking. Bootstrap imports require an authenticated project metadata shell; local structural candidates are retained for explicit reconciliation. No background login/unlock/open/pull discovery initiates migration.

Order writers bind exact current live Stage membership/heads. Order readers may prove frozen live references through authenticated causal ancestry after portable edits: all current and referenced tips must be covered within one account/project/Stage; maximum256 distinct traversed ancestry nodes per Stage. Unknown references, unrelated branches, live-membership mismatch, current tombstones or limit exhaustion remain typed durable blockers. Server sequence and timestamps never prove membership.

A selected Stage tombstone can be causally reconciled while physical cleanup remains unauthorized. Children (Notes/maps/documents/progress) and Stage-order membership are preserved; no destructive Stage removal/order transition or ACK is granted without complete child-manifest proof. The UI distinguishes this selected causal head from unresolved conflicts and from future safe cleanup. `parent_project_id` is validated local/derived ownership evidence, never a new portable Stage field. Migration/order/tombstone bounds and test evidence are recorded in `docs/WORTA_CHECKPOINT.md`; C18.4 and C18 stay IN PROGRESS at77.0%.


## 14. C18.4.03 presentation and local support diagnostics

This organizational slice inserts friendly UX/application diagnostics before **C18.4.04 account catalog/account-object v2 contract + reader readiness**. It does not amend the entity/protocol/schema/crypto contracts, transport cutover, C17 history, full-tip decision validation or contiguous ACK proofs. Official progress remains 77.0%; C18/C18.4 stay IN PROGRESS.

A shared typed presentation maps stable session/project/metadata/Stage states and blockers to human title, explanation, severity and action. Unknown codes have a deterministic fallback and remain available in collapsed technical details. Protocol jargon and raw JSON are not primary UI; internal machine values remain intact.

Shared schema-v1 local events carry UTC, severity, subsystem, operation, allowlisted event/error/status code, a generated diagnostic UUID and bounded scalar context. Desktop persists separately at `diagnostics/support.db`: latest 512 events / 512 KiB content; SQLite physical cap 2 MiB, transactional append, 64-event/150-ms frontend batches, blocking-worker native commands. A bounded memory queue/tail is best effort on abrupt exit; diagnostics failures do not affect business results or ACK. Context ingress and export reconstruction exclude messages/stacks, secrets, token/key/nonce material, names/content, application payloads and meaningful IDs. Debug is not persisted by default. No telemetry or automatic/cloud upload.

Representative application, encryption, project, Stage, document, migration, game and developer paths are instrumented. Explicit migration/decision → retry → sync-cycle results share correlation. Existing result counts classify pull/upload, metadata/Stage apply/conflicts/orphans/blockers and ACK advancement; no low-level/per-keystroke tracing. Settings exposes count/size/last UTC and explicit Copy/Export/Clear. Copy includes latest up to 100 events / 60 KiB plus safe header and truncation marker; export includes all retained sanitized JSONL after user-selected save; clear vacuums only this journal. Headers carry actual version/build/runtime/OS/schema/export UTC and inclusion counts.

Developer streak restoration now supplies the required native `{payload: ...}` envelope (also the adjacent test-series action), with optional generated correlation. The native typed request/game logic and HTTP bodies remain unchanged. Frontend requested/start, native validation/attempt/result and frontend terminal are diagnosable; failure is human text with a secondary safe code. Focused argument/privacy/service/retention/UI/native tests prove the boundary. No game-rule redesign or complete sync claim. Future C21 remains checkpoint-only: stabilize local browser build and adapters after a Tauri dependency audit before any VPS deployment.


## 15. C18.4.04 account-object transport and reader freeze

Account objects use the exact v2 namespace in section 5, with scope `account` and stable types `folder`, `folder_order`, `folder_membership`, `project_order`. The authenticated `/api/v3/sync/encrypted/account/push` endpoint accepts closed opaque descriptors without a project ID. Mixed `/pull` shares the existing global account sequence/count/ciphertext budget and immutable replay storage; project endpoints continue requiring their real registered projects and v1 crypto. No fake/sentinel project is admitted.

Schema 030 preserves account identity, descriptors and exact v2 bytes in a separate native account inbox while committing the same pull cursor atomically. Production reader authenticates using the canonical-user AMK lease, verifies scope/type, then retains `account_entity_codec_not_activated`; no payload parser or apply proof is active. Shared native ACK stops before an account row even if later project rows are applied. Cross-scope event/sequence collisions and mutation of saved descriptor/object bytes are forbidden. Old project readers fail closed; no fallback or implicit binding of local-only projects exists.

Golden fixture covers tuple/info/key/AAD/nonce/plaintext/ciphertext. TypeScript is the production AEAD boundary; independent Node HKDF and native Rust test verifier check derivation bytes, and native persistence checks the same ciphertext fixture through restart. Rust does not implement production AEAD. C11 code/vectors remain unchanged; no dependency added.

Actual catalog codecs, durable apply/conflict substrate, explicit migration/publication and normal writers belong to C18.4.05. Preserve folder + authenticated bound project → membership → project order, explicit binding only, local-only positions local, preserved concurrent conflict branches, and no silent membership deletion. Writer activation requires compatible readers and real durable apply/conflict ACK proof; authentication alone is insufficient. C18.5 and account game ledger remain out of scope.

## C18.4.05 activated account catalog contract

The frozen E classifications above are now implemented for `folder`, `folder_order`,
`folder_membership`, and `project_order`. Account crypto remains exactly the accepted
C18.4.04 2/2 namespace and vectors; project C11 is unchanged. The server validates
only the closed opaque account descriptor and ciphertext transport.

Codec v1 has the exact keys `version`, `header`, `payload`, `dependencies`,
`deleted_at`. Header identifies authenticated account, literal `account` scope,
source device, entity type/ID, event ID, operation, revision, generation, sorted
unique parent IDs and canonical UTC update time. Genesis has no parents and
revision/generation 1; update/delete has one parent; explicit resolution admits the
complete current parent set, with max-parent revision/generation + 1. Native
preparation checks full current tips and local snapshot in an IMMEDIATE transaction.
An arriving stale resolution removes only its named parents; other branches remain.

The existing uncompressed WORTA-C1 frame uses framing version 1, entity slots 4–7
in the listed order, codec version 1 and compression ID 0; both u32 big-endian
sizes equal canonical UTF-8 JSON bytes. Folder payload is `{name}` or a retained
null tombstone. Membership payload is `{folder_id}` (null is removal). Both orders
are `{ids}`. Dependencies are exact closed `folders` (folder IDs → authenticated
heads), `projects` (project IDs → bootstrap ID and authenticated metadata event ID),
and `memberships` (project IDs → authenticated relation heads). Full order sets
and heads are validated; no local path, navigation state, arbitrary extension,
local-only project ID or fake project slot is admitted.

SQLite schema31 preserves all existing folder/member/order rows and account inbox
bytes. One catalog stack stores retained source candidates, immutable snapshot and
canonical events, immutable ciphertext after seal, receipts, tips, projections,
apply ledger, local reconciliation candidates and full-tip decisions. Publication
starts only with the Cloud action “Опубликовать структуру проектов”. Read, login,
unlock, startup and pre-authority edits do not capture/publish a catalog. Each
publication stage waits for dependency/self-echo proof. Sealed retries keep identity
and bytes; subsequent edits become later causal intents. Imported device-local
candidates remain available for an explicit decision.

Only same-account explicitly bound projects with reconciled authenticated metadata
lineage are eligible. Filtering local order L1,C1,L2,C2,L3 emits C1,C2. Applying a
cloud order changes only cloud slots; local projects retain their positions. Mixed
folder membership emits cloud relations only; local relations stay intact. New
connections derive durable intents after metadata authority, so restart recovers the
transition without registering any local-only project. Existing pause does not
unbind or delete remotely. Local binding removal is guarded once catalog authority
exists; remote deletion is not invented here.

Folder tombstones never cascade. A live or unresolved relation—including a retained
local-only membership—blocks destructive completion and ACK. Explicit moves/removal
and a later retry can establish safe completion. Physical catalog history/folder
cleanup is not activated. A common contiguous ACK step requires exact catalog
inbox/event/frame/ciphertext/sequence/apply-ledger proof, or complete conflict
preservation; supported authentication alone never advances it.

Bounds: 16,384 folders and eligible project/relation/order entries; 120 Unicode
scalars and 512 UTF-8 bytes per folder name, 512 bytes per identity; 64 parents/tips;
4 MiB canonical JSON per frame; 131,072 catalog history events and 256 MiB retained
frame/ciphertext history per account. Publication batches are 8; reader limits are
1–32 items and 1–8 passes (default 8 × 4). The accepted global pull/ciphertext budgets
still apply. Exceeding a bound preserves source/inbox/progress and produces a typed
recoverable blocker; it cannot produce partial ACK. C18.7 owns future compression.

C18.4 remains IN PROGRESS. C18.4.06 should review combined metadata/Stage/catalog
integration, strict stale dependency blockers, destructive manifests/retention,
mixed-sequence ACK and platform release qualification before any closure decision.


## C18.4.07 — frozen catalog dependency recovery

The C18.4.06 audit's strict frozen/current head equality caused permanent stale
immutable dependency blockers. C18.4.07 permits scoped causal coverage rather than
rewriting a frozen event. Stage's accepted `reference_coverage` is architectural
precedent; its implementation/semantics remain unchanged. Catalog proof uses an
iterative deterministic cycle-safe walk, at most256 distinct nodes per dependency
unit and65,536 loads per event. Bounds produce `catalog_resource_limit`, never
partial proof. Each frozen/traversed catalog node requires the same account,
entity type/ID and exact authenticated apply/conflict ledger proof. Single current
tips must cover all frozen references. Unresolved dependency multi-tips block;
explicit full-tip resolution may subsequently establish a covering live tip.
Neither timestamps, sequence proximity nor matching payloads establish causality.

Folder identity dependencies survive causal live rename/resolution. Direct folder
order application still requires the exact live folder ID set. Project proofs
require explicit same-account/project/bootstrap binding, frozen applied non-delete
metadata, current `active` authority (C18.4.06 preserved) and authenticated causal
coverage. Membership survives safe folder/metadata advancement. Project order
requires exact eligible project IDs and causal membership coverage; a relation
move or null/removal does not remove the connected project. Local-only projects
cannot become eligible through proof recovery or order/membership application.

Known causally proven tombstones and incompatible exact-set changes authorize
complete conflict preservation only, never invalid projection/materialization.
An old membership pointing at a proven deleted folder cannot move a project there.
Unknown/unverified/unrelated history, unresolved authority, invalid bootstrap or
unbound project remain blockers. Folder no-cascade/child checks stay in force;
physical history cleanup and future destructive manifests remain deferred.

Recovery preserves original event ID, canonical frame, payload, dependency maps,
nonce, ciphertext and sequence. The existing atomic apply ledger outcomes
`applied`/`conflict_preserved` suffice with retained authenticated history, exact
source bytes, causal event tips and local conflict candidate. No ignore flag,
replacement event, new schema or ACK outcome. Late O removes only named parents,
preserving concurrent newer R; both tips are available to explicit ordinary R2.
Complete conflict preservation can fill the common ACK hole before user resolution;
`ack_proven` exactness is unchanged. Mixed project/account sequencing has one cursor.

Bounded reader scheduling carries an ephemeral scope/auth-epoch keyset position
across cycles, resets at end-of-list and retries retained blockers. It does not
change pull/ACK state. Existing friendly dependency/conflict/resource messages and
safe diagnostics classifications apply without new UI text or plaintext logging.
Account crypto2/2, C11, codec/frame format and blind server transport stay unchanged.

Local closure evidence is in `C18_4_INTEGRATION_ACCEPTANCE.md`: converted immutable
O10/R11/Stage12 shared-ACK regression, folder/member/project positives/negatives and
one production-crypto PostgreSQL two-device extension. C18.4 is **LOCAL COMPLETE /
REMOTE ACCEPTANCE PENDING**, not CLOSED. C18 IN PROGRESS; official progress77.0%.
C18.5 requires independent acceptance before any new implementation.
