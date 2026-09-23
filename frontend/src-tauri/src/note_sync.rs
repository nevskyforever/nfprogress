//! Durable Note sync-intent and sealing-lifecycle primitives.
//!
//! Callers prepare plaintext intents in the same SQLite transaction that
//! mutates `notes`. Sealing later replaces that sidecar with an opaque object
//! and advances the existing outbox event atomically; uploads remain outside
//! this module.

use std::fmt::Write as _;

use rusqlite::{Connection, OptionalExtension, Transaction, TransactionBehavior};
use serde::{Deserialize, Serialize};

use crate::note_sync_plaintext::{
    decode_note_sync_plaintext, eligibility, Eligibility, NoteSyncPlaintext, NoteSyncRoute,
};
use crate::sqlite::{
    OwnedRemoteApplyAuthorization, PrivilegedRemoteApplyConnection, StorageError,
};

const MAX_SYNC_INTEGER: i64 = 9_007_199_254_740_991;
const MAX_UNSEALED_INTENT_LIST_LIMIT: u32 = 200;
const MAX_SEALED_OUTBOX_LIST_LIMIT: u32 = 200;
const MAX_ENCRYPTED_SYNC_CIPHERTEXT_BYTES: usize = 8_388_624;
const MAX_ENCRYPTED_SYNC_BATCH_CIPHERTEXT_BYTES: usize = 16_777_216;
const MAX_ENCRYPTED_SYNC_WIRE_BODY_BYTES: usize = 33_554_432;
const MAX_RECEIVED_INBOX_LIST_LIMIT: u32 = 32;
const SUPPORTED_CRYPTO_VERSION: i64 = 1;
const SUPPORTED_AAD_VERSION: i64 = 1;

#[derive(Debug)]
pub(crate) enum NoteSyncError {
    Database(rusqlite::Error),
    InvalidSnapshot(&'static str),
    RevisionOverflow,
    LocalOrdinalOverflow,
    MutationGenerationOverflow,
    SealAttemptOverflow,
    ConflictingHeads,
    InvalidListLimit,
    InvalidOutboxRead(&'static str),
    InvalidEnvelope(&'static str),
    InvalidSealState(&'static str),
    MissingEvent,
    MissingIntent,
    UnexpectedLifecycle,
    SealedObjectMissing,
    ConflictingEncryptedObject,
    ConflictingUploadReceipt,
    Random(String),
}

#[cfg(test)]
mod remote_apply_tests {
    use super::*;
    use crate::note_sync_plaintext::decode_note_sync_plaintext;
    use crate::sqlite::{
        apply_migrations, PrivilegedRemoteApplyConnection, RemoteApplyAuthorization,
    };

    const ACCOUNT: &str = "account";
    const CANONICAL_USER: &str = "123e4567-e89b-42d3-a456-4266141740aa";
    const PULLING_DEVICE: &str = "123e4567-e89b-42d3-a456-426614174001";
    const REMOTE_DEVICE: &str = "123e4567-e89b-42d3-a456-426614174002";
    const CREATE_EVENT: &str = "123e4567-e89b-42d3-a456-426614174100";
    const UPDATE_EVENT: &str = "123e4567-e89b-42d3-a456-426614174101";
    const DELETE_EVENT: &str = "123e4567-e89b-42d3-a456-426614174102";

    fn database() -> PrivilegedRemoteApplyConnection {
        let connection = Connection::open_in_memory().unwrap();
        apply_migrations(&connection).unwrap();
        connection.execute(
            "INSERT INTO projects(id,name,infinite,unit,status,payload_json)
             VALUES('p','Project',0,'symbols','active','{}')",
            [],
        ).unwrap();
        connection.execute(
            "INSERT INTO cloud_sync_state(
                account_id,device_id,pull_cursor,ack_cursor,created_at,updated_at
             ) VALUES(?1,?2,0,0,'now','now')",
            rusqlite::params![ACCOUNT, PULLING_DEVICE],
        ).unwrap();
        connection.execute(
            "INSERT INTO cloud_account_bindings(
                local_account_id,canonical_user_id,created_at,validated_at
             ) VALUES(?1,?2,'now','now')",
            rusqlite::params![ACCOUNT, CANONICAL_USER],
        ).unwrap();
        connection.execute(
            "INSERT INTO cloud_sync_project_bindings(project_id,account_id,created_at,updated_at)
             VALUES('p',?1,'now','now')",
            [ACCOUNT],
        ).unwrap();
        PrivilegedRemoteApplyConnection::from_connection(connection).unwrap()
    }

    fn plaintext(
        event_id: &str,
        parent_event_id: Option<&str>,
        revision: i64,
        operation: &str,
        updated_at: &str,
        content: &str,
    ) -> NoteSyncPlaintext {
        let mutation = if operation == "delete" {
            "delete"
        } else if revision == 1 {
            "create"
        } else {
            "update"
        };
        let note = if operation == "delete" {
            serde_json::json!({
                "id":"n","project_id":"p","stage_id":null,"source_type":"project",
                "source_map_id":null,"source_node_id":null,"content_format":"html",
                "deleted_at":updated_at,
            })
        } else {
            serde_json::json!({
                "id":"n","project_id":"p","stage_id":null,"source_type":"project",
                "source_map_id":null,"source_node_id":null,"content_format":"html",
                "title":"Title","content":content,"checklist":[],"color":"default",
                "pinned":false,"archived":false,"sort_order":0,"tags":[],
                "created_at":"2026-01-01T00:00:00.000000Z",
                "updated_at":updated_at,"metadata":{},
            })
        };
        let value = serde_json::json!({
            "version":1,
            "header":{
                "event_id":event_id,"parent_event_id":parent_event_id,"project_id":"p",
                "entity_id":"n","entity_type":"note","operation":operation,
                "revision":revision,"updated_at":updated_at,
                "deleted_at":if operation == "delete" { serde_json::Value::String(updated_at.to_string()) } else { serde_json::Value::Null },
            },
            "mutation":mutation,"note":note,
        });
        decode_note_sync_plaintext(serde_json::to_string(&value).unwrap().as_bytes()).unwrap()
    }

    fn header(plaintext: &NoteSyncPlaintext) -> (&str, &str, i64, &str, Option<&str>) {
        match plaintext {
            NoteSyncPlaintext::Create { header, .. }
            | NoteSyncPlaintext::Update { header, .. }
            | NoteSyncPlaintext::Delete { header, .. } => (
                &header.event_id,
                &header.operation,
                header.revision,
                &header.updated_at,
                header.deleted_at.as_deref(),
            ),
        }
    }

    fn received(
        connection: &PrivilegedRemoteApplyConnection,
        plaintext: NoteSyncPlaintext,
        sequence: i64,
        source_device_id: &str,
    ) -> ApplyVerifiedReceivedNoteCommand {
        let (event_id, operation, revision, updated_at, deleted_at) = header(&plaintext);
        let nonce = vec![sequence as u8; 24];
        let ciphertext = vec![(sequence + 31) as u8; 16];
        connection.connection().execute(
            "INSERT INTO cloud_sync_inbox(
                account_id,event_id,server_sequence,device_id,project_id,entity_id,
                entity_type,operation,sync_revision,updated_at,deleted_at,state,received_at
             ) VALUES(?1,?2,?3,?4,'p','n','note',?5,?6,?7,?8,'received','now')",
            rusqlite::params![ACCOUNT,event_id,sequence,source_device_id,operation,revision,updated_at,deleted_at],
        ).unwrap();
        connection.connection().execute(
            "INSERT INTO cloud_sync_event_objects(
                account_id,event_id,crypto_version,aad_version,nonce,ciphertext,stored_at
             ) VALUES(?1,?2,1,1,?3,?4,'now')",
            rusqlite::params![ACCOUNT,event_id,nonce,ciphertext],
        ).unwrap();
        ApplyVerifiedReceivedNoteCommand {
            account_id: ACCOUNT.to_string(), canonical_user_id: CANONICAL_USER.to_string(),
            pulling_device_id: PULLING_DEVICE.to_string(), event_id: event_id.to_string(),
            server_sequence: sequence, source_device_id: source_device_id.to_string(),
            crypto_version: 1, aad_version: 1,
            nonce: vec![sequence as u8; 24], ciphertext: vec![(sequence + 31) as u8; 16],
            plaintext,
        }
    }

    fn apply_create(connection: &mut PrivilegedRemoteApplyConnection) -> ApplyVerifiedReceivedNoteCommand {
        let command = received(
            connection,
            plaintext(CREATE_EVENT, None, 1, "upsert", "2026-01-01T00:00:00.000000Z", "create"),
            1,
            REMOTE_DEVICE,
        );
        assert_eq!(apply_verified_received_note(connection, &command).unwrap(), ApplyVerifiedReceivedNoteResult::Applied);
        command
    }

    #[test]
    fn remote_apply_create_updates_note_head_and_inbox_without_echo() {
        let mut connection = database();
        apply_create(&mut connection);
        assert_eq!(connection.connection().query_row(
            "SELECT json_extract(payload_json,'$.content') FROM notes WHERE id='n'", [], |row| row.get::<_, String>(0),
        ).unwrap(), "create");
        assert_eq!(connection.connection().query_row(
            "SELECT head_event_id,head_sync_revision FROM cloud_sync_entities", [], |row| Ok((row.get::<_, String>(0)?, row.get::<_, i64>(1)?)),
        ).unwrap(), (CREATE_EVENT.to_string(), 1));
        assert_eq!(connection.connection().query_row(
            "SELECT state FROM cloud_sync_inbox WHERE event_id=?1", [CREATE_EVENT], |row| row.get::<_, String>(0),
        ).unwrap(), "applied");
        assert_eq!(connection.connection().query_row("SELECT count(*) FROM cloud_sync_outbox", [], |row| row.get::<_, i64>(0)).unwrap(), 0);
        assert_eq!(connection.connection().query_row("SELECT pull_cursor,ack_cursor FROM cloud_sync_state", [], |row| Ok((row.get::<_, i64>(0)?, row.get::<_, i64>(1)?)),
        ).unwrap(), (0, 0));
    }

    #[test]
    fn remote_apply_accepts_equivalent_transport_timestamp_precision() {
        let mut connection = database();
        let command = received(
            &connection,
            plaintext(
                CREATE_EVENT,
                None,
                1,
                "upsert",
                "2026-01-01T00:00:00.000000Z",
                "transport precision",
            ),
            1,
            REMOTE_DEVICE,
        );
        connection.connection().execute(
            "UPDATE cloud_sync_inbox SET updated_at='2026-01-01T00:00:00Z'
             WHERE event_id=?1",
            [CREATE_EVENT],
        ).unwrap();
        assert_eq!(
            apply_verified_received_note(&mut connection, &command).unwrap(),
            ApplyVerifiedReceivedNoteResult::Applied,
        );
        assert_eq!(connection.connection().query_row(
            "SELECT state FROM cloud_sync_inbox WHERE event_id=?1",
            [CREATE_EVENT],
            |row| row.get::<_, String>(0),
        ).unwrap(), "applied");
    }

    #[test]
    fn remote_apply_create_does_not_overwrite_unproven_existing_note() {
        let mut connection = database();
        let local_plaintext = plaintext(
            CREATE_EVENT,
            None,
            1,
            "upsert",
            "2026-01-01T00:00:00.000000Z",
            "local without remote head",
        );
        let payload_json = match &local_plaintext {
            NoteSyncPlaintext::Create { note, .. } => note_payload_from_record(note).unwrap(),
            _ => unreachable!(),
        };
        connection.authorize_once(
            RemoteApplyAuthorization {
                event_id: CREATE_EVENT,
                account_id: ACCOUNT,
                project_id: "p",
                entity_id: "n",
                operation: "upsert",
                payload_json: Some(&payload_json),
                prior_payload_json: None,
            },
            |transaction| {
                transaction.execute(
                    "INSERT INTO notes(id,project_id,stage_id,updated_at,payload_json)
                     VALUES('n','p',NULL,'2026-01-01T00:00:00.000000Z',?1)",
                    [&payload_json],
                )?;
                Ok(())
            },
        ).unwrap();

        let command = received(
            &connection,
            plaintext(
                CREATE_EVENT,
                None,
                1,
                "upsert",
                "2026-01-01T00:00:00.000000Z",
                "remote replacement",
            ),
            1,
            REMOTE_DEVICE,
        );
        assert_eq!(
            apply_verified_received_note(&mut connection, &command).unwrap(),
            ApplyVerifiedReceivedNoteResult::Conflict,
        );
        assert_eq!(connection.connection().query_row(
            "SELECT json_extract(payload_json,'$.content') FROM notes WHERE id='n'",
            [],
            |row| row.get::<_, String>(0),
        ).unwrap(), "local without remote head");
        assert_eq!(connection.connection().query_row(
            "SELECT state,error_code FROM cloud_sync_inbox WHERE event_id=?1",
            [CREATE_EVENT],
            |row| Ok((row.get::<_, String>(0)?, row.get::<_, String>(1)?)),
        ).unwrap(), ("conflict".to_string(), "conflicting_head".to_string()));
        assert_eq!(connection.connection().query_row(
            "SELECT count(*) FROM cloud_sync_entities", [], |row| row.get::<_, i64>(0),
        ).unwrap(), 0);
        assert_eq!(connection.connection().query_row(
            "SELECT count(*) FROM cloud_sync_remote_apply_authorizations", [],
            |row| row.get::<_, i64>(0),
        ).unwrap(), 0);
    }

    #[test]
    fn remote_apply_update_and_delete_advance_chain_atomically() {
        let mut connection = database();
        apply_create(&mut connection);
        let update = received(&connection,
            plaintext(UPDATE_EVENT, Some(CREATE_EVENT), 2, "upsert", "2026-01-02T00:00:00.000000Z", "update"),
            2, REMOTE_DEVICE);
        assert_eq!(apply_verified_received_note(&mut connection, &update).unwrap(), ApplyVerifiedReceivedNoteResult::Applied);
        assert_eq!(connection.connection().query_row(
            "SELECT json_extract(payload_json,'$.content') FROM notes WHERE id='n'", [], |row| row.get::<_, String>(0),
        ).unwrap(), "update");
        let delete = received(&connection,
            plaintext(DELETE_EVENT, Some(UPDATE_EVENT), 3, "delete", "2026-01-03T00:00:00.000000Z", ""),
            3, REMOTE_DEVICE);
        assert_eq!(apply_verified_received_note(&mut connection, &delete).unwrap(), ApplyVerifiedReceivedNoteResult::Applied);
        assert_eq!(connection.connection().query_row("SELECT count(*) FROM notes", [], |row| row.get::<_, i64>(0)).unwrap(), 0);
        assert_eq!(connection.connection().query_row(
            "SELECT head_event_id,head_sync_revision FROM cloud_sync_entities", [], |row| Ok((row.get::<_, String>(0)?, row.get::<_, i64>(1)?)),
        ).unwrap(), (DELETE_EVENT.to_string(), 3));
    }

    #[test]
    fn remote_apply_replay_is_idempotent() {
        let mut connection = database();
        let command = apply_create(&mut connection);
        assert_eq!(apply_verified_received_note(&mut connection, &command).unwrap(), ApplyVerifiedReceivedNoteResult::AlreadyApplied);
        assert_eq!(connection.connection().query_row("SELECT count(*) FROM notes", [], |row| row.get::<_, i64>(0)).unwrap(), 1);
    }

    #[test]
    fn remote_apply_self_echo_uses_receipt_evidence_and_preserves_newer_local_note() {
        let mut connection = database();
        let newer_payload = serde_json::json!({
            "id":"n","project_id":"p","stage_id":null,"source_type":"project",
            "source_map_id":null,"source_node_id":null,"content_format":"html",
            "title":"Title","content":"newer local","checklist":[],"color":"default",
            "pinned":false,"archived":false,"sort_order":0,"tags":[],
            "created_at":"2026-01-01T00:00:00.000000Z",
            "updated_at":"2026-01-02T00:00:00.000000Z","revision":0,"metadata":{},
        }).to_string();
        // Seed a pre-binding local row, then create the real unsealed local
        // sidecar after binding; this avoids using Notes CRUD to fake remote IO.
        connection.connection().execute(
            "DELETE FROM cloud_sync_project_bindings WHERE project_id='p'", [],
        ).unwrap();
        connection.connection().execute(
            "INSERT INTO notes(id,project_id,stage_id,updated_at,payload_json)
             VALUES('n','p',NULL,'2026-01-02T00:00:00.000000Z',?1)",
            [&newer_payload],
        ).unwrap();
        connection.connection().execute(
            "INSERT INTO cloud_sync_project_bindings(project_id,account_id,created_at,updated_at)
             VALUES('p',?1,'now','now')",
            [ACCOUNT],
        ).unwrap();
        connection.connection().execute(
            "INSERT INTO cloud_sync_outbox(
                event_id,account_id,device_id,project_id,entity_id,entity_type,operation,
                revision,updated_at,deleted_at,created_at,parent_event_id,local_ordinal,lifecycle
             ) VALUES(?1,?2,?3,'p','n','note','upsert',1,
                '2026-01-01T00:00:00.000000Z',NULL,'now',NULL,1,'accepted')",
            rusqlite::params![CREATE_EVENT, ACCOUNT, PULLING_DEVICE],
        ).unwrap();
        connection.connection().execute(
            "INSERT INTO cloud_sync_upload_receipts(
                account_id,event_id,device_id,server_sequence,duplicate,accepted_at
             ) VALUES(?1,?2,?3,1,0,'now')",
            rusqlite::params![ACCOUNT, CREATE_EVENT, PULLING_DEVICE],
        ).unwrap();
        connection.connection().execute(
            "INSERT INTO cloud_sync_outbox(
                event_id,account_id,device_id,project_id,entity_id,entity_type,operation,
                revision,updated_at,deleted_at,created_at,parent_event_id,local_ordinal,lifecycle
             ) VALUES('123e4567-e89b-42d3-a456-426614174110',?1,?2,'p','n','note','upsert',2,
                '2026-01-02T00:00:00.000000Z',NULL,'now',?3,2,'unsealed')",
            rusqlite::params![ACCOUNT, PULLING_DEVICE, CREATE_EVENT],
        ).unwrap();
        connection.connection().execute(
            "INSERT INTO cloud_sync_note_intents(
                event_id,mutation_generation,snapshot_json,seal_state,seal_attempt_count,state_updated_at
             ) VALUES('123e4567-e89b-42d3-a456-426614174110',1,?1,'pending',0,'now')",
            [&newer_payload],
        ).unwrap();

        let command = received(&connection,
            plaintext(CREATE_EVENT, None, 1, "upsert", "2026-01-01T00:00:00.000000Z", "server copy"),
            1, PULLING_DEVICE);
        assert_eq!(apply_verified_received_note(&mut connection, &command).unwrap(), ApplyVerifiedReceivedNoteResult::SelfEchoApplied);
        assert_eq!(connection.connection().query_row(
            "SELECT json_extract(payload_json,'$.content') FROM notes WHERE id='n'", [], |row| row.get::<_, String>(0),
        ).unwrap(), "newer local");
        assert_eq!(connection.connection().query_row("SELECT count(*) FROM cloud_sync_outbox", [], |row| row.get::<_, i64>(0)).unwrap(), 2);
        assert_eq!(connection.connection().query_row(
            "SELECT state FROM cloud_sync_inbox WHERE event_id=?1", [CREATE_EVENT], |row| row.get::<_, String>(0),
        ).unwrap(), "applied");
    }

    #[test]
    fn remote_apply_classifies_conflicting_and_missing_parents() {
        let mut connection = database();
        apply_create(&mut connection);
        let conflict = received(&connection,
            plaintext(UPDATE_EVENT, Some(DELETE_EVENT), 2, "upsert", "2026-01-02T00:00:00.000000Z", "conflict"),
            2, REMOTE_DEVICE);
        assert_eq!(apply_verified_received_note(&mut connection, &conflict).unwrap(), ApplyVerifiedReceivedNoteResult::Conflict);
        assert_eq!(connection.connection().query_row("SELECT state FROM cloud_sync_inbox WHERE event_id=?1", [UPDATE_EVENT], |row| row.get::<_, String>(0)).unwrap(), "conflict");

        let mut other = database();
        let missing = received(&other,
            plaintext(UPDATE_EVENT, Some(CREATE_EVENT), 2, "upsert", "2026-01-02T00:00:00.000000Z", "missing"),
            2, REMOTE_DEVICE);
        assert_eq!(apply_verified_received_note(&mut other, &missing).unwrap(), ApplyVerifiedReceivedNoteResult::Orphan);
        assert_eq!(other.connection().query_row("SELECT state,error_code FROM cloud_sync_inbox WHERE event_id=?1", [UPDATE_EVENT], |row| Ok((row.get::<_, String>(0)?, row.get::<_, String>(1)?)),
        ).unwrap(), ("orphan".to_string(), "missing_parent".to_string()));
    }

    #[test]
    fn remote_apply_preserves_local_unsealed_change_and_rejects_wrong_object() {
        let mut connection = database();
        apply_create(&mut connection);
        connection.connection().execute(
            "INSERT INTO cloud_sync_outbox(
                event_id,account_id,device_id,project_id,entity_id,entity_type,operation,
                revision,updated_at,deleted_at,created_at,parent_event_id,local_ordinal,lifecycle
             ) VALUES('123e4567-e89b-42d3-a456-426614174110',?1,?2,'p','n','note','upsert',2,
                '2026-01-02T00:00:00.000000Z',NULL,'now',?3,1,'unsealed')",
            rusqlite::params![ACCOUNT, PULLING_DEVICE, CREATE_EVENT],
        ).unwrap();
        let conflict = received(&connection,
            plaintext(UPDATE_EVENT, Some(CREATE_EVENT), 2, "upsert", "2026-01-02T00:00:00.000000Z", "remote"),
            2, REMOTE_DEVICE);
        assert_eq!(apply_verified_received_note(&mut connection, &conflict).unwrap(), ApplyVerifiedReceivedNoteResult::Conflict);
        assert_eq!(connection.connection().query_row("SELECT json_extract(payload_json,'$.content') FROM notes WHERE id='n'", [], |row| row.get::<_, String>(0)).unwrap(), "create");

        let mut mismatch = database();
        let mut command = received(&mismatch,
            plaintext(CREATE_EVENT, None, 1, "upsert", "2026-01-01T00:00:00.000000Z", "create"),
            1, REMOTE_DEVICE);
        command.ciphertext[0] ^= 1;
        assert_eq!(apply_verified_received_note(&mut mismatch, &command).unwrap(), ApplyVerifiedReceivedNoteResult::Rejected);
        assert_eq!(mismatch.connection().query_row("SELECT count(*) FROM notes", [], |row| row.get::<_, i64>(0)).unwrap(), 0);
    }

    #[test]
    fn remote_apply_rechecks_scope_and_missing_project_without_losing_inbox_evidence() {
        let mut connection = database();
        let mut wrong_device = received(&connection,
            plaintext(CREATE_EVENT, None, 1, "upsert", "2026-01-01T00:00:00.000000Z", "create"),
            1, REMOTE_DEVICE);
        wrong_device.pulling_device_id = REMOTE_DEVICE.to_string();
        assert!(apply_verified_received_note(&mut connection, &wrong_device).is_err());
        assert_eq!(connection.connection().query_row(
            "SELECT state FROM cloud_sync_inbox WHERE event_id=?1", [CREATE_EVENT], |row| row.get::<_, String>(0),
        ).unwrap(), "received");

        let mut orphan = database();
        let command = received(&orphan,
            plaintext(CREATE_EVENT, None, 1, "upsert", "2026-01-01T00:00:00.000000Z", "create"),
            1, REMOTE_DEVICE);
        orphan.connection().execute(
            "DELETE FROM cloud_sync_project_bindings WHERE project_id='p'", [],
        ).unwrap();
        assert_eq!(apply_verified_received_note(&mut orphan, &command).unwrap(), ApplyVerifiedReceivedNoteResult::Orphan);
        assert_eq!(orphan.connection().query_row(
            "SELECT state,error_code FROM cloud_sync_inbox WHERE event_id=?1", [CREATE_EVENT],
            |row| Ok((row.get::<_, String>(0)?, row.get::<_, String>(1)?)),
        ).unwrap(), ("orphan".to_string(), "missing_project".to_string()));
        assert_eq!(orphan.connection().query_row("SELECT count(*) FROM notes", [], |row| row.get::<_, i64>(0)).unwrap(), 0);
    }

    #[test]
    fn remote_apply_fault_rolls_back_note_head_inbox_and_capability() {
        let mut connection = database();
        connection.connection().execute_batch(
            "CREATE TRIGGER test_remote_apply_fault BEFORE INSERT ON cloud_sync_entities
             BEGIN SELECT RAISE(ABORT, 'deterministic remote apply fault'); END;",
        ).unwrap();
        let command = received(&connection,
            plaintext(CREATE_EVENT, None, 1, "upsert", "2026-01-01T00:00:00.000000Z", "create"),
            1, REMOTE_DEVICE);
        assert!(apply_verified_received_note(&mut connection, &command).is_err());
        assert_eq!(connection.connection().query_row("SELECT count(*) FROM notes", [], |row| row.get::<_, i64>(0)).unwrap(), 0);
        assert_eq!(connection.connection().query_row("SELECT count(*) FROM cloud_sync_entities", [], |row| row.get::<_, i64>(0)).unwrap(), 0);
        assert_eq!(connection.connection().query_row("SELECT state FROM cloud_sync_inbox WHERE event_id=?1", [CREATE_EVENT], |row| row.get::<_, String>(0)).unwrap(), "received");
        assert_eq!(connection.connection().query_row("SELECT count(*) FROM cloud_sync_remote_apply_authorizations", [], |row| row.get::<_, i64>(0)).unwrap(), 0);
        assert!(connection.connection().execute(
            "INSERT INTO notes(id,project_id,stage_id,updated_at,payload_json)
             VALUES('n','p',NULL,'now','{}')", [],
        ).is_err());
    }

    #[test]
    fn remote_apply_ipc_rejects_invalid_plaintext_before_any_sqlite_mutation() {
        let mut connection = database();
        let result = apply_verified_received_note_ipc(
            &mut connection,
            ApplyVerifiedReceivedNoteIpcCommand {
                account_id: ACCOUNT.to_string(),
                canonical_user_id: CANONICAL_USER.to_string(),
                pulling_device_id: PULLING_DEVICE.to_string(),
                event_id: CREATE_EVENT.to_string(),
                server_sequence: 1,
                source_device_id: REMOTE_DEVICE.to_string(),
                crypto_version: 1,
                aad_version: 1,
                nonce: vec![0; 24],
                ciphertext: vec![0; 16],
                plaintext: br#"{"not":"a NoteSyncPlaintext"}"#.to_vec(),
            },
        );
        assert!(result.is_err());
        assert_eq!(connection.connection().query_row("SELECT count(*) FROM notes", [], |row| row.get::<_, i64>(0)).unwrap(), 0);
        assert_eq!(connection.connection().query_row("SELECT count(*) FROM cloud_sync_entities", [], |row| row.get::<_, i64>(0)).unwrap(), 0);
        assert_eq!(connection.connection().query_row("SELECT count(*) FROM cloud_sync_remote_apply_authorizations", [], |row| row.get::<_, i64>(0)).unwrap(), 0);
    }

    #[test]
    fn remote_apply_ipc_decodes_checked_in_typescript_canonical_bytes() {
        let mut connection = database();
        let fixture: serde_json::Value = serde_json::from_str(include_str!(concat!(
            env!("CARGO_MANIFEST_DIR"),
            "/../src/cloud/__fixtures__/noteSyncPlaintextV1.json"
        ))).unwrap();
        let plaintext = fixture["canonical_json"].as_str().unwrap().as_bytes().to_vec();
        let typed = decode_note_sync_plaintext(&plaintext).unwrap();
        let received = received(&connection, typed, 1, REMOTE_DEVICE);
        let result = apply_verified_received_note_ipc(
            &mut connection,
            ApplyVerifiedReceivedNoteIpcCommand {
                account_id: received.account_id,
                canonical_user_id: received.canonical_user_id,
                pulling_device_id: received.pulling_device_id,
                event_id: received.event_id,
                server_sequence: received.server_sequence,
                source_device_id: received.source_device_id,
                crypto_version: received.crypto_version,
                aad_version: received.aad_version,
                nonce: received.nonce,
                ciphertext: received.ciphertext,
                plaintext,
            },
        );
        assert_eq!(result.unwrap(), ApplyVerifiedReceivedNoteResult::Applied);
        assert_eq!(connection.connection().query_row("SELECT count(*) FROM notes", [], |row| row.get::<_, i64>(0)).unwrap(), 1);
    }
}

impl std::fmt::Display for NoteSyncError {
    fn fmt(&self, formatter: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::Database(error) => write!(formatter, "SQLite error: {error}"),
            Self::InvalidSnapshot(message) => {
                write!(formatter, "Invalid Note sync snapshot: {message}")
            }
            Self::RevisionOverflow => write!(
                formatter,
                "Note sync revision exceeds the wire integer limit"
            ),
            Self::LocalOrdinalOverflow => write!(formatter, "Note sync local ordinal overflow"),
            Self::MutationGenerationOverflow => {
                write!(formatter, "Note sync mutation generation overflow")
            }
            Self::SealAttemptOverflow => write!(formatter, "Note sync seal attempt overflow"),
            Self::ConflictingHeads => write!(formatter, "Note sync entity has conflicting heads"),
            Self::InvalidListLimit => write!(formatter, "Invalid Note sync intent list limit"),
            Self::InvalidOutboxRead(message) => {
                write!(
                    formatter,
                    "Invalid sealed Note sync outbox state: {message}"
                )
            }
            Self::InvalidEnvelope(message) => {
                write!(formatter, "Invalid encrypted Note sync envelope: {message}")
            }
            Self::InvalidSealState(message) => {
                write!(formatter, "Invalid durable Note sealing state: {message}")
            }
            Self::MissingEvent => write!(formatter, "Note sync outbox event does not exist"),
            Self::MissingIntent => write!(formatter, "Unsealed Note sync intent is missing"),
            Self::UnexpectedLifecycle => {
                write!(formatter, "Note sync event has an unexpected lifecycle")
            }
            Self::SealedObjectMissing => {
                write!(formatter, "Sealed Note sync event has no encrypted object")
            }
            Self::ConflictingEncryptedObject => {
                write!(
                    formatter,
                    "Note sync event has a conflicting encrypted object"
                )
            }
            Self::ConflictingUploadReceipt => write!(
                formatter,
                "Note sync event has a conflicting server receipt"
            ),
            Self::Random(error) => {
                write!(formatter, "Could not generate Note sync event ID: {error}")
            }
        }
    }
}

impl std::error::Error for NoteSyncError {}

impl NoteSyncError {
    pub(crate) fn user_message(&self) -> &'static str {
        match self {
            Self::RevisionOverflow => "Исчерпан диапазон sync revision заметки.",
            Self::LocalOrdinalOverflow => "Исчерпан диапазон локального sync-порядка.",
            Self::MutationGenerationOverflow => {
                "Исчерпан диапазон поколений локального изменения заметки."
            }
            Self::SealAttemptOverflow => "Исчерпан диапазон попыток шифрования изменения заметки.",
            Self::ConflictingHeads => "Обнаружено конфликтующее локальное состояние синхронизации.",
            Self::Database(_)
            | Self::InvalidSnapshot(_)
            | Self::InvalidListLimit
            | Self::InvalidOutboxRead(_)
            | Self::InvalidEnvelope(_)
            | Self::InvalidSealState(_)
            | Self::MissingEvent
            | Self::MissingIntent
            | Self::UnexpectedLifecycle
            | Self::SealedObjectMissing
            | Self::ConflictingEncryptedObject
            | Self::ConflictingUploadReceipt
            | Self::Random(_) => {
                "Не удалось надёжно зарегистрировать изменение заметки для синхронизации."
            }
        }
    }
}

impl From<rusqlite::Error> for NoteSyncError {
    fn from(error: rusqlite::Error) -> Self {
        Self::Database(error)
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize)]
#[serde(rename_all = "snake_case")]
pub(crate) enum NoteSyncOperation {
    Upsert,
    Delete,
}

impl NoteSyncOperation {
    fn from_stored(value: &str) -> Result<Self, NoteSyncError> {
        match value {
            "upsert" => Ok(Self::Upsert),
            "delete" => Ok(Self::Delete),
            _ => Err(NoteSyncError::InvalidSealState("invalid operation")),
        }
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize)]
#[serde(rename_all = "snake_case")]
pub(crate) enum NoteSyncSealState {
    Pending,
    RetryableError,
    Blocked,
    InvariantError,
}

impl NoteSyncSealState {
    fn from_stored(value: &str) -> Result<Self, NoteSyncError> {
        match value {
            "pending" => Ok(Self::Pending),
            "retryable_error" => Ok(Self::RetryableError),
            "blocked" => Ok(Self::Blocked),
            "invariant_error" => Ok(Self::InvariantError),
            _ => Err(NoteSyncError::InvalidSealState("invalid seal state")),
        }
    }
}

#[derive(Clone, Copy, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(rename_all = "snake_case")]
pub(crate) enum NoteSyncSealErrorCode {
    KeyUnavailable,
    PayloadTooLarge,
    EncryptedSyncObjectTooLarge,
    DependencyNotSynced,
    UnsupportedContentFormat,
    InvalidNotePayload,
    CryptoContextInvalid,
    InvalidSyncMetadata,
    InvalidEnvelope,
    MetadataMismatch,
    RuntimeUnavailable,
}

impl NoteSyncSealErrorCode {
    fn as_str(self) -> &'static str {
        match self {
            Self::KeyUnavailable => "key_unavailable",
            Self::PayloadTooLarge => "payload_too_large",
            Self::EncryptedSyncObjectTooLarge => "encrypted_sync_object_too_large",
            Self::DependencyNotSynced => "dependency_not_synced",
            Self::UnsupportedContentFormat => "unsupported_content_format",
            Self::InvalidNotePayload => "invalid_note_payload",
            Self::CryptoContextInvalid => "crypto_context_invalid",
            Self::InvalidSyncMetadata => "invalid_sync_metadata",
            Self::InvalidEnvelope => "invalid_envelope",
            Self::MetadataMismatch => "metadata_mismatch",
            Self::RuntimeUnavailable => "runtime_unavailable",
        }
    }

    fn seal_state(self) -> NoteSyncSealState {
        match self {
            Self::KeyUnavailable
            | Self::PayloadTooLarge
            | Self::EncryptedSyncObjectTooLarge
            | Self::DependencyNotSynced
            | Self::UnsupportedContentFormat => NoteSyncSealState::Blocked,
            Self::RuntimeUnavailable => NoteSyncSealState::RetryableError,
            Self::InvalidNotePayload
            | Self::CryptoContextInvalid
            | Self::InvalidSyncMetadata
            | Self::InvalidEnvelope
            | Self::MetadataMismatch => NoteSyncSealState::InvariantError,
        }
    }
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize)]
pub(crate) struct UnsealedNoteSyncIntent {
    pub event_id: String,
    pub account_id: String,
    pub device_id: String,
    pub project_id: String,
    pub entity_id: String,
    pub entity_type: String,
    pub operation: NoteSyncOperation,
    pub revision: i64,
    pub parent_event_id: Option<String>,
    pub updated_at: String,
    pub deleted_at: Option<String>,
    pub local_ordinal: i64,
    pub mutation_generation: i64,
    pub snapshot_json: String,
    pub seal_state: NoteSyncSealState,
    pub seal_attempt_count: i64,
    pub last_error_code: Option<String>,
    pub next_attempt_at: Option<String>,
}

/// Read-only transport input assembled from one sealed outbox event and its
/// already-persisted encrypted object. This deliberately contains no intent
/// snapshot or key material.
#[derive(Clone, Debug, Eq, PartialEq, Serialize)]
pub(crate) struct SealedNoteSyncOutboxItem {
    pub event_id: String,
    pub account_id: String,
    pub device_id: String,
    pub project_id: String,
    pub entity_id: String,
    pub entity_type: String,
    pub operation: NoteSyncOperation,
    pub revision: i64,
    pub parent_event_id: Option<String>,
    pub updated_at: String,
    pub deleted_at: Option<String>,
    pub local_ordinal: i64,
    pub envelope: EncryptedNoteSyncEnvelope,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub(crate) struct NoteSyncUploadReceipt {
    pub event_id: String,
    pub server_sequence: i64,
    pub duplicate: bool,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub(crate) struct CommitNoteSyncUploadAcceptanceCommand {
    pub account_id: String,
    pub device_id: String,
    pub receipts: Vec<NoteSyncUploadReceipt>,
}

#[derive(Clone, Copy, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(rename_all = "snake_case")]
pub(crate) enum NoteSyncUploadErrorCode {
    NetworkUnavailable,
    RequestTimeout,
    Http5xx,
    RateLimited,
    Unauthorized,
    DeviceNotRegistered,
    CloudProjectDisabled,
    InvalidProtocol,
    ConflictingEvent,
    MalformedReceipt,
    LocalAcceptanceFailed,
}

impl NoteSyncUploadErrorCode {
    fn as_str(self) -> &'static str {
        match self {
            Self::NetworkUnavailable => "network_unavailable",
            Self::RequestTimeout => "request_timeout",
            Self::Http5xx => "http_5xx",
            Self::RateLimited => "rate_limited",
            Self::Unauthorized => "unauthorized",
            Self::DeviceNotRegistered => "device_not_registered",
            Self::CloudProjectDisabled => "cloud_project_disabled",
            Self::InvalidProtocol => "invalid_protocol",
            Self::ConflictingEvent => "conflicting_event",
            Self::MalformedReceipt => "malformed_receipt",
            Self::LocalAcceptanceFailed => "local_acceptance_failed",
        }
    }

    fn retryable(self) -> bool {
        matches!(
            self,
            Self::NetworkUnavailable
                | Self::RequestTimeout
                | Self::Http5xx
                | Self::RateLimited
                | Self::LocalAcceptanceFailed
        )
    }
}

#[derive(Clone, Debug, Deserialize)]
pub(crate) struct RecordNoteSyncUploadFailureCommand {
    pub account_id: String,
    pub device_id: String,
    pub event_ids: Vec<String>,
    pub error_code: NoteSyncUploadErrorCode,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize)]
#[serde(rename_all = "snake_case")]
pub(crate) enum CommitNoteSyncUploadAcceptanceResult {
    Accepted,
    AlreadyAccepted,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize)]
#[serde(rename_all = "snake_case")]
pub(crate) enum NoteSyncPreflightIssueCode {
    MissingCreatedAt,
    InvalidCreatedAt,
    MissingUpdatedAt,
    InvalidUpdatedAt,
    InvalidNotePayload,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize)]
pub(crate) struct NoteSyncPreflightIssue {
    pub note_id: String,
    pub code: NoteSyncPreflightIssueCode,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub(crate) struct RecordNoteSyncSealFailureCommand {
    pub event_id: String,
    pub expected_mutation_generation: i64,
    pub error_code: NoteSyncSealErrorCode,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub(crate) struct EncryptedNoteSyncEnvelope {
    pub crypto_version: i64,
    pub aad_version: i64,
    pub nonce: String,
    pub ciphertext: String,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub(crate) struct CommitSealedNoteSyncEventCommand {
    pub event_id: String,
    pub expected_mutation_generation: i64,
    pub envelope: EncryptedNoteSyncEnvelope,
}

/// Opaque, already transport-validated data accepted into the durable inbox.
/// This is intentionally separate from the outbox commands: receipt never
/// decrypts or applies a user note.
#[derive(Clone, Debug, Deserialize)]
#[serde(deny_unknown_fields)]
pub(crate) struct ReadNoteSyncPullStateCommand {
    pub account_id: String,
    pub device_id: String,
    pub canonical_user_id: String,
}

#[derive(Clone, Debug, Serialize)]
pub(crate) struct NoteSyncPullState {
    pub pull_cursor: i64,
    pub ack_cursor: i64,
}

/// A read-only, locally proven prefix that a later transport layer may ACK.
/// It is deliberately not evidence of a remote ACK.
#[derive(Clone, Debug, Eq, PartialEq, Serialize)]
pub(crate) struct NoteSyncAckCandidate {
    pub current_ack_cursor: i64,
    pub candidate_cursor: i64,
}

#[derive(Clone, Debug, Deserialize)]
#[serde(deny_unknown_fields)]
pub(crate) struct PrepareNoteSyncAckCommand {
    pub account_id: String,
    pub device_id: String,
    pub canonical_user_id: String,
}

#[derive(Clone, Debug, Deserialize)]
#[serde(deny_unknown_fields)]
pub(crate) struct CommitNoteSyncAckCommand {
    pub account_id: String,
    pub device_id: String,
    pub canonical_user_id: String,
    pub expected_old_ack_cursor: i64,
    pub acknowledged_cursor: i64,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize)]
#[serde(rename_all = "snake_case")]
pub(crate) enum CommitNoteSyncAckResult {
    Advanced,
    AlreadyAcknowledged,
    AlreadyAdvanced,
    Stale,
}

#[derive(Clone, Debug, Deserialize)]
#[serde(deny_unknown_fields)]
pub(crate) struct CommitNoteSyncInboundPageCommand {
    pub account_id: String,
    pub device_id: String,
    pub canonical_user_id: String,
    pub expected_cursor: i64,
    pub next_cursor: i64,
    pub has_more: bool,
    pub items: Vec<InboundNoteSyncItem>,
}

#[derive(Clone, Debug, Deserialize)]
#[serde(deny_unknown_fields)]
pub(crate) struct InboundNoteSyncItem {
    pub event_id: String,
    pub server_sequence: i64,
    pub source_device_id: String,
    pub project_id: String,
    pub entity_id: String,
    pub entity_type: String,
    pub operation: String,
    pub revision: i64,
    pub updated_at: String,
    pub deleted_at: Option<String>,
    pub envelope: Option<EncryptedNoteSyncEnvelope>,
}

#[derive(Clone, Debug, Serialize)]
pub(crate) struct CommitNoteSyncInboundPageResult {
    pub committed_cursor: i64,
    pub new_events: u32,
    pub replayed_events: u32,
    pub has_more: bool,
}

/// Opaque received Note events for the TypeScript authenticated decryptor.
/// This command deliberately neither decrypts nor changes inbox state.
#[derive(Clone, Debug, Deserialize)]
#[serde(deny_unknown_fields)]
pub(crate) struct ListReceivedNoteSyncInboxCommand {
    pub account_id: String,
    pub device_id: String,
    pub canonical_user_id: String,
    pub limit: u32,
}

#[derive(Clone, Debug, Serialize)]
pub(crate) struct ReceivedNoteSyncInboxItem {
    pub event_id: String,
    pub server_sequence: i64,
    pub source_device_id: String,
    pub project_id: String,
    pub entity_id: String,
    pub entity_type: String,
    pub operation: String,
    pub revision: i64,
    pub updated_at: String,
    pub deleted_at: Option<String>,
    pub envelope: StoredEncryptedNoteSyncEnvelope,
}

/// Inputs already authenticated by the TypeScript crypto boundary.  Rust
/// treats every routing/envelope field as untrusted until it matches the
/// durable received inbox row in the same SQLite transaction.
#[derive(Clone, Debug)]
pub(crate) struct ApplyVerifiedReceivedNoteCommand {
    pub account_id: String,
    pub canonical_user_id: String,
    pub pulling_device_id: String,
    pub event_id: String,
    pub server_sequence: i64,
    pub source_device_id: String,
    pub crypto_version: i64,
    pub aad_version: i64,
    pub nonce: Vec<u8>,
    pub ciphertext: Vec<u8>,
    pub plaintext: NoteSyncPlaintext,
}

/// Narrow renderer-to-Rust IPC shape. `plaintext` is canonical plaintext JSON
/// emitted only after TypeScript authenticated decryption; it is decoded again
/// immediately and is never persisted separately.
#[derive(Clone, Debug, Deserialize)]
#[serde(deny_unknown_fields)]
pub(crate) struct ApplyVerifiedReceivedNoteIpcCommand {
    pub account_id: String,
    pub canonical_user_id: String,
    pub pulling_device_id: String,
    pub event_id: String,
    pub server_sequence: i64,
    pub source_device_id: String,
    pub crypto_version: i64,
    pub aad_version: i64,
    pub nonce: Vec<u8>,
    pub ciphertext: Vec<u8>,
    pub plaintext: Vec<u8>,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize)]
#[serde(rename_all = "snake_case")]
pub(crate) enum ApplyVerifiedReceivedNoteResult {
    Applied,
    AlreadyApplied,
    SelfEchoApplied,
    Orphan,
    Conflict,
    Rejected,
}

#[derive(Clone, Debug, Serialize)]
pub(crate) struct StoredEncryptedNoteSyncEnvelope {
    pub crypto_version: i64,
    pub aad_version: i64,
    pub nonce: String,
    pub ciphertext: String,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize)]
#[serde(rename_all = "snake_case")]
pub(crate) enum RecordNoteSyncSealFailureResult {
    Recorded,
    StaleGeneration,
    AlreadySealed,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize)]
#[serde(rename_all = "snake_case")]
pub(crate) enum CommitSealedNoteSyncEventResult {
    Sealed,
    StaleGeneration,
    AlreadySealed,
}

#[derive(Debug, Eq, PartialEq)]
struct DecodedEncryptedNoteSyncEnvelope {
    crypto_version: i64,
    aad_version: i64,
    nonce: Vec<u8>,
    ciphertext: Vec<u8>,
}

impl NoteSyncOperation {
    fn as_str(self) -> &'static str {
        match self {
            Self::Upsert => "upsert",
            Self::Delete => "delete",
        }
    }
}

#[derive(Debug, Eq, PartialEq)]
pub(crate) struct ProjectCloudBinding {
    pub account_id: String,
    pub device_id: String,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct EntitySyncHead {
    pub event_id: String,
    pub revision: i64,
}

#[derive(Debug, Eq, PartialEq)]
pub(crate) struct PreparedNoteIntent {
    pub event_id: String,
    pub revision: i64,
    pub parent_event_id: Option<String>,
    pub local_ordinal: i64,
    pub mutation_generation: i64,
    pub coalesced: bool,
}

pub(crate) struct PrepareNoteIntent<'a> {
    pub project_id: &'a str,
    pub entity_id: &'a str,
    pub operation: NoteSyncOperation,
    pub updated_at: &'a str,
    pub deleted_at: Option<&'a str>,
    pub snapshot_json: &'a str,
    pub state_updated_at: &'a str,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) enum NoteDeleteScope<'a> {
    Project,
    Stage(&'a str),
}

pub(crate) fn build_note_tombstone(
    note: &serde_json::Value,
    deleted_at: &str,
) -> Result<String, NoteSyncError> {
    let source = note
        .as_object()
        .ok_or(NoteSyncError::InvalidSnapshot("snapshot is not an object"))?;
    let mut tombstone = serde_json::Map::new();
    for key in [
        "id",
        "project_id",
        "stage_id",
        "source_type",
        "source_map_id",
        "source_node_id",
        "content_format",
    ] {
        tombstone.insert(
            key.to_string(),
            source
                .get(key)
                .cloned()
                .ok_or(NoteSyncError::InvalidSnapshot("incomplete note route"))?,
        );
    }
    tombstone.insert(
        "deleted_at".to_string(),
        serde_json::Value::String(deleted_at.to_string()),
    );
    serde_json::to_string(&tombstone)
        .map_err(|_| NoteSyncError::InvalidSnapshot("tombstone cannot be encoded"))
}

pub(crate) fn prepare_note_delete_intent(
    transaction: &Transaction<'_>,
    project_id: &str,
    note_id: &str,
    note: &serde_json::Value,
    deleted_at: &str,
) -> Result<Option<PreparedNoteIntent>, NoteSyncError> {
    if resolve_project_cloud_binding(transaction, project_id)?.is_none() {
        return Ok(None);
    }
    let tombstone = build_note_tombstone(note, deleted_at)?;
    prepare_unsealed_note_intent(
        transaction,
        PrepareNoteIntent {
            project_id,
            entity_id: note_id,
            operation: NoteSyncOperation::Delete,
            updated_at: deleted_at,
            deleted_at: Some(deleted_at),
            snapshot_json: &tombstone,
            state_updated_at: deleted_at,
        },
    )
}

pub(crate) fn prepare_note_delete_intents_for_scope(
    transaction: &Transaction<'_>,
    project_id: &str,
    scope: NoteDeleteScope<'_>,
    deleted_at: &str,
) -> Result<usize, NoteSyncError> {
    // Preserve the pre-sync local-only deletion behavior, including for legacy
    // rows whose payload cannot form a cloud tombstone.
    if resolve_project_cloud_binding(transaction, project_id)?.is_none() {
        return Ok(0);
    }
    let mut notes = Vec::new();
    match scope {
        NoteDeleteScope::Project => {
            let mut statement = transaction
                .prepare("SELECT id,payload_json FROM notes WHERE project_id=?1 ORDER BY rowid")?;
            let rows = statement.query_map([project_id], |row| {
                Ok((row.get::<_, String>(0)?, row.get::<_, String>(1)?))
            })?;
            notes.extend(rows.collect::<Result<Vec<_>, _>>()?);
        }
        NoteDeleteScope::Stage(stage_id) => {
            let mut statement = transaction.prepare(
                "SELECT id,payload_json FROM notes
                 WHERE project_id=?1 AND stage_id=?2 ORDER BY rowid",
            )?;
            let rows = statement.query_map(rusqlite::params![project_id, stage_id], |row| {
                Ok((row.get::<_, String>(0)?, row.get::<_, String>(1)?))
            })?;
            notes.extend(rows.collect::<Result<Vec<_>, _>>()?);
        }
    }
    for (note_id, raw) in &notes {
        let note: serde_json::Value = serde_json::from_str(raw)
            .map_err(|_| NoteSyncError::InvalidSnapshot("snapshot is not valid JSON"))?;
        prepare_note_delete_intent(transaction, project_id, note_id, &note, deleted_at)?;
    }
    Ok(notes.len())
}

pub(crate) fn resolve_project_cloud_binding(
    transaction: &Transaction<'_>,
    project_id: &str,
) -> Result<Option<ProjectCloudBinding>, NoteSyncError> {
    transaction
        .query_row(
            "SELECT binding.account_id,state.device_id
             FROM cloud_sync_project_bindings AS binding
             JOIN cloud_sync_state AS state ON state.account_id=binding.account_id
             WHERE binding.project_id=?1",
            [project_id],
            |row| {
                Ok(ProjectCloudBinding {
                    account_id: row.get(0)?,
                    device_id: row.get(1)?,
                })
            },
        )
        .optional()
        .map_err(Into::into)
}

fn parse_ascii_number(bytes: &[u8]) -> Option<i64> {
    bytes.iter().try_fold(0_i64, |value, byte| {
        byte.is_ascii_digit()
            .then(|| value * 10 + i64::from(byte - b'0'))
    })
}

fn leap_year(year: i64) -> bool {
    year % 4 == 0 && (year % 100 != 0 || year % 400 == 0)
}

fn days_in_month(year: i64, month: i64) -> i64 {
    match month {
        2 if leap_year(year) => 29,
        2 => 28,
        4 | 6 | 9 | 11 => 30,
        _ => 31,
    }
}

// Proleptic Gregorian civil date to days relative to 1970-01-01. This mirrors
// the frozen TypeScript syncTimestamp contract without adding a date dependency.
fn days_from_civil(year: i64, month: i64, day: i64) -> i64 {
    let adjusted_year = year - i64::from(month <= 2);
    let era = adjusted_year.div_euclid(400);
    let year_of_era = adjusted_year - era * 400;
    let shifted_month = month + if month > 2 { -3 } else { 9 };
    let day_of_year = (153 * shifted_month + 2) / 5 + day - 1;
    let day_of_era = year_of_era * 365 + year_of_era / 4 - year_of_era / 100 + day_of_year;
    era * 146_097 + day_of_era - 719_468
}

fn parse_note_sync_timestamp(value: &str) -> Option<(i64, i64)> {
    let bytes = value.as_bytes();
    if !value.is_ascii()
        || bytes.len() < 20
        || bytes.get(4) != Some(&b'-')
        || bytes.get(7) != Some(&b'-')
        || bytes.get(10) != Some(&b'T')
        || bytes.get(13) != Some(&b':')
        || bytes.get(16) != Some(&b':')
    {
        return None;
    }
    let Some(year) = parse_ascii_number(&bytes[0..4]) else {
        return None;
    };
    let Some(month) = parse_ascii_number(&bytes[5..7]) else {
        return None;
    };
    let Some(day) = parse_ascii_number(&bytes[8..10]) else {
        return None;
    };
    let Some(hour) = parse_ascii_number(&bytes[11..13]) else {
        return None;
    };
    let Some(minute) = parse_ascii_number(&bytes[14..16]) else {
        return None;
    };
    let Some(second) = parse_ascii_number(&bytes[17..19]) else {
        return None;
    };
    if !(1..=9999).contains(&year)
        || !(1..=12).contains(&month)
        || !(1..=days_in_month(year, month)).contains(&day)
        || hour > 23
        || minute > 59
        || second > 59
    {
        return None;
    }

    let mut cursor = 19;
    let mut fractional_microseconds = 0_i64;
    if bytes.get(cursor) == Some(&b'.') {
        cursor += 1;
        let fraction_start = cursor;
        while bytes.get(cursor).is_some_and(u8::is_ascii_digit) {
            cursor += 1;
        }
        if !(1..=6).contains(&(cursor - fraction_start)) {
            return None;
        }
        let digits = cursor - fraction_start;
        fractional_microseconds = parse_ascii_number(&bytes[fraction_start..cursor])?
            * 10_i64.pow((6 - digits) as u32);
    }

    let offset_seconds = if bytes.get(cursor) == Some(&b'Z') && cursor + 1 == bytes.len() {
        0
    } else if cursor + 6 == bytes.len()
        && matches!(bytes.get(cursor), Some(b'+') | Some(b'-'))
        && bytes.get(cursor + 3) == Some(&b':')
    {
        let Some(offset_hour) = parse_ascii_number(&bytes[cursor + 1..cursor + 3]) else {
            return None;
        };
        let Some(offset_minute) = parse_ascii_number(&bytes[cursor + 4..cursor + 6]) else {
            return None;
        };
        if offset_hour > 23
            || offset_minute > 59
            || (bytes[cursor] == b'-' && offset_hour == 0 && offset_minute == 0)
        {
            return None;
        }
        let seconds = (offset_hour * 60 + offset_minute) * 60;
        if bytes[cursor] == b'+' {
            seconds
        } else {
            -seconds
        }
    } else {
        return None;
    };

    let utc_seconds =
        days_from_civil(year, month, day) * 86_400 + hour * 3600 + minute * 60 + second
            - offset_seconds;
    let minimum = days_from_civil(1, 1, 1) * 86_400;
    let maximum = days_from_civil(10_000, 1, 1) * 86_400;
    (minimum..maximum).contains(&utc_seconds).then_some((utc_seconds, fractional_microseconds))
}

fn valid_note_sync_timestamp(value: &str) -> bool {
    parse_note_sync_timestamp(value).is_some()
}

fn note_sync_timestamps_equal(left: &str, right: &str) -> bool {
    parse_note_sync_timestamp(left).is_some_and(|left| {
        parse_note_sync_timestamp(right).is_some_and(|right| right == left)
    })
}

pub(crate) fn preflight_note_sync_project(
    connection: &Connection,
    project_id: &str,
) -> Result<Vec<NoteSyncPreflightIssue>, NoteSyncError> {
    if project_id.is_empty() {
        return Err(NoteSyncError::InvalidSnapshot("missing project identity"));
    }
    let mut statement =
        connection.prepare("SELECT id,payload_json FROM notes WHERE project_id=?1 ORDER BY id")?;
    let rows = statement.query_map([project_id], |row| {
        Ok((row.get::<_, String>(0)?, row.get::<_, String>(1)?))
    })?;
    let mut issues = Vec::new();
    for row in rows {
        let (note_id, snapshot_json) = row?;
        let Ok(snapshot) = serde_json::from_str::<serde_json::Value>(&snapshot_json) else {
            issues.push(NoteSyncPreflightIssue {
                note_id,
                code: NoteSyncPreflightIssueCode::InvalidNotePayload,
            });
            continue;
        };
        let Some(object) = snapshot.as_object() else {
            issues.push(NoteSyncPreflightIssue {
                note_id,
                code: NoteSyncPreflightIssueCode::InvalidNotePayload,
            });
            continue;
        };
        for (field, missing, invalid) in [
            (
                "created_at",
                NoteSyncPreflightIssueCode::MissingCreatedAt,
                NoteSyncPreflightIssueCode::InvalidCreatedAt,
            ),
            (
                "updated_at",
                NoteSyncPreflightIssueCode::MissingUpdatedAt,
                NoteSyncPreflightIssueCode::InvalidUpdatedAt,
            ),
        ] {
            let code = match object.get(field) {
                None => Some(missing),
                Some(serde_json::Value::String(value)) if value.is_empty() => Some(missing),
                Some(serde_json::Value::String(value)) if valid_note_sync_timestamp(value) => None,
                _ => Some(invalid),
            };
            if let Some(code) = code {
                issues.push(NoteSyncPreflightIssue {
                    note_id: note_id.clone(),
                    code,
                });
            }
        }
    }
    Ok(issues)
}

pub(crate) fn next_local_ordinal(
    transaction: &Transaction<'_>,
    account_id: &str,
    device_id: &str,
) -> Result<i64, NoteSyncError> {
    let current: i64 = transaction.query_row(
        "SELECT COALESCE(MAX(local_ordinal),0)
         FROM cloud_sync_outbox
         WHERE account_id=?1 AND device_id=?2 AND lifecycle!='legacy'",
        rusqlite::params![account_id, device_id],
        |row| row.get(0),
    )?;
    current
        .checked_add(1)
        .filter(|value| (1..=MAX_SYNC_INTEGER).contains(value))
        .ok_or(NoteSyncError::LocalOrdinalOverflow)
}

pub(crate) fn read_entity_sync_head(
    transaction: &Transaction<'_>,
    account_id: &str,
    project_id: &str,
    entity_id: &str,
) -> Result<Option<EntitySyncHead>, NoteSyncError> {
    let local = transaction
        .query_row(
            "SELECT event_id,revision
             FROM cloud_sync_outbox
             WHERE account_id=?1 AND project_id=?2 AND entity_id=?3
               AND entity_type='note' AND lifecycle IN ('sealed','accepted')
               AND local_ordinal>0
             ORDER BY revision DESC,local_ordinal DESC,event_id DESC LIMIT 1",
            rusqlite::params![account_id, project_id, entity_id],
            |row| {
                Ok(EntitySyncHead {
                    event_id: row.get(0)?,
                    revision: row.get(1)?,
                })
            },
        )
        .optional()?;
    let applied = transaction
        .query_row(
            "SELECT head_event_id,head_sync_revision
             FROM cloud_sync_entities
             WHERE account_id=?1 AND project_id=?2 AND entity_id=?3 AND entity_type='note'",
            rusqlite::params![account_id, project_id, entity_id],
            |row| {
                Ok(EntitySyncHead {
                    event_id: row.get(0)?,
                    revision: row.get(1)?,
                })
            },
        )
        .optional()?;
    match (local, applied) {
        (None, None) => Ok(None),
        (Some(head), None) | (None, Some(head)) => Ok(Some(head)),
        (Some(local), Some(applied)) if local.revision > applied.revision => Ok(Some(local)),
        (Some(local), Some(applied)) if applied.revision > local.revision => Ok(Some(applied)),
        (Some(local), Some(applied)) if local.event_id == applied.event_id => Ok(Some(local)),
        (Some(_), Some(_)) => Err(NoteSyncError::ConflictingHeads),
    }
}

fn validate_snapshot(input: &PrepareNoteIntent<'_>) -> Result<(), NoteSyncError> {
    if input.project_id.is_empty() || input.entity_id.is_empty() || input.updated_at.is_empty() {
        return Err(NoteSyncError::InvalidSnapshot("missing event identity"));
    }
    if (input.operation == NoteSyncOperation::Delete) != input.deleted_at.is_some() {
        return Err(NoteSyncError::InvalidSnapshot(
            "operation/deleted_at mismatch",
        ));
    }
    let snapshot: serde_json::Value = serde_json::from_str(input.snapshot_json)
        .map_err(|_| NoteSyncError::InvalidSnapshot("snapshot is not valid JSON"))?;
    let object = snapshot
        .as_object()
        .ok_or(NoteSyncError::InvalidSnapshot("snapshot is not an object"))?;
    if object.get("id").and_then(serde_json::Value::as_str) != Some(input.entity_id)
        || object.get("project_id").and_then(serde_json::Value::as_str) != Some(input.project_id)
    {
        return Err(NoteSyncError::InvalidSnapshot("snapshot identity mismatch"));
    }
    if input.operation == NoteSyncOperation::Delete {
        for key in [
            "stage_id",
            "source_type",
            "source_map_id",
            "source_node_id",
            "content_format",
            "deleted_at",
        ] {
            if !object.contains_key(key) {
                return Err(NoteSyncError::InvalidSnapshot("incomplete tombstone"));
            }
        }
        if object.get("deleted_at").and_then(serde_json::Value::as_str) != input.deleted_at {
            return Err(NoteSyncError::InvalidSnapshot(
                "tombstone timestamp mismatch",
            ));
        }
    }
    Ok(())
}

fn canonical_uuid_v4() -> Result<String, NoteSyncError> {
    let mut bytes = [0_u8; 16];
    getrandom::fill(&mut bytes).map_err(|error| NoteSyncError::Random(error.to_string()))?;
    bytes[6] = (bytes[6] & 0x0f) | 0x40;
    bytes[8] = (bytes[8] & 0x3f) | 0x80;
    let mut value = String::with_capacity(36);
    for (index, byte) in bytes.iter().enumerate() {
        if matches!(index, 4 | 6 | 8 | 10) {
            value.push('-');
        }
        write!(&mut value, "{byte:02x}").expect("writing to a String cannot fail");
    }
    Ok(value)
}

pub(crate) fn prepare_unsealed_note_intent(
    transaction: &Transaction<'_>,
    input: PrepareNoteIntent<'_>,
) -> Result<Option<PreparedNoteIntent>, NoteSyncError> {
    let Some(binding) = resolve_project_cloud_binding(transaction, input.project_id)? else {
        return Ok(None);
    };
    validate_snapshot(&input)?;

    let existing = transaction
        .query_row(
            "SELECT event.event_id,event.revision,event.parent_event_id,event.local_ordinal,
                    intent.mutation_generation
             FROM cloud_sync_outbox AS event
             JOIN cloud_sync_note_intents AS intent ON intent.event_id=event.event_id
             WHERE event.account_id=?1 AND event.project_id=?2 AND event.entity_id=?3
               AND event.entity_type='note' AND event.lifecycle='unsealed'
               AND event.local_ordinal>0",
            rusqlite::params![binding.account_id, input.project_id, input.entity_id],
            |row| {
                Ok(PreparedNoteIntent {
                    event_id: row.get(0)?,
                    revision: row.get(1)?,
                    parent_event_id: row.get(2)?,
                    local_ordinal: row.get(3)?,
                    mutation_generation: row.get(4)?,
                    coalesced: true,
                })
            },
        )
        .optional()?;
    if let Some(mut intent) = existing {
        intent.mutation_generation = intent
            .mutation_generation
            .checked_add(1)
            .filter(|generation| *generation <= MAX_SYNC_INTEGER)
            .ok_or(NoteSyncError::MutationGenerationOverflow)?;
        transaction.execute(
            "UPDATE cloud_sync_outbox
             SET operation=?1,updated_at=?2,deleted_at=?3,attempt_count=0,
                 last_error=NULL,next_attempt_at=NULL
             WHERE event_id=?4",
            rusqlite::params![
                input.operation.as_str(),
                input.updated_at,
                input.deleted_at,
                intent.event_id,
            ],
        )?;
        transaction.execute(
            "UPDATE cloud_sync_note_intents
             SET mutation_generation=?1,snapshot_json=?2,seal_state='pending',
                 seal_attempt_count=0,last_error_code=NULL,next_attempt_at=NULL,
                 state_updated_at=?3
             WHERE event_id=?4",
            rusqlite::params![
                intent.mutation_generation,
                input.snapshot_json,
                input.state_updated_at,
                intent.event_id,
            ],
        )?;
        return Ok(Some(intent));
    }

    let head = read_entity_sync_head(
        transaction,
        &binding.account_id,
        input.project_id,
        input.entity_id,
    )?;
    let revision = match &head {
        Some(value) => value
            .revision
            .checked_add(1)
            .filter(|revision| *revision <= MAX_SYNC_INTEGER)
            .ok_or(NoteSyncError::RevisionOverflow)?,
        None => 1,
    };
    let parent_event_id = head.map(|value| value.event_id);
    let local_ordinal = next_local_ordinal(transaction, &binding.account_id, &binding.device_id)?;
    let event_id = canonical_uuid_v4()?;
    transaction.execute(
        "INSERT INTO cloud_sync_outbox(
            event_id,account_id,device_id,project_id,entity_id,entity_type,
            operation,revision,updated_at,deleted_at,created_at,parent_event_id,
            local_ordinal,lifecycle
         ) VALUES(?1,?2,?3,?4,?5,'note',?6,?7,?8,?9,?10,?11,?12,'unsealed')",
        rusqlite::params![
            event_id,
            binding.account_id,
            binding.device_id,
            input.project_id,
            input.entity_id,
            input.operation.as_str(),
            revision,
            input.updated_at,
            input.deleted_at,
            input.state_updated_at,
            parent_event_id,
            local_ordinal,
        ],
    )?;
    transaction.execute(
        "INSERT INTO cloud_sync_note_intents(
            event_id,mutation_generation,snapshot_json,seal_state,
            seal_attempt_count,last_error_code,next_attempt_at,state_updated_at
         ) VALUES(?1,1,?2,'pending',0,NULL,NULL,?3)",
        rusqlite::params![event_id, input.snapshot_json, input.state_updated_at],
    )?;
    Ok(Some(PreparedNoteIntent {
        event_id,
        revision,
        parent_event_id,
        local_ordinal,
        mutation_generation: 1,
        coalesced: false,
    }))
}

pub(crate) fn list_unsealed_note_sync_intents(
    connection: &mut Connection,
    limit: u32,
    retry_blocked: bool,
) -> Result<Vec<UnsealedNoteSyncIntent>, NoteSyncError> {
    if !(1..=MAX_UNSEALED_INTENT_LIST_LIMIT).contains(&limit) {
        return Err(NoteSyncError::InvalidListLimit);
    }
    // Advancing the mode-specific cursor in the same transaction makes a
    // bounded pass durable without changing any intent or event lifecycle.
    let transaction = connection.transaction_with_behavior(TransactionBehavior::Immediate)?;
    let cursor_mode = if retry_blocked {
        "retry_blocked"
    } else {
        "regular"
    };
    let intents = {
        let mut statement = transaction.prepare(
            "WITH cursor AS (
                 SELECT account_id,device_id,local_ordinal,event_id
                 FROM cloud_sync_note_intent_cursors WHERE mode=?1
             )
             SELECT event.event_id,event.account_id,event.device_id,event.project_id,
                event.entity_id,event.entity_type,event.operation,event.revision,
                event.parent_event_id,event.updated_at,event.deleted_at,event.local_ordinal,
                intent.mutation_generation,intent.snapshot_json,intent.seal_state,
                intent.seal_attempt_count,intent.last_error_code,intent.next_attempt_at
         FROM cloud_sync_outbox AS event
         JOIN cloud_sync_note_intents AS intent ON intent.event_id=event.event_id
         CROSS JOIN cursor
         WHERE event.entity_type='note' AND event.lifecycle='unsealed'
           AND (
               intent.seal_state='pending'
               OR (
                   intent.seal_state='retryable_error'
                   AND (
                       intent.next_attempt_at IS NULL
                       OR intent.next_attempt_at <= strftime('%Y-%m-%dT%H:%M:%fZ','now')
                   )
               )
               OR (?2 AND intent.seal_state='blocked')
           )
         ORDER BY CASE WHEN cursor.event_id IS NULL OR
                    (event.account_id,event.device_id,event.local_ordinal,event.event_id) >
                    (cursor.account_id,cursor.device_id,cursor.local_ordinal,cursor.event_id)
                  THEN 0 ELSE 1 END,
                  event.account_id,event.device_id,event.local_ordinal,event.event_id
         LIMIT ?3",
        )?;
        let rows = statement.query_map(
            rusqlite::params![cursor_mode, retry_blocked, i64::from(limit)],
            |row| {
                Ok((
                    row.get::<_, String>(0)?,
                    row.get::<_, String>(1)?,
                    row.get::<_, String>(2)?,
                    row.get::<_, String>(3)?,
                    row.get::<_, String>(4)?,
                    row.get::<_, String>(5)?,
                    row.get::<_, String>(6)?,
                    row.get::<_, i64>(7)?,
                    row.get::<_, Option<String>>(8)?,
                    row.get::<_, String>(9)?,
                    row.get::<_, Option<String>>(10)?,
                    row.get::<_, i64>(11)?,
                    row.get::<_, i64>(12)?,
                    row.get::<_, String>(13)?,
                    row.get::<_, String>(14)?,
                    row.get::<_, i64>(15)?,
                    row.get::<_, Option<String>>(16)?,
                    row.get::<_, Option<String>>(17)?,
                ))
            },
        )?;
        rows.map(|row| {
            let (
                event_id,
                account_id,
                device_id,
                project_id,
                entity_id,
                entity_type,
                operation,
                revision,
                parent_event_id,
                updated_at,
                deleted_at,
                local_ordinal,
                mutation_generation,
                snapshot_json,
                seal_state,
                seal_attempt_count,
                last_error_code,
                next_attempt_at,
            ) = row?;
            if !(1..=MAX_SYNC_INTEGER).contains(&mutation_generation) {
                return Err(NoteSyncError::InvalidSealState(
                    "mutation generation exceeds the wire integer limit",
                ));
            }
            Ok(UnsealedNoteSyncIntent {
                event_id,
                account_id,
                device_id,
                project_id,
                entity_id,
                entity_type,
                operation: NoteSyncOperation::from_stored(&operation)?,
                revision,
                parent_event_id,
                updated_at,
                deleted_at,
                local_ordinal,
                mutation_generation,
                snapshot_json,
                seal_state: NoteSyncSealState::from_stored(&seal_state)?,
                seal_attempt_count,
                last_error_code,
                next_attempt_at,
            })
        })
        .collect::<Result<Vec<_>, NoteSyncError>>()?
    };
    if let Some(last) = intents.last() {
        let changed = transaction.execute(
            "UPDATE cloud_sync_note_intent_cursors
             SET account_id=?1,device_id=?2,local_ordinal=?3,event_id=?4,
                 updated_at=strftime('%Y-%m-%dT%H:%M:%fZ','now')
             WHERE mode=?5",
            rusqlite::params![
                last.account_id,
                last.device_id,
                last.local_ordinal,
                last.event_id,
                cursor_mode,
            ],
        )?;
        if changed != 1 {
            return Err(NoteSyncError::InvalidSealState("missing fairness cursor"));
        }
    }
    transaction.commit()?;
    Ok(intents)
}

/// Lists one account's sealed Note events in a dependency-safe order. Its only
/// durable side effect is the per-account device round-robin cursor.
/// The ciphertext batch cap is applied before the DTOs leave SQLite.
pub(crate) fn list_sealed_note_sync_outbox(
    connection: &mut Connection,
    account_id: &str,
    limit: u32,
) -> Result<Vec<SealedNoteSyncOutboxItem>, NoteSyncError> {
    if account_id.is_empty() || account_id.len() > 512 {
        return Err(NoteSyncError::InvalidOutboxRead("invalid account scope"));
    }
    if !(1..=MAX_SEALED_OUTBOX_LIST_LIMIT).contains(&limit) {
        return Err(NoteSyncError::InvalidListLimit);
    }

    let transaction = connection.transaction_with_behavior(TransactionBehavior::Deferred)?;
    let rows = {
        let mut statement = transaction.prepare(
            "WITH eligible AS (
                SELECT event.* FROM cloud_sync_outbox AS event
                WHERE event.account_id=?1 AND event.entity_type='note' AND event.lifecycle='sealed'
                  AND (event.next_attempt_at IS NULL OR event.next_attempt_at <= strftime('%Y-%m-%dT%H:%M:%fZ','now'))
                  AND (event.parent_event_id IS NULL OR EXISTS (
                       SELECT 1 FROM cloud_sync_outbox AS eligible_parent
                       WHERE eligible_parent.event_id=event.parent_event_id
                         AND (eligible_parent.lifecycle='accepted' OR (
                              eligible_parent.lifecycle='sealed'
                              AND (eligible_parent.next_attempt_at IS NULL OR eligible_parent.next_attempt_at <= strftime('%Y-%m-%dT%H:%M:%fZ','now'))
                         ))
                  ))
             ), selected_device AS (
                SELECT device_id FROM eligible
                WHERE device_id > COALESCE((SELECT device_id FROM cloud_sync_note_upload_cursors WHERE account_id=?1), '')
                ORDER BY device_id LIMIT 1
             ), chosen_device AS (
                SELECT device_id FROM selected_device
                UNION ALL
                SELECT device_id FROM eligible
                WHERE NOT EXISTS (SELECT 1 FROM selected_device)
                ORDER BY device_id LIMIT 1
             )
             SELECT event.event_id,event.account_id,event.device_id,event.project_id,
                event.entity_id,event.entity_type,event.operation,event.revision,
                event.parent_event_id,event.updated_at,event.deleted_at,event.local_ordinal,
                object.crypto_version,object.aad_version,object.nonce,object.ciphertext,
                (SELECT count(*) FROM cloud_sync_event_objects AS duplicate
                 WHERE duplicate.event_id=event.event_id),
                (SELECT count(*) FROM cloud_sync_note_intents AS intent
                 WHERE intent.event_id=event.event_id),
                parent.account_id,parent.project_id,parent.entity_id,parent.entity_type,
                parent.revision,parent.lifecycle
             FROM eligible AS event
             LEFT JOIN cloud_sync_event_objects AS object
               ON object.account_id=event.account_id AND object.event_id=event.event_id
             LEFT JOIN cloud_sync_outbox AS parent ON parent.event_id=event.parent_event_id
             WHERE event.device_id=(SELECT device_id FROM chosen_device)
             ORDER BY event.revision,event.device_id,event.local_ordinal,event.event_id
             LIMIT ?2",
        )?;
        let rows = statement
            .query_map(rusqlite::params![account_id, i64::from(limit)], |row| {
                Ok((
                    row.get::<_, String>(0)?,
                    row.get::<_, String>(1)?,
                    row.get::<_, String>(2)?,
                    row.get::<_, String>(3)?,
                    row.get::<_, String>(4)?,
                    row.get::<_, String>(5)?,
                    row.get::<_, String>(6)?,
                    row.get::<_, i64>(7)?,
                    row.get::<_, Option<String>>(8)?,
                    row.get::<_, String>(9)?,
                    row.get::<_, Option<String>>(10)?,
                    row.get::<_, i64>(11)?,
                    row.get::<_, Option<i64>>(12)?,
                    row.get::<_, Option<i64>>(13)?,
                    row.get::<_, Option<Vec<u8>>>(14)?,
                    row.get::<_, Option<Vec<u8>>>(15)?,
                    row.get::<_, i64>(16)?,
                    row.get::<_, i64>(17)?,
                    row.get::<_, Option<String>>(18)?,
                    row.get::<_, Option<String>>(19)?,
                    row.get::<_, Option<String>>(20)?,
                    row.get::<_, Option<String>>(21)?,
                    row.get::<_, Option<i64>>(22)?,
                    row.get::<_, Option<String>>(23)?,
                ))
            })?
            .collect::<Result<Vec<_>, _>>()?;
        rows
    };

    let mut items = Vec::with_capacity(rows.len());
    let mut ciphertext_total = 0_usize;
    for row in rows {
        let (
            event_id,
            stored_account_id,
            device_id,
            project_id,
            entity_id,
            entity_type,
            operation,
            revision,
            parent_event_id,
            updated_at,
            deleted_at,
            local_ordinal,
            crypto_version,
            aad_version,
            nonce,
            ciphertext,
            object_count,
            sidecar_count,
            parent_account_id,
            parent_project_id,
            parent_entity_id,
            parent_entity_type,
            parent_revision,
            parent_lifecycle,
        ) = row;
        if sidecar_count != 0 || object_count != 1 {
            return Err(NoteSyncError::InvalidOutboxRead(
                "sealed event/object relation is inconsistent",
            ));
        }
        let (crypto_version, aad_version, nonce, ciphertext) =
            match (crypto_version, aad_version, nonce, ciphertext) {
                (Some(crypto_version), Some(aad_version), Some(nonce), Some(ciphertext)) => {
                    (crypto_version, aad_version, nonce, ciphertext)
                }
                _ => return Err(NoteSyncError::SealedObjectMissing),
            };
        if crypto_version != SUPPORTED_CRYPTO_VERSION
            || aad_version != SUPPORTED_AAD_VERSION
            || nonce.len() != 24
            || !(16..=MAX_ENCRYPTED_SYNC_CIPHERTEXT_BYTES).contains(&ciphertext.len())
        {
            return Err(NoteSyncError::InvalidOutboxRead(
                "sealed encrypted object is invalid",
            ));
        }
        match (revision, parent_event_id.as_deref()) {
            (1, None) => {}
            (1, Some(_)) | (_, None) => {
                return Err(NoteSyncError::InvalidOutboxRead(
                    "invalid revision dependency",
                ))
            }
            (_, Some(_)) => {
                if parent_account_id.as_deref() != Some(account_id)
                    || parent_project_id.as_deref() != Some(project_id.as_str())
                    || parent_entity_id.as_deref() != Some(entity_id.as_str())
                    || parent_entity_type.as_deref() != Some("note")
                    || parent_revision != Some(revision - 1)
                    || !matches!(
                        parent_lifecycle.as_deref(),
                        Some("sealed") | Some("accepted")
                    )
                {
                    return Err(NoteSyncError::InvalidOutboxRead(
                        "parent dependency is unavailable",
                    ));
                }
            }
        }
        let next_total = ciphertext_total.checked_add(ciphertext.len()).ok_or(
            NoteSyncError::InvalidOutboxRead("ciphertext batch size overflow"),
        )?;
        if next_total > MAX_ENCRYPTED_SYNC_BATCH_CIPHERTEXT_BYTES {
            break;
        }
        ciphertext_total = next_total;
        items.push(SealedNoteSyncOutboxItem {
            event_id,
            account_id: stored_account_id,
            device_id,
            project_id,
            entity_id,
            entity_type,
            operation: NoteSyncOperation::from_stored(&operation)?,
            revision,
            parent_event_id,
            updated_at,
            deleted_at,
            local_ordinal,
            envelope: EncryptedNoteSyncEnvelope {
                crypto_version,
                aad_version,
                nonce: encode_canonical_base64url(&nonce),
                ciphertext: encode_canonical_base64url(&ciphertext),
            },
        });
    }
    if serde_json::to_vec(&items)
        .map_err(|_| NoteSyncError::InvalidOutboxRead("could not encode outbox DTO"))?
        .len()
        > MAX_ENCRYPTED_SYNC_WIRE_BODY_BYTES
    {
        return Err(NoteSyncError::InvalidOutboxRead(
            "outbox DTO exceeds wire body limit",
        ));
    }
    if let Some(item) = items.first() {
        transaction.execute(
            "INSERT INTO cloud_sync_note_upload_cursors(account_id,device_id,updated_at)
             VALUES(?1,?2,strftime('%Y-%m-%dT%H:%M:%fZ','now'))
             ON CONFLICT(account_id) DO UPDATE SET device_id=excluded.device_id,updated_at=excluded.updated_at",
            rusqlite::params![account_id, item.device_id],
        )?;
    }
    transaction.commit()?;
    Ok(items)
}

pub(crate) fn record_note_sync_seal_failure(
    connection: &mut Connection,
    command: &RecordNoteSyncSealFailureCommand,
) -> Result<RecordNoteSyncSealFailureResult, NoteSyncError> {
    if command.event_id.is_empty()
        || !(1..=MAX_SYNC_INTEGER).contains(&command.expected_mutation_generation)
    {
        return Err(NoteSyncError::InvalidSealState("invalid failure identity"));
    }
    let transaction = connection.transaction_with_behavior(TransactionBehavior::Immediate)?;
    let lifecycle = transaction
        .query_row(
            "SELECT lifecycle FROM cloud_sync_outbox
             WHERE event_id=?1 AND entity_type='note'",
            [&command.event_id],
            |row| row.get::<_, String>(0),
        )
        .optional()?
        .ok_or(NoteSyncError::MissingEvent)?;
    if lifecycle == "sealed" {
        ensure_consistent_sealed_event(&transaction, &command.event_id)?;
        transaction.commit()?;
        return Ok(RecordNoteSyncSealFailureResult::AlreadySealed);
    }
    if lifecycle != "unsealed" {
        return Err(NoteSyncError::UnexpectedLifecycle);
    }
    let current_generation = transaction
        .query_row(
            "SELECT mutation_generation FROM cloud_sync_note_intents WHERE event_id=?1",
            [&command.event_id],
            |row| row.get::<_, i64>(0),
        )
        .optional()?
        .ok_or(NoteSyncError::MissingIntent)?;
    if current_generation != command.expected_mutation_generation {
        transaction.commit()?;
        return Ok(RecordNoteSyncSealFailureResult::StaleGeneration);
    }
    let attempt_count = transaction.query_row(
        "SELECT seal_attempt_count FROM cloud_sync_note_intents WHERE event_id=?1",
        [&command.event_id],
        |row| row.get::<_, i64>(0),
    )?;
    let next_attempt_count = attempt_count
        .checked_add(1)
        .filter(|value| *value <= MAX_SYNC_INTEGER)
        .ok_or(NoteSyncError::SealAttemptOverflow)?;
    let seal_state = command.error_code.seal_state();
    let next_attempt_seconds = (seal_state == NoteSyncSealState::RetryableError)
        .then(|| retry_backoff_seconds(next_attempt_count));
    let changed = transaction.execute(
        "UPDATE cloud_sync_note_intents
         SET seal_state=?1,seal_attempt_count=?2,last_error_code=?3,
             next_attempt_at=CASE WHEN ?4 IS NULL THEN NULL ELSE
                 strftime('%Y-%m-%dT%H:%M:%fZ','now',printf('+%d seconds',?4)) END,
             state_updated_at=strftime('%Y-%m-%dT%H:%M:%fZ','now')
         WHERE event_id=?5 AND mutation_generation=?6",
        rusqlite::params![
            match seal_state {
                NoteSyncSealState::Pending => "pending",
                NoteSyncSealState::RetryableError => "retryable_error",
                NoteSyncSealState::Blocked => "blocked",
                NoteSyncSealState::InvariantError => "invariant_error",
            },
            next_attempt_count,
            command.error_code.as_str(),
            next_attempt_seconds,
            command.event_id,
            command.expected_mutation_generation,
        ],
    )?;
    if changed != 1 {
        return Err(NoteSyncError::MissingIntent);
    }
    transaction.commit()?;
    Ok(RecordNoteSyncSealFailureResult::Recorded)
}

pub(crate) fn commit_sealed_note_sync_event(
    connection: &mut Connection,
    command: &CommitSealedNoteSyncEventCommand,
) -> Result<CommitSealedNoteSyncEventResult, NoteSyncError> {
    if command.event_id.is_empty()
        || !(1..=MAX_SYNC_INTEGER).contains(&command.expected_mutation_generation)
    {
        return Err(NoteSyncError::InvalidSealState("invalid sealing identity"));
    }
    let envelope = decode_encrypted_note_sync_envelope(&command.envelope)?;
    let transaction = connection.transaction_with_behavior(TransactionBehavior::Immediate)?;
    let event = transaction
        .query_row(
            "SELECT account_id,entity_type,lifecycle FROM cloud_sync_outbox WHERE event_id=?1",
            [&command.event_id],
            |row| {
                Ok((
                    row.get::<_, String>(0)?,
                    row.get::<_, String>(1)?,
                    row.get::<_, String>(2)?,
                ))
            },
        )
        .optional()?
        .ok_or(NoteSyncError::MissingEvent)?;
    let (account_id, entity_type, lifecycle) = event;
    if entity_type != "note" {
        return Err(NoteSyncError::UnexpectedLifecycle);
    }
    if lifecycle == "sealed" {
        ensure_matching_sealed_envelope(&transaction, &account_id, &command.event_id, &envelope)?;
        transaction.commit()?;
        return Ok(CommitSealedNoteSyncEventResult::AlreadySealed);
    }
    if lifecycle != "unsealed" {
        return Err(NoteSyncError::UnexpectedLifecycle);
    }
    let current_generation = transaction
        .query_row(
            "SELECT mutation_generation FROM cloud_sync_note_intents WHERE event_id=?1",
            [&command.event_id],
            |row| row.get::<_, i64>(0),
        )
        .optional()?
        .ok_or(NoteSyncError::MissingIntent)?;
    if current_generation != command.expected_mutation_generation {
        transaction.commit()?;
        return Ok(CommitSealedNoteSyncEventResult::StaleGeneration);
    }
    if transaction
        .query_row(
            "SELECT 1 FROM cloud_sync_event_objects WHERE event_id=?1",
            [&command.event_id],
            |_| Ok(()),
        )
        .optional()?
        .is_some()
    {
        return Err(NoteSyncError::ConflictingEncryptedObject);
    }
    transaction.execute(
        "INSERT INTO cloud_sync_event_objects(
            account_id,event_id,crypto_version,aad_version,nonce,ciphertext,stored_at
         ) VALUES(?1,?2,?3,?4,?5,?6,strftime('%Y-%m-%dT%H:%M:%fZ','now'))",
        rusqlite::params![
            account_id,
            command.event_id,
            envelope.crypto_version,
            envelope.aad_version,
            envelope.nonce,
            envelope.ciphertext,
        ],
    )?;
    let deleted = transaction.execute(
        "DELETE FROM cloud_sync_note_intents
         WHERE event_id=?1 AND mutation_generation=?2",
        rusqlite::params![command.event_id, command.expected_mutation_generation],
    )?;
    if deleted != 1 {
        return Err(NoteSyncError::MissingIntent);
    }
    let updated = transaction.execute(
        "UPDATE cloud_sync_outbox SET lifecycle='sealed'
         WHERE event_id=?1 AND entity_type='note' AND lifecycle='unsealed'",
        [&command.event_id],
    )?;
    if updated != 1 {
        return Err(NoteSyncError::UnexpectedLifecycle);
    }
    transaction.commit()?;
    Ok(CommitSealedNoteSyncEventResult::Sealed)
}

fn valid_inbound_identity(value: &str, maximum: usize) -> bool {
    !value.is_empty() && value.len() <= maximum
}

fn validate_pull_scope(
    transaction: &Transaction<'_>, account_id: &str, device_id: &str, canonical_user_id: &str,
) -> Result<(), NoteSyncError> {
    if !valid_inbound_identity(account_id, 512) || device_id.len() != 36 || canonical_user_id.len() != 36 {
        return Err(NoteSyncError::InvalidEnvelope("invalid inbox scope"));
    }
    let bound: Option<String> = transaction.query_row(
        "SELECT canonical_user_id FROM cloud_account_bindings WHERE local_account_id=?1",
        [account_id], |row| row.get(0),
    ).optional()?;
    if bound.as_deref() != Some(canonical_user_id) {
        return Err(NoteSyncError::InvalidEnvelope("account binding mismatch"));
    }
    let stored_device: Option<String> = transaction.query_row(
        "SELECT device_id FROM cloud_sync_state WHERE account_id=?1", [account_id], |row| row.get(0),
    ).optional()?;
    if stored_device.as_deref() != Some(device_id) {
        return Err(NoteSyncError::InvalidEnvelope("pulling device mismatch"));
    }
    Ok(())
}

pub(crate) fn read_note_sync_pull_state(
    connection: &mut Connection, command: &ReadNoteSyncPullStateCommand,
) -> Result<NoteSyncPullState, NoteSyncError> {
    let transaction = connection.transaction_with_behavior(TransactionBehavior::Immediate)?;
    validate_pull_scope(&transaction, &command.account_id, &command.device_id, &command.canonical_user_id)?;
    let state = transaction.query_row(
        "SELECT pull_cursor,ack_cursor FROM cloud_sync_state WHERE account_id=?1", [&command.account_id],
        |row| Ok(NoteSyncPullState { pull_cursor: row.get(0)?, ack_cursor: row.get(1)? }),
    )?;
    transaction.commit()?;
    Ok(state)
}

fn contiguous_applied_ack_prefix(
    transaction: &Transaction<'_>, account_id: &str, ack_cursor: i64, pull_cursor: i64,
) -> Result<i64, NoteSyncError> {
    if !(0..=MAX_SYNC_INTEGER).contains(&ack_cursor)
        || !(0..=MAX_SYNC_INTEGER).contains(&pull_cursor)
        || ack_cursor > pull_cursor {
        return Err(NoteSyncError::InvalidEnvelope("invalid durable ACK state"));
    }
    let mut candidate = ack_cursor;
    while candidate < pull_cursor {
        let next = candidate.checked_add(1).ok_or(NoteSyncError::InvalidEnvelope("ACK cursor overflow"))?;
        let state: Option<String> = transaction.query_row(
            "SELECT state FROM cloud_sync_inbox WHERE account_id=?1 AND server_sequence=?2",
            rusqlite::params![account_id, next], |row| row.get(0),
        ).optional()?;
        if state.as_deref() != Some("applied") { break; }
        candidate = next;
    }
    Ok(candidate)
}

/// Reads the largest contiguous, durably applied inbound prefix. It neither
/// changes SQLite state nor proves a remote transport acknowledgement.
pub(crate) fn prepare_note_sync_ack(
    connection: &mut Connection, command: &PrepareNoteSyncAckCommand,
) -> Result<NoteSyncAckCandidate, NoteSyncError> {
    let transaction = connection.transaction_with_behavior(TransactionBehavior::Immediate)?;
    validate_pull_scope(&transaction, &command.account_id, &command.device_id, &command.canonical_user_id)?;
    let (pull_cursor, ack_cursor): (i64, i64) = transaction.query_row(
        "SELECT pull_cursor,ack_cursor FROM cloud_sync_state WHERE account_id=?1", [&command.account_id],
        |row| Ok((row.get(0)?, row.get(1)?)),
    )?;
    let candidate_cursor = contiguous_applied_ack_prefix(&transaction, &command.account_id, ack_cursor, pull_cursor)?;
    transaction.commit()?;
    Ok(NoteSyncAckCandidate { current_ack_cursor: ack_cursor, candidate_cursor })
}

/// Records a previously confirmed remote ACK only if the local proof is still
/// valid. Transport remains outside this Rust/SQLite substrate.
pub(crate) fn commit_note_sync_ack(
    connection: &mut Connection, command: &CommitNoteSyncAckCommand,
) -> Result<CommitNoteSyncAckResult, NoteSyncError> {
    if !(0..=MAX_SYNC_INTEGER).contains(&command.expected_old_ack_cursor)
        || !(0..=MAX_SYNC_INTEGER).contains(&command.acknowledged_cursor)
        || command.acknowledged_cursor < command.expected_old_ack_cursor {
        return Err(NoteSyncError::InvalidEnvelope("invalid ACK advancement command"));
    }
    let transaction = connection.transaction_with_behavior(TransactionBehavior::Immediate)?;
    validate_pull_scope(&transaction, &command.account_id, &command.device_id, &command.canonical_user_id)?;
    let (pull_cursor, current_ack_cursor): (i64, i64) = transaction.query_row(
        "SELECT pull_cursor,ack_cursor FROM cloud_sync_state WHERE account_id=?1", [&command.account_id],
        |row| Ok((row.get(0)?, row.get(1)?)),
    )?;
    if command.acknowledged_cursor > pull_cursor {
        return Err(NoteSyncError::InvalidEnvelope("ACK exceeds pull cursor"));
    }
    if current_ack_cursor == command.acknowledged_cursor {
        transaction.commit()?;
        return Ok(CommitNoteSyncAckResult::AlreadyAcknowledged);
    }
    if current_ack_cursor > command.acknowledged_cursor {
        transaction.commit()?;
        return Ok(CommitNoteSyncAckResult::AlreadyAdvanced);
    }
    if current_ack_cursor != command.expected_old_ack_cursor {
        transaction.commit()?;
        return Ok(CommitNoteSyncAckResult::Stale);
    }
    let safe_candidate = contiguous_applied_ack_prefix(&transaction, &command.account_id, current_ack_cursor, pull_cursor)?;
    if safe_candidate < command.acknowledged_cursor {
        return Err(NoteSyncError::InvalidEnvelope("ACK skips unresolved inbox event"));
    }
    let updated = transaction.execute(
        "UPDATE cloud_sync_state SET ack_cursor=?1,updated_at=strftime('%Y-%m-%dT%H:%M:%fZ','now') WHERE account_id=?2 AND ack_cursor=?3",
        rusqlite::params![command.acknowledged_cursor, command.account_id, current_ack_cursor],
    )?;
    if updated != 1 { return Err(NoteSyncError::InvalidEnvelope("ACK cursor compare-and-swap failed")); }
    transaction.commit()?;
    Ok(CommitNoteSyncAckResult::Advanced)
}

/// Lists one bounded page of durable received Note events.  Scope validation is
/// intentionally repeated here because this is a separate IPC boundary from
/// pull receipt.  No transaction is retained while TypeScript decrypts bytes.
pub(crate) fn list_received_note_sync_inbox(
    connection: &Connection, command: &ListReceivedNoteSyncInboxCommand,
) -> Result<Vec<ReceivedNoteSyncInboxItem>, NoteSyncError> {
    if !(1..=MAX_RECEIVED_INBOX_LIST_LIMIT).contains(&command.limit) {
        return Err(NoteSyncError::InvalidListLimit);
    }
    let transaction = connection.unchecked_transaction()?;
    validate_pull_scope(&transaction, &command.account_id, &command.device_id, &command.canonical_user_id)?;
    let mut statement = transaction.prepare(
        "SELECT inbox.event_id,inbox.server_sequence,inbox.device_id,inbox.project_id,
                inbox.entity_id,inbox.entity_type,inbox.operation,inbox.sync_revision,
                inbox.updated_at,inbox.deleted_at,object.crypto_version,object.aad_version,
                object.nonce,object.ciphertext
         FROM cloud_sync_inbox AS inbox
         LEFT JOIN cloud_sync_event_objects AS object
           ON object.account_id=inbox.account_id AND object.event_id=inbox.event_id
         WHERE inbox.account_id=?1 AND inbox.entity_type='note' AND inbox.state='received'
         ORDER BY inbox.server_sequence ASC LIMIT ?2",
    )?;
    let rows = statement.query_map(rusqlite::params![command.account_id, command.limit], |row| {
        Ok((
            row.get::<_, String>(0)?, row.get::<_, i64>(1)?, row.get::<_, String>(2)?,
            row.get::<_, String>(3)?, row.get::<_, String>(4)?, row.get::<_, String>(5)?,
            row.get::<_, String>(6)?, row.get::<_, i64>(7)?, row.get::<_, String>(8)?,
            row.get::<_, Option<String>>(9)?, row.get::<_, Option<i64>>(10)?,
            row.get::<_, Option<i64>>(11)?, row.get::<_, Option<Vec<u8>>>(12)?,
            row.get::<_, Option<Vec<u8>>>(13)?,
        ))
    })?;
    let mut items = Vec::new();
    let mut aggregate = 0usize;
    for row in rows {
        let (event_id, server_sequence, source_device_id, project_id, entity_id, entity_type,
            operation, revision, updated_at, deleted_at, crypto_version, aad_version, nonce, ciphertext) = row?;
        let (crypto_version, aad_version, nonce, ciphertext) = match (crypto_version, aad_version, nonce, ciphertext) {
            (Some(version), Some(aad), Some(nonce), Some(ciphertext)) => (version, aad, nonce, ciphertext),
            _ => return Err(NoteSyncError::SealedObjectMissing),
        };
        let envelope = decode_encrypted_note_sync_envelope(&EncryptedNoteSyncEnvelope {
            crypto_version,
            aad_version,
            nonce: encode_canonical_base64url(&nonce),
            ciphertext: encode_canonical_base64url(&ciphertext),
        })?;
        aggregate = aggregate.checked_add(envelope.ciphertext.len())
            .ok_or(NoteSyncError::InvalidEnvelope("inbox object overflow"))?;
        if aggregate > MAX_ENCRYPTED_SYNC_BATCH_CIPHERTEXT_BYTES {
            return Err(NoteSyncError::InvalidEnvelope("inbox aggregate too large"));
        }
        if !matches!(operation.as_str(), "upsert" | "delete") {
            return Err(NoteSyncError::InvalidEnvelope("unsupported Note operation"));
        }
        items.push(ReceivedNoteSyncInboxItem {
            event_id, server_sequence, source_device_id, project_id, entity_id, entity_type,
            operation, revision, updated_at, deleted_at,
            envelope: StoredEncryptedNoteSyncEnvelope {
                crypto_version: envelope.crypto_version,
                aad_version: envelope.aad_version,
                nonce: encode_canonical_base64url(&envelope.nonce),
                ciphertext: encode_canonical_base64url(&envelope.ciphertext),
            },
        });
    }
    drop(statement);
    transaction.commit()?;
    Ok(items)
}

pub(crate) fn commit_note_sync_inbound_page(
    connection: &mut Connection, command: &CommitNoteSyncInboundPageCommand,
) -> Result<CommitNoteSyncInboundPageResult, NoteSyncError> {
    if command.items.len() > 200 || !(0..=MAX_SYNC_INTEGER).contains(&command.expected_cursor)
        || !(0..=MAX_SYNC_INTEGER).contains(&command.next_cursor) {
        return Err(NoteSyncError::InvalidEnvelope("invalid inbox cursor or page size"));
    }
    if command.items.is_empty() && (command.next_cursor != command.expected_cursor || command.has_more) {
        return Err(NoteSyncError::InvalidEnvelope("invalid empty inbox page"));
    }
    let transaction = connection.transaction_with_behavior(TransactionBehavior::Immediate)?;
    validate_pull_scope(&transaction, &command.account_id, &command.device_id, &command.canonical_user_id)?;
    let current: i64 = transaction.query_row(
        "SELECT pull_cursor FROM cloud_sync_state WHERE account_id=?1", [&command.account_id], |row| row.get(0),
    )?;
    // A lost IPC result may replay the exact page after its transaction
    // committed.  Permit only that non-regressing shape; every item is still
    // compared below and any missing/conflicting row rolls the transaction back.
    let exact_replay = current == command.next_cursor && current > command.expected_cursor;
    if current != command.expected_cursor && !exact_replay {
        return Err(NoteSyncError::InvalidEnvelope("stale pull cursor"));
    }
    let mut previous = if exact_replay { 0 } else { command.expected_cursor };
    let mut aggregate = 0usize;
    let mut new_events = 0u32;
    let mut replayed_events = 0u32;
    for item in &command.items {
        if item.server_sequence <= previous || item.server_sequence > MAX_SYNC_INTEGER
            || !valid_inbound_identity(&item.event_id, 36) || item.source_device_id.len() != 36
            || !valid_inbound_identity(&item.project_id, 512) || !valid_inbound_identity(&item.entity_id, 512)
            || !valid_inbound_identity(&item.entity_type, 128) || !(1..=MAX_SYNC_INTEGER).contains(&item.revision)
            || !valid_note_sync_timestamp(&item.updated_at)
            || item.deleted_at.as_deref().is_some_and(|value| !valid_note_sync_timestamp(value))
            || !matches!(item.operation.as_str(), "upsert" | "delete" | "event")
            || (item.operation == "delete") != item.deleted_at.is_some() {
            return Err(NoteSyncError::InvalidEnvelope("invalid inbound event"));
        }
        if item.entity_type == "note" && item.envelope.is_none() {
            return Err(NoteSyncError::InvalidEnvelope("note object missing"));
        }
        let decoded = item.envelope.as_ref().map(decode_encrypted_note_sync_envelope).transpose()?;
        if let Some(envelope) = &decoded {
            aggregate = aggregate.checked_add(envelope.ciphertext.len()).ok_or(NoteSyncError::InvalidEnvelope("inbox object overflow"))?;
            if aggregate > MAX_ENCRYPTED_SYNC_BATCH_CIPHERTEXT_BYTES { return Err(NoteSyncError::InvalidEnvelope("inbox aggregate too large")); }
        }
        let existing: Option<(i64, String, String, String, String, String, i64, String, Option<String>)> = transaction.query_row(
            "SELECT server_sequence,device_id,project_id,entity_id,entity_type,operation,sync_revision,updated_at,deleted_at FROM cloud_sync_inbox WHERE account_id=?1 AND event_id=?2",
            rusqlite::params![command.account_id, item.event_id],
            |row| Ok((row.get(0)?,row.get(1)?,row.get(2)?,row.get(3)?,row.get(4)?,row.get(5)?,row.get(6)?,row.get(7)?,row.get(8)?)),
        ).optional()?;
        if let Some(row) = existing {
            if row != (item.server_sequence, item.source_device_id.clone(), item.project_id.clone(), item.entity_id.clone(), item.entity_type.clone(), item.operation.clone(), item.revision, item.updated_at.clone(), item.deleted_at.clone()) {
                return Err(NoteSyncError::InvalidEnvelope("conflicting inbox replay"));
            }
            replayed_events += 1;
        } else {
            if exact_replay {
                return Err(NoteSyncError::InvalidEnvelope("incomplete inbox replay"));
            }
            let state = if item.entity_type == "note" { "received" } else { "unknown_entity" };
            transaction.execute("INSERT INTO cloud_sync_inbox(account_id,event_id,server_sequence,device_id,project_id,entity_id,entity_type,operation,sync_revision,updated_at,deleted_at,state,received_at) VALUES(?1,?2,?3,?4,?5,?6,?7,?8,?9,?10,?11,?12,strftime('%Y-%m-%dT%H:%M:%fZ','now'))",
                rusqlite::params![command.account_id,item.event_id,item.server_sequence,item.source_device_id,item.project_id,item.entity_id,item.entity_type,item.operation,item.revision,item.updated_at,item.deleted_at,state])?;
            new_events += 1;
        }
        if let Some(envelope) = decoded {
            let object: Option<(i64,i64,Vec<u8>,Vec<u8>)> = transaction.query_row(
                "SELECT crypto_version,aad_version,nonce,ciphertext FROM cloud_sync_event_objects WHERE account_id=?1 AND event_id=?2",
                rusqlite::params![command.account_id,item.event_id], |row| Ok((row.get(0)?,row.get(1)?,row.get(2)?,row.get(3)?)),
            ).optional()?;
            if let Some(object) = object {
                if object != (envelope.crypto_version,envelope.aad_version,envelope.nonce,envelope.ciphertext) { return Err(NoteSyncError::ConflictingEncryptedObject); }
            } else {
                transaction.execute("INSERT INTO cloud_sync_event_objects(account_id,event_id,crypto_version,aad_version,nonce,ciphertext,stored_at) VALUES(?1,?2,?3,?4,?5,?6,strftime('%Y-%m-%dT%H:%M:%fZ','now'))", rusqlite::params![command.account_id,item.event_id,envelope.crypto_version,envelope.aad_version,envelope.nonce,envelope.ciphertext])?;
            }
        }
        previous = item.server_sequence;
    }
    if !command.items.is_empty() && command.next_cursor != previous { return Err(NoteSyncError::InvalidEnvelope("next cursor mismatch")); }
    if !exact_replay {
        transaction.execute("UPDATE cloud_sync_state SET pull_cursor=?1,updated_at=strftime('%Y-%m-%dT%H:%M:%fZ','now') WHERE account_id=?2 AND pull_cursor=?3", rusqlite::params![command.next_cursor,command.account_id,command.expected_cursor])?;
    }
    transaction.commit()?;
    Ok(CommitNoteSyncInboundPageResult { committed_cursor: command.next_cursor, new_events, replayed_events, has_more: command.has_more })
}

/// Stores server receipts and transitions exactly their sealed Note events in
/// the same SQLite transaction. A retry of an identical receipt is harmless;
/// any conflicting receipt rolls back the complete batch.
pub(crate) fn commit_note_sync_upload_acceptance(
    connection: &mut Connection,
    command: &CommitNoteSyncUploadAcceptanceCommand,
) -> Result<Vec<CommitNoteSyncUploadAcceptanceResult>, NoteSyncError> {
    if command.account_id.is_empty()
        || command.account_id.len() > 512
        || command.device_id.len() != 36
        || command.receipts.is_empty()
        || command.receipts.len() > MAX_SEALED_OUTBOX_LIST_LIMIT as usize
    {
        return Err(NoteSyncError::InvalidSealState(
            "invalid upload acceptance command",
        ));
    }
    let transaction = connection.transaction_with_behavior(TransactionBehavior::Immediate)?;
    let mut results = Vec::with_capacity(command.receipts.len());
    for receipt in &command.receipts {
        if receipt.event_id.len() != 36
            || !(1..=MAX_SYNC_INTEGER).contains(&receipt.server_sequence)
        {
            return Err(NoteSyncError::InvalidSealState("invalid upload receipt"));
        }
        let (account_id, device_id, lifecycle): (String, String, String) = transaction.query_row(
            "SELECT account_id,device_id,lifecycle FROM cloud_sync_outbox WHERE event_id=?1 AND entity_type='note'",
            [&receipt.event_id],
            |row| Ok((row.get(0)?, row.get(1)?, row.get(2)?)),
        ).optional()?.ok_or(NoteSyncError::MissingEvent)?;
        if account_id != command.account_id || device_id != command.device_id {
            return Err(NoteSyncError::ConflictingUploadReceipt);
        }
        let stored: Option<i64> = transaction.query_row(
            "SELECT server_sequence,duplicate FROM cloud_sync_upload_receipts WHERE event_id=?1",
            [&receipt.event_id], |row| row.get(0),
        ).optional()?;
        if let Some(sequence) = stored {
            // `duplicate` describes this HTTP response.  The persisted receipt
            // keeps its first diagnostic value; idempotency is the stable server
            // sequence for this event/account/device identity.
            if sequence != receipt.server_sequence {
                return Err(NoteSyncError::ConflictingUploadReceipt);
            }
            if lifecycle != "accepted" {
                return Err(NoteSyncError::UnexpectedLifecycle);
            }
            results.push(CommitNoteSyncUploadAcceptanceResult::AlreadyAccepted);
            continue;
        }
        if lifecycle != "sealed" {
            return Err(NoteSyncError::UnexpectedLifecycle);
        }
        ensure_consistent_sealed_event(&transaction, &receipt.event_id)?;
        transaction.execute(
            "INSERT INTO cloud_sync_upload_receipts(account_id,event_id,device_id,server_sequence,duplicate,accepted_at)
             VALUES(?1,?2,?3,?4,?5,strftime('%Y-%m-%dT%H:%M:%fZ','now'))",
            rusqlite::params![command.account_id, receipt.event_id, command.device_id,
                receipt.server_sequence, i64::from(receipt.duplicate)],
        )?;
        let changed = transaction.execute(
            "UPDATE cloud_sync_outbox SET lifecycle='accepted'
             WHERE event_id=?1 AND entity_type='note' AND lifecycle='sealed'",
            [&receipt.event_id],
        )?;
        if changed != 1 {
            return Err(NoteSyncError::UnexpectedLifecycle);
        }
        results.push(CommitNoteSyncUploadAcceptanceResult::Accepted);
    }
    transaction.commit()?;
    Ok(results)
}

/// Durably backs off a failed already-sealed upload without touching its opaque
/// object. Permanent protocol failures are retained as rejected evidence.
pub(crate) fn record_note_sync_upload_failure(
    connection: &mut Connection,
    command: &RecordNoteSyncUploadFailureCommand,
) -> Result<(), NoteSyncError> {
    if command.account_id.is_empty()
        || command.account_id.len() > 512
        || command.device_id.len() != 36
        || command.event_ids.is_empty()
        || command.event_ids.len() > MAX_SEALED_OUTBOX_LIST_LIMIT as usize
    {
        return Err(NoteSyncError::InvalidSealState(
            "invalid upload failure command",
        ));
    }
    let transaction = connection.transaction_with_behavior(TransactionBehavior::Immediate)?;
    for event_id in &command.event_ids {
        if event_id.len() != 36 {
            return Err(NoteSyncError::InvalidSealState(
                "invalid upload failure event",
            ));
        }
        let changed = if command.error_code.retryable() {
            transaction.execute(
                "UPDATE cloud_sync_outbox
                 SET attempt_count=attempt_count+1,last_error=?1,
                     next_attempt_at=strftime('%Y-%m-%dT%H:%M:%fZ','now',printf('+%d seconds',MIN(300,5 * (1 << MIN(6,attempt_count)))))
                 WHERE event_id=?2 AND account_id=?3 AND device_id=?4
                   AND entity_type='note' AND lifecycle='sealed'",
                rusqlite::params![command.error_code.as_str(), event_id, command.account_id, command.device_id],
            )?
        } else {
            transaction.execute(
                "UPDATE cloud_sync_outbox
                 SET attempt_count=attempt_count+1,last_error=?1,next_attempt_at=NULL,lifecycle='rejected'
                 WHERE event_id=?2 AND account_id=?3 AND device_id=?4
                   AND entity_type='note' AND lifecycle='sealed'",
                rusqlite::params![command.error_code.as_str(), event_id, command.account_id, command.device_id],
            )?
        };
        if changed != 1 {
            return Err(NoteSyncError::UnexpectedLifecycle);
        }
    }
    transaction.commit()?;
    Ok(())
}

fn retry_backoff_seconds(attempt_count: i64) -> i64 {
    let exponent = u32::try_from(attempt_count.saturating_sub(1).min(6)).unwrap_or(6);
    5_i64
        .saturating_mul(2_i64.saturating_pow(exponent))
        .min(300)
}

fn ensure_consistent_sealed_event(
    transaction: &Transaction<'_>,
    event_id: &str,
) -> Result<(), NoteSyncError> {
    let (account_id, sidecar_count): (String, i64) = transaction.query_row(
        "SELECT event.account_id,
                (SELECT count(*) FROM cloud_sync_note_intents AS intent
                 WHERE intent.event_id=event.event_id)
         FROM cloud_sync_outbox AS event WHERE event.event_id=?1",
        [event_id],
        |row| Ok((row.get(0)?, row.get(1)?)),
    )?;
    if sidecar_count != 0 {
        return Err(NoteSyncError::InvalidSealState(
            "sealed event retains plaintext intent",
        ));
    }
    let object = transaction
        .query_row(
            "SELECT crypto_version,aad_version,length(nonce),length(ciphertext)
             FROM cloud_sync_event_objects WHERE account_id=?1 AND event_id=?2",
            rusqlite::params![account_id, event_id],
            |row| {
                Ok((
                    row.get::<_, i64>(0)?,
                    row.get::<_, i64>(1)?,
                    row.get::<_, i64>(2)?,
                    row.get::<_, i64>(3)?,
                ))
            },
        )
        .optional()?
        .ok_or(NoteSyncError::SealedObjectMissing)?;
    if object.0 != SUPPORTED_CRYPTO_VERSION
        || object.1 != SUPPORTED_AAD_VERSION
        || object.2 != 24
        || !(16..=MAX_ENCRYPTED_SYNC_CIPHERTEXT_BYTES as i64).contains(&object.3)
    {
        return Err(NoteSyncError::InvalidSealState(
            "sealed event has an invalid encrypted object",
        ));
    }
    ensure_single_encrypted_object(transaction, event_id)?;
    Ok(())
}

fn ensure_matching_sealed_envelope(
    transaction: &Transaction<'_>,
    account_id: &str,
    event_id: &str,
    envelope: &DecodedEncryptedNoteSyncEnvelope,
) -> Result<(), NoteSyncError> {
    let sidecar_exists = transaction
        .query_row(
            "SELECT 1 FROM cloud_sync_note_intents WHERE event_id=?1",
            [event_id],
            |_| Ok(()),
        )
        .optional()?
        .is_some();
    if sidecar_exists {
        return Err(NoteSyncError::InvalidSealState(
            "sealed event retains plaintext intent",
        ));
    }
    let stored = transaction
        .query_row(
            "SELECT crypto_version,aad_version,nonce,ciphertext
             FROM cloud_sync_event_objects WHERE account_id=?1 AND event_id=?2",
            rusqlite::params![account_id, event_id],
            |row| {
                Ok(DecodedEncryptedNoteSyncEnvelope {
                    crypto_version: row.get(0)?,
                    aad_version: row.get(1)?,
                    nonce: row.get(2)?,
                    ciphertext: row.get(3)?,
                })
            },
        )
        .optional()?
        .ok_or(NoteSyncError::SealedObjectMissing)?;
    ensure_single_encrypted_object(transaction, event_id)?;
    if stored != *envelope {
        return Err(NoteSyncError::ConflictingEncryptedObject);
    }
    Ok(())
}

fn ensure_single_encrypted_object(
    transaction: &Transaction<'_>,
    event_id: &str,
) -> Result<(), NoteSyncError> {
    let object_count = transaction.query_row(
        "SELECT count(*) FROM cloud_sync_event_objects WHERE event_id=?1",
        [event_id],
        |row| row.get::<_, i64>(0),
    )?;
    if object_count != 1 {
        return Err(NoteSyncError::ConflictingEncryptedObject);
    }
    Ok(())
}

fn decode_encrypted_note_sync_envelope(
    envelope: &EncryptedNoteSyncEnvelope,
) -> Result<DecodedEncryptedNoteSyncEnvelope, NoteSyncError> {
    if envelope.crypto_version != SUPPORTED_CRYPTO_VERSION {
        return Err(NoteSyncError::InvalidEnvelope("unsupported crypto version"));
    }
    if envelope.aad_version != SUPPORTED_AAD_VERSION {
        return Err(NoteSyncError::InvalidEnvelope("unsupported AAD version"));
    }
    let nonce = decode_canonical_base64url(&envelope.nonce, 24, 24)?;
    let ciphertext = decode_canonical_base64url(
        &envelope.ciphertext,
        16,
        MAX_ENCRYPTED_SYNC_CIPHERTEXT_BYTES,
    )?;
    Ok(DecodedEncryptedNoteSyncEnvelope {
        crypto_version: envelope.crypto_version,
        aad_version: envelope.aad_version,
        nonce,
        ciphertext,
    })
}

fn decode_canonical_base64url(
    input: &str,
    minimum_length: usize,
    maximum_length: usize,
) -> Result<Vec<u8>, NoteSyncError> {
    let maximum_encoded_length = base64url_encoded_length(maximum_length).ok_or(
        NoteSyncError::InvalidEnvelope("encoded payload is too large"),
    )?;
    if input.len() > maximum_encoded_length || input.len() % 4 == 1 {
        return Err(NoteSyncError::InvalidEnvelope("invalid base64url length"));
    }
    let remainder = input.len() % 4;
    let decoded_length = input.len() / 4 * 3
        + match remainder {
            0 => 0,
            2 => 1,
            3 => 2,
            _ => unreachable!(),
        };
    if !(minimum_length..=maximum_length).contains(&decoded_length) {
        return Err(NoteSyncError::InvalidEnvelope(
            "decoded payload length is out of bounds",
        ));
    }
    let bytes = input.as_bytes();
    let mut decoded = Vec::with_capacity(decoded_length);
    let complete_length = input.len() - remainder;
    for chunk in bytes[..complete_length].chunks_exact(4) {
        let a = base64url_value(chunk[0])?;
        let b = base64url_value(chunk[1])?;
        let c = base64url_value(chunk[2])?;
        let d = base64url_value(chunk[3])?;
        decoded.push((a << 2) | (b >> 4));
        decoded.push(((b & 0x0f) << 4) | (c >> 2));
        decoded.push(((c & 0x03) << 6) | d);
    }
    if remainder == 2 {
        let a = base64url_value(bytes[complete_length])?;
        let b = base64url_value(bytes[complete_length + 1])?;
        if b & 0x0f != 0 {
            return Err(NoteSyncError::InvalidEnvelope(
                "non-canonical base64url tail",
            ));
        }
        decoded.push((a << 2) | (b >> 4));
    } else if remainder == 3 {
        let a = base64url_value(bytes[complete_length])?;
        let b = base64url_value(bytes[complete_length + 1])?;
        let c = base64url_value(bytes[complete_length + 2])?;
        if c & 0x03 != 0 {
            return Err(NoteSyncError::InvalidEnvelope(
                "non-canonical base64url tail",
            ));
        }
        decoded.push((a << 2) | (b >> 4));
        decoded.push(((b & 0x0f) << 4) | (c >> 2));
    }
    Ok(decoded)
}

fn base64url_encoded_length(byte_length: usize) -> Option<usize> {
    byte_length
        .checked_div(3)?
        .checked_mul(4)?
        .checked_add(match byte_length % 3 {
            0 => 0,
            1 => 2,
            2 => 3,
            _ => unreachable!(),
        })
}

fn encode_canonical_base64url(bytes: &[u8]) -> String {
    const ALPHABET: &[u8; 64] = b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_";
    let mut encoded = String::with_capacity(base64url_encoded_length(bytes.len()).unwrap_or(0));
    let complete_length = bytes.len() / 3 * 3;
    for chunk in bytes[..complete_length].chunks_exact(3) {
        encoded.push(ALPHABET[(chunk[0] >> 2) as usize] as char);
        encoded.push(ALPHABET[(((chunk[0] & 0x03) << 4) | (chunk[1] >> 4)) as usize] as char);
        encoded.push(ALPHABET[(((chunk[1] & 0x0f) << 2) | (chunk[2] >> 6)) as usize] as char);
        encoded.push(ALPHABET[(chunk[2] & 0x3f) as usize] as char);
    }
    match bytes.len() - complete_length {
        1 => {
            encoded.push(ALPHABET[(bytes[complete_length] >> 2) as usize] as char);
            encoded.push(ALPHABET[((bytes[complete_length] & 0x03) << 4) as usize] as char);
        }
        2 => {
            encoded.push(ALPHABET[(bytes[complete_length] >> 2) as usize] as char);
            encoded.push(
                ALPHABET[(((bytes[complete_length] & 0x03) << 4)
                    | (bytes[complete_length + 1] >> 4)) as usize] as char,
            );
            encoded.push(ALPHABET[((bytes[complete_length + 1] & 0x0f) << 2) as usize] as char);
        }
        _ => {}
    }
    encoded
}

fn base64url_value(value: u8) -> Result<u8, NoteSyncError> {
    match value {
        b'A'..=b'Z' => Ok(value - b'A'),
        b'a'..=b'z' => Ok(value - b'a' + 26),
        b'0'..=b'9' => Ok(value - b'0' + 52),
        b'-' => Ok(62),
        b'_' => Ok(63),
        _ => Err(NoteSyncError::InvalidEnvelope(
            "invalid base64url character",
        )),
    }
}

#[derive(Clone, Debug)]
struct VerifiedIncomingNote {
    event_id: String,
    parent_event_id: Option<String>,
    project_id: String,
    entity_id: String,
    operation: String,
    revision: i64,
    updated_at: String,
    deleted_at: Option<String>,
    route: NoteSyncRoute,
    payload_json: Option<String>,
}

#[derive(Clone, Debug)]
enum RemoteNoteMutation {
    Insert { payload_json: String, updated_at: String },
    Update { payload_json: String, updated_at: String },
    Delete,
    None,
}

#[derive(Clone, Debug)]
struct RemoteApplyPlan {
    result: ApplyVerifiedReceivedNoteResult,
    mutation: RemoteNoteMutation,
    account_id: String,
    project_id: String,
    entity_id: String,
    event_id: String,
    revision: i64,
    updated_at: String,
}

fn note_payload_from_record(
    record: &crate::note_sync_plaintext::NoteSyncRecord,
) -> Result<String, NoteSyncError> {
    let mut payload = serde_json::to_value(record)
        .map_err(|_| NoteSyncError::InvalidSnapshot("could not serialize remote Note"))?;
    payload
        .as_object_mut()
        .ok_or(NoteSyncError::InvalidSnapshot("remote Note payload is not an object"))?
        // This is a local Notes payload field, not the cloud revision.
        .insert("revision".to_string(), serde_json::Value::from(0));
    serde_json::to_string(&payload)
        .map_err(|_| NoteSyncError::InvalidSnapshot("could not encode remote Note payload"))
}

fn verified_incoming_note(
    plaintext: &NoteSyncPlaintext,
) -> Result<VerifiedIncomingNote, NoteSyncError> {
    match plaintext {
        NoteSyncPlaintext::Create { header, note }
        | NoteSyncPlaintext::Update { header, note } => Ok(VerifiedIncomingNote {
            event_id: header.event_id.clone(),
            parent_event_id: header.parent_event_id.clone(),
            project_id: header.project_id.clone(),
            entity_id: header.entity_id.clone(),
            operation: header.operation.clone(),
            revision: header.revision,
            updated_at: header.updated_at.clone(),
            deleted_at: header.deleted_at.clone(),
            route: note.route.clone(),
            payload_json: Some(note_payload_from_record(note)?),
        }),
        NoteSyncPlaintext::Delete { header, note } => Ok(VerifiedIncomingNote {
            event_id: header.event_id.clone(),
            parent_event_id: header.parent_event_id.clone(),
            project_id: header.project_id.clone(),
            entity_id: header.entity_id.clone(),
            operation: header.operation.clone(),
            revision: header.revision,
            updated_at: header.updated_at.clone(),
            deleted_at: header.deleted_at.clone(),
            route: note.route.clone(),
            payload_json: None,
        }),
    }
}

fn update_received_inbox_state(
    transaction: &Transaction<'_>,
    account_id: &str,
    event_id: &str,
    state: &str,
    error_code: Option<&str>,
    applied_at: Option<&str>,
) -> rusqlite::Result<()> {
    let changed = transaction.execute(
        "UPDATE cloud_sync_inbox
         SET state=?1,error_code=?2,applied_at=?3
         WHERE account_id=?4 AND event_id=?5 AND state='received'",
        rusqlite::params![state, error_code, applied_at, account_id, event_id],
    )?;
    if changed != 1 {
        return Err(rusqlite::Error::QueryReturnedNoRows);
    }
    Ok(())
}

fn advance_remote_entity_head(
    transaction: &Transaction<'_>,
    plan: &RemoteApplyPlan,
) -> rusqlite::Result<()> {
    transaction.execute(
        "INSERT INTO cloud_sync_entities(
            account_id,project_id,entity_id,entity_type,head_event_id,
            head_sync_revision,conflict_event_id,conflict_state,updated_at
         ) VALUES(?1,?2,?3,'note',?4,?5,NULL,NULL,?6)
         ON CONFLICT(account_id,project_id,entity_id,entity_type) DO UPDATE SET
            head_event_id=excluded.head_event_id,
            head_sync_revision=excluded.head_sync_revision,
            conflict_event_id=NULL,conflict_state=NULL,updated_at=excluded.updated_at",
        rusqlite::params![
            plan.account_id,
            plan.project_id,
            plan.entity_id,
            plan.event_id,
            plan.revision,
            plan.updated_at,
        ],
    )?;
    Ok(())
}

fn classify_remote_apply(
    transaction: &Transaction<'_>,
    command: &ApplyVerifiedReceivedNoteCommand,
    result: ApplyVerifiedReceivedNoteResult,
    state: &str,
    error_code: &str,
) -> rusqlite::Result<(Option<OwnedRemoteApplyAuthorization>, RemoteApplyPlan)> {
    update_received_inbox_state(
        transaction,
        &command.account_id,
        &command.event_id,
        state,
        Some(error_code),
        None,
    )?;
    Ok((
        None,
        RemoteApplyPlan {
            result,
            mutation: RemoteNoteMutation::None,
            account_id: command.account_id.clone(),
            project_id: String::new(),
            entity_id: String::new(),
            event_id: command.event_id.clone(),
            revision: 0,
            updated_at: String::new(),
        },
    ))
}

fn remote_apply_storage_error(error: StorageError) -> NoteSyncError {
    match error {
        StorageError::Database(error) => NoteSyncError::Database(error),
        StorageError::RemoteApplyAuthorization(_) => {
            NoteSyncError::InvalidEnvelope("remote apply authorization failed")
        }
        StorageError::UnsupportedSchema(_) | StorageError::CorruptSchema(_) => {
            NoteSyncError::InvalidEnvelope("remote apply storage unavailable")
        }
    }
}

/// Applies one TypeScript-authenticated Note plaintext.  The caller never
/// supplies a capability, and every mutable SQLite fact is re-checked inside
/// the immediate transaction owned by the privileged connection.
pub(crate) fn apply_verified_received_note_ipc(
    connection: &mut PrivilegedRemoteApplyConnection,
    mut command: ApplyVerifiedReceivedNoteIpcCommand,
) -> Result<ApplyVerifiedReceivedNoteResult, NoteSyncError> {
    // This clears Rust's command-owned mutable byte copy on both success and
    // decode failure. Tauri/serde and JavaScript may retain independent copies.
    let plaintext = decode_note_sync_plaintext(&command.plaintext)
        .map_err(|_| NoteSyncError::InvalidEnvelope("invalid verified Note plaintext"));
    command.plaintext.fill(0);
    let plaintext = plaintext?;
    apply_verified_received_note(
        connection,
        &ApplyVerifiedReceivedNoteCommand {
            account_id: command.account_id,
            canonical_user_id: command.canonical_user_id,
            pulling_device_id: command.pulling_device_id,
            event_id: command.event_id,
            server_sequence: command.server_sequence,
            source_device_id: command.source_device_id,
            crypto_version: command.crypto_version,
            aad_version: command.aad_version,
            nonce: command.nonce,
            ciphertext: command.ciphertext,
            plaintext,
        },
    )
}

pub(crate) fn apply_verified_received_note(
    connection: &mut PrivilegedRemoteApplyConnection,
    command: &ApplyVerifiedReceivedNoteCommand,
) -> Result<ApplyVerifiedReceivedNoteResult, NoteSyncError> {
    let incoming = verified_incoming_note(&command.plaintext)?;
    if command.event_id != incoming.event_id {
        return Err(NoteSyncError::InvalidEnvelope("plaintext event mismatch"));
    }

    connection
        .execute_planned_once(
            |transaction| {
                validate_pull_scope(
                    transaction,
                    &command.account_id,
                    &command.pulling_device_id,
                    &command.canonical_user_id,
                )
                .map_err(|error| StorageError::RemoteApplyAuthorization(error.to_string()))?;

                let inbox: Option<(i64, String, String, String, String, i64, String, Option<String>, String)> = transaction
                    .query_row(
                        "SELECT server_sequence,device_id,project_id,entity_id,operation,
                                sync_revision,updated_at,deleted_at,state
                         FROM cloud_sync_inbox
                         WHERE account_id=?1 AND event_id=?2 AND entity_type='note'",
                        rusqlite::params![command.account_id, command.event_id],
                        |row| Ok((
                            row.get(0)?, row.get(1)?, row.get(2)?, row.get(3)?, row.get(4)?,
                            row.get(5)?, row.get(6)?, row.get(7)?, row.get(8)?,
                        )),
                    )
                    .optional()?;
                let Some((server_sequence, source_device_id, project_id, entity_id, operation,
                    revision, updated_at, deleted_at, inbox_state)) = inbox else {
                    return Err(StorageError::RemoteApplyAuthorization(
                        "received inbox event is missing".to_string(),
                    ));
                };
                let immutable_matches = server_sequence == command.server_sequence
                    && source_device_id == command.source_device_id
                    && project_id == incoming.project_id
                    && entity_id == incoming.entity_id
                    && operation == incoming.operation
                    && revision == incoming.revision
                    && note_sync_timestamps_equal(&updated_at, &incoming.updated_at)
                    && match (deleted_at.as_deref(), incoming.deleted_at.as_deref()) {
                        (None, None) => true,
                        (Some(stored), Some(opened)) => note_sync_timestamps_equal(stored, opened),
                        _ => false,
                    };
                if !immutable_matches {
                    return classify_remote_apply(
                        transaction,
                        command,
                        ApplyVerifiedReceivedNoteResult::Rejected,
                        "rejected",
                        "metadata_mismatch",
                    )
                    .map_err(Into::into);
                }
                let object: Option<(i64, i64, Vec<u8>, Vec<u8>)> = transaction
                    .query_row(
                        "SELECT crypto_version,aad_version,nonce,ciphertext
                         FROM cloud_sync_event_objects WHERE account_id=?1 AND event_id=?2",
                        rusqlite::params![command.account_id, command.event_id],
                        |row| Ok((row.get(0)?, row.get(1)?, row.get(2)?, row.get(3)?)),
                    )
                    .optional()?;
                let expected_object = (
                    command.crypto_version,
                    command.aad_version,
                    command.nonce.clone(),
                    command.ciphertext.clone(),
                );
                let object_error = match object.as_ref() {
                    None => Some("missing_encrypted_object"),
                    Some(actual) if actual != &expected_object => Some("metadata_mismatch"),
                    Some(_) => None,
                };
                if let Some(error_code) = object_error {
                    return classify_remote_apply(
                        transaction,
                        command,
                        ApplyVerifiedReceivedNoteResult::Rejected,
                        "rejected",
                        error_code,
                    )
                    .map_err(Into::into);
                }
                if inbox_state == "applied" {
                    return Ok((
                        None,
                        RemoteApplyPlan {
                            result: ApplyVerifiedReceivedNoteResult::AlreadyApplied,
                            mutation: RemoteNoteMutation::None,
                            account_id: command.account_id.clone(),
                            project_id,
                            entity_id,
                            event_id: command.event_id.clone(),
                            revision,
                            updated_at,
                        },
                    ));
                }
                if inbox_state != "received" {
                    return Ok((
                        None,
                        RemoteApplyPlan {
                            result: match inbox_state.as_str() {
                                "orphan" => ApplyVerifiedReceivedNoteResult::Orphan,
                                "conflict" => ApplyVerifiedReceivedNoteResult::Conflict,
                                _ => ApplyVerifiedReceivedNoteResult::Rejected,
                            },
                            mutation: RemoteNoteMutation::None,
                            account_id: command.account_id.clone(),
                            project_id,
                            entity_id,
                            event_id: command.event_id.clone(),
                            revision,
                            updated_at,
                        },
                    ));
                }
                if transaction
                    .query_row(
                        "SELECT 1 FROM projects AS project
                         JOIN cloud_sync_project_bindings AS binding
                           ON binding.project_id=project.id
                         WHERE project.id=?1 AND binding.account_id=?2",
                        rusqlite::params![incoming.project_id, command.account_id],
                        |_| Ok(()),
                    )
                    .optional()?
                    .is_none()
                {
                    return classify_remote_apply(
                        transaction,
                        command,
                        ApplyVerifiedReceivedNoteResult::Orphan,
                        "orphan",
                        "missing_project",
                    )
                    .map_err(Into::into);
                }
                match eligibility(&incoming.route) {
                    Eligibility::DependencyNotSynced => {
                        return classify_remote_apply(transaction, command,
                            ApplyVerifiedReceivedNoteResult::Orphan, "orphan", "dependency_not_synced")
                            .map_err(Into::into);
                    }
                    Eligibility::UnsupportedContentFormat => {
                        return classify_remote_apply(transaction, command,
                            ApplyVerifiedReceivedNoteResult::Rejected, "rejected", "unsupported_content_format")
                            .map_err(Into::into);
                    }
                    Eligibility::Eligible => {}
                }

                let self_echo = source_device_id == command.pulling_device_id
                    && transaction.query_row(
                        "SELECT 1 FROM cloud_sync_outbox AS outbox
                         JOIN cloud_sync_upload_receipts AS receipt
                           ON receipt.event_id=outbox.event_id
                         WHERE outbox.event_id=?1 AND outbox.account_id=?2
                           AND outbox.device_id=?3 AND receipt.account_id=?2
                           AND receipt.device_id=?3 AND receipt.server_sequence=?4
                           AND outbox.project_id=?5 AND outbox.entity_id=?6
                           AND outbox.entity_type='note' AND outbox.operation=?7
                           AND outbox.revision=?8 AND outbox.updated_at=?9
                           AND outbox.deleted_at IS ?10",
                        rusqlite::params![
                            command.event_id, command.account_id, command.pulling_device_id,
                            command.server_sequence, incoming.project_id, incoming.entity_id,
                            incoming.operation, incoming.revision, incoming.updated_at,
                            incoming.deleted_at,
                        ],
                        |_| Ok(()),
                    ).optional()?.is_some();
                if self_echo {
                    let head: Option<(String, i64)> = transaction.query_row(
                        "SELECT head_event_id,head_sync_revision FROM cloud_sync_entities
                         WHERE account_id=?1 AND project_id=?2 AND entity_id=?3 AND entity_type='note'",
                        rusqlite::params![command.account_id, incoming.project_id, incoming.entity_id],
                        |row| Ok((row.get(0)?, row.get(1)?)),
                    ).optional()?;
                    if head.as_ref().is_some_and(|(event_id, value)| {
                        *value == incoming.revision && event_id != &incoming.event_id
                    }) {
                        return classify_remote_apply(transaction, command,
                            ApplyVerifiedReceivedNoteResult::Conflict, "conflict", "conflicting_head")
                            .map_err(Into::into);
                    }
                    let plan = RemoteApplyPlan {
                        result: ApplyVerifiedReceivedNoteResult::SelfEchoApplied,
                        mutation: RemoteNoteMutation::None,
                        account_id: command.account_id.clone(),
                        project_id: incoming.project_id.clone(), entity_id: incoming.entity_id.clone(),
                        event_id: incoming.event_id.clone(), revision: incoming.revision,
                        updated_at: incoming.updated_at.clone(),
                    };
                    if head.as_ref().is_none_or(|(_, value)| *value < incoming.revision) {
                        advance_remote_entity_head(transaction, &plan)?;
                    }
                    update_received_inbox_state(transaction, &command.account_id, &command.event_id,
                        "applied", None, Some(&incoming.updated_at))?;
                    return Ok((None, plan));
                }

                let local_unsealed = transaction.query_row(
                    "SELECT 1 FROM cloud_sync_outbox
                     WHERE account_id=?1 AND project_id=?2 AND entity_id=?3
                       AND entity_type='note' AND lifecycle='unsealed' AND local_ordinal>0",
                    rusqlite::params![command.account_id, incoming.project_id, incoming.entity_id],
                    |_| Ok(()),
                ).optional()?.is_some();
                if local_unsealed {
                    return classify_remote_apply(transaction, command,
                        ApplyVerifiedReceivedNoteResult::Conflict, "conflict", "local_unsealed_change")
                        .map_err(Into::into);
                }
                let head = match read_entity_sync_head(
                    transaction, &command.account_id, &incoming.project_id, &incoming.entity_id,
                ) {
                    Ok(head) => head,
                    Err(NoteSyncError::ConflictingHeads) => {
                        return classify_remote_apply(transaction, command,
                            ApplyVerifiedReceivedNoteResult::Conflict, "conflict", "conflicting_head")
                            .map_err(Into::into);
                    }
                    Err(NoteSyncError::Database(error)) => return Err(StorageError::Database(error)),
                    Err(error) => return Err(StorageError::RemoteApplyAuthorization(error.to_string())),
                };
                let chain_valid = if incoming.revision == 1 {
                    incoming.parent_event_id.is_none() && head.is_none()
                } else {
                    head.as_ref().is_some_and(|head| {
                        head.revision == incoming.revision - 1
                            && incoming.parent_event_id.as_deref() == Some(&head.event_id)
                    })
                };
                if !chain_valid {
                    let is_missing_parent = incoming.revision > 1
                        && head.as_ref().is_none_or(|head| head.revision < incoming.revision - 1);
                    return classify_remote_apply(transaction, command,
                        if is_missing_parent { ApplyVerifiedReceivedNoteResult::Orphan } else { ApplyVerifiedReceivedNoteResult::Conflict },
                        if is_missing_parent { "orphan" } else { "conflict" },
                        if is_missing_parent { "missing_parent" } else { "conflicting_head" })
                        .map_err(Into::into);
                }
                let existing: Option<(String, String)> = transaction.query_row(
                    "SELECT project_id,payload_json FROM notes WHERE id=?1", [&incoming.entity_id],
                    |row| Ok((row.get(0)?, row.get(1)?)),
                ).optional()?;
                if existing.as_ref().is_some_and(|(project_id, _)| project_id != &incoming.project_id) {
                    return classify_remote_apply(transaction, command,
                        ApplyVerifiedReceivedNoteResult::Conflict, "conflict", "conflicting_head")
                        .map_err(Into::into);
                }
                if incoming.revision == 1 && existing.is_some() {
                    return classify_remote_apply(transaction, command,
                        ApplyVerifiedReceivedNoteResult::Conflict, "conflict", "conflicting_head")
                        .map_err(Into::into);
                }
                let (mutation, authorization) = match (&incoming.payload_json, existing) {
                    (Some(payload_json), None) => (
                        RemoteNoteMutation::Insert { payload_json: payload_json.clone(), updated_at: incoming.updated_at.clone() },
                        Some(OwnedRemoteApplyAuthorization {
                            event_id: incoming.event_id.clone(), account_id: command.account_id.clone(),
                            project_id: incoming.project_id.clone(), entity_id: incoming.entity_id.clone(),
                            operation: "upsert".to_string(), payload_json: Some(payload_json.clone()),
                            prior_payload_json: None,
                        }),
                    ),
                    (Some(payload_json), Some((_, prior_payload_json))) => (
                        RemoteNoteMutation::Update { payload_json: payload_json.clone(), updated_at: incoming.updated_at.clone() },
                        Some(OwnedRemoteApplyAuthorization {
                            event_id: incoming.event_id.clone(), account_id: command.account_id.clone(),
                            project_id: incoming.project_id.clone(), entity_id: incoming.entity_id.clone(),
                            operation: "upsert".to_string(), payload_json: Some(payload_json.clone()),
                            prior_payload_json: Some(prior_payload_json),
                        }),
                    ),
                    (None, Some((_, prior_payload_json))) => (
                        RemoteNoteMutation::Delete,
                        Some(OwnedRemoteApplyAuthorization {
                            event_id: incoming.event_id.clone(), account_id: command.account_id.clone(),
                            project_id: incoming.project_id.clone(), entity_id: incoming.entity_id.clone(),
                            operation: "delete".to_string(), payload_json: None,
                            prior_payload_json: Some(prior_payload_json),
                        }),
                    ),
                    (None, None) => (RemoteNoteMutation::None, None),
                };
                Ok((authorization, RemoteApplyPlan {
                    result: ApplyVerifiedReceivedNoteResult::Applied, mutation,
                    account_id: command.account_id.clone(), project_id: incoming.project_id.clone(),
                    entity_id: incoming.entity_id.clone(), event_id: incoming.event_id.clone(),
                    revision: incoming.revision, updated_at: incoming.updated_at.clone(),
                }))
            },
            |transaction, plan| {
                match &plan.mutation {
                    RemoteNoteMutation::Insert { payload_json, updated_at } => {
                        transaction.execute(
                            "INSERT INTO notes(id,project_id,stage_id,updated_at,payload_json)
                             VALUES(?1,?2,NULL,?3,?4)",
                            rusqlite::params![plan.entity_id, plan.project_id, updated_at, payload_json],
                        )?;
                    }
                    RemoteNoteMutation::Update { payload_json, updated_at } => {
                        let changed = transaction.execute(
                            "UPDATE notes SET updated_at=?1,payload_json=?2
                             WHERE id=?3 AND project_id=?4",
                            rusqlite::params![updated_at, payload_json, plan.entity_id, plan.project_id],
                        )?;
                        if changed != 1 {
                            return Err(StorageError::RemoteApplyAuthorization(
                                "remote Note update target disappeared".to_string(),
                            ));
                        }
                    }
                    RemoteNoteMutation::Delete => {
                        transaction.execute(
                            "DELETE FROM notes WHERE id=?1 AND project_id=?2",
                            rusqlite::params![plan.entity_id, plan.project_id],
                        )?;
                    }
                    RemoteNoteMutation::None => {}
                }
                if plan.result == ApplyVerifiedReceivedNoteResult::Applied {
                    advance_remote_entity_head(transaction, &plan)?;
                    update_received_inbox_state(
                        transaction, &plan.account_id, &plan.event_id, "applied", None,
                        Some(&plan.updated_at),
                    )?;
                }
                Ok(plan.result)
            },
        )
        .map_err(remote_apply_storage_error)
}

#[cfg(test)]
mod tests {
    use super::*;
    use rusqlite::Connection;

    const DEVICE_ID: &str = "123e4567-e89b-42d3-a456-426614174000";

    fn database() -> Connection {
        let connection = Connection::open_in_memory().unwrap();
        crate::sqlite::apply_migrations(&connection).unwrap();
        configure_database(&connection);
        connection
    }

    fn inbound_scope(connection: &mut Connection) {
        connection.execute("INSERT OR IGNORE INTO cloud_sync_state(account_id,device_id,pull_cursor,ack_cursor,created_at,updated_at) VALUES('inbox-account',?1,0,0,'now','now')", [DEVICE_ID]).unwrap();
        connection.execute("INSERT OR IGNORE INTO cloud_account_bindings(local_account_id,canonical_user_id,created_at,validated_at) VALUES('inbox-account','abcdefab-0000-0000-0000-000000000101','now','now')", []).unwrap();
    }

    fn inbound_command() -> CommitNoteSyncInboundPageCommand {
        CommitNoteSyncInboundPageCommand {
            account_id: "inbox-account".into(), device_id: DEVICE_ID.into(),
            canonical_user_id: "abcdefab-0000-0000-0000-000000000101".into(),
            expected_cursor: 0, next_cursor: 1, has_more: false,
            items: vec![InboundNoteSyncItem {
                event_id: "123e4567-e89b-42d3-a456-426614174099".into(), server_sequence: 1,
                source_device_id: DEVICE_ID.into(), project_id: "project".into(), entity_id: "note".into(),
                entity_type: "note".into(), operation: "upsert".into(), revision: 1,
                updated_at: "2026-09-22T00:00:00Z".into(), deleted_at: None,
                envelope: Some(EncryptedNoteSyncEnvelope { crypto_version: 1, aad_version: 1, nonce: "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA".into(), ciphertext: "AAAAAAAAAAAAAAAAAAAAAA".into() }),
            }],
        }
    }

    fn received_list_command(limit: u32) -> ListReceivedNoteSyncInboxCommand {
        ListReceivedNoteSyncInboxCommand {
            account_id: "inbox-account".into(), device_id: DEVICE_ID.into(),
            canonical_user_id: "abcdefab-0000-0000-0000-000000000101".into(), limit,
        }
    }

    fn ack_prepare_command() -> PrepareNoteSyncAckCommand {
        PrepareNoteSyncAckCommand { account_id: "inbox-account".into(), device_id: DEVICE_ID.into(), canonical_user_id: "abcdefab-0000-0000-0000-000000000101".into() }
    }

    fn ack_commit_command(expected_old_ack_cursor: i64, acknowledged_cursor: i64) -> CommitNoteSyncAckCommand {
        CommitNoteSyncAckCommand { account_id: "inbox-account".into(), device_id: DEVICE_ID.into(), canonical_user_id: "abcdefab-0000-0000-0000-000000000101".into(), expected_old_ack_cursor, acknowledged_cursor }
    }

    fn set_ack_pull_cursor(connection: &Connection, pull_cursor: i64) {
        connection.execute("UPDATE cloud_sync_state SET pull_cursor=?1 WHERE account_id='inbox-account'", [pull_cursor]).unwrap();
    }

    fn insert_ack_inbox(connection: &Connection, sequence: i64, state: &str) {
        connection.execute(
            "INSERT INTO cloud_sync_inbox(account_id,event_id,server_sequence,device_id,project_id,entity_id,entity_type,operation,sync_revision,updated_at,deleted_at,state,received_at) VALUES('inbox-account',?1,?2,?3,'project',?4,'note','upsert',1,'2026-09-22T00:00:00Z',NULL,?5,'now')",
            rusqlite::params![format!("123e4567-e89b-42d3-a456-426614174{sequence:03}"), sequence, DEVICE_ID, format!("note-{sequence}"), state],
        ).unwrap();
    }

    #[test]
    fn inbound_page_is_atomic_idempotent_and_advances_only_pull_cursor() {
        let mut connection = database(); inbound_scope(&mut connection);
        let command = inbound_command();
        assert_eq!(commit_note_sync_inbound_page(&mut connection, &command).unwrap().new_events, 1);
        assert_eq!(connection.query_row("SELECT pull_cursor,ack_cursor FROM cloud_sync_state WHERE account_id='inbox-account'", [], |row| Ok((row.get::<_, i64>(0)?,row.get::<_, i64>(1)?))).unwrap(), (1, 0));
        assert_eq!(connection.query_row("SELECT count(*) FROM cloud_sync_inbox", [], |row| row.get::<_, i64>(0)).unwrap(), 1);
        assert_eq!(commit_note_sync_inbound_page(&mut connection, &command).unwrap().replayed_events, 1);
    }

    #[test]
    fn received_inbox_reader_is_bounded_scoped_ordered_and_read_only() {
        let mut connection = database(); inbound_scope(&mut connection);
        let mut first = inbound_command();
        first.items[0].event_id = "123e4567-e89b-42d3-a456-426614174098".into();
        first.items[0].server_sequence = 1; first.next_cursor = 1;
        commit_note_sync_inbound_page(&mut connection, &first).unwrap();
        let mut second = inbound_command(); second.expected_cursor = 1; second.next_cursor = 2;
        second.items[0].server_sequence = 2;
        commit_note_sync_inbound_page(&mut connection, &second).unwrap();
        let before: (i64, i64, String) = connection.query_row(
            "SELECT pull_cursor,ack_cursor,state FROM cloud_sync_state JOIN cloud_sync_inbox ON cloud_sync_inbox.account_id=cloud_sync_state.account_id WHERE cloud_sync_state.account_id='inbox-account' ORDER BY server_sequence LIMIT 1",
            [], |row| Ok((row.get(0)?, row.get(1)?, row.get(2)?)),
        ).unwrap();
        let listed = list_received_note_sync_inbox(&connection, &received_list_command(1)).unwrap();
        assert_eq!(listed.len(), 1); assert_eq!(listed[0].server_sequence, 1);
        assert_eq!(listed[0].event_id, "123e4567-e89b-42d3-a456-426614174098");
        let after: (i64, i64, String) = connection.query_row(
            "SELECT pull_cursor,ack_cursor,state FROM cloud_sync_state JOIN cloud_sync_inbox ON cloud_sync_inbox.account_id=cloud_sync_state.account_id WHERE cloud_sync_state.account_id='inbox-account' ORDER BY server_sequence LIMIT 1",
            [], |row| Ok((row.get(0)?, row.get(1)?, row.get(2)?)),
        ).unwrap();
        assert_eq!(after, before);
        assert!(list_received_note_sync_inbox(&connection, &received_list_command(33)).is_err());
        let mut wrong_device = received_list_command(1); wrong_device.device_id = "123e4567-e89b-42d3-a456-426614174111".into();
        assert!(list_received_note_sync_inbox(&connection, &wrong_device).is_err());
    }

    #[test]
    fn received_inbox_reader_requires_a_valid_durable_object() {
        let mut connection = database(); inbound_scope(&mut connection);
        let command = inbound_command(); commit_note_sync_inbound_page(&mut connection, &command).unwrap();
        connection.execute("DELETE FROM cloud_sync_event_objects WHERE account_id='inbox-account'", []).unwrap();
        assert!(matches!(list_received_note_sync_inbox(&connection, &received_list_command(8)), Err(NoteSyncError::SealedObjectMissing)));
    }

    #[test]
    fn inbound_conflict_rolls_back_page_and_cursor() {
        let mut connection = database(); inbound_scope(&mut connection);
        let command = inbound_command(); commit_note_sync_inbound_page(&mut connection, &command).unwrap();
        let mut conflict = inbound_command();
        conflict.items[0].envelope.as_mut().unwrap().ciphertext = "AQAAAAAAAAAAAAAAAAAAAA".into();
        assert!(commit_note_sync_inbound_page(&mut connection, &conflict).is_err());
        assert_eq!(connection.query_row("SELECT pull_cursor FROM cloud_sync_state WHERE account_id='inbox-account'", [], |row| row.get::<_, i64>(0)).unwrap(), 1);
    }

    #[test]
    fn inbound_replay_survives_reopen_and_stale_or_partial_pages_rollback() {
        let (root, path) = temporary_database_path("inbound-replay");
        let mut connection = crate::sqlite::open_database(&path).unwrap();
        configure_database(&connection); inbound_scope(&mut connection);
        let command = inbound_command();
        commit_note_sync_inbound_page(&mut connection, &command).unwrap();
        drop(connection);
        let mut reopened = crate::sqlite::open_database(&path).unwrap();
        assert_eq!(commit_note_sync_inbound_page(&mut reopened, &command).unwrap().replayed_events, 1);
        let mut stale = inbound_command(); stale.expected_cursor = 2; stale.next_cursor = 3;
        assert!(commit_note_sync_inbound_page(&mut reopened, &stale).is_err());
        let mut partial = inbound_command(); partial.items.clear();
        assert!(commit_note_sync_inbound_page(&mut reopened, &partial).is_err());
        assert_eq!(reopened.query_row("SELECT pull_cursor,ack_cursor FROM cloud_sync_state WHERE account_id='inbox-account'", [], |row| Ok((row.get::<_, i64>(0)?, row.get::<_, i64>(1)?))).unwrap(), (1, 0));
        assert_eq!(reopened.query_row("SELECT count(*) FROM notes", [], |row| row.get::<_, i64>(0)).unwrap(), 0);
        assert_eq!(reopened.query_row("SELECT count(*) FROM cloud_sync_outbox", [], |row| row.get::<_, i64>(0)).unwrap(), 0);
        drop(reopened); std::fs::remove_dir_all(root).unwrap();
    }

    #[test]
    fn durable_ack_candidate_requires_a_contiguous_applied_prefix() {
        let mut connection = database(); inbound_scope(&mut connection);
        assert_eq!(prepare_note_sync_ack(&mut connection, &ack_prepare_command()).unwrap().candidate_cursor, 0);
        set_ack_pull_cursor(&connection, 3);
        for sequence in 1..=3 { insert_ack_inbox(&connection, sequence, "applied"); }
        assert_eq!(prepare_note_sync_ack(&mut connection, &ack_prepare_command()).unwrap(), NoteSyncAckCandidate { current_ack_cursor: 0, candidate_cursor: 3 });
        let mut gap = database(); inbound_scope(&mut gap); set_ack_pull_cursor(&gap, 3);
        insert_ack_inbox(&gap, 1, "applied"); insert_ack_inbox(&gap, 3, "applied");
        assert_eq!(prepare_note_sync_ack(&mut gap, &ack_prepare_command()).unwrap().candidate_cursor, 1);
    }

    #[test]
    fn durable_ack_candidate_stops_at_unresolved_states_and_pull_bound() {
        for state in ["conflict", "orphan", "rejected", "unknown_entity"] {
            let mut connection = database(); inbound_scope(&mut connection); set_ack_pull_cursor(&connection, 3);
            insert_ack_inbox(&connection, 1, "applied"); insert_ack_inbox(&connection, 2, state); insert_ack_inbox(&connection, 3, "applied");
            assert_eq!(prepare_note_sync_ack(&mut connection, &ack_prepare_command()).unwrap().candidate_cursor, 1, "{state}");
        }
        let mut bounded = database(); inbound_scope(&mut bounded); set_ack_pull_cursor(&bounded, 1);
        insert_ack_inbox(&bounded, 1, "applied"); insert_ack_inbox(&bounded, 2, "applied");
        assert_eq!(prepare_note_sync_ack(&mut bounded, &ack_prepare_command()).unwrap().candidate_cursor, 1);
    }

    #[test]
    fn durable_ack_advance_is_conditional_idempotent_and_replay_safe() {
        let mut connection = database(); inbound_scope(&mut connection); set_ack_pull_cursor(&connection, 2);
        insert_ack_inbox(&connection, 1, "applied"); insert_ack_inbox(&connection, 2, "applied");
        assert_eq!(commit_note_sync_ack(&mut connection, &ack_commit_command(0, 2)).unwrap(), CommitNoteSyncAckResult::Advanced);
        assert_eq!(commit_note_sync_ack(&mut connection, &ack_commit_command(0, 2)).unwrap(), CommitNoteSyncAckResult::AlreadyAcknowledged);
        assert_eq!(commit_note_sync_ack(&mut connection, &ack_commit_command(0, 1)).unwrap(), CommitNoteSyncAckResult::AlreadyAdvanced);
        let mut stale = database(); inbound_scope(&mut stale); set_ack_pull_cursor(&stale, 2); insert_ack_inbox(&stale, 1, "applied"); insert_ack_inbox(&stale, 2, "applied"); stale.execute("UPDATE cloud_sync_state SET ack_cursor=1 WHERE account_id='inbox-account'", []).unwrap();
        assert_eq!(commit_note_sync_ack(&mut stale, &ack_commit_command(0, 2)).unwrap(), CommitNoteSyncAckResult::Stale);
    }

    #[test]
    fn durable_ack_advance_revalidates_scope_prefix_restart_and_rollback() {
        let mut connection = database(); inbound_scope(&mut connection); set_ack_pull_cursor(&connection, 2); insert_ack_inbox(&connection, 1, "applied"); insert_ack_inbox(&connection, 2, "conflict");
        assert!(commit_note_sync_ack(&mut connection, &ack_commit_command(0, 2)).is_err());
        let mut wrong = ack_prepare_command(); wrong.device_id = "123e4567-e89b-42d3-a456-426614174111".into(); assert!(prepare_note_sync_ack(&mut connection, &wrong).is_err()); wrong = ack_prepare_command(); wrong.account_id = "other-account".into(); assert!(prepare_note_sync_ack(&mut connection, &wrong).is_err());
        connection.execute("UPDATE cloud_sync_inbox SET state='applied' WHERE account_id='inbox-account' AND server_sequence=2", []).unwrap(); connection.execute_batch("CREATE TRIGGER note_sync_ack_test_fail BEFORE UPDATE OF ack_cursor ON cloud_sync_state WHEN NEW.account_id='inbox-account' BEGIN SELECT RAISE(ABORT,'injected_ack_failure'); END;").unwrap();
        assert!(commit_note_sync_ack(&mut connection, &ack_commit_command(0, 2)).is_err()); assert_eq!(connection.query_row("SELECT ack_cursor FROM cloud_sync_state WHERE account_id='inbox-account'", [], |row| row.get::<_, i64>(0)).unwrap(), 0); connection.execute_batch("DROP TRIGGER note_sync_ack_test_fail;").unwrap(); assert_eq!(commit_note_sync_ack(&mut connection, &ack_commit_command(0, 2)).unwrap(), CommitNoteSyncAckResult::Advanced);
        let (root, path) = temporary_database_path("ack-restart"); let mut persistent = crate::sqlite::open_database(&path).unwrap(); configure_database(&persistent); inbound_scope(&mut persistent); set_ack_pull_cursor(&persistent, 1); insert_ack_inbox(&persistent, 1, "applied"); assert_eq!(commit_note_sync_ack(&mut persistent, &ack_commit_command(0, 1)).unwrap(), CommitNoteSyncAckResult::Advanced); drop(persistent); let mut reopened = crate::sqlite::open_database(&path).unwrap(); assert_eq!(prepare_note_sync_ack(&mut reopened, &ack_prepare_command()).unwrap(), NoteSyncAckCandidate { current_ack_cursor: 1, candidate_cursor: 1 }); drop(reopened); std::fs::remove_dir_all(root).unwrap();
    }

    fn configure_database(connection: &Connection) {
        connection.execute_batch("PRAGMA foreign_keys=ON;").unwrap();
        connection.execute("INSERT INTO projects(id,name,infinite,unit,status,payload_json) VALUES('p','P',0,'symbols','active','{}')", []).unwrap();
        connection
            .execute(
                "INSERT INTO project_order(project_id,position) VALUES('p',0)",
                [],
            )
            .unwrap();
        connection.execute("INSERT INTO cloud_sync_state(account_id,device_id,pull_cursor,ack_cursor,created_at,updated_at) VALUES('account',?1,0,0,'now','now')", [DEVICE_ID]).unwrap();
        connection.execute("INSERT INTO cloud_sync_project_bindings(project_id,account_id,created_at,updated_at) VALUES('p','account','now','now')", []).unwrap();
    }

    fn note(content: &str, revision: i64) -> String {
        note_for("n", content, revision)
    }

    fn note_for(note_id: &str, content: &str, revision: i64) -> String {
        serde_json::json!({
            "id":note_id, "project_id":"p", "stage_id":null, "title":"",
            "content":content, "content_format":"html", "checklist":[],
            "color":"default", "pinned":false, "archived":false,
            "sort_order":0, "tags":[], "source_type":"project",
            "source_map_id":null, "source_node_id":null,
            "created_at":"2026-09-22T00:00:00Z",
            "updated_at":"2026-09-22T00:00:00Z", "revision":revision,
            "metadata":{}
        })
        .to_string()
    }

    fn prepare<'a>(snapshot: &'a str) -> PrepareNoteIntent<'a> {
        prepare_for("n", snapshot)
    }

    fn prepare_for<'a>(note_id: &'a str, snapshot: &'a str) -> PrepareNoteIntent<'a> {
        PrepareNoteIntent {
            project_id: "p",
            entity_id: note_id,
            operation: NoteSyncOperation::Upsert,
            updated_at: "2026-09-22T00:00:00Z",
            deleted_at: None,
            snapshot_json: snapshot,
            state_updated_at: "2026-09-22T00:00:00Z",
        }
    }

    fn persist_note_intent(
        connection: &mut Connection,
        note_id: &str,
        content: &str,
    ) -> (PreparedNoteIntent, String) {
        let snapshot = note_for(note_id, content, 0);
        let transaction = connection.transaction().unwrap();
        let intent = prepare_unsealed_note_intent(&transaction, prepare_for(note_id, &snapshot))
            .unwrap()
            .unwrap();
        let exists = transaction
            .query_row("SELECT 1 FROM notes WHERE id=?1", [note_id], |_| Ok(()))
            .optional()
            .unwrap()
            .is_some();
        if exists {
            transaction
                .execute(
                    "UPDATE notes SET updated_at='2026-09-22T00:00:00Z',payload_json=?1
                     WHERE id=?2",
                    rusqlite::params![snapshot, note_id],
                )
                .unwrap();
        } else {
            transaction
                .execute(
                    "INSERT INTO notes(id,project_id,stage_id,updated_at,payload_json)
                     VALUES(?1,'p',NULL,'2026-09-22T00:00:00Z',?2)",
                    rusqlite::params![note_id, snapshot],
                )
                .unwrap();
        }
        transaction.commit().unwrap();
        (intent, snapshot)
    }

    fn encode_base64url(bytes: &[u8]) -> String {
        const ALPHABET: &[u8; 64] =
            b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_";
        let mut encoded = String::with_capacity(base64url_encoded_length(bytes.len()).unwrap());
        let complete_length = bytes.len() / 3 * 3;
        for chunk in bytes[..complete_length].chunks_exact(3) {
            encoded.push(ALPHABET[(chunk[0] >> 2) as usize] as char);
            encoded.push(ALPHABET[(((chunk[0] & 0x03) << 4) | (chunk[1] >> 4)) as usize] as char);
            encoded.push(ALPHABET[(((chunk[1] & 0x0f) << 2) | (chunk[2] >> 6)) as usize] as char);
            encoded.push(ALPHABET[(chunk[2] & 0x3f) as usize] as char);
        }
        match bytes.len() - complete_length {
            1 => {
                encoded.push(ALPHABET[(bytes[complete_length] >> 2) as usize] as char);
                encoded.push(ALPHABET[((bytes[complete_length] & 0x03) << 4) as usize] as char);
            }
            2 => {
                encoded.push(ALPHABET[(bytes[complete_length] >> 2) as usize] as char);
                encoded.push(
                    ALPHABET[(((bytes[complete_length] & 0x03) << 4)
                        | (bytes[complete_length + 1] >> 4)) as usize] as char,
                );
                encoded.push(ALPHABET[((bytes[complete_length + 1] & 0x0f) << 2) as usize] as char);
            }
            _ => {}
        }
        encoded
    }

    fn envelope(fill: u8) -> EncryptedNoteSyncEnvelope {
        EncryptedNoteSyncEnvelope {
            crypto_version: 1,
            aad_version: 1,
            nonce: encode_base64url(&vec![fill; 24]),
            ciphertext: encode_base64url(&vec![fill.wrapping_add(1); 16]),
        }
    }

    fn seal_command(
        event_id: &str,
        mutation_generation: i64,
        envelope: EncryptedNoteSyncEnvelope,
    ) -> CommitSealedNoteSyncEventCommand {
        CommitSealedNoteSyncEventCommand {
            event_id: event_id.to_string(),
            expected_mutation_generation: mutation_generation,
            envelope,
        }
    }

    fn failure_command(
        event_id: &str,
        mutation_generation: i64,
        error_code: NoteSyncSealErrorCode,
    ) -> RecordNoteSyncSealFailureCommand {
        RecordNoteSyncSealFailureCommand {
            event_id: event_id.to_string(),
            expected_mutation_generation: mutation_generation,
            error_code,
        }
    }

    fn seal_persisted_intent(
        connection: &mut Connection,
        note_id: &str,
        content: &str,
        fill: u8,
    ) -> PreparedNoteIntent {
        let (intent, _) = persist_note_intent(connection, note_id, content);
        assert_eq!(
            commit_sealed_note_sync_event(
                connection,
                &seal_command(&intent.event_id, intent.mutation_generation, envelope(fill)),
            )
            .unwrap(),
            CommitSealedNoteSyncEventResult::Sealed
        );
        intent
    }

    fn temporary_database_path(label: &str) -> (std::path::PathBuf, std::path::PathBuf) {
        let root = std::env::temp_dir().join(format!(
            "nfprogress-note-sync-{label}-{}-{}",
            std::process::id(),
            std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_nanos()
        ));
        std::fs::create_dir_all(&root).unwrap();
        let path = root.join("nfprogress.db");
        (root, path)
    }

    #[test]
    fn note_sync_unbound_project_needs_no_intent() {
        let mut connection = database();
        connection
            .execute("DELETE FROM cloud_sync_project_bindings", [])
            .unwrap();
        let snapshot = note("local", 0);
        let transaction = connection.transaction().unwrap();
        assert!(
            prepare_unsealed_note_intent(&transaction, prepare(&snapshot))
                .unwrap()
                .is_none()
        );
        transaction.commit().unwrap();
    }

    #[test]
    fn note_sync_coalesces_unsealed_identity_and_advances_generation() {
        let mut connection = database();
        let first_snapshot = note("first", 0);
        let transaction = connection.transaction().unwrap();
        let first = prepare_unsealed_note_intent(&transaction, prepare(&first_snapshot))
            .unwrap()
            .unwrap();
        transaction.execute("INSERT INTO notes(id,project_id,stage_id,updated_at,payload_json) VALUES('n','p',NULL,'2026-09-22T00:00:00Z',?1)", [&first_snapshot]).unwrap();
        transaction.commit().unwrap();

        let second_snapshot = note("second", 1);
        let transaction = connection.transaction().unwrap();
        let second = prepare_unsealed_note_intent(&transaction, prepare(&second_snapshot))
            .unwrap()
            .unwrap();
        transaction
            .execute(
                "UPDATE notes SET updated_at='2026-09-22T00:00:00Z',payload_json=?1 \
                 WHERE id='n'",
                [&second_snapshot],
            )
            .unwrap();
        transaction.commit().unwrap();

        assert_eq!(second.event_id, first.event_id);
        assert_eq!(second.revision, 1);
        assert_eq!(second.parent_event_id, None);
        assert_eq!(second.local_ordinal, first.local_ordinal);
        assert_eq!(second.mutation_generation, 2);
        assert!(second.coalesced);
        assert_eq!(second.event_id.len(), 36);
        assert_eq!(&second.event_id[14..15], "4");
        assert!(matches!(&second.event_id[19..20], "8" | "9" | "a" | "b"));
        assert_eq!(
            connection
                .query_row(
                    "SELECT snapshot_json FROM cloud_sync_note_intents",
                    [],
                    |row| row.get::<_, String>(0)
                )
                .unwrap(),
            second_snapshot
        );
    }

    #[test]
    fn note_sync_generation_reaches_wire_max_and_refuses_the_next_increment() {
        let mut connection = database();
        let (first, _) = persist_note_intent(&mut connection, "n", "first");
        connection
            .execute(
                "UPDATE cloud_sync_note_intents SET mutation_generation=?1 WHERE event_id=?2",
                rusqlite::params![MAX_SYNC_INTEGER - 1, first.event_id],
            )
            .unwrap();

        let maximum_snapshot = note("maximum", 1);
        let transaction = connection.transaction().unwrap();
        let maximum = prepare_unsealed_note_intent(&transaction, prepare(&maximum_snapshot))
            .unwrap()
            .unwrap();
        transaction
            .execute(
                "UPDATE notes SET payload_json=?1 WHERE id='n'",
                [&maximum_snapshot],
            )
            .unwrap();
        transaction.commit().unwrap();

        assert_eq!(maximum.event_id, first.event_id);
        assert_eq!(maximum.mutation_generation, MAX_SYNC_INTEGER);
        let listed = list_unsealed_note_sync_intents(&mut connection, 1, false).unwrap();
        assert_eq!(listed[0].mutation_generation, MAX_SYNC_INTEGER);
        assert_eq!(
            serde_json::to_value(&listed[0]).unwrap()["mutation_generation"].as_u64(),
            Some(MAX_SYNC_INTEGER as u64)
        );

        let overflow_snapshot = note("overflow", 2);
        let transaction = connection.transaction().unwrap();
        assert!(matches!(
            prepare_unsealed_note_intent(&transaction, prepare(&overflow_snapshot)),
            Err(NoteSyncError::MutationGenerationOverflow)
        ));
        drop(transaction);
        let stored: (i64, String) = connection
            .query_row(
                "SELECT mutation_generation,snapshot_json FROM cloud_sync_note_intents",
                [],
                |row| Ok((row.get(0)?, row.get(1)?)),
            )
            .unwrap();
        assert_eq!(stored, (MAX_SYNC_INTEGER, maximum_snapshot));
    }

    #[test]
    fn note_sync_generation_cas_and_listing_enforce_the_wire_limit() {
        let mut connection = database();
        let (failure_intent, _) = persist_note_intent(&mut connection, "failure", "failure");
        connection
            .execute(
                "UPDATE cloud_sync_note_intents SET mutation_generation=?1 WHERE event_id=?2",
                rusqlite::params![MAX_SYNC_INTEGER, failure_intent.event_id],
            )
            .unwrap();
        assert_eq!(
            record_note_sync_seal_failure(
                &mut connection,
                &failure_command(
                    &failure_intent.event_id,
                    MAX_SYNC_INTEGER,
                    NoteSyncSealErrorCode::KeyUnavailable,
                ),
            )
            .unwrap(),
            RecordNoteSyncSealFailureResult::Recorded
        );
        assert!(matches!(
            record_note_sync_seal_failure(
                &mut connection,
                &failure_command(
                    &failure_intent.event_id,
                    MAX_SYNC_INTEGER + 1,
                    NoteSyncSealErrorCode::KeyUnavailable,
                ),
            ),
            Err(NoteSyncError::InvalidSealState(_))
        ));

        let (seal_intent, _) = persist_note_intent(&mut connection, "seal", "seal");
        connection
            .execute(
                "UPDATE cloud_sync_note_intents SET mutation_generation=?1 WHERE event_id=?2",
                rusqlite::params![MAX_SYNC_INTEGER, seal_intent.event_id],
            )
            .unwrap();
        assert_eq!(
            commit_sealed_note_sync_event(
                &mut connection,
                &seal_command(&seal_intent.event_id, MAX_SYNC_INTEGER, envelope(31)),
            )
            .unwrap(),
            CommitSealedNoteSyncEventResult::Sealed
        );

        connection
            .execute(
                "UPDATE cloud_sync_note_intents SET mutation_generation=?1 WHERE event_id=?2",
                rusqlite::params![MAX_SYNC_INTEGER + 1, failure_intent.event_id],
            )
            .unwrap();
        assert!(matches!(
            list_unsealed_note_sync_intents(&mut connection, 10, true),
            Err(NoteSyncError::InvalidSealState(_))
        ));
        assert!(matches!(
            commit_sealed_note_sync_event(
                &mut connection,
                &seal_command(&failure_intent.event_id, MAX_SYNC_INTEGER + 1, envelope(32)),
            ),
            Err(NoteSyncError::InvalidSealState(_))
        ));
    }

    #[test]
    fn note_sync_legacy_timestamp_preflight_is_project_scoped_and_read_only() {
        let connection = database();
        connection
            .execute("DELETE FROM cloud_sync_project_bindings", [])
            .unwrap();
        connection.execute("INSERT INTO projects(id,name,infinite,unit,status,payload_json) VALUES('other','Other',0,'symbols','active','{}')", []).unwrap();
        connection
            .execute(
                "INSERT INTO project_order(project_id,position) VALUES('other',1)",
                [],
            )
            .unwrap();

        let mut valid: serde_json::Value = serde_json::from_str(&note_for("valid", "", 0)).unwrap();
        valid["created_at"] = serde_json::json!("2024-02-29T23:59:59.123456+03:30");
        valid["updated_at"] = serde_json::json!("2026-09-22T00:00:00Z");
        let mut missing: serde_json::Value =
            serde_json::from_str(&note_for("missing", "", 0)).unwrap();
        missing["created_at"] = serde_json::json!("");
        let mut invalid: serde_json::Value =
            serde_json::from_str(&note_for("invalid", "", 0)).unwrap();
        invalid["created_at"] = serde_json::json!("2025-02-29T00:00:00Z");
        invalid["updated_at"] = serde_json::json!("not-a-timestamp");
        let other = note_for("other-note", "", 0);

        for (note_id, project_id, payload) in [
            ("valid", "p", valid.to_string()),
            ("missing", "p", missing.to_string()),
            ("invalid", "p", invalid.to_string()),
            ("other-note", "other", other),
        ] {
            connection
                .execute(
                    "INSERT INTO notes(id,project_id,stage_id,updated_at,payload_json)
                     VALUES(?1,?2,NULL,'',?3)",
                    rusqlite::params![note_id, project_id, payload],
                )
                .unwrap();
        }

        assert_eq!(
            preflight_note_sync_project(&connection, "p").unwrap(),
            vec![
                NoteSyncPreflightIssue {
                    note_id: "invalid".to_string(),
                    code: NoteSyncPreflightIssueCode::InvalidCreatedAt,
                },
                NoteSyncPreflightIssue {
                    note_id: "invalid".to_string(),
                    code: NoteSyncPreflightIssueCode::InvalidUpdatedAt,
                },
                NoteSyncPreflightIssue {
                    note_id: "missing".to_string(),
                    code: NoteSyncPreflightIssueCode::MissingCreatedAt,
                },
            ]
        );
        assert!(preflight_note_sync_project(&connection, "other")
            .unwrap()
            .is_empty());
        assert_eq!(
            connection
                .query_row("SELECT count(*) FROM cloud_sync_outbox", [], |row| row
                    .get::<_, i64>(0))
                .unwrap(),
            0
        );
        assert_eq!(
            connection
                .query_row("SELECT count(*) FROM notes", [], |row| row.get::<_, i64>(0))
                .unwrap(),
            4
        );
    }

    #[test]
    fn note_sync_timestamp_preflight_matches_frozen_timestamp_boundaries() {
        for valid in [
            "0001-01-01T00:00:00Z",
            "2024-02-29T23:59:59.1Z",
            "9999-12-31T23:59:59.999999Z",
            "2026-09-22T00:00:00+23:59",
        ] {
            assert!(valid_note_sync_timestamp(valid), "expected valid: {valid}");
        }
        for invalid in [
            "",
            "20x6-09-22T00:00:00Z",
            "0000-01-01T00:00:00Z",
            "2025-02-29T00:00:00Z",
            "2026-09-22T00:00:00.1234567Z",
            "2026-09-22T00:00:00-00:00",
            "0001-01-01T00:00:00+00:01",
            "9999-12-31T23:59:59-00:01",
        ] {
            assert!(
                !valid_note_sync_timestamp(invalid),
                "expected invalid: {invalid}"
            );
        }
    }

    #[test]
    fn note_sync_ipc_fixture_matches_real_rust_serde_contract() {
        let expected: serde_json::Value = serde_json::from_str(include_str!(
            "../../src/infrastructure/sqlite/noteSyncIpcContract.v1.json"
        ))
        .unwrap();
        let event_id = "123e4567-e89b-42d3-a456-426614174000";
        let actual = serde_json::json!({
            "list_unsealed_note_sync_intents": [
                UnsealedNoteSyncIntent {
                    event_id: event_id.to_string(),
                    account_id: "account-1".to_string(),
                    device_id: "123e4567-e89b-42d3-a456-426614174001".to_string(),
                    project_id: "project-1".to_string(),
                    entity_id: "note-1".to_string(),
                    entity_type: "note".to_string(),
                    operation: NoteSyncOperation::Upsert,
                    revision: 1,
                    parent_event_id: None,
                    updated_at: "2026-09-22T00:00:00.000000Z".to_string(),
                    deleted_at: None,
                    local_ordinal: 1,
                    mutation_generation: MAX_SYNC_INTEGER,
                    snapshot_json: "{\"id\":\"note-1\"}".to_string(),
                    seal_state: NoteSyncSealState::Pending,
                    seal_attempt_count: 0,
                    last_error_code: None,
                    next_attempt_at: None,
                },
                UnsealedNoteSyncIntent {
                    event_id: "123e4567-e89b-42d3-a456-426614174002".to_string(),
                    account_id: "account-1".to_string(),
                    device_id: "123e4567-e89b-42d3-a456-426614174001".to_string(),
                    project_id: "project-1".to_string(),
                    entity_id: "note-2".to_string(),
                    entity_type: "note".to_string(),
                    operation: NoteSyncOperation::Delete,
                    revision: 2,
                    parent_event_id: Some(
                        "123e4567-e89b-42d3-a456-426614174003".to_string()
                    ),
                    updated_at: "2026-09-22T00:00:01.000000Z".to_string(),
                    deleted_at: Some("2026-09-22T00:00:01.000000Z".to_string()),
                    local_ordinal: 2,
                    mutation_generation: 7,
                    snapshot_json: concat!(
                        "{\"id\":\"note-2\",",
                        "\"deleted_at\":\"2026-09-22T00:00:01.000000Z\"}"
                    )
                    .to_string(),
                    seal_state: NoteSyncSealState::RetryableError,
                    seal_attempt_count: 2,
                    last_error_code: Some("runtime_unavailable".to_string()),
                    next_attempt_at: Some("2026-09-22T00:00:31.000000Z".to_string()),
                },
            ],
            "record_note_sync_seal_failure": {
                "command": RecordNoteSyncSealFailureCommand {
                    event_id: event_id.to_string(),
                    expected_mutation_generation: MAX_SYNC_INTEGER,
                    error_code: NoteSyncSealErrorCode::RuntimeUnavailable,
                },
            },
            "commit_sealed_note_sync_event": {
                "command": CommitSealedNoteSyncEventCommand {
                    event_id: event_id.to_string(),
                    expected_mutation_generation: MAX_SYNC_INTEGER,
                    envelope: EncryptedNoteSyncEnvelope {
                        crypto_version: SUPPORTED_CRYPTO_VERSION,
                        aad_version: SUPPORTED_AAD_VERSION,
                        nonce: encode_base64url(&[0; 24]),
                        ciphertext: encode_base64url(&[0; 16]),
                    },
                },
            },
            "commit_note_sync_upload_acceptance": {
                "command": CommitNoteSyncUploadAcceptanceCommand {
                    account_id: "account-1".to_string(),
                    device_id: "123e4567-e89b-42d3-a456-426614174001".to_string(),
                    receipts: vec![NoteSyncUploadReceipt {
                        event_id: "123e4567-e89b-42d3-a456-426614174004".to_string(),
                        server_sequence: 9,
                        duplicate: true,
                    }],
                },
            },
            "record_note_sync_upload_failure": {
                "account_id": "account-1",
                "device_id": "123e4567-e89b-42d3-a456-426614174001",
                "event_ids": ["123e4567-e89b-42d3-a456-426614174004"],
                "error_code": NoteSyncUploadErrorCode::RequestTimeout,
            },
            "list_sealed_note_sync_outbox": [
                SealedNoteSyncOutboxItem {
                    event_id: "123e4567-e89b-42d3-a456-426614174004".to_string(),
                    account_id: "account-1".to_string(),
                    device_id: "123e4567-e89b-42d3-a456-426614174001".to_string(),
                    project_id: "deleted-project".to_string(),
                    entity_id: "note-3".to_string(),
                    entity_type: "note".to_string(),
                    operation: NoteSyncOperation::Delete,
                    revision: 2,
                    parent_event_id: Some("123e4567-e89b-42d3-a456-426614174003".to_string()),
                    updated_at: "2026-09-22T00:00:02.000000Z".to_string(),
                    deleted_at: Some("2026-09-22T00:00:02.000000Z".to_string()),
                    local_ordinal: 3,
                    envelope: EncryptedNoteSyncEnvelope {
                        crypto_version: SUPPORTED_CRYPTO_VERSION,
                        aad_version: SUPPORTED_AAD_VERSION,
                        nonce: encode_base64url(&[0; 24]),
                        ciphertext: encode_base64url(&[0; 16]),
                    },
                }
            ],
            "operation_values": [NoteSyncOperation::Upsert, NoteSyncOperation::Delete],
            "seal_state_values": [
                NoteSyncSealState::Pending,
                NoteSyncSealState::RetryableError,
                NoteSyncSealState::Blocked,
                NoteSyncSealState::InvariantError,
            ],
            "error_code_values": [
                NoteSyncSealErrorCode::KeyUnavailable,
                NoteSyncSealErrorCode::PayloadTooLarge,
                NoteSyncSealErrorCode::EncryptedSyncObjectTooLarge,
                NoteSyncSealErrorCode::DependencyNotSynced,
                NoteSyncSealErrorCode::UnsupportedContentFormat,
                NoteSyncSealErrorCode::InvalidNotePayload,
                NoteSyncSealErrorCode::CryptoContextInvalid,
                NoteSyncSealErrorCode::InvalidSyncMetadata,
                NoteSyncSealErrorCode::InvalidEnvelope,
                NoteSyncSealErrorCode::MetadataMismatch,
                NoteSyncSealErrorCode::RuntimeUnavailable,
            ],
            "record_failure_result_values": [
                RecordNoteSyncSealFailureResult::Recorded,
                RecordNoteSyncSealFailureResult::StaleGeneration,
                RecordNoteSyncSealFailureResult::AlreadySealed,
            ],
            "commit_result_values": [
                CommitSealedNoteSyncEventResult::Sealed,
                CommitSealedNoteSyncEventResult::StaleGeneration,
                CommitSealedNoteSyncEventResult::AlreadySealed,
            ],
        });

        assert_eq!(actual, expected);
    }

    #[test]
    fn sealed_outbox_is_bounded_deterministic_and_read_only() {
        let mut connection = database();
        assert!(list_sealed_note_sync_outbox(&mut connection, "account", 2)
            .unwrap()
            .is_empty());
        let first = seal_persisted_intent(&mut connection, "z-note", "first", 1);
        let second = seal_persisted_intent(&mut connection, "a-note", "second", 2);
        let lifecycle_before: Vec<(String, i64, i64)> = connection.prepare(
            "SELECT lifecycle,attempt_count,local_ordinal FROM cloud_sync_outbox ORDER BY event_id"
        ).unwrap().query_map([], |row| Ok((row.get::<_, String>(0)?, row.get::<_, i64>(1)?, row.get::<_, i64>(2)?)))
            .unwrap().collect::<Result<_, _>>().unwrap();
        let once = list_sealed_note_sync_outbox(&mut connection, "account", 1).unwrap();
        assert_eq!(once.len(), 1);
        assert_eq!(once[0].event_id, first.event_id);
        assert_eq!(once[0].envelope.nonce, encode_canonical_base64url(&[1; 24]));
        let all = list_sealed_note_sync_outbox(&mut connection, "account", 2).unwrap();
        assert_eq!(
            all.iter().map(|item| &item.event_id).collect::<Vec<_>>(),
            vec![&first.event_id, &second.event_id]
        );
        let repeated = list_sealed_note_sync_outbox(&mut connection, "account", 2).unwrap();
        assert_eq!(all, repeated);
        assert!(
            list_sealed_note_sync_outbox(&mut connection, "other-account", 2)
                .unwrap()
                .is_empty()
        );
        assert!(list_sealed_note_sync_outbox(&mut connection, "account", 0).is_err());
        let lifecycle_after: Vec<(String, i64, i64)> = connection.prepare(
            "SELECT lifecycle,attempt_count,local_ordinal FROM cloud_sync_outbox ORDER BY event_id"
        ).unwrap().query_map([], |row| Ok((row.get::<_, String>(0)?, row.get::<_, i64>(1)?, row.get::<_, i64>(2)?)))
            .unwrap().collect::<Result<_, _>>().unwrap();
        assert_eq!(lifecycle_before, lifecycle_after);
        assert_eq!(
            connection
                .query_row("SELECT count(*) FROM cloud_sync_note_intents", [], |row| {
                    row.get::<_, i64>(0)
                })
                .unwrap(),
            0
        );
    }

    #[test]
    fn upload_acceptance_is_atomic_idempotent_and_keeps_the_encrypted_object() {
        let mut connection = database();
        let event_id = seal_persisted_intent(&mut connection, "n", "sealed upload", 0).event_id;
        let ciphertext: Vec<u8> = connection
            .query_row(
                "SELECT ciphertext FROM cloud_sync_event_objects WHERE event_id=?1",
                [&event_id],
                |row| row.get(0),
            )
            .unwrap();
        let command = CommitNoteSyncUploadAcceptanceCommand {
            account_id: "account".to_string(),
            device_id: DEVICE_ID.to_string(),
            receipts: vec![NoteSyncUploadReceipt {
                event_id: event_id.clone(),
                server_sequence: 7,
                duplicate: false,
            }],
        };
        assert_eq!(
            commit_note_sync_upload_acceptance(&mut connection, &command).unwrap(),
            vec![CommitNoteSyncUploadAcceptanceResult::Accepted]
        );
        assert!(list_sealed_note_sync_outbox(&mut connection, "account", 10)
            .unwrap()
            .is_empty());
        assert_eq!(
            connection
                .query_row(
                    "SELECT ciphertext FROM cloud_sync_event_objects WHERE event_id=?1",
                    [&event_id],
                    |row| row.get::<_, Vec<u8>>(0)
                )
                .unwrap(),
            ciphertext
        );
        assert_eq!(
            commit_note_sync_upload_acceptance(&mut connection, &command).unwrap(),
            vec![CommitNoteSyncUploadAcceptanceResult::AlreadyAccepted]
        );
        let duplicate_response = CommitNoteSyncUploadAcceptanceCommand {
            receipts: vec![NoteSyncUploadReceipt {
                duplicate: true,
                ..command.receipts[0].clone()
            }],
            ..command.clone()
        };
        assert_eq!(
            commit_note_sync_upload_acceptance(&mut connection, &duplicate_response).unwrap(),
            vec![CommitNoteSyncUploadAcceptanceResult::AlreadyAccepted]
        );
        let conflicting = CommitNoteSyncUploadAcceptanceCommand {
            receipts: vec![NoteSyncUploadReceipt {
                server_sequence: 8,
                ..command.receipts[0].clone()
            }],
            ..command
        };
        assert!(matches!(
            commit_note_sync_upload_acceptance(&mut connection, &conflicting),
            Err(NoteSyncError::ConflictingUploadReceipt)
        ));
        assert_eq!(
            connection
                .query_row(
                    "SELECT lifecycle FROM cloud_sync_outbox WHERE event_id=?1",
                    [&event_id],
                    |row| row.get::<_, String>(0)
                )
                .unwrap(),
            "accepted"
        );
    }

    #[test]
    fn upload_failure_backoff_is_durable_and_permanent_failure_does_not_starve_later_events() {
        let mut connection = database();
        let delayed = seal_persisted_intent(&mut connection, "delayed", "delayed", 0);
        let later = seal_persisted_intent(&mut connection, "later", "later", 1);
        record_note_sync_upload_failure(
            &mut connection,
            &RecordNoteSyncUploadFailureCommand {
                account_id: "account".to_string(),
                device_id: DEVICE_ID.to_string(),
                event_ids: vec![delayed.event_id.clone()],
                error_code: NoteSyncUploadErrorCode::RequestTimeout,
            },
        )
        .unwrap();
        let row: (i64, String, Option<String>) = connection.query_row(
            "SELECT attempt_count,last_error,next_attempt_at FROM cloud_sync_outbox WHERE event_id=?1", [&delayed.event_id],
            |row| Ok((row.get(0)?, row.get(1)?, row.get(2)?)),
        ).unwrap();
        assert_eq!((row.0, row.1), (1, "request_timeout".to_string()));
        assert!(row.2.is_some());
        assert_eq!(
            list_sealed_note_sync_outbox(&mut connection, "account", 10)
                .unwrap()
                .iter()
                .map(|item| &item.event_id)
                .collect::<Vec<_>>(),
            vec![&later.event_id]
        );
        record_note_sync_upload_failure(
            &mut connection,
            &RecordNoteSyncUploadFailureCommand {
                account_id: "account".to_string(),
                device_id: DEVICE_ID.to_string(),
                event_ids: vec![delayed.event_id.clone()],
                error_code: NoteSyncUploadErrorCode::ConflictingEvent,
            },
        )
        .unwrap();
        assert_eq!(
            connection
                .query_row(
                    "SELECT lifecycle FROM cloud_sync_outbox WHERE event_id=?1",
                    [&delayed.event_id],
                    |row| row.get::<_, String>(0)
                )
                .unwrap(),
            "rejected"
        );
        assert_eq!(
            list_sealed_note_sync_outbox(&mut connection, "account", 10)
                .unwrap()
                .iter()
                .map(|item| &item.event_id)
                .collect::<Vec<_>>(),
            vec![&later.event_id]
        );
    }

    #[test]
    fn sealed_outbox_enforces_dependencies_objects_and_batch_limits_after_restart() {
        let (root, path) = temporary_database_path("sealed-outbox");
        let mut connection = crate::sqlite::open_database(&path).unwrap();
        configure_database(&connection);
        let parent = seal_persisted_intent(&mut connection, "n", "parent", 3);
        let child = seal_persisted_intent(&mut connection, "n", "child", 4);
        let listed = list_sealed_note_sync_outbox(&mut connection, "account", 2).unwrap();
        assert_eq!(
            listed.iter().map(|item| &item.event_id).collect::<Vec<_>>(),
            vec![&parent.event_id, &child.event_id]
        );
        assert_eq!(
            listed[1].parent_event_id.as_deref(),
            Some(parent.event_id.as_str())
        );
        connection
            .execute(
                "UPDATE cloud_sync_event_objects SET ciphertext=?1 WHERE event_id=?2",
                rusqlite::params![
                    vec![9_u8; MAX_ENCRYPTED_SYNC_CIPHERTEXT_BYTES],
                    parent.event_id
                ],
            )
            .unwrap();
        connection
            .execute(
                "UPDATE cloud_sync_event_objects SET ciphertext=?1 WHERE event_id=?2",
                rusqlite::params![
                    vec![8_u8; MAX_ENCRYPTED_SYNC_CIPHERTEXT_BYTES],
                    child.event_id
                ],
            )
            .unwrap();
        assert_eq!(
            list_sealed_note_sync_outbox(&mut connection, "account", 2)
                .unwrap()
                .len(),
            1
        );
        drop(connection);
        let mut reopened = crate::sqlite::open_database(&path).unwrap();
        assert_eq!(
            list_sealed_note_sync_outbox(&mut reopened, "account", 2)
                .unwrap()
                .len(),
            1
        );
        reopened
            .execute(
                "DELETE FROM cloud_sync_event_objects WHERE event_id=?1",
                [&parent.event_id],
            )
            .unwrap();
        assert!(matches!(
            list_sealed_note_sync_outbox(&mut reopened, "account", 2),
            Err(NoteSyncError::InvalidOutboxRead(_))
        ));
        std::fs::remove_dir_all(root).unwrap();
    }

    #[test]
    fn sealed_outbox_never_mixes_accounts_or_devices() {
        let mut connection = database();
        let first = seal_persisted_intent(&mut connection, "account-one", "one", 6);
        let second = seal_persisted_intent(&mut connection, "account-two", "two", 7);
        connection.execute(
            "UPDATE cloud_sync_outbox SET account_id='other-account',device_id='123e4567-e89b-42d3-a456-426614174099' WHERE event_id=?1",
            [&second.event_id],
        ).unwrap();
        connection
            .execute(
                "UPDATE cloud_sync_event_objects SET account_id='other-account' WHERE event_id=?1",
                [&second.event_id],
            )
            .unwrap();
        let own = list_sealed_note_sync_outbox(&mut connection, "account", 2).unwrap();
        let other = list_sealed_note_sync_outbox(&mut connection, "other-account", 2).unwrap();
        assert_eq!(
            own.iter().map(|item| &item.event_id).collect::<Vec<_>>(),
            vec![&first.event_id]
        );
        assert_eq!(
            other.iter().map(|item| &item.event_id).collect::<Vec<_>>(),
            vec![&second.event_id]
        );
        assert_eq!(other[0].device_id, "123e4567-e89b-42d3-a456-426614174099");
    }

    #[test]
    fn sealed_outbox_round_robins_devices_durably() {
        let mut connection = database();
        let first = seal_persisted_intent(&mut connection, "first", "first", 6);
        let second = seal_persisted_intent(&mut connection, "second", "second", 7);
        connection.execute(
            "UPDATE cloud_sync_outbox SET device_id='123e4567-e89b-42d3-a456-426614174099' WHERE event_id=?1",
            [&second.event_id],
        ).unwrap();
        let first_pass = list_sealed_note_sync_outbox(&mut connection, "account", 1).unwrap();
        let second_pass = list_sealed_note_sync_outbox(&mut connection, "account", 1).unwrap();
        assert_eq!(first_pass.len(), 1);
        assert_eq!(second_pass.len(), 1);
        assert_ne!(first_pass[0].device_id, second_pass[0].device_id);
        assert_eq!(
            [first_pass[0].event_id.as_str(), second_pass[0].event_id.as_str()].into_iter().collect::<std::collections::BTreeSet<_>>(),
            [first.event_id.as_str(), second.event_id.as_str()].into_iter().collect::<std::collections::BTreeSet<_>>(),
        );
    }

    #[test]
    fn sealed_outbox_keeps_tombstones_after_project_deletion_and_rejects_corruption() {
        let mut connection = database();
        let (_, snapshot) = persist_note_intent(&mut connection, "n", "tombstone");
        let note_value: serde_json::Value = serde_json::from_str(&snapshot).unwrap();
        let transaction = connection.transaction().unwrap();
        let event =
            prepare_note_delete_intent(&transaction, "p", "n", &note_value, "2026-09-22T00:01:00Z")
                .unwrap()
                .unwrap();
        transaction
            .execute("DELETE FROM notes WHERE id='n'", [])
            .unwrap();
        transaction
            .execute("DELETE FROM project_order WHERE project_id='p'", [])
            .unwrap();
        transaction
            .execute("DELETE FROM cloud_sync_project_bindings", [])
            .unwrap();
        transaction
            .execute("DELETE FROM projects WHERE id='p'", [])
            .unwrap();
        transaction.commit().unwrap();
        assert_eq!(
            commit_sealed_note_sync_event(
                &mut connection,
                &seal_command(&event.event_id, event.mutation_generation, envelope(5)),
            )
            .unwrap(),
            CommitSealedNoteSyncEventResult::Sealed
        );
        let listed = list_sealed_note_sync_outbox(&mut connection, "account", 1).unwrap();
        assert_eq!(listed[0].event_id, event.event_id);
        assert_eq!(listed[0].operation, NoteSyncOperation::Delete);
        connection
            .execute(
                "UPDATE cloud_sync_event_objects SET crypto_version=2 WHERE event_id=?1",
                [&event.event_id],
            )
            .unwrap();
        assert!(matches!(
            list_sealed_note_sync_outbox(&mut connection, "account", 1),
            Err(NoteSyncError::InvalidOutboxRead(_))
        ));
    }

    #[test]
    fn note_sync_lists_pending_intents_bounded_in_durable_round_robin_order() {
        let mut connection = database();
        let (first, first_snapshot) = persist_note_intent(&mut connection, "later-name", "first");
        let (second, _) = persist_note_intent(&mut connection, "earlier-name", "second");
        connection
            .execute("DELETE FROM cloud_sync_project_bindings", [])
            .unwrap();

        let limited = list_unsealed_note_sync_intents(&mut connection, 1, false).unwrap();
        assert_eq!(limited.len(), 1);
        assert_eq!(limited[0].event_id, first.event_id);
        assert_eq!(limited[0].account_id, "account");
        assert_eq!(limited[0].device_id, DEVICE_ID);
        assert_eq!(limited[0].project_id, "p");
        assert_eq!(limited[0].entity_id, "later-name");
        assert_eq!(limited[0].entity_type, "note");
        assert_eq!(limited[0].operation, NoteSyncOperation::Upsert);
        assert_eq!(limited[0].revision, 1);
        assert_eq!(limited[0].parent_event_id, None);
        assert_eq!(limited[0].local_ordinal, 1);
        assert_eq!(limited[0].mutation_generation, 1);
        assert_eq!(limited[0].snapshot_json, first_snapshot);
        assert_eq!(limited[0].seal_state, NoteSyncSealState::Pending);
        assert_eq!(limited[0].seal_attempt_count, 0);
        assert_eq!(limited[0].last_error_code, None);
        assert_eq!(limited[0].next_attempt_at, None);

        let all = list_unsealed_note_sync_intents(&mut connection, 10, false).unwrap();
        assert_eq!(
            all.iter()
                .map(|intent| intent.event_id.as_str())
                .collect::<Vec<_>>(),
            vec![second.event_id.as_str(), first.event_id.as_str()]
        );
        assert!(list_unsealed_note_sync_intents(&mut connection, 0, false).is_err());
        assert!(list_unsealed_note_sync_intents(&mut connection, 201, false).is_err());
    }

    #[test]
    fn note_sync_fairness_cursor_reaches_later_pending_intents_after_restart() {
        let (root, path) = temporary_database_path("pending-fairness-reopen");
        let mut connection = crate::sqlite::open_database(&path).unwrap();
        configure_database(&connection);
        let mut event_ids = Vec::new();
        for index in 0..10 {
            let note_id = format!("note-{index:02}");
            event_ids.push(
                persist_note_intent(&mut connection, &note_id, "pending")
                    .0
                    .event_id,
            );
        }

        let first = list_unsealed_note_sync_intents(&mut connection, 8, false).unwrap();
        assert_eq!(first.len(), 8);
        assert_eq!(first[0].event_id, event_ids[0]);
        assert_eq!(first[7].event_id, event_ids[7]);
        drop(connection);

        let mut connection = crate::sqlite::open_database(&path).unwrap();
        let second = list_unsealed_note_sync_intents(&mut connection, 8, false).unwrap();
        assert!(second.iter().any(|intent| intent.event_id == event_ids[8]));
        assert!(second.iter().any(|intent| intent.event_id == event_ids[9]));
        assert_eq!(
            connection
                .query_row("SELECT count(*) FROM cloud_sync_note_intents", [], |row| {
                    row.get::<_, i64>(0)
                })
                .unwrap(),
            10
        );
        assert_eq!(
            connection
                .query_row(
                    "SELECT count(*) FROM cloud_sync_outbox WHERE lifecycle='unsealed'",
                    [],
                    |row| row.get::<_, i64>(0),
                )
                .unwrap(),
            10
        );
        drop(connection);
        std::fs::remove_dir_all(root).unwrap();
    }

    #[test]
    fn note_sync_retry_blocked_cursor_reaches_later_eligible_intent_after_restart() {
        let (root, path) = temporary_database_path("blocked-fairness-reopen");
        let mut connection = crate::sqlite::open_database(&path).unwrap();
        configure_database(&connection);
        let mut event_ids = Vec::new();
        for index in 0..34 {
            let note_id = format!("note-{index:02}");
            let prepared = persist_note_intent(&mut connection, &note_id, "blocked").0;
            if index < 33 {
                assert_eq!(
                    record_note_sync_seal_failure(
                        &mut connection,
                        &failure_command(
                            &prepared.event_id,
                            prepared.mutation_generation,
                            NoteSyncSealErrorCode::DependencyNotSynced,
                        ),
                    )
                    .unwrap(),
                    RecordNoteSyncSealFailureResult::Recorded
                );
            }
            event_ids.push(prepared.event_id);
        }

        let regular = list_unsealed_note_sync_intents(&mut connection, 8, false).unwrap();
        assert_eq!(regular.len(), 1);
        assert_eq!(regular[0].event_id, event_ids[33]);

        let first_retry = list_unsealed_note_sync_intents(&mut connection, 32, true).unwrap();
        assert_eq!(first_retry.len(), 32);
        assert!(!first_retry
            .iter()
            .any(|intent| intent.event_id == event_ids[33]));
        drop(connection);

        let mut connection = crate::sqlite::open_database(&path).unwrap();
        let second_retry = list_unsealed_note_sync_intents(&mut connection, 32, true).unwrap();
        assert!(second_retry
            .iter()
            .any(|intent| intent.event_id == event_ids[33]));
        assert_eq!(
            connection
                .query_row(
                    "SELECT max(seal_attempt_count) FROM cloud_sync_note_intents",
                    [],
                    |row| row.get::<_, i64>(0),
                )
                .unwrap(),
            1
        );
        assert_eq!(
            connection
                .query_row("SELECT count(*) FROM cloud_sync_note_intents", [], |row| {
                    row.get::<_, i64>(0)
                })
                .unwrap(),
            34
        );
        drop(connection);
        std::fs::remove_dir_all(root).unwrap();
    }

    #[test]
    fn note_sync_blocked_failure_is_durable_after_database_reopen() {
        let (root, path) = temporary_database_path("blocked-reopen");
        let mut connection = crate::sqlite::open_database(&path).unwrap();
        configure_database(&connection);
        let (intent, snapshot) = persist_note_intent(&mut connection, "n", "blocked");
        assert_eq!(
            record_note_sync_seal_failure(
                &mut connection,
                &failure_command(
                    &intent.event_id,
                    intent.mutation_generation,
                    NoteSyncSealErrorCode::KeyUnavailable,
                ),
            )
            .unwrap(),
            RecordNoteSyncSealFailureResult::Recorded
        );
        drop(connection);

        let mut connection = crate::sqlite::open_database(&path).unwrap();
        let intents = list_unsealed_note_sync_intents(&mut connection, 10, true).unwrap();
        assert_eq!(intents.len(), 1);
        assert_eq!(intents[0].seal_state, NoteSyncSealState::Blocked);
        assert_eq!(intents[0].seal_attempt_count, 1);
        assert_eq!(
            intents[0].last_error_code.as_deref(),
            Some("key_unavailable")
        );
        assert_eq!(intents[0].snapshot_json, snapshot);
        assert_eq!(intents[0].next_attempt_at, None);
        assert_eq!(
            connection
                .query_row("SELECT count(*) FROM cloud_sync_outbox", [], |row| row
                    .get::<_, i64>(0))
                .unwrap(),
            1
        );
        drop(connection);
        std::fs::remove_dir_all(root).unwrap();
    }

    #[test]
    fn note_sync_retryable_failure_has_durable_bounded_backoff() {
        let mut connection = database();
        let (intent, _) = persist_note_intent(&mut connection, "n", "retry");
        record_note_sync_seal_failure(
            &mut connection,
            &failure_command(
                &intent.event_id,
                intent.mutation_generation,
                NoteSyncSealErrorCode::RuntimeUnavailable,
            ),
        )
        .unwrap();

        let stored = connection
            .query_row(
                "SELECT seal_state,seal_attempt_count,last_error_code,next_attempt_at,
                        state_updated_at,next_attempt_at > state_updated_at
                 FROM cloud_sync_note_intents WHERE event_id=?1",
                [&intent.event_id],
                |row| {
                    Ok((
                        row.get::<_, String>(0)?,
                        row.get::<_, i64>(1)?,
                        row.get::<_, String>(2)?,
                        row.get::<_, Option<String>>(3)?,
                        row.get::<_, String>(4)?,
                        row.get::<_, i64>(5)?,
                    ))
                },
            )
            .unwrap();
        assert_eq!(stored.0, "retryable_error");
        assert_eq!(stored.1, 1);
        assert_eq!(stored.2, "runtime_unavailable");
        assert!(stored.3.is_some());
        assert_eq!(stored.5, 1);
        assert!(list_unsealed_note_sync_intents(&mut connection, 10, false)
            .unwrap()
            .is_empty());
    }

    #[test]
    fn note_sync_new_mutation_resets_sealing_failure() {
        let mut connection = database();
        let (first, _) = persist_note_intent(&mut connection, "n", "first");
        record_note_sync_seal_failure(
            &mut connection,
            &failure_command(
                &first.event_id,
                first.mutation_generation,
                NoteSyncSealErrorCode::PayloadTooLarge,
            ),
        )
        .unwrap();
        let (second, second_snapshot) = persist_note_intent(&mut connection, "n", "second");

        assert_eq!(second.event_id, first.event_id);
        assert_eq!(second.mutation_generation, 2);
        let stored = connection
            .query_row(
                "SELECT seal_state,seal_attempt_count,last_error_code,next_attempt_at,snapshot_json
                 FROM cloud_sync_note_intents WHERE event_id=?1",
                [&first.event_id],
                |row| {
                    Ok((
                        row.get::<_, String>(0)?,
                        row.get::<_, i64>(1)?,
                        row.get::<_, Option<String>>(2)?,
                        row.get::<_, Option<String>>(3)?,
                        row.get::<_, String>(4)?,
                    ))
                },
            )
            .unwrap();
        assert_eq!(stored.0, "pending");
        assert_eq!(stored.1, 0);
        assert_eq!(stored.2, None);
        assert_eq!(stored.3, None);
        assert_eq!(stored.4, second_snapshot);
    }

    #[test]
    fn note_sync_stale_failure_cannot_overwrite_new_generation() {
        let mut connection = database();
        let (first, _) = persist_note_intent(&mut connection, "n", "first");
        let (second, second_snapshot) = persist_note_intent(&mut connection, "n", "second");
        assert_eq!(
            record_note_sync_seal_failure(
                &mut connection,
                &failure_command(
                    &first.event_id,
                    first.mutation_generation,
                    NoteSyncSealErrorCode::CryptoContextInvalid,
                ),
            )
            .unwrap(),
            RecordNoteSyncSealFailureResult::StaleGeneration
        );
        let intent = list_unsealed_note_sync_intents(&mut connection, 10, false)
            .unwrap()
            .pop()
            .unwrap();
        assert_eq!(intent.mutation_generation, second.mutation_generation);
        assert_eq!(intent.snapshot_json, second_snapshot);
        assert_eq!(intent.seal_state, NoteSyncSealState::Pending);
        assert_eq!(intent.seal_attempt_count, 0);
    }

    #[test]
    fn note_sync_failure_codes_have_bounded_lifecycle_classification() {
        for code in [
            NoteSyncSealErrorCode::KeyUnavailable,
            NoteSyncSealErrorCode::PayloadTooLarge,
            NoteSyncSealErrorCode::EncryptedSyncObjectTooLarge,
            NoteSyncSealErrorCode::DependencyNotSynced,
            NoteSyncSealErrorCode::UnsupportedContentFormat,
        ] {
            assert_eq!(code.seal_state(), NoteSyncSealState::Blocked);
        }
        assert_eq!(
            NoteSyncSealErrorCode::RuntimeUnavailable.seal_state(),
            NoteSyncSealState::RetryableError
        );
        for code in [
            NoteSyncSealErrorCode::InvalidNotePayload,
            NoteSyncSealErrorCode::CryptoContextInvalid,
            NoteSyncSealErrorCode::InvalidSyncMetadata,
            NoteSyncSealErrorCode::InvalidEnvelope,
            NoteSyncSealErrorCode::MetadataMismatch,
        ] {
            assert_eq!(code.seal_state(), NoteSyncSealState::InvariantError);
        }
    }

    #[test]
    fn note_sync_envelope_requires_canonical_unpadded_base64url() {
        assert_eq!(decode_canonical_base64url("_w", 1, 1).unwrap(), vec![0xff]);
        assert!(decode_canonical_base64url("_x", 1, 1).is_err());
        assert!(decode_canonical_base64url("_w=", 1, 1).is_err());
        assert!(decode_canonical_base64url("+w", 1, 1).is_err());
    }

    #[test]
    fn note_sync_sealing_command_rejects_plaintext_and_unknown_fields() {
        let value = serde_json::json!({
            "event_id": "123e4567-e89b-42d3-a456-426614174001",
            "expected_mutation_generation": 1,
            "envelope": {
                "crypto_version": 1,
                "aad_version": 1,
                "nonce": encode_base64url(&[0_u8; 24]),
                "ciphertext": encode_base64url(&[0_u8; 16]),
            },
            "plaintext": {"content": "must not be accepted"},
        });
        assert!(serde_json::from_value::<CommitSealedNoteSyncEventCommand>(value).is_err());
    }

    #[test]
    fn note_sync_successful_sealing_stores_object_and_removes_plaintext() {
        let mut connection = database();
        let (intent, _) = persist_note_intent(&mut connection, "n", "sealed");
        let command = seal_command(&intent.event_id, intent.mutation_generation, envelope(7));
        assert_eq!(
            commit_sealed_note_sync_event(&mut connection, &command).unwrap(),
            CommitSealedNoteSyncEventResult::Sealed
        );

        let stored = connection
            .query_row(
                "SELECT event.lifecycle,object.account_id,object.crypto_version,
                        object.aad_version,length(object.nonce),length(object.ciphertext)
                 FROM cloud_sync_outbox AS event
                 JOIN cloud_sync_event_objects AS object ON object.event_id=event.event_id
                    AND object.account_id=event.account_id
                 WHERE event.event_id=?1",
                [&intent.event_id],
                |row| {
                    Ok((
                        row.get::<_, String>(0)?,
                        row.get::<_, String>(1)?,
                        row.get::<_, i64>(2)?,
                        row.get::<_, i64>(3)?,
                        row.get::<_, i64>(4)?,
                        row.get::<_, i64>(5)?,
                    ))
                },
            )
            .unwrap();
        assert_eq!(
            stored,
            ("sealed".to_string(), "account".to_string(), 1, 1, 24, 16)
        );
        assert_eq!(
            connection
                .query_row(
                    "SELECT count(*) FROM cloud_sync_note_intents WHERE event_id=?1",
                    [&intent.event_id],
                    |row| row.get::<_, i64>(0),
                )
                .unwrap(),
            0
        );
        assert!(list_unsealed_note_sync_intents(&mut connection, 10, false)
            .unwrap()
            .is_empty());
    }

    #[test]
    fn note_sync_ciphertext_survives_database_reopen() {
        let (root, path) = temporary_database_path("ciphertext-reopen");
        let mut connection = crate::sqlite::open_database(&path).unwrap();
        configure_database(&connection);
        let (intent, _) = persist_note_intent(&mut connection, "n", "reopen");
        let expected = vec![10_u8; 16];
        commit_sealed_note_sync_event(
            &mut connection,
            &seal_command(&intent.event_id, intent.mutation_generation, envelope(9)),
        )
        .unwrap();
        drop(connection);

        let mut connection = crate::sqlite::open_database(&path).unwrap();
        let ciphertext = connection
            .query_row(
                "SELECT ciphertext FROM cloud_sync_event_objects WHERE event_id=?1",
                [&intent.event_id],
                |row| row.get::<_, Vec<u8>>(0),
            )
            .unwrap();
        assert_eq!(ciphertext, expected);
        assert!(list_unsealed_note_sync_intents(&mut connection, 10, false)
            .unwrap()
            .is_empty());
        drop(connection);
        std::fs::remove_dir_all(root).unwrap();
    }

    #[test]
    fn note_sync_generation_race_rejects_stale_ciphertext() {
        let mut connection = database();
        let (first, _) = persist_note_intent(&mut connection, "n", "snapshot-a");
        let listed = list_unsealed_note_sync_intents(&mut connection, 10, false)
            .unwrap()
            .pop()
            .unwrap();
        let (second, second_snapshot) = persist_note_intent(&mut connection, "n", "snapshot-b");
        assert_eq!(
            commit_sealed_note_sync_event(
                &mut connection,
                &seal_command(&first.event_id, listed.mutation_generation, envelope(1)),
            )
            .unwrap(),
            CommitSealedNoteSyncEventResult::StaleGeneration
        );
        assert_eq!(
            connection
                .query_row("SELECT count(*) FROM cloud_sync_event_objects", [], |row| {
                    row.get::<_, i64>(0)
                })
                .unwrap(),
            0
        );
        let remaining = list_unsealed_note_sync_intents(&mut connection, 10, false)
            .unwrap()
            .pop()
            .unwrap();
        assert_eq!(remaining.event_id, first.event_id);
        assert_eq!(remaining.mutation_generation, second.mutation_generation);
        assert_eq!(remaining.snapshot_json, second_snapshot);
    }

    #[test]
    fn note_sync_sealing_rolls_back_when_object_insert_is_followed_by_failure() {
        let mut connection = database();
        let (intent, snapshot) = persist_note_intent(&mut connection, "n", "rollback-object");
        connection
            .execute_batch(
                "CREATE TRIGGER note_sync_test_fail_after_object
             BEFORE DELETE ON cloud_sync_note_intents
             BEGIN SELECT RAISE(ABORT,'injected_after_object_insert'); END;",
            )
            .unwrap();
        assert!(commit_sealed_note_sync_event(
            &mut connection,
            &seal_command(&intent.event_id, intent.mutation_generation, envelope(2)),
        )
        .is_err());
        connection
            .execute_batch("DROP TRIGGER note_sync_test_fail_after_object;")
            .unwrap();

        assert_eq!(
            connection
                .query_row("SELECT count(*) FROM cloud_sync_event_objects", [], |row| {
                    row.get::<_, i64>(0)
                })
                .unwrap(),
            0
        );
        let remaining = list_unsealed_note_sync_intents(&mut connection, 10, false)
            .unwrap()
            .pop()
            .unwrap();
        assert_eq!(remaining.snapshot_json, snapshot);
    }

    #[test]
    fn note_sync_sealing_rolls_back_temporary_sidecar_delete() {
        let mut connection = database();
        let (intent, snapshot) = persist_note_intent(&mut connection, "n", "rollback-sidecar");
        connection
            .execute_batch(
                "CREATE TRIGGER note_sync_test_fail_lifecycle
             BEFORE UPDATE OF lifecycle ON cloud_sync_outbox
             WHEN NEW.lifecycle='sealed'
             BEGIN SELECT RAISE(ABORT,'injected_before_lifecycle_update'); END;",
            )
            .unwrap();
        assert!(commit_sealed_note_sync_event(
            &mut connection,
            &seal_command(&intent.event_id, intent.mutation_generation, envelope(3)),
        )
        .is_err());
        connection
            .execute_batch("DROP TRIGGER note_sync_test_fail_lifecycle;")
            .unwrap();

        assert_eq!(
            connection
                .query_row("SELECT count(*) FROM cloud_sync_event_objects", [], |row| {
                    row.get::<_, i64>(0)
                })
                .unwrap(),
            0
        );
        let remaining = list_unsealed_note_sync_intents(&mut connection, 10, false)
            .unwrap()
            .pop()
            .unwrap();
        assert_eq!(remaining.snapshot_json, snapshot);
    }

    #[test]
    fn note_sync_duplicate_sealing_is_idempotent_only_for_matching_envelope() {
        let mut connection = database();
        let (intent, _) = persist_note_intent(&mut connection, "n", "duplicate");
        let command = seal_command(&intent.event_id, intent.mutation_generation, envelope(4));
        assert_eq!(
            commit_sealed_note_sync_event(&mut connection, &command).unwrap(),
            CommitSealedNoteSyncEventResult::Sealed
        );
        assert_eq!(
            commit_sealed_note_sync_event(&mut connection, &command).unwrap(),
            CommitSealedNoteSyncEventResult::AlreadySealed
        );
        let conflicting = seal_command(&intent.event_id, intent.mutation_generation, envelope(5));
        assert!(matches!(
            commit_sealed_note_sync_event(&mut connection, &conflicting),
            Err(NoteSyncError::ConflictingEncryptedObject)
        ));
        let stored: Vec<u8> = connection
            .query_row(
                "SELECT ciphertext FROM cloud_sync_event_objects WHERE event_id=?1",
                [&intent.event_id],
                |row| row.get(0),
            )
            .unwrap();
        assert_eq!(stored, vec![5_u8; 16]);
    }

    #[test]
    fn note_sync_rejected_commit_preserves_intent_then_retries_idempotently() {
        let mut connection = database();
        let (intent, snapshot) = persist_note_intent(&mut connection, "n", "retry-after-reject");
        let command = seal_command(&intent.event_id, intent.mutation_generation, envelope(11));
        connection
            .execute_batch(
                "CREATE TRIGGER note_sync_test_reject_commit
                 BEFORE DELETE ON cloud_sync_note_intents
                 BEGIN SELECT RAISE(ABORT,'injected_commit_rejection'); END;",
            )
            .unwrap();

        assert!(commit_sealed_note_sync_event(&mut connection, &command).is_err());
        assert_eq!(
            connection
                .query_row(
                    "SELECT snapshot_json FROM cloud_sync_note_intents WHERE event_id=?1",
                    [&intent.event_id],
                    |row| row.get::<_, String>(0),
                )
                .unwrap(),
            snapshot
        );
        assert_eq!(
            connection
                .query_row("SELECT count(*) FROM cloud_sync_event_objects", [], |row| {
                    row.get::<_, i64>(0)
                })
                .unwrap(),
            0
        );

        connection
            .execute_batch("DROP TRIGGER note_sync_test_reject_commit;")
            .unwrap();
        assert_eq!(
            commit_sealed_note_sync_event(&mut connection, &command).unwrap(),
            CommitSealedNoteSyncEventResult::Sealed
        );
        assert_eq!(
            commit_sealed_note_sync_event(&mut connection, &command).unwrap(),
            CommitSealedNoteSyncEventResult::AlreadySealed
        );
        assert_eq!(
            connection
                .query_row(
                    "SELECT count(*) FROM cloud_sync_note_intents WHERE event_id=?1",
                    [&intent.event_id],
                    |row| row.get::<_, i64>(0),
                )
                .unwrap(),
            0
        );
    }

    #[test]
    fn note_sync_rejects_invalid_nonce_and_ciphertext_lengths() {
        let mut connection = database();
        let (intent, _) = persist_note_intent(&mut connection, "n", "invalid-envelope");
        let invalid_envelopes = [
            EncryptedNoteSyncEnvelope {
                crypto_version: 1,
                aad_version: 1,
                nonce: encode_base64url(&[0_u8; 23]),
                ciphertext: encode_base64url(&[0_u8; 16]),
            },
            EncryptedNoteSyncEnvelope {
                crypto_version: 1,
                aad_version: 1,
                nonce: encode_base64url(&[0_u8; 24]),
                ciphertext: encode_base64url(&[0_u8; 15]),
            },
            EncryptedNoteSyncEnvelope {
                crypto_version: 2,
                aad_version: 1,
                nonce: encode_base64url(&[0_u8; 24]),
                ciphertext: encode_base64url(&[0_u8; 16]),
            },
        ];
        for invalid in invalid_envelopes {
            assert!(matches!(
                commit_sealed_note_sync_event(
                    &mut connection,
                    &seal_command(&intent.event_id, intent.mutation_generation, invalid),
                ),
                Err(NoteSyncError::InvalidEnvelope(_))
            ));
        }
        let oversized = EncryptedNoteSyncEnvelope {
            crypto_version: 1,
            aad_version: 1,
            nonce: encode_base64url(&[0_u8; 24]),
            ciphertext: encode_base64url(&vec![0_u8; MAX_ENCRYPTED_SYNC_CIPHERTEXT_BYTES + 1]),
        };
        assert!(matches!(
            commit_sealed_note_sync_event(
                &mut connection,
                &seal_command(&intent.event_id, intent.mutation_generation, oversized),
            ),
            Err(NoteSyncError::InvalidEnvelope(_))
        ));
        assert_eq!(
            connection
                .query_row("SELECT count(*) FROM cloud_sync_event_objects", [], |row| {
                    row.get::<_, i64>(0)
                })
                .unwrap(),
            0
        );
    }

    #[test]
    fn note_sync_sealed_event_without_object_is_an_invariant_error() {
        let mut connection = database();
        let (intent, _) = persist_note_intent(&mut connection, "n", "missing-object");
        connection
            .execute(
                "DELETE FROM cloud_sync_note_intents WHERE event_id=?1",
                [&intent.event_id],
            )
            .unwrap();
        connection
            .execute(
                "UPDATE cloud_sync_outbox SET lifecycle='sealed' WHERE event_id=?1",
                [&intent.event_id],
            )
            .unwrap();

        assert!(matches!(
            commit_sealed_note_sync_event(
                &mut connection,
                &seal_command(&intent.event_id, intent.mutation_generation, envelope(6)),
            ),
            Err(NoteSyncError::SealedObjectMissing)
        ));
        assert!(matches!(
            record_note_sync_seal_failure(
                &mut connection,
                &failure_command(
                    &intent.event_id,
                    intent.mutation_generation,
                    NoteSyncSealErrorCode::RuntimeUnavailable,
                ),
            ),
            Err(NoteSyncError::SealedObjectMissing)
        ));
    }

    #[test]
    fn note_sync_deleted_project_tombstone_can_be_sealed() {
        let mut connection = database();
        let (_, snapshot) = persist_note_intent(&mut connection, "n", "delete-me");
        let note_value: serde_json::Value = serde_json::from_str(&snapshot).unwrap();
        let transaction = connection.transaction().unwrap();
        let tombstone =
            prepare_note_delete_intent(&transaction, "p", "n", &note_value, "2026-09-22T00:01:00Z")
                .unwrap()
                .unwrap();
        transaction
            .execute("DELETE FROM notes WHERE id='n'", [])
            .unwrap();
        transaction
            .execute("DELETE FROM project_order WHERE project_id='p'", [])
            .unwrap();
        transaction
            .execute(
                "DELETE FROM cloud_sync_project_bindings WHERE project_id='p'",
                [],
            )
            .unwrap();
        transaction
            .execute("DELETE FROM projects WHERE id='p'", [])
            .unwrap();
        transaction.commit().unwrap();

        let listed = list_unsealed_note_sync_intents(&mut connection, 10, false)
            .unwrap()
            .pop()
            .unwrap();
        assert_eq!(listed.operation, NoteSyncOperation::Delete);
        assert_eq!(listed.event_id, tombstone.event_id);
        assert_eq!(listed.account_id, "account");
        assert_eq!(
            commit_sealed_note_sync_event(
                &mut connection,
                &seal_command(
                    &tombstone.event_id,
                    tombstone.mutation_generation,
                    envelope(8),
                ),
            )
            .unwrap(),
            CommitSealedNoteSyncEventResult::Sealed
        );
    }

    #[test]
    fn note_sync_sealed_head_creates_next_revision_and_parent() {
        let mut connection = database();
        let first_snapshot = note("first", 0);
        let transaction = connection.transaction().unwrap();
        let first = prepare_unsealed_note_intent(&transaction, prepare(&first_snapshot))
            .unwrap()
            .unwrap();
        transaction.execute("INSERT INTO notes(id,project_id,stage_id,updated_at,payload_json) VALUES('n','p',NULL,'2026-09-22T00:00:00Z',?1)", [&first_snapshot]).unwrap();
        transaction.commit().unwrap();
        connection
            .execute(
                "DELETE FROM cloud_sync_note_intents WHERE event_id=?1",
                [&first.event_id],
            )
            .unwrap();
        connection
            .execute(
                "UPDATE cloud_sync_outbox SET lifecycle='sealed' WHERE event_id=?1",
                [&first.event_id],
            )
            .unwrap();

        let second_snapshot = note("second", 1);
        let transaction = connection.transaction().unwrap();
        let second = prepare_unsealed_note_intent(&transaction, prepare(&second_snapshot))
            .unwrap()
            .unwrap();
        transaction
            .execute(
                "UPDATE notes SET updated_at='2026-09-22T00:00:00Z',payload_json=?1 \
                 WHERE id='n'",
                [&second_snapshot],
            )
            .unwrap();
        transaction.commit().unwrap();

        assert_ne!(second.event_id, first.event_id);
        assert_eq!(second.revision, 2);
        assert_eq!(
            second.parent_event_id.as_deref(),
            Some(first.event_id.as_str())
        );
        assert_eq!(second.local_ordinal, first.local_ordinal + 1);
        assert_eq!(second.mutation_generation, 1);
        assert!(!second.coalesced);
    }

    #[test]
    fn note_sync_failed_mutation_rolls_back_prepared_intent() {
        let mut connection = database();
        let snapshot = note("prepared", 0);
        {
            let transaction = connection.transaction().unwrap();
            prepare_unsealed_note_intent(&transaction, prepare(&snapshot))
                .unwrap()
                .unwrap();
            let mismatched = note("different", 0);
            assert!(transaction
                .execute(
                    "INSERT INTO notes(id,project_id,stage_id,updated_at,payload_json) \
                     VALUES('n','p',NULL,'now',?1)",
                    [&mismatched],
                )
                .is_err());
        }

        assert_eq!(
            connection
                .query_row("SELECT count(*) FROM cloud_sync_outbox", [], |row| {
                    row.get::<_, i64>(0)
                })
                .unwrap(),
            0
        );
        assert_eq!(
            connection
                .query_row("SELECT count(*) FROM cloud_sync_note_intents", [], |row| {
                    row.get::<_, i64>(0)
                })
                .unwrap(),
            0
        );
    }

    fn direct_database(bound: bool) -> Connection {
        let connection = Connection::open_in_memory().unwrap();
        crate::sqlite::apply_migrations(&connection).unwrap();
        configure_direct_database(&connection, bound);
        connection
    }

    fn configure_direct_database(connection: &Connection, bound: bool) {
        connection
            .execute(
                "INSERT INTO mirror_state(
                    id,source_format,source_schema_version,sync_status
                 ) VALUES(1,'test','1','healthy')",
                [],
            )
            .unwrap();
        connection
            .execute(
                "UPDATE storage_ownership SET owner='sqlite' WHERE subsystem='notes'",
                [],
            )
            .unwrap();
        connection.execute("INSERT INTO projects(id,name,infinite,unit,status,payload_json) VALUES('project','Project',0,'symbols','active','{}')", []).unwrap();
        connection
            .execute(
                "INSERT INTO project_order(project_id,position) VALUES('project',0)",
                [],
            )
            .unwrap();
        if bound {
            bind_direct_project(connection);
        }
    }

    fn bind_direct_project(connection: &Connection) {
        connection.execute("INSERT INTO cloud_sync_state(account_id,device_id,pull_cursor,ack_cursor,created_at,updated_at) VALUES('account',?1,0,0,'now','now')", [DEVICE_ID]).unwrap();
        connection.execute("INSERT INTO cloud_sync_project_bindings(project_id,account_id,created_at,updated_at) VALUES('project','account','now','now')", []).unwrap();
    }

    fn add_stage(connection: &Connection) {
        connection.execute("INSERT INTO stages(id,project_id,name,infinite,unit,status,payload_json) VALUES('stage','project','Stage',0,'symbols','active','{}')", []).unwrap();
        connection
            .execute(
                "INSERT INTO stage_order(stage_id,project_id,position) VALUES('stage','project',0)",
                [],
            )
            .unwrap();
    }

    fn outbox_identity(
        connection: &Connection,
        note_id: &str,
    ) -> (String, i64, Option<String>, i64, String) {
        connection
            .query_row(
                "SELECT event.event_id,event.revision,event.parent_event_id,
                        intent.mutation_generation,event.operation
                 FROM cloud_sync_outbox AS event
                 JOIN cloud_sync_note_intents AS intent USING(event_id)
                 WHERE event.entity_id=?1",
                [note_id],
                |row| {
                    Ok((
                        row.get(0)?,
                        row.get(1)?,
                        row.get(2)?,
                        row.get(3)?,
                        row.get(4)?,
                    ))
                },
            )
            .unwrap()
    }

    #[test]
    fn note_sync_direct_create_survives_database_reopen() {
        let root = std::env::temp_dir().join(format!(
            "nfprogress-note-sync-restart-{}-{}",
            std::process::id(),
            std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_nanos()
        ));
        std::fs::create_dir_all(&root).unwrap();
        let path = root.join("nfprogress.db");
        let mut connection = crate::sqlite::open_database(&path).unwrap();
        configure_direct_database(&connection, true);
        let snapshot =
            crate::create_note_in_connection(&mut connection, "project", None, "restart-note")
                .unwrap();
        drop(connection);

        let connection = crate::sqlite::open_database(&path).unwrap();
        let stored: String = connection
            .query_row(
                "SELECT payload_json FROM notes WHERE id='restart-note'",
                [],
                |row| row.get(0),
            )
            .unwrap();
        let event: (i64, Option<String>, i64, String, String, String, String) = connection
            .query_row(
                "SELECT event.revision,event.parent_event_id,intent.mutation_generation,
                        event.lifecycle,intent.seal_state,event.operation,intent.snapshot_json
                 FROM cloud_sync_outbox AS event
                 JOIN cloud_sync_note_intents AS intent USING(event_id)
                 WHERE event.entity_id='restart-note'",
                [],
                |row| {
                    Ok((
                        row.get(0)?,
                        row.get(1)?,
                        row.get(2)?,
                        row.get(3)?,
                        row.get(4)?,
                        row.get(5)?,
                        row.get(6)?,
                    ))
                },
            )
            .unwrap();
        assert_eq!(stored, snapshot);
        assert_eq!(
            event,
            (
                1,
                None,
                1,
                "unsealed".to_string(),
                "pending".to_string(),
                "upsert".to_string(),
                snapshot,
            )
        );
        drop(connection);
        std::fs::remove_dir_all(root).unwrap();
    }

    #[test]
    fn note_sync_direct_updates_coalesce_without_advancing_sync_revision() {
        let mut connection = direct_database(true);
        crate::create_note_in_connection(&mut connection, "project", None, "note").unwrap();
        let first = outbox_identity(&connection, "note");
        crate::update_note_in_connection(
            &mut connection,
            "project",
            "note",
            &serde_json::json!({"title":"First","pinned":true,"color":"blue"}),
            None,
        )
        .unwrap();
        crate::update_note_in_connection(
            &mut connection,
            "project",
            "note",
            &serde_json::json!({"title":"Latest","tags":["tag"],"archived":true}),
            None,
        )
        .unwrap();
        let latest = outbox_identity(&connection, "note");
        let stored: String = connection
            .query_row(
                "SELECT payload_json FROM notes WHERE id='note'",
                [],
                |row| row.get(0),
            )
            .unwrap();
        let intent: String = connection
            .query_row(
                "SELECT snapshot_json FROM cloud_sync_note_intents",
                [],
                |row| row.get(0),
            )
            .unwrap();
        let payload: serde_json::Value = serde_json::from_str(&stored).unwrap();

        assert_eq!(latest.0, first.0);
        assert_eq!(latest.1, 1);
        assert_eq!(latest.2, None);
        assert_eq!(latest.3, 3);
        assert_eq!(latest.4, "upsert");
        assert_eq!(payload["revision"], 2);
        assert_eq!(payload["title"], "Latest");
        assert_eq!(stored, intent);
    }

    #[test]
    fn note_sync_direct_delete_coalesces_or_advances_from_sealed_head() {
        let mut coalesced = direct_database(true);
        crate::create_note_in_connection(&mut coalesced, "project", None, "note").unwrap();
        let before = outbox_identity(&coalesced, "note");
        crate::delete_note_in_connection(&mut coalesced, "project", "note", None).unwrap();
        let after = outbox_identity(&coalesced, "note");
        let tombstone: serde_json::Value = serde_json::from_str(
            &coalesced
                .query_row(
                    "SELECT snapshot_json FROM cloud_sync_note_intents",
                    [],
                    |row| row.get::<_, String>(0),
                )
                .unwrap(),
        )
        .unwrap();
        assert_eq!(after.0, before.0);
        assert_eq!(after.1, 1);
        assert_eq!(after.3, 2);
        assert_eq!(after.4, "delete");
        assert_eq!(tombstone["id"], "note");
        assert_eq!(tombstone["source_type"], "project");
        let delete_times: (String, String) = coalesced
            .query_row(
                "SELECT updated_at,deleted_at FROM cloud_sync_outbox WHERE event_id=?1",
                [&after.0],
                |row| Ok((row.get(0)?, row.get(1)?)),
            )
            .unwrap();
        assert_eq!(delete_times.0, delete_times.1);
        assert_eq!(tombstone["deleted_at"], delete_times.0);
        assert_eq!(
            coalesced
                .query_row("SELECT count(*) FROM notes", [], |row| row.get::<_, i64>(0))
                .unwrap(),
            0
        );

        let mut after_seal = direct_database(true);
        crate::create_note_in_connection(&mut after_seal, "project", None, "note").unwrap();
        let sealed = outbox_identity(&after_seal, "note");
        after_seal
            .execute(
                "DELETE FROM cloud_sync_note_intents WHERE event_id=?1",
                [&sealed.0],
            )
            .unwrap();
        after_seal
            .execute(
                "UPDATE cloud_sync_outbox SET lifecycle='sealed' WHERE event_id=?1",
                [&sealed.0],
            )
            .unwrap();
        crate::delete_note_in_connection(&mut after_seal, "project", "note", None).unwrap();
        let next = outbox_identity(&after_seal, "note");
        assert_ne!(next.0, sealed.0);
        assert_eq!(next.1, 2);
        assert_eq!(next.2.as_deref(), Some(sealed.0.as_str()));
        assert_eq!(next.3, 1);
        assert_eq!(next.4, "delete");
    }

    #[test]
    fn note_sync_direct_reorder_is_exact_and_rolls_back_as_one_unit() {
        let mut connection = direct_database(true);
        crate::create_note_in_connection(&mut connection, "project", None, "first").unwrap();
        crate::create_note_in_connection(&mut connection, "project", None, "second").unwrap();
        let before_first: String = connection
            .query_row(
                "SELECT payload_json FROM notes WHERE id='first'",
                [],
                |row| row.get(0),
            )
            .unwrap();
        let before_second: String = connection
            .query_row(
                "SELECT payload_json FROM notes WHERE id='second'",
                [],
                |row| row.get(0),
            )
            .unwrap();
        let generations_before: i64 = connection
            .query_row(
                "SELECT SUM(mutation_generation) FROM cloud_sync_note_intents",
                [],
                |row| row.get(0),
            )
            .unwrap();
        connection.execute_batch("CREATE TRIGGER note_sync_test_fail_second BEFORE UPDATE ON notes WHEN NEW.id='second' BEGIN SELECT RAISE(ABORT,'injected_note_failure'); END;").unwrap();
        assert!(crate::reorder_notes_in_connection(
            &mut connection,
            "project",
            &["second".to_string(), "first".to_string()],
            None,
        )
        .is_err());
        connection
            .execute_batch("DROP TRIGGER note_sync_test_fail_second;")
            .unwrap();
        assert_eq!(
            connection
                .query_row(
                    "SELECT payload_json FROM notes WHERE id='first'",
                    [],
                    |row| row.get::<_, String>(0)
                )
                .unwrap(),
            before_first
        );
        assert_eq!(
            connection
                .query_row(
                    "SELECT payload_json FROM notes WHERE id='second'",
                    [],
                    |row| row.get::<_, String>(0)
                )
                .unwrap(),
            before_second
        );
        assert_eq!(
            connection
                .query_row(
                    "SELECT SUM(mutation_generation) FROM cloud_sync_note_intents",
                    [],
                    |row| row.get::<_, i64>(0)
                )
                .unwrap(),
            generations_before
        );

        crate::reorder_notes_in_connection(
            &mut connection,
            "project",
            &[
                "second".to_string(),
                "missing".to_string(),
                "first".to_string(),
            ],
            None,
        )
        .unwrap();
        for (id, order) in [("second", 0), ("first", 2)] {
            let (stored, intent): (String, String) = connection
                .query_row(
                    "SELECT note.payload_json,intent.snapshot_json FROM notes AS note
                 JOIN cloud_sync_outbox AS event ON event.entity_id=note.id
                 JOIN cloud_sync_note_intents AS intent USING(event_id)
                 WHERE note.id=?1",
                    [id],
                    |row| Ok((row.get(0)?, row.get(1)?)),
                )
                .unwrap();
            let payload: serde_json::Value = serde_json::from_str(&stored).unwrap();
            let stored_updated_at: String = connection
                .query_row("SELECT updated_at FROM notes WHERE id=?1", [id], |row| {
                    row.get(0)
                })
                .unwrap();
            assert_eq!(stored, intent);
            assert_eq!(payload["sort_order"], order);
            assert_eq!(payload["revision"], 1);
            assert_eq!(
                payload["updated_at"].as_str(),
                Some(stored_updated_at.as_str())
            );
        }
        assert_eq!(
            connection
                .query_row("SELECT count(*) FROM cloud_sync_outbox", [], |row| row
                    .get::<_, i64>(0))
                .unwrap(),
            2
        );
    }

    #[test]
    fn note_sync_direct_stage_and_mindmap_paths_capture_intents_and_map_effects() {
        let mut stage_connection = direct_database(true);
        add_stage(&stage_connection);
        crate::create_note_in_connection(
            &mut stage_connection,
            "project",
            Some("stage"),
            "stage-note",
        )
        .unwrap();
        crate::update_note_in_connection(
            &mut stage_connection,
            "project",
            "stage-note",
            &serde_json::json!({"title":"Stage changed"}),
            Some("stage"),
        )
        .unwrap();
        let stage_event = outbox_identity(&stage_connection, "stage-note");
        assert_eq!(stage_event.1, 1);
        assert_eq!(stage_event.3, 2);

        let mut map_connection = direct_database(false);
        let map = serde_json::json!({
            "nodeData":{"id":"root","topic":"Root","children":[]},
            "freeNodes":[{"id":"map-note","topic":"Old","children":[],"nfprogressNote":true}]
        });
        let mut project: serde_json::Value = serde_json::json!({"mindmap":map});
        map_connection
            .execute("UPDATE projects SET payload_json=?1", [project.to_string()])
            .unwrap();
        let note = serde_json::json!({
            "id":"map-note","project_id":"project","stage_id":null,"title":"",
            "content":"Old","content_format":"plain","checklist":[],"color":"default",
            "pinned":false,"archived":false,"sort_order":0,"tags":[],
            "source_type":"mindmap","source_map_id":"root","source_node_id":"map-note",
            "created_at":"now","updated_at":"now","revision":0,"metadata":{}
        });
        map_connection.execute("INSERT INTO notes(id,project_id,stage_id,updated_at,payload_json) VALUES('map-note','project',NULL,'now',?1)", [note.to_string()]).unwrap();
        crate::update_note_in_connection(
            &mut map_connection,
            "project",
            "map-note",
            &serde_json::json!({"content":"Local"}),
            None,
        )
        .unwrap();
        assert_eq!(
            map_connection
                .query_row("SELECT count(*) FROM cloud_sync_outbox", [], |row| row
                    .get::<_, i64>(0))
                .unwrap(),
            0
        );
        bind_direct_project(&map_connection);
        crate::update_note_in_connection(
            &mut map_connection,
            "project",
            "map-note",
            &serde_json::json!({"content":"New"}),
            None,
        )
        .unwrap();
        project = serde_json::from_str(
            &map_connection
                .query_row(
                    "SELECT payload_json FROM projects WHERE id='project'",
                    [],
                    |row| row.get::<_, String>(0),
                )
                .unwrap(),
        )
        .unwrap();
        assert_eq!(project["mindmap"]["freeNodes"][0]["topic"], "New");
        assert_eq!(outbox_identity(&map_connection, "map-note").4, "upsert");
        crate::delete_note_in_connection(&mut map_connection, "project", "map-note", None).unwrap();
        project = serde_json::from_str(
            &map_connection
                .query_row(
                    "SELECT payload_json FROM projects WHERE id='project'",
                    [],
                    |row| row.get::<_, String>(0),
                )
                .unwrap(),
        )
        .unwrap();
        assert!(project["mindmap"]["freeNodes"]
            .as_array()
            .unwrap()
            .is_empty());
        assert_eq!(outbox_identity(&map_connection, "map-note").4, "delete");
    }

    #[test]
    fn note_sync_direct_local_only_and_failed_note_write_leave_no_outbox() {
        let mut local = direct_database(false);
        add_stage(&local);
        crate::create_note_in_connection(&mut local, "project", None, "local").unwrap();
        crate::create_note_in_connection(&mut local, "project", Some("stage"), "stage-local")
            .unwrap();
        crate::update_note_in_connection(
            &mut local,
            "project",
            "local",
            &serde_json::json!({"checklist":[],"tags":["x"]}),
            None,
        )
        .unwrap();
        crate::reorder_notes_in_connection(
            &mut local,
            "project",
            &["local".to_string(), "stage-local".to_string()],
            None,
        )
        .unwrap();
        crate::delete_note_in_connection(&mut local, "project", "local", None).unwrap();
        local
            .execute(
                "UPDATE projects SET status='завершен' WHERE id='project'",
                [],
            )
            .unwrap();
        assert!(
            crate::create_note_in_connection(&mut local, "project", None, "read-only").is_err()
        );
        assert_eq!(
            local
                .query_row("SELECT count(*) FROM cloud_sync_outbox", [], |row| row
                    .get::<_, i64>(0))
                .unwrap(),
            0
        );

        let mut failing = direct_database(true);
        failing.execute_batch("CREATE TRIGGER note_sync_test_fail_create BEFORE INSERT ON notes BEGIN SELECT RAISE(ABORT,'injected_note_failure'); END;").unwrap();
        assert!(crate::create_note_in_connection(&mut failing, "project", None, "failed").is_err());
        assert_eq!(
            failing
                .query_row("SELECT count(*) FROM notes", [], |row| row.get::<_, i64>(0))
                .unwrap(),
            0
        );
        assert_eq!(
            failing
                .query_row("SELECT count(*) FROM cloud_sync_outbox", [], |row| row
                    .get::<_, i64>(0))
                .unwrap(),
            0
        );
        assert_eq!(
            failing
                .query_row("SELECT count(*) FROM cloud_sync_note_intents", [], |row| {
                    row.get::<_, i64>(0)
                })
                .unwrap(),
            0
        );
    }

    fn test_map(notes: &[(&str, &str)]) -> serde_json::Value {
        serde_json::json!({
            "nodeData":{"id":"map-root","topic":"Project","children":[]},
            "freeNodes": notes.iter().map(|(id, topic)| serde_json::json!({
                "id":id,"topic":topic,"children":[],"nfprogressNote":true
            })).collect::<Vec<_>>()
        })
    }

    fn save_test_map(connection: &mut Connection, map: serde_json::Value) -> Result<(), String> {
        let normalized = crate::mindmap::normalize(map.clone())?;
        crate::save_map_in_connection(
            connection,
            &crate::MapCommand {
                project_id: "project".to_string(),
                stage_id: None,
                data: map,
            },
            &normalized,
        )
    }

    #[test]
    fn note_sync_save_map_captures_create_update_and_delete() {
        let mut connection = direct_database(true);
        let note_id = crate::mindmap::linked_note_id("node");

        save_test_map(&mut connection, test_map(&[("node", "First")])).unwrap();
        let created: (String, String, i64, String) = connection
            .query_row(
                "SELECT note.payload_json,intent.snapshot_json,intent.mutation_generation,event.operation
                 FROM notes AS note
                 JOIN cloud_sync_outbox AS event ON event.entity_id=note.id
                 JOIN cloud_sync_note_intents AS intent USING(event_id)
                 WHERE note.id=?1",
                [&note_id],
                |row| Ok((row.get(0)?, row.get(1)?, row.get(2)?, row.get(3)?)),
            )
            .unwrap();
        assert_eq!(created.0, created.1);
        assert_eq!(created.2, 1);
        assert_eq!(created.3, "upsert");

        save_test_map(&mut connection, test_map(&[("node", "Latest")])).unwrap();
        let updated: (String, String, i64, i64, String) = connection
            .query_row(
                "SELECT note.payload_json,intent.snapshot_json,intent.mutation_generation,
                        event.revision,event.event_id
                 FROM notes AS note
                 JOIN cloud_sync_outbox AS event ON event.entity_id=note.id
                 JOIN cloud_sync_note_intents AS intent USING(event_id)
                 WHERE note.id=?1",
                [&note_id],
                |row| {
                    Ok((
                        row.get(0)?,
                        row.get(1)?,
                        row.get(2)?,
                        row.get(3)?,
                        row.get(4)?,
                    ))
                },
            )
            .unwrap();
        assert_eq!(updated.0, updated.1);
        assert_eq!(updated.2, 2);
        assert_eq!(updated.3, 1);
        assert_eq!(updated.4, outbox_identity(&connection, &note_id).0);
        assert_eq!(
            serde_json::from_str::<serde_json::Value>(&updated.0).unwrap()["content"],
            "Latest"
        );

        save_test_map(&mut connection, test_map(&[])).unwrap();
        assert_eq!(
            connection
                .query_row(
                    "SELECT count(*) FROM notes WHERE id=?1",
                    [&note_id],
                    |row| { row.get::<_, i64>(0) }
                )
                .unwrap(),
            0
        );
        let deleted: (String, i64, String, String, String) = connection
            .query_row(
                "SELECT event.operation,intent.mutation_generation,event.updated_at,
                        event.deleted_at,intent.snapshot_json
                 FROM cloud_sync_outbox AS event
                 JOIN cloud_sync_note_intents AS intent USING(event_id)
                 WHERE event.entity_id=?1",
                [&note_id],
                |row| {
                    Ok((
                        row.get(0)?,
                        row.get(1)?,
                        row.get(2)?,
                        row.get(3)?,
                        row.get(4)?,
                    ))
                },
            )
            .unwrap();
        let tombstone: serde_json::Value = serde_json::from_str(&deleted.4).unwrap();
        assert_eq!(deleted.0, "delete");
        assert_eq!(deleted.1, 3);
        assert_eq!(deleted.2, deleted.3);
        assert_eq!(tombstone["deleted_at"], deleted.2);
        assert_eq!(tombstone["source_type"], "mindmap");
    }

    #[test]
    fn note_sync_load_map_reconciliation_captures_hidden_write() {
        let mut connection = direct_database(true);
        let map = test_map(&[("loaded-node", "Loaded")]);
        connection
            .execute(
                "UPDATE projects SET payload_json=?1 WHERE id='project'",
                [serde_json::json!({"mindmap":map}).to_string()],
            )
            .unwrap();

        crate::reconcile_loaded_map_view_in_connection(&mut connection, "project", None).unwrap();

        let note_id = crate::mindmap::linked_note_id("loaded-node");
        let (stored, intent): (String, String) = connection
            .query_row(
                "SELECT note.payload_json,intent.snapshot_json
                 FROM notes AS note
                 JOIN cloud_sync_outbox AS event ON event.entity_id=note.id
                 JOIN cloud_sync_note_intents AS intent USING(event_id)
                 WHERE note.id=?1 AND event.lifecycle='unsealed'",
                [&note_id],
                |row| Ok((row.get(0)?, row.get(1)?)),
            )
            .unwrap();
        assert_eq!(stored, intent);
        assert_eq!(
            serde_json::from_str::<serde_json::Value>(&stored).unwrap()["content"],
            "Loaded"
        );
    }

    #[test]
    fn note_sync_local_only_load_and_save_map_create_no_outbox() {
        let mut connection = direct_database(false);
        let loaded = test_map(&[("local-node", "Loaded locally")]);
        connection
            .execute(
                "UPDATE projects SET payload_json=?1 WHERE id='project'",
                [serde_json::json!({"mindmap":loaded}).to_string()],
            )
            .unwrap();
        crate::reconcile_loaded_map_view_in_connection(&mut connection, "project", None).unwrap();
        save_test_map(
            &mut connection,
            test_map(&[("local-node", "Saved locally")]),
        )
        .unwrap();

        let note_id = crate::mindmap::linked_note_id("local-node");
        let payload: String = connection
            .query_row(
                "SELECT payload_json FROM notes WHERE id=?1",
                [&note_id],
                |row| row.get(0),
            )
            .unwrap();
        assert_eq!(
            serde_json::from_str::<serde_json::Value>(&payload).unwrap()["content"],
            "Saved locally"
        );
        assert_eq!(
            connection
                .query_row("SELECT count(*) FROM cloud_sync_outbox", [], |row| {
                    row.get::<_, i64>(0)
                })
                .unwrap(),
            0
        );
    }

    #[test]
    fn note_sync_save_map_rolls_back_all_reconciliation_changes() {
        let mut connection = direct_database(true);
        save_test_map(
            &mut connection,
            test_map(&[("first-node", "First"), ("second-node", "Second")]),
        )
        .unwrap();
        let first_id = crate::mindmap::linked_note_id("first-node");
        let second_id = crate::mindmap::linked_note_id("second-node");
        let owner_before: String = connection
            .query_row(
                "SELECT payload_json FROM projects WHERE id='project'",
                [],
                |row| row.get(0),
            )
            .unwrap();
        let first_before = connection
            .query_row(
                "SELECT note.payload_json,intent.snapshot_json,intent.mutation_generation
                 FROM notes AS note
                 JOIN cloud_sync_outbox AS event ON event.entity_id=note.id
                 JOIN cloud_sync_note_intents AS intent USING(event_id)
                 WHERE note.id=?1",
                [&first_id],
                |row| {
                    Ok((
                        row.get::<_, String>(0)?,
                        row.get::<_, String>(1)?,
                        row.get::<_, i64>(2)?,
                    ))
                },
            )
            .unwrap();
        let second_before = connection
            .query_row(
                "SELECT note.payload_json,intent.snapshot_json,intent.mutation_generation
                 FROM notes AS note
                 JOIN cloud_sync_outbox AS event ON event.entity_id=note.id
                 JOIN cloud_sync_note_intents AS intent USING(event_id)
                 WHERE note.id=?1",
                [&second_id],
                |row| {
                    Ok((
                        row.get::<_, String>(0)?,
                        row.get::<_, String>(1)?,
                        row.get::<_, i64>(2)?,
                    ))
                },
            )
            .unwrap();
        connection
            .execute_batch(&format!(
                "CREATE TRIGGER note_sync_test_fail_map_second BEFORE UPDATE ON notes
                 WHEN NEW.id='{second_id}' BEGIN SELECT RAISE(ABORT,'injected_note_failure'); END;"
            ))
            .unwrap();

        assert!(save_test_map(
            &mut connection,
            test_map(&[
                ("first-node", "Changed first"),
                ("second-node", "Changed second")
            ]),
        )
        .is_err());
        connection
            .execute_batch("DROP TRIGGER note_sync_test_fail_map_second")
            .unwrap();

        let owner_after: String = connection
            .query_row(
                "SELECT payload_json FROM projects WHERE id='project'",
                [],
                |row| row.get(0),
            )
            .unwrap();
        assert_eq!(owner_after, owner_before);
        for (id, before) in [(&first_id, first_before), (&second_id, second_before)] {
            let after = connection
                .query_row(
                    "SELECT note.payload_json,intent.snapshot_json,intent.mutation_generation
                     FROM notes AS note
                     JOIN cloud_sync_outbox AS event ON event.entity_id=note.id
                     JOIN cloud_sync_note_intents AS intent USING(event_id)
                     WHERE note.id=?1",
                    [id],
                    |row| {
                        Ok((
                            row.get::<_, String>(0)?,
                            row.get::<_, String>(1)?,
                            row.get::<_, i64>(2)?,
                        ))
                    },
                )
                .unwrap();
            assert_eq!(after, before);
        }
    }

    #[test]
    fn note_sync_combined_map_failure_rolls_back_prior_owner_and_note_changes() {
        let mut connection = direct_database(true);
        add_stage(&connection);
        connection
            .execute(
                "UPDATE projects SET payload_json=?1 WHERE id='project'",
                [serde_json::json!({
                    "combine_stage_mindmaps":true,
                    "mindmap":test_map(&[("project-existing", "Project old")])
                })
                .to_string()],
            )
            .unwrap();
        let stage_map = serde_json::json!({
            "nodeData":{"id":"stage-root","topic":"Stage","children":[]},
            "freeNodes":[
                {"id":"stage-existing","topic":"Stage old","children":[],"nfprogressNote":true}
            ]
        });
        connection
            .execute(
                "UPDATE stages SET payload_json=?1 WHERE id='stage'",
                [serde_json::json!({"mindmap":stage_map}).to_string()],
            )
            .unwrap();
        crate::reconcile_loaded_map_view_in_connection(&mut connection, "project", None).unwrap();

        let mut changed_stage_map: serde_json::Value = serde_json::from_str::<serde_json::Value>(
            &connection
                .query_row(
                    "SELECT payload_json FROM stages WHERE id='stage'",
                    [],
                    |row| row.get::<_, String>(0),
                )
                .unwrap(),
        )
        .unwrap()["mindmap"]
            .clone();
        changed_stage_map["freeNodes"][0]["topic"] = "Stage changed".into();
        connection
            .execute(
                "UPDATE stages SET payload_json=?1 WHERE id='stage'",
                [serde_json::json!({"mindmap":changed_stage_map}).to_string()],
            )
            .unwrap();

        let (project, stages) = {
            let repository = crate::ProjectsRepository::new(&mut connection);
            (
                repository.get_project("project").unwrap().unwrap(),
                repository.list_stages("project").unwrap(),
            )
        };
        let mut combined = crate::compose_combined_map(&project, &stages).unwrap();
        combined["freeNodes"][0]["topic"] = "Project changed".into();
        let normalized = crate::mindmap::normalize(combined.clone()).unwrap();
        let project_owner_before: String = connection
            .query_row(
                "SELECT payload_json FROM projects WHERE id='project'",
                [],
                |row| row.get(0),
            )
            .unwrap();
        let stage_owner_before: String = connection
            .query_row(
                "SELECT payload_json FROM stages WHERE id='stage'",
                [],
                |row| row.get(0),
            )
            .unwrap();
        let project_note_id = crate::mindmap::linked_note_id("project-existing");
        let stage_note_id = crate::mindmap::linked_note_id("stage-existing");
        let note_state = |connection: &Connection, note_id: &str| {
            connection
                .query_row(
                    "SELECT note.payload_json,intent.snapshot_json,intent.mutation_generation
                     FROM notes AS note
                     JOIN cloud_sync_outbox AS event ON event.entity_id=note.id
                     JOIN cloud_sync_note_intents AS intent USING(event_id)
                     WHERE note.id=?1",
                    [note_id],
                    |row| {
                        Ok((
                            row.get::<_, String>(0)?,
                            row.get::<_, String>(1)?,
                            row.get::<_, i64>(2)?,
                        ))
                    },
                )
                .unwrap()
        };
        let project_note_before = note_state(&connection, &project_note_id);
        let stage_note_before = note_state(&connection, &stage_note_id);
        connection
            .execute_batch(&format!(
                "CREATE TRIGGER note_sync_test_fail_combined_stage BEFORE UPDATE ON notes
                 WHEN NEW.id='{stage_note_id}' BEGIN SELECT RAISE(ABORT,'injected_note_failure'); END;"
            ))
            .unwrap();

        assert!(crate::save_map_in_connection(
            &mut connection,
            &crate::MapCommand {
                project_id: "project".to_string(),
                stage_id: None,
                data: combined,
            },
            &normalized,
        )
        .is_err());
        connection
            .execute_batch("DROP TRIGGER note_sync_test_fail_combined_stage")
            .unwrap();

        assert_eq!(
            connection
                .query_row(
                    "SELECT payload_json FROM projects WHERE id='project'",
                    [],
                    |row| row.get::<_, String>(0)
                )
                .unwrap(),
            project_owner_before
        );
        assert_eq!(
            connection
                .query_row(
                    "SELECT payload_json FROM stages WHERE id='stage'",
                    [],
                    |row| row.get::<_, String>(0)
                )
                .unwrap(),
            stage_owner_before
        );
        assert_eq!(
            note_state(&connection, &project_note_id),
            project_note_before
        );
        assert_eq!(note_state(&connection, &stage_note_id), stage_note_before);
    }

    #[test]
    fn note_sync_combined_save_map_captures_project_and_stage_notes() {
        let mut connection = direct_database(true);
        add_stage(&connection);
        let project_map = test_map(&[]);
        let stage_map = serde_json::json!({
            "nodeData":{"id":"stage-root","topic":"Stage","children":[]},
            "freeNodes":[
                {"id":"stage-node","topic":"Stage note","children":[],"nfprogressNote":true}
            ]
        });
        connection
            .execute(
                "UPDATE projects SET payload_json=?1 WHERE id='project'",
                [serde_json::json!({
                    "combine_stage_mindmaps":true,
                    "mindmap":project_map
                })
                .to_string()],
            )
            .unwrap();
        connection
            .execute(
                "UPDATE stages SET payload_json=?1 WHERE id='stage'",
                [serde_json::json!({"mindmap":stage_map}).to_string()],
            )
            .unwrap();
        let (project, stages) = {
            let repository = crate::ProjectsRepository::new(&mut connection);
            (
                repository.get_project("project").unwrap().unwrap(),
                repository.list_stages("project").unwrap(),
            )
        };
        let mut combined = crate::compose_combined_map(&project, &stages).unwrap();
        combined["freeNodes"] = serde_json::json!([
            {"id":"project-node","topic":"Project note","children":[],"nfprogressNote":true}
        ]);
        let normalized = crate::mindmap::normalize(combined.clone()).unwrap();
        crate::save_map_in_connection(
            &mut connection,
            &crate::MapCommand {
                project_id: "project".to_string(),
                stage_id: None,
                data: combined,
            },
            &normalized,
        )
        .unwrap();

        assert_eq!(
            connection
                .query_row("SELECT count(*) FROM notes", [], |row| row.get::<_, i64>(0))
                .unwrap(),
            2
        );
        assert_eq!(
            connection
                .query_row("SELECT count(*) FROM cloud_sync_note_intents", [], |row| {
                    row.get::<_, i64>(0)
                })
                .unwrap(),
            2
        );
        assert_eq!(
            connection
                .query_row(
                    "SELECT count(*) FROM notes WHERE stage_id='stage'",
                    [],
                    |row| row.get::<_, i64>(0)
                )
                .unwrap(),
            1
        );
    }
}
