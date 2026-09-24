//! Test-only JSON bridge used by the cross-runtime C15 acceptance proof.
//! It is compiled only by `cargo test` and exposes no production command.

use std::path::{Path, PathBuf};

use rusqlite::OptionalExtension;
use serde_json::{json, Value};

use crate::account_binding::{provision_cloud_identity, CloudIdentity};
use crate::note_sync::{
    apply_verified_received_note_ipc, commit_note_sync_ack, commit_note_sync_inbound_page,
    prepare_note_sync_ack, prepare_cloud_project_bootstrap, confirm_cloud_project_registration,
    capture_initial_note_sync_intents, read_initial_note_cohort_status,
    mark_cloud_project_bootstrap_completing, mark_cloud_project_bootstrap_ready,
    import_remote_cloud_project, commit_sealed_note_sync_event,
    commit_note_sync_upload_acceptance, ApplyVerifiedReceivedNoteIpcCommand,
    CommitNoteSyncAckCommand, CommitNoteSyncInboundPageCommand, EncryptedNoteSyncEnvelope,
    InboundNoteSyncItem, PrepareNoteSyncAckCommand, PrepareCloudProjectBootstrapCommand,
    ConfirmCloudProjectRegistrationCommand, CloudProjectBootstrapScopeCommand,
    ImportRemoteCloudProjectCommand, CommitSealedNoteSyncEventCommand,
    CommitNoteSyncUploadAcceptanceCommand, NoteSyncUploadReceipt,
};
use crate::sqlite::{open_database, open_privileged_remote_apply_database};

fn required_string<'a>(value: &'a Value, key: &str) -> &'a str {
    value.get(key).and_then(Value::as_str).unwrap_or_else(|| panic!("missing string field {key}"))
}

fn required_i64(value: &Value, key: &str) -> i64 {
    value.get(key).and_then(Value::as_i64).unwrap_or_else(|| panic!("missing integer field {key}"))
}

fn bytes(value: &Value, key: &str) -> Vec<u8> {
    value.get(key).and_then(Value::as_array).unwrap_or_else(|| panic!("missing byte array {key}"))
        .iter().map(|item| item.as_u64().filter(|byte| *byte <= 255).expect("invalid byte") as u8).collect()
}

fn database_path(request: &Value) -> PathBuf {
    PathBuf::from(required_string(request, "database_path"))
}

fn write_response(value: &Value) {
    let output = std::env::var("NFPROGRESS_C15_NATIVE_BRIDGE_RESPONSE")
        .expect("NFPROGRESS_C15_NATIVE_BRIDGE_RESPONSE is required");
    std::fs::write(output, serde_json::to_vec(value).expect("serialize bridge response"))
        .expect("write bridge response");
}

fn provision(request: &Value) -> Value {
    let path = database_path(request);
    let root = Path::new(required_string(request, "data_root"));
    std::fs::create_dir_all(root).expect("create device root");
    let mut connection = open_database(&path).expect("open device database");
    crate::initialize_fresh_desktop_database(&connection, root).expect("initialize desktop database");
    let identity: CloudIdentity = provision_cloud_identity(
        &mut connection,
        required_string(request, "canonical_user_id"),
    ).expect("provision cloud identity");
    let project_id = required_string(request, "project_id");
    let create_project = request.get("create_project").and_then(Value::as_bool).unwrap_or(true);
    if create_project {
        connection.execute(
            "INSERT INTO projects(id,name,goal,infinite,unit,status,payload_json)
             VALUES(?1,'Cross-runtime project',NULL,1,'symbols','active','{}')",
            [project_id],
        ).expect("create project fixture");
        connection.execute(
            "INSERT INTO project_order(project_id,position) VALUES(?1,0)",
            [project_id],
        ).expect("create project order fixture");
    }
    if create_project && request.get("bind_project").and_then(Value::as_bool).unwrap_or(true) {
        connection.execute(
            "INSERT INTO cloud_sync_project_bindings(project_id,account_id,created_at,updated_at)
             VALUES(?1,?2,'2026-09-23T00:00:00.000000Z','2026-09-23T00:00:00.000000Z')",
            rusqlite::params![project_id, identity.local_account_id],
        ).expect("create explicit cloud project binding fixture");
    }
    if let Some(notes) = request.get("notes").and_then(Value::as_array) {
        for note in notes {
            connection.execute(
                "INSERT INTO notes(id,project_id,stage_id,updated_at,payload_json)
                 VALUES(?1,?2,NULL,?3,?4)",
                rusqlite::params![
                    required_string(note, "id"), project_id,
                    required_string(note, "updated_at"), serde_json::to_string(note).unwrap(),
                ],
            ).expect("create Note fixture");
        }
    }
    json!({
        "local_account_id": identity.local_account_id,
        "device_id": identity.device_id,
    })
}

fn bootstrap_scope(request: &Value) -> CloudProjectBootstrapScopeCommand {
    CloudProjectBootstrapScopeCommand {
        project_id: required_string(request, "project_id").to_string(),
        account_id: required_string(request, "local_account_id").to_string(),
        device_id: required_string(request, "device_id").to_string(),
        bootstrap_id: required_string(request, "bootstrap_id").to_string(),
    }
}

fn bootstrap_prepare(request: &Value) -> Value {
    let path = database_path(request);
    let mut connection = open_database(&path).expect("open bootstrap database");
    serde_json::to_value(prepare_cloud_project_bootstrap(&mut connection, &PrepareCloudProjectBootstrapCommand {
        project_id: required_string(request, "project_id").to_string(),
        account_id: required_string(request, "local_account_id").to_string(),
        device_id: required_string(request, "device_id").to_string(),
        mode: crate::note_sync::CloudProjectBootstrapMode::UploadExisting,
    }).expect("prepare durable bootstrap token")).unwrap()
}

fn bootstrap_prepare_capture(request: &Value) -> Value {
    let path = database_path(request);
    let mut connection = open_database(&path).expect("open bootstrap database");
    let prepared = prepare_cloud_project_bootstrap(&mut connection, &PrepareCloudProjectBootstrapCommand {
        project_id: required_string(request, "project_id").to_string(),
        account_id: required_string(request, "local_account_id").to_string(),
        device_id: required_string(request, "device_id").to_string(),
        mode: crate::note_sync::CloudProjectBootstrapMode::UploadExisting,
    }).expect("prepare durable bootstrap token");
    assert_eq!(prepared.bootstrap_id, required_string(request, "bootstrap_id"));
    let registered = confirm_cloud_project_registration(&mut connection, &ConfirmCloudProjectRegistrationCommand {
        project_id: prepared.project_id.clone(), account_id: prepared.account_id.clone(),
        device_id: prepared.device_id.clone(), bootstrap_id: prepared.bootstrap_id.clone(),
        remote_state: "initializing".to_string(), remote_high_water: required_i64(request, "remote_high_water"),
    }).expect("confirm server registration");
    let captured = capture_initial_note_sync_intents(&mut connection, &CloudProjectBootstrapScopeCommand {
        project_id: registered.project_id, account_id: registered.account_id,
        device_id: registered.device_id, bootstrap_id: registered.bootstrap_id,
    }).expect("capture initial Note cohort");
    let mut statement = connection.prepare(
        "SELECT event.event_id,event.project_id,event.entity_id,event.entity_type,event.operation,
                event.revision,event.updated_at,event.deleted_at,intent.mutation_generation,intent.snapshot_json
         FROM cloud_sync_outbox event JOIN cloud_sync_note_intents intent USING(event_id)
         WHERE event.account_id=?1 AND event.device_id=?2 AND event.local_ordinal<=?3
         ORDER BY event.local_ordinal",
    ).expect("prepare captured cohort read");
    let events: Vec<Value> = statement.query_map(
        rusqlite::params![captured.account_id, captured.device_id, captured.initial_local_ordinal_hi],
        |row| Ok(json!({
            "event_id":row.get::<_,String>(0)?, "project_id":row.get::<_,String>(1)?,
            "entity_id":row.get::<_,String>(2)?, "entity_type":row.get::<_,String>(3)?,
            "operation":row.get::<_,String>(4)?, "revision":row.get::<_,i64>(5)?,
            "updated_at":row.get::<_,String>(6)?, "deleted_at":row.get::<_,Option<String>>(7)?,
            "mutation_generation":row.get::<_,i64>(8)?,
            "note":serde_json::from_str::<Value>(&row.get::<_,String>(9)?).unwrap(),
        })),
    ).expect("read captured cohort").collect::<Result<_,_>>().expect("collect captured cohort");
    drop(statement);
    let mut ids_statement = connection.prepare(
        "SELECT event_id FROM cloud_sync_outbox WHERE account_id=?1 AND device_id=?2
         AND local_ordinal<=?3 ORDER BY local_ordinal",
    ).expect("prepare cohort identity read");
    let event_ids: Vec<String> = ids_statement.query_map(
        rusqlite::params![captured.account_id, captured.device_id, captured.initial_local_ordinal_hi],
        |row| row.get(0),
    ).expect("read cohort identities").collect::<Result<_,_>>().expect("collect cohort identities");
    json!({"record":captured,"events":events,"event_ids":event_ids})
}

fn bootstrap_commit_upload(request: &Value) -> Value {
    let path = database_path(request);
    let mut connection = open_database(&path).expect("open bootstrap receipt database");
    for accepted in request.get("accepted").and_then(Value::as_array).expect("accepted receipts") {
        let object = accepted.get("object").expect("sealed object");
        commit_sealed_note_sync_event(&mut connection, &CommitSealedNoteSyncEventCommand {
            event_id: required_string(accepted, "event_id").to_string(),
            expected_mutation_generation: required_i64(accepted, "mutation_generation"),
            envelope: EncryptedNoteSyncEnvelope {
                crypto_version: required_i64(object, "crypto_version"),
                aad_version: required_i64(object, "aad_version"),
                nonce: required_string(object, "nonce").to_string(),
                ciphertext: required_string(object, "ciphertext").to_string(),
            },
        }).expect("commit immutable sealed envelope");
        commit_note_sync_upload_acceptance(&mut connection, &CommitNoteSyncUploadAcceptanceCommand {
            account_id: required_string(request, "local_account_id").to_string(),
            device_id: required_string(request, "device_id").to_string(),
            receipts: vec![NoteSyncUploadReceipt {
                event_id: required_string(accepted, "event_id").to_string(),
                server_sequence: required_i64(accepted, "server_sequence"), duplicate: false,
            }],
        }).expect("commit durable server receipt");
    }
    let cohort = read_initial_note_cohort_status(&mut connection, &bootstrap_scope(request)).expect("read initial cohort");
    let completing = if cohort.complete {
        Some(mark_cloud_project_bootstrap_completing(&mut connection, &bootstrap_scope(request)).expect("mark completing"))
    } else { None };
    json!({"cohort":cohort,"completing":completing})
}

fn bootstrap_confirm_active(request: &Value) -> Value {
    let path = database_path(request);
    let mut connection = open_database(&path).expect("open active bootstrap database");
    serde_json::to_value(confirm_cloud_project_registration(&mut connection, &ConfirmCloudProjectRegistrationCommand {
        project_id: required_string(request, "project_id").to_string(),
        account_id: required_string(request, "local_account_id").to_string(),
        device_id: required_string(request, "device_id").to_string(),
        bootstrap_id: required_string(request, "bootstrap_id").to_string(),
        remote_state: "active".to_string(), remote_high_water: required_i64(request, "remote_high_water"),
    }).expect("confirm active server registry")).unwrap()
}

fn bootstrap_import(request: &Value) -> Value {
    let path = database_path(request);
    let mut connection = open_database(&path).expect("open import database");
    serde_json::to_value(import_remote_cloud_project(&mut connection, &ImportRemoteCloudProjectCommand {
        project_id: required_string(request, "project_id").to_string(),
        display_name: required_string(request, "display_name").to_string(),
        account_id: required_string(request, "local_account_id").to_string(),
        device_id: required_string(request, "device_id").to_string(),
        bootstrap_id: required_string(request, "bootstrap_id").to_string(),
        remote_high_water: required_i64(request, "remote_high_water"),
    }).expect("import active remote project")).unwrap()
}

fn bootstrap_mark_ready(request: &Value) -> Value {
    let path = database_path(request);
    let mut connection = open_database(&path).expect("open ready bootstrap database");
    serde_json::to_value(mark_cloud_project_bootstrap_ready(&mut connection, &bootstrap_scope(request)).expect("mark bootstrap ready")).unwrap()
}

fn receive_apply_prepare(request: &Value) -> Value {
    let path = database_path(request);
    let account_id = required_string(request, "local_account_id").to_string();
    let device_id = required_string(request, "device_id").to_string();
    let canonical_user_id = required_string(request, "canonical_user_id").to_string();
    let item = request.get("item").expect("missing pulled item");
    let event = item.get("event").expect("missing pulled event");
    let object = item.get("object").expect("missing pulled object");
    let event_id = required_string(event, "event_id").to_string();
    let server_sequence = required_i64(event, "server_sequence");
    let source_device_id = required_string(event, "device_id").to_string();
    let next_cursor = required_i64(request, "next_cursor");
    let expected_cursor = request.get("expected_cursor").and_then(Value::as_i64).unwrap_or(0);

    let inbound = CommitNoteSyncInboundPageCommand {
        account_id: account_id.clone(),
        device_id: device_id.clone(),
        canonical_user_id: canonical_user_id.clone(),
        expected_cursor,
        next_cursor,
        has_more: false,
        items: vec![InboundNoteSyncItem {
            event_id: event_id.clone(),
            server_sequence,
            source_device_id: source_device_id.clone(),
            project_id: required_string(event, "project_id").to_string(),
            entity_id: required_string(event, "entity_id").to_string(),
            entity_type: required_string(event, "entity_type").to_string(),
            operation: required_string(event, "operation").to_string(),
            revision: required_i64(event, "revision"),
            updated_at: required_string(event, "updated_at").to_string(),
            deleted_at: event.get("deleted_at").and_then(Value::as_str).map(str::to_string),
            envelope: Some(EncryptedNoteSyncEnvelope {
                crypto_version: required_i64(object, "crypto_version"),
                aad_version: required_i64(object, "aad_version"),
                nonce: required_string(object, "nonce").to_string(),
                ciphertext: required_string(object, "ciphertext").to_string(),
            }),
        }],
    };
    let mut connection = open_database(&path).expect("open inbox database");
    let inbound_result = commit_note_sync_inbound_page(&mut connection, &inbound)
        .expect("commit encrypted inbound page");
    drop(connection);

    let opened = request.get("opened").expect("missing TypeScript opened payload");
    let mut privileged = open_privileged_remote_apply_database(&path).expect("open protected apply database");
    let apply_result = apply_verified_received_note_ipc(
        &mut privileged,
        ApplyVerifiedReceivedNoteIpcCommand {
            account_id: account_id.clone(),
            canonical_user_id: canonical_user_id.clone(),
            pulling_device_id: device_id.clone(),
            event_id: event_id.clone(),
            server_sequence,
            source_device_id,
            crypto_version: required_i64(opened, "crypto_version"),
            aad_version: required_i64(opened, "aad_version"),
            nonce: bytes(opened, "nonce"),
            ciphertext: bytes(opened, "ciphertext"),
            plaintext: bytes(opened, "plaintext"),
        },
    ).expect("protected remote apply");
    let note_payload: Option<String> = privileged.connection().query_row(
        "SELECT payload_json FROM notes WHERE id=?1",
        [required_string(event, "entity_id")],
        |row| row.get(0),
    ).optional().expect("read applied Note");
    let head: Option<(String, i64)> = privileged.connection().query_row(
        "SELECT head_event_id,head_sync_revision FROM cloud_sync_entities
         WHERE account_id=?1 AND project_id=?2 AND entity_id=?3 AND entity_type='note'",
        rusqlite::params![account_id, required_string(event, "project_id"), required_string(event, "entity_id")],
        |row| Ok((row.get(0)?, row.get(1)?)),
    ).optional().expect("read applied Note head");
    let inbox_state: String = privileged.connection().query_row(
        "SELECT state FROM cloud_sync_inbox WHERE account_id=?1 AND event_id=?2",
        rusqlite::params![account_id, event_id],
        |row| row.get(0),
    ).expect("read applied inbox state");
    drop(privileged);

    let mut connection = open_database(&path).expect("reopen ACK database");
    let candidate = prepare_note_sync_ack(
        &mut connection,
        &PrepareNoteSyncAckCommand {
            account_id,
            device_id,
            canonical_user_id,
        },
    ).expect("prepare durable ACK candidate");
    json!({
        "inbound": inbound_result,
        "apply_result": apply_result,
        "note": note_payload.map(|payload| serde_json::from_str::<Value>(&payload).expect("parse applied Note")),
        "head_event_id": head.as_ref().map(|value| value.0.clone()),
        "head_revision": head.as_ref().map(|value| value.1),
        "inbox_state": inbox_state,
        "ack": candidate,
    })
}

fn commit_ack(request: &Value) -> Value {
    let path = database_path(request);
    let account_id = required_string(request, "local_account_id").to_string();
    let mut connection = open_database(&path).expect("open ACK database");
    let result = commit_note_sync_ack(
        &mut connection,
        &CommitNoteSyncAckCommand {
            account_id: account_id.clone(),
            device_id: required_string(request, "device_id").to_string(),
            canonical_user_id: required_string(request, "canonical_user_id").to_string(),
            expected_old_ack_cursor: required_i64(request, "expected_old_ack_cursor"),
            acknowledged_cursor: required_i64(request, "acknowledged_cursor"),
        },
    ).expect("commit confirmed remote ACK");
    let (pull_cursor, ack_cursor): (i64, i64) = connection.query_row(
        "SELECT pull_cursor,ack_cursor FROM cloud_sync_state WHERE account_id=?1",
        [&account_id],
        |row| Ok((row.get(0)?, row.get(1)?)),
    ).expect("read durable cursors");
    let note_count: i64 = connection.query_row(
        "SELECT count(*) FROM notes WHERE project_id=?1",
        [required_string(request, "project_id")],
        |row| row.get(0),
    ).optional().expect("read Note count").unwrap_or(0);
    json!({
        "result": result,
        "pull_cursor": pull_cursor,
        "ack_cursor": ack_cursor,
        "note_count": note_count,
    })
}

#[test]
#[ignore = "invoked only by tests/test_c15_headless_cross_runtime.py"]
fn c15_headless_native_bridge() {
    let request_path = std::env::var("NFPROGRESS_C15_NATIVE_BRIDGE_REQUEST")
        .expect("NFPROGRESS_C15_NATIVE_BRIDGE_REQUEST is required");
    let request: Value = serde_json::from_slice(
        &std::fs::read(request_path).expect("read bridge request"),
    ).expect("parse bridge request");
    let response = match required_string(&request, "action") {
        "provision" => provision(&request),
        "bootstrap_prepare" => bootstrap_prepare(&request),
        "bootstrap_prepare_capture" => bootstrap_prepare_capture(&request),
        "bootstrap_commit_upload" => bootstrap_commit_upload(&request),
        "bootstrap_confirm_active" => bootstrap_confirm_active(&request),
        "bootstrap_import" => bootstrap_import(&request),
        "bootstrap_mark_ready" => bootstrap_mark_ready(&request),
        "receive_apply_prepare" => receive_apply_prepare(&request),
        "commit_ack" => commit_ack(&request),
        action => panic!("unsupported native bridge action {action}"),
    };
    write_response(&response);
}
