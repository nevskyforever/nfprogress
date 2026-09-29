//! C18 project-metadata storage boundary, activated only by explicit migration.
//! The caller must authenticate and unframe the C18 object before passing its
//! canonical payload here; this module repeats scope and causal checks in SQLite.
use rusqlite::{params, Connection, OptionalExtension, TransactionBehavior};
use serde::{Deserialize, Serialize};
use serde_json::{json, Map, Value};

const MAX_BYTES: usize = 1024 * 1024;
const MAX_REVISION: i64 = 9_007_199_254_740_991;
const FIELDS: [&str; 12] = [
    "auto_freeze",
    "combine_stage_mindmaps",
    "deadline",
    "goal",
    "infinite",
    "name",
    "personal_goal",
    "stages_enabled",
    "status",
    "streak_enabled",
    "unit",
    "work_method",
];
const LEGACY_PROJECT_FIELDS: &[&str] = &[
    "id",
    "name",
    "goal",
    "infinite",
    "total",
    "progress",
    "deadline",
    "status",
    "unit",
    "created_at",
    "updated_at",
    "notes_updated_at",
    "mindmap_updated_at",
    "completed_at",
    "personal_goal",
    "today_goal",
    "planning_date",
    "plan_daily_goal",
    "added_today",
    "remaining",
    "streak_enabled",
    "streak_status",
    "streak_length",
    "max_streak",
    "auto_freeze",
    "progress_entries",
    "project_notes",
    "mindmap",
    "stages",
    "stages_enabled",
    "combine_stage_mindmaps",
    "cover_image",
    "folder_id",
    "sync_available",
    "work_method",
];

#[derive(Debug)]
pub(crate) enum MetadataError {
    Invalid,
    Scope,
    Conflict,
    Database(rusqlite::Error),
}
impl From<rusqlite::Error> for MetadataError {
    fn from(e: rusqlite::Error) -> Self {
        Self::Database(e)
    }
}
impl std::fmt::Display for MetadataError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::Invalid => write!(f, "invalid_project_metadata"),
            Self::Scope => write!(f, "metadata_scope_mismatch"),
            Self::Conflict => write!(f, "metadata_conflict"),
            Self::Database(e) => write!(f, "{e}"),
        }
    }
}
fn uuid(value: &str) -> bool {
    let b = value.as_bytes();
    b.len() == 36
        && (b'1'..=b'5').contains(&b[14])
        && matches!(b[19], b'8' | b'9' | b'a' | b'b')
        && b.iter().enumerate().all(|(i, c)| {
            if matches!(i, 8 | 13 | 18 | 23) {
                *c == b'-'
            } else {
                c.is_ascii_hexdigit() && !c.is_ascii_uppercase()
            }
        })
}
fn exact(o: &Map<String, Value>, keys: &[&str]) -> bool {
    o.len() == keys.len() && keys.iter().all(|k| o.contains_key(*k))
}
fn str_field<'a>(o: &'a Map<String, Value>, key: &str) -> Result<&'a str, MetadataError> {
    o.get(key)
        .and_then(Value::as_str)
        .filter(|s| !s.is_empty() && s.len() <= 512)
        .ok_or(MetadataError::Invalid)
}
fn positive(o: &Map<String, Value>, key: &str) -> Result<i64, MetadataError> {
    o.get(key)
        .and_then(Value::as_i64)
        .filter(|v| (1..=MAX_REVISION).contains(v))
        .ok_or(MetadataError::Invalid)
}
fn timestamp(value: &str) -> bool {
    let b = value.as_bytes();
    if !(b.len() == 27
        && b[4] == b'-'
        && b[7] == b'-'
        && b[10] == b'T'
        && b[13] == b':'
        && b[16] == b':'
        && b[19] == b'.'
        && b[26] == b'Z'
        && b.iter()
            .enumerate()
            .all(|(i, c)| matches!(i, 4 | 7 | 10 | 13 | 16 | 19 | 26) || c.is_ascii_digit()))
    {
        return false;
    }
    let number = |start: usize, end: usize| value[start..end].parse::<u32>().unwrap();
    let (year, month, day, hour, minute, second) = (
        number(0, 4),
        number(5, 7),
        number(8, 10),
        number(11, 13),
        number(14, 16),
        number(17, 19),
    );
    let leap = year % 4 == 0 && (year % 100 != 0 || year % 400 == 0);
    let days = match month {
        1 | 3 | 5 | 7 | 8 | 10 | 12 => 31,
        4 | 6 | 9 | 11 => 30,
        2 if leap => 29,
        2 => 28,
        _ => 0,
    };
    day > 0 && day <= days && hour < 24 && minute < 60 && second < 60
}
fn new_event_id() -> Result<String, MetadataError> {
    let mut bytes = [0_u8; 16];
    getrandom::fill(&mut bytes).map_err(|_| MetadataError::Invalid)?;
    bytes[6] = (bytes[6] & 0x0f) | 0x40;
    bytes[8] = (bytes[8] & 0x3f) | 0x80;
    Ok(format!(
        "{:08x}-{:04x}-{:04x}-{:04x}-{:012x}",
        u32::from_be_bytes(bytes[0..4].try_into().unwrap()),
        u16::from_be_bytes(bytes[4..6].try_into().unwrap()),
        u16::from_be_bytes(bytes[6..8].try_into().unwrap()),
        u16::from_be_bytes(bytes[8..10].try_into().unwrap()),
        u64::from_be_bytes([
            0, 0, bytes[10], bytes[11], bytes[12], bytes[13], bytes[14], bytes[15]
        ])
    ))
}
fn validate_metadata(value: &Value) -> Result<(), MetadataError> {
    let o = value.as_object().ok_or(MetadataError::Invalid)?;
    if !exact(o, &FIELDS) {
        return Err(MetadataError::Invalid);
    }
    for key in ["name", "unit", "status", "work_method"] {
        str_field(o, key)?;
    }
    if !o["goal"].is_null()
        && !o["goal"]
            .as_f64()
            .is_some_and(|v| v.is_finite() && v >= 0.0)
    {
        return Err(MetadataError::Invalid);
    }
    if !o["personal_goal"]
        .as_f64()
        .is_some_and(|v| v.is_finite() && v >= 0.0)
    {
        return Err(MetadataError::Invalid);
    }
    if !o["deadline"].is_null()
        && !o["deadline"]
            .as_str()
            .is_some_and(|s| !s.is_empty() && s.len() <= 512)
    {
        return Err(MetadataError::Invalid);
    }
    for key in [
        "infinite",
        "auto_freeze",
        "streak_enabled",
        "stages_enabled",
        "combine_stage_mindmaps",
    ] {
        if !o[key].is_boolean() {
            return Err(MetadataError::Invalid);
        }
    }
    Ok(())
}

/// Capture the exact current legacy source and its allowlisted projection. The
/// existing row is reused on retry, including after process restart.
pub(crate) fn capture_legacy_candidate(
    connection: &mut Connection,
    account: &str,
    project: &str,
    now: &str,
) -> Result<String, MetadataError> {
    let tx = connection.transaction_with_behavior(TransactionBehavior::Immediate)?;
    let row = tx.query_row(
        "SELECT b.account_id,s.device_id,boot.bootstrap_id,p.name,p.goal,p.infinite,p.unit,p.status,p.payload_json,p.updated_at \
         FROM cloud_sync_project_bindings b JOIN cloud_sync_state s ON s.account_id=b.account_id \
         LEFT JOIN cloud_sync_project_bootstraps boot ON boot.project_id=b.project_id AND boot.account_id=b.account_id \
         JOIN projects p ON p.id=b.project_id WHERE b.account_id=?1 AND b.project_id=?2",
        params![account, project], |r| Ok((r.get::<_,String>(0)?,r.get::<_,String>(1)?,r.get::<_,Option<String>>(2)?,r.get::<_,String>(3)?,r.get::<_,Option<f64>>(4)?,r.get::<_,i64>(5)?,r.get::<_,String>(6)?,r.get::<_,String>(7)?,r.get::<_,String>(8)?,r.get::<_,Option<String>>(9)?))
    ).optional()?.ok_or(MetadataError::Scope)?;
    let (scope, device, bootstrap, name, goal, infinite, unit, status, source, updated) = row;
    if scope != account || !uuid(&device) || bootstrap.as_deref().is_some_and(|id| !uuid(id)) {
        return Err(MetadataError::Scope);
    }
    let raw: Value = serde_json::from_str(&source).map_err(|_| MetadataError::Invalid)?;
    let original = raw.as_object().ok_or(MetadataError::Invalid)?;
    let snapshot = json!({
        "name":name,"goal":goal,"infinite":infinite!=0,"unit":unit,"status":status,
        "deadline":original.get("deadline").cloned().unwrap_or(Value::Null),
        "personal_goal":original.get("personal_goal").cloned().unwrap_or(json!(0)),
        "auto_freeze":original.get("auto_freeze").cloned().unwrap_or(json!(true)),
        "streak_enabled":original.get("streak_enabled").cloned().unwrap_or(json!(true)),
        "work_method":original.get("work_method").cloned().unwrap_or(json!("manual")),
        "stages_enabled":original.get("stages_enabled").cloned().unwrap_or(json!(false)),
        "combine_stage_mindmaps":original.get("combine_stage_mindmaps").cloned().unwrap_or(json!(false))
    });
    validate_metadata(&snapshot)?;
    let extensions: Option<String> = tx.query_row(
        "SELECT payload_json FROM project_extensions WHERE entity_type='project' AND entity_id=?1",
        [project], |r| r.get(0)).optional()?;
    let mut unsupported: Vec<String> = original
        .keys()
        .filter(|key| !LEGACY_PROJECT_FIELDS.contains(&key.as_str()))
        .cloned()
        .collect();
    if bootstrap.is_none() {
        unsupported.push("bootstrap_lineage_missing".into());
    }
    if let Some(raw) = extensions {
        let extension: Value = serde_json::from_str(&raw).map_err(|_| MetadataError::Invalid)?;
        if extension
            .as_object()
            .is_none_or(|object| !object.is_empty())
        {
            unsupported.push("project_extensions".into());
        }
    }
    unsupported.sort();
    let snapshot_json = serde_json::to_string(&snapshot).map_err(|_| MetadataError::Invalid)?;
    let unsupported_json =
        serde_json::to_string(&unsupported).map_err(|_| MetadataError::Invalid)?;
    if let Some((id, previous_snapshot, previous_unsupported)) = tx.query_row(
        "SELECT candidate_id,snapshot_json,unsupported_json FROM cloud_sync_metadata_candidates WHERE account_id=?1 AND project_id=?2 AND device_id=?3 ORDER BY generation DESC LIMIT 1",
        params![account,project,device], |r| Ok((r.get::<_,String>(0)?,r.get::<_,String>(1)?,r.get::<_,String>(2)?))).optional()? {
        if previous_snapshot == snapshot_json && previous_unsupported == unsupported_json {
            tx.commit()?; return Ok(id);
        }
    }
    let generation: i64 = tx.query_row(
        "SELECT COALESCE(MAX(generation),0)+1 FROM cloud_sync_metadata_candidates WHERE account_id=?1 AND project_id=?2 AND device_id=?3",
        params![account,project,device], |r| r.get(0))?;
    if !(1..=MAX_REVISION).contains(&generation) {
        return Err(MetadataError::Invalid);
    }
    let id = new_event_id()?;
    tx.execute("INSERT INTO cloud_sync_metadata_candidates(candidate_id,account_id,project_id,device_id,bootstrap_id,generation,codec_version,snapshot_json,unsupported_json,source_payload_json,source_updated_at,state,created_at) VALUES(?1,?2,?3,?4,?5,?6,1,?7,?8,?9,?10,'candidate',?11)",
        params![id,account,project,device,bootstrap,generation,snapshot_json,unsupported_json,source,updated,now])?;
    tx.commit()?;
    Ok(id)
}

/// Explicit preparation. C18.3.01 sealing/upload reuses this exact event ID;
/// neither capture nor this method contacts the server.
pub(crate) fn prepare_metadata_genesis(
    connection: &mut Connection,
    account: &str,
    candidate_id: &str,
    now: &str,
) -> Result<String, MetadataError> {
    if !timestamp(now) {
        return Err(MetadataError::Invalid);
    }
    let tx = connection.transaction_with_behavior(TransactionBehavior::Immediate)?;
    let row = tx.query_row(
        "SELECT c.project_id,c.device_id,c.bootstrap_id,c.snapshot_json,c.unsupported_json,c.state,b.account_id,s.device_id \
         FROM cloud_sync_metadata_candidates c JOIN cloud_sync_project_bindings b ON b.project_id=c.project_id \
         JOIN cloud_sync_state s ON s.account_id=c.account_id \
         WHERE c.account_id=?1 AND c.candidate_id=?2",
        params![account,candidate_id], |r| Ok((r.get::<_,String>(0)?,r.get::<_,String>(1)?,r.get::<_,Option<String>>(2)?,r.get::<_,String>(3)?,r.get::<_,String>(4)?,r.get::<_,String>(5)?,r.get::<_,String>(6)?,r.get::<_,String>(7)?))
    ).optional()?.ok_or(MetadataError::Scope)?;
    let (project, device, bootstrap, snapshot, unsupported, state, binding_account, current_device) =
        row;
    if binding_account != account
        || current_device != device
        || bootstrap.is_none()
        || unsupported != "[]"
    {
        return Err(MetadataError::Scope);
    }
    if let Some(existing) = tx.query_row(
        "SELECT event_id FROM cloud_sync_metadata_events WHERE account_id=?1 AND candidate_id=?2",
        params![account,candidate_id], |r|r.get::<_,String>(0)).optional()? {
        tx.commit()?; return Ok(existing);
    }
    if state != "candidate" {
        return Err(MetadataError::Conflict);
    }
    let known_history: bool = tx.query_row(
        "SELECT EXISTS(SELECT 1 FROM cloud_sync_metadata_tips WHERE account_id=?1 AND project_id=?2)",
        params![account,project],|r|r.get(0))?;
    if known_history { return Err(MetadataError::Conflict); }
    let active: bool = tx.query_row(
        "SELECT EXISTS(SELECT 1 FROM cloud_sync_metadata_candidates WHERE account_id=?1 AND project_id=?2 AND state='publishing')",
        params![account,project], |r|r.get(0))?;
    if active {
        return Err(MetadataError::Conflict);
    }
    let event_id = new_event_id()?;
    let ordinal: i64 = tx.query_row(
        "SELECT COALESCE(MAX(local_ordinal),0)+1 FROM cloud_sync_outbox WHERE account_id=?1 AND device_id=?2",
        params![account,device], |r|r.get(0))?;
    if !(1..=MAX_REVISION).contains(&ordinal) {
        return Err(MetadataError::Invalid);
    }
    tx.execute("INSERT INTO cloud_sync_outbox(event_id,account_id,device_id,project_id,entity_id,entity_type,operation,revision,updated_at,created_at,parent_event_id,local_ordinal,lifecycle) VALUES(?1,?2,?3,?4,?4,'project_metadata','upsert',1,?5,?5,NULL,?6,'unsealed')",
        params![event_id,account,device,project,now,ordinal])?;
    tx.execute("INSERT INTO cloud_sync_metadata_events(account_id,event_id,project_id,device_id,bootstrap_id,candidate_id,parent_event_ids_json,generation,revision,operation,payload_json,state,created_at) VALUES(?1,?2,?3,?4,?5,?6,'[]',1,1,'create',?7,'unsealed',?8)",
        params![account,event_id,project,device,bootstrap,candidate_id,snapshot,now])?;
    tx.execute(
        "UPDATE cloud_sync_metadata_candidates SET state='publishing' WHERE candidate_id=?1",
        [candidate_id],
    )?;
    tx.commit()?;
    Ok(event_id)
}

/// Stores an authenticated plaintext event in a transaction. The visible
/// project row is untouched; concurrent genesis tips remain explicit.
pub(crate) fn preserve_authenticated_event(
    connection: &mut Connection,
    account: &str,
    project: &str,
    bytes: &[u8],
    now: &str,
) -> Result<&'static str, MetadataError> {
    preserve_authenticated_event_checked(connection, account, project, bytes, now, None)
}

pub(crate) fn preserve_authenticated_event_checked(
    connection: &mut Connection,
    account: &str,
    project: &str,
    bytes: &[u8],
    now: &str,
    expected_object: Option<(&[u8], &[u8])>,
) -> Result<&'static str, MetadataError> {
    if bytes.is_empty() || bytes.len() > MAX_BYTES {
        return Err(MetadataError::Invalid);
    }
    let value: Value = serde_json::from_slice(bytes).map_err(|_| MetadataError::Invalid)?;
    if value.to_string().as_bytes() != bytes {
        return Err(MetadataError::Invalid);
    }
    let root = value.as_object().ok_or(MetadataError::Invalid)?;
    if !exact(root, &["version", "header", "metadata", "deleted_at"]) || root["version"] != 1 {
        return Err(MetadataError::Invalid);
    }
    let header = root["header"].as_object().ok_or(MetadataError::Invalid)?;
    if !exact(
        header,
        &[
            "account_id",
            "bootstrap_id",
            "device_id",
            "entity_id",
            "event_id",
            "generation",
            "operation",
            "parent_event_ids",
            "project_id",
            "revision",
            "updated_at",
        ],
    ) {
        return Err(MetadataError::Invalid);
    }
    let event_id = str_field(header, "event_id")?;
    let device = str_field(header, "device_id")?;
    let bootstrap = str_field(header, "bootstrap_id")?;
    let operation = str_field(header, "operation")?;
    let revision = positive(header, "revision")?;
    let generation = positive(header, "generation")?;
    let updated = str_field(header, "updated_at")?;
    if !uuid(event_id)
        || !uuid(device)
        || !uuid(bootstrap)
        || !timestamp(updated)
        || str_field(header, "project_id")? != project
        || str_field(header, "entity_id")? != project
    {
        return Err(MetadataError::Invalid);
    }
    let parents = header["parent_event_ids"]
        .as_array()
        .ok_or(MetadataError::Invalid)?;
    if parents.len() > 64
        || parents.iter().any(|v| !v.as_str().is_some_and(uuid))
        || parents.windows(2).any(|w| w[0].as_str() >= w[1].as_str())
        || parents.iter().any(|v| v.as_str() == Some(event_id))
    {
        return Err(MetadataError::Invalid);
    }
    if (operation == "create" && (revision != 1 || generation != 1 || !parents.is_empty()))
        || (operation == "genesis_resolution" && (revision < 2 || parents.len() < 2))
        || (matches!(operation, "update" | "delete") && parents.len() != 1)
        || (operation == "resolution" && parents.len() < 2)
        || !matches!(
            operation,
            "create" | "update" | "delete" | "genesis_resolution" | "resolution"
        )
    {
        return Err(MetadataError::Invalid);
    }
    let deleted = root["deleted_at"].as_str();
    if operation == "delete" {
        if !root["metadata"].is_null() || deleted != Some(updated) {
            return Err(MetadataError::Invalid);
        }
    } else if !root["deleted_at"].is_null() {
        return Err(MetadataError::Invalid);
    } else {
        validate_metadata(&root["metadata"])?;
    }
    let tx = connection.transaction_with_behavior(TransactionBehavior::Immediate)?;
    let bound: Option<String> = tx.query_row("SELECT a.canonical_user_id FROM cloud_sync_project_bindings b JOIN cloud_account_bindings a ON a.local_account_id=b.account_id JOIN cloud_sync_project_bootstraps boot ON boot.project_id=b.project_id AND boot.account_id=b.account_id WHERE b.account_id=?1 AND b.project_id=?2 AND boot.bootstrap_id=?3",
        params![account,project,bootstrap], |r| r.get(0)).optional()?;
    if bound.as_deref() != header["account_id"].as_str() {
        return Err(MetadataError::Scope);
    }
    if let Some((stored, outcome)) = tx.query_row(
        "SELECT canonical_payload,outcome FROM cloud_sync_metadata_apply_ledger WHERE account_id=?1 AND event_id=?2",
        params![account,event_id], |r| Ok((r.get::<_,Vec<u8>>(0)?, r.get::<_,String>(1)?))
    ).optional()? {
        if let Some((expected_nonce,expected_ciphertext))=expected_object {
            let object:Option<(Vec<u8>,Vec<u8>)>=tx.query_row("SELECT nonce,ciphertext FROM cloud_sync_event_objects WHERE account_id=?1 AND event_id=?2 AND crypto_version=1 AND aad_version=1",params![account,event_id],|r|Ok((r.get(0)?,r.get(1)?))).optional()?;
            if object.as_ref().is_none_or(|(nonce,ciphertext)|nonce!=expected_nonce||ciphertext!=expected_ciphertext){return Err(MetadataError::Scope);}
        }
        if stored == bytes { return Ok(if outcome == "applied" { "applied" } else { "conflict_preserved" }); }
        return Err(MetadataError::Conflict);
    }
    let inbox: Option<(String,String,String,String,i64,String,Option<String>,i64)> = tx.query_row(
        "SELECT device_id,project_id,entity_id,operation,sync_revision,updated_at,deleted_at,server_sequence FROM cloud_sync_inbox WHERE account_id=?1 AND event_id=?2 AND entity_type='project_metadata' AND state IN ('received','orphan')",
        params![account,event_id], |r| Ok((r.get(0)?,r.get(1)?,r.get(2)?,r.get(3)?,r.get(4)?,r.get(5)?,r.get(6)?,r.get(7)?))).optional()?;
    let Some((
        in_device,
        in_project,
        in_entity,
        in_operation,
        in_revision,
        in_updated,
        in_deleted,
        server_sequence,
    )) = inbox
    else {
        if let Some((stored, outcome)) = tx.query_row("SELECT canonical_payload,outcome FROM cloud_sync_metadata_apply_ledger WHERE account_id=?1 AND event_id=?2",params![account,event_id],|r| Ok((r.get::<_,Vec<u8>>(0)?,r.get::<_,String>(1)?))).optional()? {
            if stored == bytes { return Ok(if outcome == "applied" {"applied"} else {"conflict_preserved"}); }
        }
        return Err(MetadataError::Scope);
    };
    if in_device != device
        || in_project != project
        || in_entity != project
        || in_revision != revision
        || in_updated != updated
        || in_operation
            != if operation == "delete" {
                "delete"
            } else {
                "upsert"
            }
        || in_deleted.as_deref() != deleted
    {
        return Err(MetadataError::Scope);
    }
    let object: Option<(i64, i64, Vec<u8>, Vec<u8>)> = tx.query_row(
        "SELECT crypto_version,aad_version,nonce,ciphertext FROM cloud_sync_event_objects WHERE account_id=?1 AND event_id=?2",
        params![account, event_id],
        |r| Ok((r.get(0)?, r.get(1)?, r.get(2)?, r.get(3)?)),
    ).optional()?;
    let Some((crypto_version, aad_version, nonce, ciphertext)) = object else {
        return Err(MetadataError::Scope);
    };
    if crypto_version != 1 || aad_version != 1 || expected_object.is_some_and(|(n, c)| n != nonce || c != ciphertext) {
        return Err(MetadataError::Scope);
    }
    let local_event: Option<(Option<String>,String,String)> = tx.query_row(
        "SELECT candidate_id,payload_json,state FROM cloud_sync_metadata_events WHERE account_id=?1 AND event_id=?2",
        params![account,event_id],|r|Ok((r.get(0)?,r.get(1)?,r.get(2)?))).optional()?;
    let existing_orphan = local_event
        .as_ref()
        .is_some_and(|(candidate, _, state)| candidate.is_none() && state == "orphan");
    let self_echo = if let Some((candidate_id, stored_payload, state)) = &local_event {
        if existing_orphan {
            if stored_payload
                != &if operation == "delete" {
                    "{}".to_string()
                } else {
                    root["metadata"].to_string()
                }
            {
                return Err(MetadataError::Conflict);
            }
            false
        } else {
            if candidate_id.is_none()
                || !matches!(state.as_str(), "unsealed" | "sealed" | "accepted")
                || stored_payload != &root["metadata"].to_string()
                || operation != "create"
            {
                return Err(MetadataError::Conflict);
            }
            let receipt: bool = tx.query_row(
            "SELECT EXISTS(SELECT 1 FROM cloud_sync_upload_receipts receipt JOIN cloud_sync_outbox outbox ON outbox.event_id=receipt.event_id WHERE receipt.account_id=?1 AND receipt.event_id=?2 AND receipt.device_id=?3 AND receipt.server_sequence=?4 AND outbox.account_id=?1 AND outbox.project_id=?5 AND outbox.entity_type='project_metadata' AND outbox.revision=1 AND outbox.lifecycle IN ('sealed','accepted'))",
            params![account,event_id,device,server_sequence,project],|r|r.get(0))?;
            if !receipt {
                let sealed: bool = tx.query_row(
                    "SELECT EXISTS(SELECT 1 FROM cloud_sync_outbox WHERE account_id=?1 AND event_id=?2 AND device_id=?3 AND project_id=?4 AND entity_type='project_metadata' AND lifecycle='sealed')",
                    params![account,event_id,device,project], |r|r.get(0))?;
                if !sealed { return Err(MetadataError::Scope); }
                // The authenticated server echo is the lost upload response.
                tx.execute("INSERT INTO cloud_sync_upload_receipts(account_id,event_id,device_id,server_sequence,duplicate,accepted_at) VALUES(?1,?2,?3,?4,0,?5)",
                    params![account,event_id,device,server_sequence,now])?;
                tx.execute("UPDATE cloud_sync_outbox SET lifecycle='accepted' WHERE account_id=?1 AND event_id=?2 AND lifecycle='sealed'",
                    params![account,event_id])?;
            }
            true
        }
    } else {
        false
    };
    let parents_json = serde_json::to_string(parents).map_err(|_| MetadataError::Invalid)?;
    let payload_json = if operation == "delete" {
        "{}".to_string()
    } else {
        root["metadata"].to_string()
    };
    if existing_orphan {
        let exact_orphan: bool = tx.query_row(
            "SELECT EXISTS(SELECT 1 FROM cloud_sync_metadata_events WHERE account_id=?1 AND event_id=?2 AND project_id=?3 AND device_id=?4 AND bootstrap_id=?5 AND parent_event_ids_json=?6 AND generation=?7 AND revision=?8 AND operation=?9 AND payload_json=?10 AND deleted_at IS ?11 AND server_sequence=?12 AND state='orphan')",
            params![account,event_id,project,device,bootstrap,parents_json,generation,revision,operation,payload_json,deleted,server_sequence], |r|r.get(0))?;
        if !exact_orphan {
            return Err(MetadataError::Conflict);
        }
    }
    let tip_count: i64 = tx.query_row(
        "SELECT COUNT(*) FROM cloud_sync_metadata_tips WHERE account_id=?1 AND project_id=?2",
        params![account, project],
        |r| r.get(0),
    )?;
    if operation != "create" {
        let mut max_parent_revision = 0_i64;
        let mut genesis_parents = true;
        for parent in parents {
            let parent = parent.as_str().ok_or(MetadataError::Invalid)?;
            let prior: Option<(i64, String, String)> = tx.query_row(
                "SELECT revision,operation,parent_event_ids_json FROM cloud_sync_metadata_events WHERE account_id=?1 AND event_id=?2 AND project_id=?3 AND state IN ('applied','conflict_preserved')",
                params![account,parent,project], |r| Ok((r.get(0)?,r.get(1)?,r.get(2)?))).optional()?;
            if prior.is_none() {
                if !existing_orphan {
                    tx.execute("INSERT INTO cloud_sync_metadata_events(account_id,event_id,project_id,device_id,bootstrap_id,parent_event_ids_json,generation,revision,operation,payload_json,deleted_at,state,server_sequence,created_at) VALUES(?1,?2,?3,?4,?5,?6,?7,?8,?9,?10,?11,'orphan',?12,?13)",
                        params![account,event_id,project,device,bootstrap,parents_json,generation,revision,operation,payload_json,deleted,server_sequence,now])?;
                    tx.execute("UPDATE cloud_sync_inbox SET state='orphan' WHERE account_id=?1 AND event_id=?2",params![account,event_id])?;
                }
                tx.commit()?;
                return Ok("orphan");
            }
            let (parent_revision, parent_operation, parent_parents) =
                prior.ok_or(MetadataError::Invalid)?;
            max_parent_revision = max_parent_revision.max(parent_revision);
            genesis_parents &=
                parent_operation == "create" && parent_revision == 1 && parent_parents == "[]";
        }
        if revision
            != max_parent_revision
                .checked_add(1)
                .ok_or(MetadataError::Invalid)?
            || (operation == "genesis_resolution" && !genesis_parents)
        {
            return Err(MetadataError::Invalid);
        }
    }
    let local_candidates: i64 = tx.query_row("SELECT COUNT(*) FROM cloud_sync_metadata_candidates WHERE account_id=?1 AND project_id=?2 AND state!='resolved'",params![account,project],|r|r.get(0))?;
    let mut tip_query = tx.prepare("SELECT event_id FROM cloud_sync_metadata_tips WHERE account_id=?1 AND project_id=?2 ORDER BY event_id")?;
    let tip_ids: Vec<String> = tip_query
        .query_map(params![account, project], |r| r.get(0))?
        .collect::<Result<_, _>>()?;
    drop(tip_query);
    let parent_ids: Vec<&str> = parents
        .iter()
        .map(|p| p.as_str().ok_or(MetadataError::Invalid))
        .collect::<Result<_, _>>()?;
    let exact_tips = tip_ids
        .iter()
        .map(String::as_str)
        .eq(parent_ids.iter().copied());
    if matches!(operation, "genesis_resolution" | "resolution") && !exact_tips {
        return Err(MetadataError::Conflict);
    }
    let outcome = if self_echo && tip_count == 0 {
        "applied"
    } else if operation == "create" && (tip_count > 0 || local_candidates > 0) {
        "conflict_preserved"
    } else if operation == "create" || exact_tips {
        "applied"
    } else {
        "conflict_preserved"
    };
    if self_echo {
        tx.execute("UPDATE cloud_sync_metadata_events SET state=?1,server_sequence=?2 WHERE account_id=?3 AND event_id=?4",
            params![if outcome=="applied" {"applied"} else {"conflict_preserved"},server_sequence,account,event_id])?;
        tx.execute("UPDATE cloud_sync_metadata_candidates SET state=?1 WHERE candidate_id=(SELECT candidate_id FROM cloud_sync_metadata_events WHERE account_id=?2 AND event_id=?3)",params![if outcome=="applied" {"published"} else {"conflict"},account,event_id])?;
    } else if existing_orphan {
        tx.execute(
            "UPDATE cloud_sync_metadata_events SET state=?1 WHERE account_id=?2 AND event_id=?3",
            params![
                if outcome == "applied" {
                    "applied"
                } else {
                    "conflict_preserved"
                },
                account,
                event_id
            ],
        )?;
    } else {
        tx.execute("INSERT INTO cloud_sync_metadata_events(account_id,event_id,project_id,device_id,bootstrap_id,parent_event_ids_json,generation,revision,operation,payload_json,deleted_at,state,server_sequence,created_at) SELECT ?1,?2,?3,?4,?5,?6,?7,?8,?9,?10,?11,?12,server_sequence,?13 FROM cloud_sync_inbox WHERE account_id=?1 AND event_id=?2",
            params![account,event_id,project,device,bootstrap,parents_json,generation,revision,operation,payload_json,deleted,if outcome=="applied" {"applied"} else {"conflict_preserved"},now])?;
    }
    tx.execute(
        "INSERT INTO cloud_sync_metadata_tips(account_id,project_id,event_id) VALUES(?1,?2,?3)",
        params![account, project, event_id],
    )?;
    if outcome == "applied" {
        for parent in parents {
            tx.execute("DELETE FROM cloud_sync_metadata_tips WHERE account_id=?1 AND project_id=?2 AND event_id=?3",params![account,project,parent.as_str()])?;
        }
        tx.execute("INSERT INTO cloud_sync_metadata_projection(account_id,project_id,head_event_id,revision,payload_json,deleted_at) VALUES(?1,?2,?3,?4,?5,?6) ON CONFLICT(account_id,project_id) DO UPDATE SET head_event_id=excluded.head_event_id,revision=excluded.revision,payload_json=excluded.payload_json,deleted_at=excluded.deleted_at",
            params![account,project,event_id,revision,payload_json,deleted])?;
    } else {
        tx.execute(
            "DELETE FROM cloud_sync_metadata_projection WHERE account_id=?1 AND project_id=?2",
            params![account, project],
        )?;
    }
    tx.execute("INSERT INTO cloud_sync_metadata_apply_ledger(account_id,event_id,project_id,outcome,canonical_payload,applied_at) VALUES(?1,?2,?3,?4,?5,?6)",params![account,event_id,project,outcome,bytes,now])?;
    tx.execute("UPDATE cloud_sync_inbox SET state=?1,applied_at=CASE WHEN ?1='applied' THEN ?2 ELSE applied_at END WHERE account_id=?3 AND event_id=?4 AND state IN ('received','orphan')",
        params![if outcome=="applied" {"applied"} else {"conflict"},now,account,event_id])?;
    tx.commit()?;
    Ok(outcome)
}

pub(crate) fn assert_runtime_scope(connection: &Connection, account: &str, user: &str, device: &str) -> Result<(), MetadataError> {
    let stored: Option<(String,String)> = connection.query_row(
        "SELECT binding.canonical_user_id,state.device_id FROM cloud_account_bindings binding JOIN cloud_sync_state state ON state.account_id=binding.local_account_id WHERE binding.local_account_id=?1",
        [account], |r|Ok((r.get(0)?,r.get(1)?))).optional()?;
    if stored.as_ref().is_none_or(|(u,d)| u != user || d != device) || !uuid(user) || !uuid(device) {
        return Err(MetadataError::Scope);
    }
    Ok(())
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
pub(crate) struct MetadataScope {
    pub account_id:String,
    pub canonical_user_id:String,
    pub device_id:String,
}

#[derive(Serialize)]
pub(crate) struct MetadataMigrationStatus {
    pub state: String,
    pub candidate_id: Option<String>,
    pub event_id: Option<String>,
    pub blockers: Value,
    pub genesis_tips: i64,
}

pub(crate) fn migration_status(connection: &Connection, account: &str, project: &str) -> Result<MetadataMigrationStatus, MetadataError> {
    let candidate: Option<(String,String,String)> = connection.query_row(
        "SELECT candidate_id,state,unsupported_json FROM cloud_sync_metadata_candidates WHERE account_id=?1 AND project_id=?2 ORDER BY generation DESC LIMIT 1",
        params![account,project], |r|Ok((r.get(0)?,r.get(1)?,r.get(2)?))).optional()?;
    let tips: i64 = connection.query_row("SELECT COUNT(*) FROM cloud_sync_metadata_tips WHERE account_id=?1 AND project_id=?2",params![account,project],|r|r.get(0))?;
    let event: Option<(String,String)> = if let Some((candidate_id,_,_))=&candidate {
        connection.query_row("SELECT event_id,state FROM cloud_sync_metadata_events WHERE account_id=?1 AND candidate_id=?2",params![account,candidate_id],|r|Ok((r.get(0)?,r.get(1)?))).optional()?
    } else { None };
    let blockers: Value = candidate.as_ref().map(|(_,_,raw)|serde_json::from_str(raw)).transpose().map_err(|_|MetadataError::Invalid)?.unwrap_or_else(||json!([]));
    let pending_inbox:bool=connection.query_row("SELECT EXISTS(SELECT 1 FROM cloud_sync_inbox WHERE account_id=?1 AND project_id=?2 AND entity_type='project_metadata' AND state IN ('received','orphan'))",params![account,project],|r|r.get(0))?;
    let state = if tips > 1 || tips > 0 && candidate.as_ref().is_some_and(|(_,state,_)|state=="candidate")
        || candidate.as_ref().is_some_and(|(_,state,_)|state=="conflict") { "genesis_conflict" }
        else if tips == 1 && candidate.is_none() || event.as_ref().is_some_and(|(_,state)|state=="applied") { "authenticated_metadata_active" }
        else if blockers.as_array().is_some_and(|a|a.iter().any(|v|v=="bootstrap_lineage_missing")) { "blocked_missing_bootstrap" }
        else if blockers.as_array().is_some_and(|a|!a.is_empty()) { "blocked_unsupported" }
        else if pending_inbox { "apply_blocked" }
        else if event.as_ref().is_some_and(|(_,state)|state=="accepted") { "awaiting_remote_confirmation" }
        else if event.as_ref().is_some_and(|(_,state)|matches!(state.as_str(),"unsealed"|"sealed")) { "genesis_pending" }
        else if candidate.is_some() { "legacy_candidate_present" }
        else { "legacy_local" };
    Ok(MetadataMigrationStatus { state:state.into(), candidate_id:candidate.as_ref().map(|(id,_,_)|id.clone()),event_id:event.map(|(id,_)|id),blockers,genesis_tips:tips })
}

pub(crate) fn unsealed_genesis(connection: &Connection, account: &str, device: &str) -> Result<Vec<Value>, MetadataError> {
    let mut statement=connection.prepare("SELECT e.event_id,e.project_id,e.bootstrap_id,e.payload_json,o.updated_at FROM cloud_sync_metadata_events e JOIN cloud_sync_outbox o ON o.event_id=e.event_id WHERE e.account_id=?1 AND e.device_id=?2 AND e.state='unsealed' AND o.lifecycle='unsealed' ORDER BY o.local_ordinal LIMIT 8")?;
    let events: Result<Vec<Value>, MetadataError> = statement.query_map(params![account,device],|r|Ok((r.get::<_,String>(0)?,r.get::<_,String>(1)?,r.get::<_,String>(2)?,r.get::<_,String>(3)?,r.get::<_,String>(4)?)))?
        .map(|row| { let (event,project,bootstrap,payload,updated)=row?;
            let user:String=connection.query_row("SELECT canonical_user_id FROM cloud_account_bindings WHERE local_account_id=?1",[account],|r|r.get(0))?;
            let metadata:Value=serde_json::from_str(&payload).map_err(|_|MetadataError::Invalid)?;
            Ok(json!({"version":1,"header":{"account_id":user,"bootstrap_id":bootstrap,"device_id":device,"entity_id":project,"event_id":event,"generation":1,"operation":"create","parent_event_ids":[],"project_id":project,"revision":1,"updated_at":updated},"metadata":metadata,"deleted_at":null}))
        }).collect();
    events
}

pub(crate) fn commit_sealed_genesis(connection:&mut Connection, account:&str, device:&str, event:&str, nonce:&[u8], ciphertext:&[u8]) -> Result<(),MetadataError> {
    if nonce.len()!=24 || !(16..=MAX_BYTES+64).contains(&ciphertext.len()) {return Err(MetadataError::Invalid);}
    let tx=connection.transaction_with_behavior(TransactionBehavior::Immediate)?;
    let state:Option<(String,String)>=tx.query_row("SELECT e.state,o.lifecycle FROM cloud_sync_metadata_events e JOIN cloud_sync_outbox o ON o.event_id=e.event_id WHERE e.account_id=?1 AND e.device_id=?2 AND e.event_id=?3 AND e.operation='create' AND o.entity_type='project_metadata'",params![account,device,event],|r|Ok((r.get(0)?,r.get(1)?))).optional()?;
    if state.as_ref().is_none_or(|(e,o)|e!="unsealed"||o!="unsealed") {return Err(MetadataError::Scope);}
    tx.execute("INSERT INTO cloud_sync_event_objects(account_id,event_id,crypto_version,aad_version,nonce,ciphertext,stored_at) VALUES(?1,?2,1,1,?3,?4,strftime('%Y-%m-%dT%H:%M:%fZ','now'))",params![account,event,nonce,ciphertext])?;
    tx.execute("UPDATE cloud_sync_metadata_events SET state='sealed' WHERE account_id=?1 AND event_id=?2",params![account,event])?;
    tx.execute("UPDATE cloud_sync_outbox SET lifecycle='sealed' WHERE account_id=?1 AND event_id=?2",params![account,event])?;
    tx.commit()?;Ok(())
}

#[derive(Serialize)]
pub(crate) struct MetadataUploadItem {
    pub event_id:String,pub project_id:String,pub revision:i64,pub updated_at:String,pub nonce:Vec<u8>,pub ciphertext:Vec<u8>,
}
pub(crate) fn sealed_genesis(connection:&Connection, account:&str, device:&str)->Result<Vec<MetadataUploadItem>,MetadataError>{
    let mut statement=connection.prepare("SELECT e.event_id,e.project_id,e.revision,o.updated_at,obj.nonce,obj.ciphertext FROM cloud_sync_metadata_events e JOIN cloud_sync_outbox o ON o.event_id=e.event_id JOIN cloud_sync_event_objects obj ON obj.account_id=e.account_id AND obj.event_id=e.event_id WHERE e.account_id=?1 AND e.device_id=?2 AND e.state='sealed' AND o.lifecycle='sealed' ORDER BY o.local_ordinal LIMIT 8")?;
    let items=statement.query_map(params![account,device],|r|Ok(MetadataUploadItem{event_id:r.get(0)?,project_id:r.get(1)?,revision:r.get(2)?,updated_at:r.get(3)?,nonce:r.get(4)?,ciphertext:r.get(5)?}))?.collect::<Result<Vec<_>,_>>()?;
    Ok(items)
}

pub(crate) fn commit_upload_receipt(connection:&mut Connection,account:&str,device:&str,event:&str,sequence:i64,duplicate:bool,now:&str)->Result<(),MetadataError>{
    if !(1..=MAX_REVISION).contains(&sequence) || !timestamp(now){return Err(MetadataError::Invalid);}
    let tx=connection.transaction_with_behavior(TransactionBehavior::Immediate)?;
    let state:Option<String>=tx.query_row("SELECT lifecycle FROM cloud_sync_outbox WHERE account_id=?1 AND device_id=?2 AND event_id=?3 AND entity_type='project_metadata'",params![account,device,event],|r|r.get(0)).optional()?;
    if !matches!(state.as_deref(),Some("sealed"|"accepted")){return Err(MetadataError::Scope);}
    let existing:Option<i64>=tx.query_row("SELECT server_sequence FROM cloud_sync_upload_receipts WHERE account_id=?1 AND event_id=?2",params![account,event],|r|r.get(0)).optional()?;
    if let Some(old)=existing {if old!=sequence{return Err(MetadataError::Conflict);}}
    else {tx.execute("INSERT INTO cloud_sync_upload_receipts(account_id,event_id,device_id,server_sequence,duplicate,accepted_at) VALUES(?1,?2,?3,?4,?5,?6)",params![account,event,device,sequence,i64::from(duplicate),now])?;}
    tx.execute("UPDATE cloud_sync_outbox SET lifecycle='accepted' WHERE account_id=?1 AND event_id=?2 AND lifecycle='sealed'",params![account,event])?;
    tx.execute("UPDATE cloud_sync_metadata_events SET state='accepted',server_sequence=?1 WHERE account_id=?2 AND event_id=?3 AND state='sealed'",params![sequence,account,event])?;
    tx.commit()?;Ok(())
}

#[derive(Serialize)]
pub(crate) struct MetadataInboxItem {
    pub event_id:String,pub server_sequence:i64,pub source_device_id:String,pub project_id:String,pub entity_id:String,pub revision:i64,pub updated_at:String,pub deleted_at:Option<String>,pub operation:String,pub crypto_version:i64,pub aad_version:i64,pub nonce:Vec<u8>,pub ciphertext:Vec<u8>,
}
pub(crate) fn received_metadata(connection:&Connection,account:&str,limit:i64,after:i64)->Result<Vec<MetadataInboxItem>,MetadataError>{
    if !(1..=32).contains(&limit)||!(0..=MAX_REVISION).contains(&after){return Err(MetadataError::Invalid);}
    let mut statement=connection.prepare("SELECT inbox.event_id,inbox.server_sequence,inbox.device_id,inbox.project_id,inbox.entity_id,inbox.sync_revision,inbox.updated_at,inbox.deleted_at,inbox.operation,obj.crypto_version,obj.aad_version,obj.nonce,obj.ciphertext FROM cloud_sync_inbox inbox JOIN cloud_sync_event_objects obj ON obj.account_id=inbox.account_id AND obj.event_id=inbox.event_id WHERE inbox.account_id=?1 AND inbox.entity_type='project_metadata' AND inbox.state IN ('received','orphan') AND inbox.server_sequence>?3 ORDER BY inbox.server_sequence LIMIT ?2")?;
    let items=statement.query_map(params![account,limit,after],|r|Ok(MetadataInboxItem{event_id:r.get(0)?,server_sequence:r.get(1)?,source_device_id:r.get(2)?,project_id:r.get(3)?,entity_id:r.get(4)?,revision:r.get(5)?,updated_at:r.get(6)?,deleted_at:r.get(7)?,operation:r.get(8)?,crypto_version:r.get(9)?,aad_version:r.get(10)?,nonce:r.get(11)?,ciphertext:r.get(12)?}))?.collect::<Result<Vec<_>,_>>()?;
    Ok(items)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::{note_sync,sqlite};
    const ACCOUNT: &str = "local-account";
    const USER: &str = "123e4567-e89b-42d3-a456-426614174099";
    const DEVICE: &str = "123e4567-e89b-42d3-a456-426614174003";
    const BOOT: &str = "123e4567-e89b-42d3-a456-426614174002";
    const NOW: &str = "2026-09-21T00:00:00.000000Z";
    fn database() -> (Connection, std::path::PathBuf) {
        let path = std::env::temp_dir().join(format!(
            "c18-metadata-{}-{}.db",
            std::process::id(),
            new_event_id().unwrap()
        ));
        let db = sqlite::open_database(&path).unwrap();
        db.execute("INSERT INTO projects(id,name,infinite,unit,status,payload_json) VALUES('project','Local name',1,'symbols','active',?1)",
            [r#"{"deadline":null,"personal_goal":100,"auto_freeze":true,"streak_enabled":true,"work_method":"manual","stages_enabled":false,"combine_stage_mindmaps":false}"#]).unwrap();
        db.execute(
            "INSERT INTO project_order(project_id,position) VALUES('project',0)",
            [],
        )
        .unwrap();
        db.execute("INSERT INTO cloud_sync_state(account_id,device_id,pull_cursor,ack_cursor,created_at,updated_at) VALUES(?1,?2,0,0,?3,?3)",params![ACCOUNT,DEVICE,NOW]).unwrap();
        db.execute("INSERT INTO cloud_account_bindings(local_account_id,canonical_user_id,created_at,validated_at) VALUES(?1,?2,?3,?3)",params![ACCOUNT,USER,NOW]).unwrap();
        db.execute("INSERT INTO cloud_sync_project_bindings(project_id,account_id,created_at,updated_at) VALUES('project',?1,?2,?2)",params![ACCOUNT,NOW]).unwrap();
        db.execute("INSERT INTO cloud_sync_project_bootstraps(project_id,account_id,device_id,bootstrap_id,mode,phase,created_at,updated_at) VALUES('project',?1,?2,?3,'upload_existing','prepared',?4,?4)",params![ACCOUNT,DEVICE,BOOT,NOW]).unwrap();
        (db, path)
    }
    fn event(id: &str, device: &str, name: &str) -> Vec<u8> {
        serde_json::to_vec(&json!({"version":1,"header":{"account_id":USER,"bootstrap_id":BOOT,"device_id":device,"entity_id":"project","event_id":id,"generation":1,"operation":"create","parent_event_ids":[],"project_id":"project","revision":1,"updated_at":NOW},"metadata":{"name":name,"goal":null,"infinite":true,"unit":"symbols","deadline":null,"status":"active","personal_goal":100,"auto_freeze":true,"streak_enabled":true,"work_method":"manual","stages_enabled":false,"combine_stage_mindmaps":false},"deleted_at":null})).unwrap()
    }
    fn inbound(db: &Connection, id: &str, device: &str, sequence: i64) {
        db.execute("INSERT INTO cloud_sync_inbox(account_id,event_id,server_sequence,device_id,project_id,entity_id,entity_type,operation,sync_revision,updated_at,state,received_at) VALUES(?1,?2,?3,?4,'project','project','project_metadata','upsert',1,?5,'received',?5)",params![ACCOUNT,id,sequence,device,NOW]).unwrap();
        db.execute("INSERT INTO cloud_sync_event_objects(account_id,event_id,crypto_version,aad_version,nonce,ciphertext,stored_at) VALUES(?1,?2,1,1,zeroblob(24),zeroblob(16),?3)",params![ACCOUNT,id,NOW]).unwrap();
    }
    fn inbox_for_sealed(db:&Connection,id:&str,device:&str,sequence:i64){
        db.execute("INSERT INTO cloud_sync_inbox(account_id,event_id,server_sequence,device_id,project_id,entity_id,entity_type,operation,sync_revision,updated_at,state,received_at) VALUES(?1,?2,?3,?4,'project','project','project_metadata','upsert',1,?5,'received',?5)",params![ACCOUNT,id,sequence,device,NOW]).unwrap();
        let exists:bool=db.query_row("SELECT EXISTS(SELECT 1 FROM cloud_sync_event_objects WHERE account_id=?1 AND event_id=?2)",params![ACCOUNT,id],|r|r.get(0)).unwrap();
        if !exists {
            let nonce=if device==DEVICE {[1_u8;24]} else {[2_u8;24]};
            let ciphertext=if device==DEVICE {[1_u8;32]} else {[2_u8;32]};
            db.execute("INSERT INTO cloud_sync_event_objects(account_id,event_id,crypto_version,aad_version,nonce,ciphertext,stored_at) VALUES(?1,?2,1,1,?3,?4,?5)",params![ACCOUNT,id,nonce.as_slice(),ciphertext.as_slice(),NOW]).unwrap();
        }
    }
    fn ack_candidate(db:&mut Connection)->i64{
        let device=db.query_row("SELECT device_id FROM cloud_sync_state WHERE account_id=?1",[ACCOUNT],|r|r.get(0)).unwrap();
        note_sync::prepare_note_sync_ack(db,&note_sync::PrepareNoteSyncAckCommand{account_id:ACCOUNT.into(),device_id:device,canonical_user_id:USER.into()}).unwrap().candidate_cursor
    }
    #[test]
    fn project_metadata_lost_upload_response_self_echo_is_durable_and_ack_safe(){
        let (mut db,path)=database();
        let candidate=capture_legacy_candidate(&mut db,ACCOUNT,"project",NOW).unwrap();
        let id=prepare_metadata_genesis(&mut db,ACCOUNT,&candidate,NOW).unwrap();
        assert_eq!(unsealed_genesis(&db,ACCOUNT,DEVICE).unwrap().len(),1);
        commit_sealed_genesis(&mut db,ACCOUNT,DEVICE,&id,&[0;24],&[1;32]).unwrap();
        assert_eq!(sealed_genesis(&db,ACCOUNT,DEVICE).unwrap().len(),1);
        inbox_for_sealed(&db,&id,DEVICE,1);
        db.execute("UPDATE cloud_sync_state SET pull_cursor=1 WHERE account_id=?1",[ACCOUNT]).unwrap();
        let bytes=event(&id,DEVICE,"Local name");
        assert_eq!(preserve_authenticated_event_checked(&mut db,ACCOUNT,"project",&bytes,NOW,Some((&[0;24],&[1;32]))).unwrap(),"applied");
        assert_eq!(ack_candidate(&mut db),1);
        assert_eq!(db.query_row("SELECT COUNT(*) FROM cloud_sync_upload_receipts WHERE event_id=?1",[&id],|r|r.get::<_,i64>(0)).unwrap(),1);
        drop(db);
        let mut reopened=sqlite::open_database(&path).unwrap();
        assert_eq!(preserve_authenticated_event_checked(&mut reopened,ACCOUNT,"project",&bytes,NOW,Some((&[0;24],&[1;32]))).unwrap(),"applied");
        assert!(matches!(preserve_authenticated_event_checked(&mut reopened,ACCOUNT,"project",&bytes,NOW,Some((&[9;24],&[1;32]))),Err(MetadataError::Scope)));
        assert_eq!(ack_candidate(&mut reopened),1);
        assert!(received_metadata(&reopened,ACCOUNT,8,0).unwrap().is_empty());
        drop(reopened);std::fs::remove_file(path).unwrap();
    }
    #[test]
    fn project_metadata_two_device_genesis_survives_restart_without_winner(){
        let (mut a,path_a)=database();
        let (mut b,path_b)=database();
        let b_device="123e4567-e89b-42d3-a456-426614174004";
        b.execute("UPDATE cloud_sync_state SET device_id=?1 WHERE account_id=?2",params![b_device,ACCOUNT]).unwrap();
        b.execute("UPDATE projects SET name='Other name' WHERE id='project'",[]).unwrap();
        let a_candidate=capture_legacy_candidate(&mut a,ACCOUNT,"project",NOW).unwrap();
        let b_candidate=capture_legacy_candidate(&mut b,ACCOUNT,"project",NOW).unwrap();
        let a_id=prepare_metadata_genesis(&mut a,ACCOUNT,&a_candidate,NOW).unwrap();
        let b_id=prepare_metadata_genesis(&mut b,ACCOUNT,&b_candidate,NOW).unwrap();
        assert_ne!(a_id,b_id);
        commit_sealed_genesis(&mut a,ACCOUNT,DEVICE,&a_id,&[1;24],&[1;32]).unwrap();
        commit_sealed_genesis(&mut b,ACCOUNT,b_device,&b_id,&[2;24],&[2;32]).unwrap();
        for db in [&a,&b] {
            inbox_for_sealed(db,&a_id,DEVICE,1);
            inbox_for_sealed(db,&b_id,b_device,2);
            db.execute("UPDATE cloud_sync_state SET pull_cursor=2 WHERE account_id=?1",[ACCOUNT]).unwrap();
        }
        // Each device applies its own self echo and preserves the independent peer genesis.
        for (db,own_id,own_device,own_name,peer_id,peer_device,peer_name) in [
            (&mut a,&a_id,DEVICE,"Local name",&b_id,b_device,"Other name"),
            (&mut b,&b_id,b_device,"Other name",&a_id,DEVICE,"Local name")
        ] {
            let own=event(own_id,own_device,own_name);
            let peer=event(peer_id,peer_device,peer_name);
            assert_eq!(preserve_authenticated_event(db,ACCOUNT,"project",&own,NOW).unwrap(),"applied");
            assert_eq!(preserve_authenticated_event(db,ACCOUNT,"project",&peer,NOW).unwrap(),"conflict_preserved");
            assert_eq!(ack_candidate(db),2);
            assert_eq!(db.query_row("SELECT COUNT(*) FROM cloud_sync_metadata_tips",[],|r|r.get::<_,i64>(0)).unwrap(),2);
            assert_eq!(db.query_row("SELECT name FROM projects WHERE id='project'",[],|r|r.get::<_,String>(0)).unwrap(),own_name);
        }
        drop(a);drop(b);
        for (path,device) in [(&path_a,DEVICE),(&path_b,b_device)] {
            let mut db=sqlite::open_database(path).unwrap();
            assert_eq!(migration_status(&db,ACCOUNT,"project").unwrap().state,"genesis_conflict");
            assert_eq!(ack_candidate(&mut db),2);
            assert_eq!(db.query_row("SELECT COUNT(*) FROM cloud_sync_metadata_tips",[],|r|r.get::<_,i64>(0)).unwrap(),2);
            assert_runtime_scope(&db,ACCOUNT,USER,device).unwrap();
            drop(db);std::fs::remove_file(path).unwrap();
        }
    }
    #[test]
    fn project_metadata_candidate_is_durable_and_reused() {
        let (mut db, path) = database();
        let first = capture_legacy_candidate(&mut db, ACCOUNT, "project", NOW).unwrap();
        assert_eq!(
            first,
            capture_legacy_candidate(&mut db, ACCOUNT, "project", NOW).unwrap()
        );
        drop(db);
        let mut db = sqlite::open_database(&path).unwrap();
        assert_eq!(
            first,
            capture_legacy_candidate(&mut db, ACCOUNT, "project", NOW).unwrap()
        );
        db.execute("UPDATE projects SET name='Changed' WHERE id='project'", [])
            .unwrap();
        let second = capture_legacy_candidate(&mut db, ACCOUNT, "project", NOW).unwrap();
        assert_ne!(first, second);
        assert_eq!(
            db.query_row(
                "SELECT COUNT(*) FROM cloud_sync_metadata_candidates",
                [],
                |r| r.get::<_, i64>(0)
            )
            .unwrap(),
            2
        );
        let event_id = prepare_metadata_genesis(&mut db, ACCOUNT, &first, NOW).unwrap();
        assert_eq!(
            event_id,
            prepare_metadata_genesis(&mut db, ACCOUNT, &first, NOW).unwrap()
        );
        assert!(matches!(
            prepare_metadata_genesis(&mut db, ACCOUNT, &second, NOW),
            Err(MetadataError::Conflict)
        ));
        drop(db);
        let mut db = sqlite::open_database(&path).unwrap();
        assert_eq!(
            event_id,
            prepare_metadata_genesis(&mut db, ACCOUNT, &first, NOW).unwrap()
        );
        assert_eq!(
            db.query_row(
                "SELECT COUNT(*) FROM cloud_sync_outbox WHERE entity_type='project_metadata'",
                [],
                |r| r.get::<_, i64>(0)
            )
            .unwrap(),
            1
        );
        db.execute("UPDATE projects SET payload_json=json_set(payload_json,'$.future_user_field','private') WHERE id='project'",[]).unwrap();
        let unsupported = capture_legacy_candidate(&mut db, ACCOUNT, "project", NOW).unwrap();
        assert!(matches!(
            prepare_metadata_genesis(&mut db, ACCOUNT, &unsupported, NOW),
            Err(MetadataError::Scope)
        ));
        drop(db);
        std::fs::remove_file(path).unwrap();
    }
    #[test]
    fn project_metadata_legacy_binding_without_bootstrap_is_preserved_but_not_publishable() {
        let (mut db, path) = database();
        db.execute(
            "DELETE FROM cloud_sync_project_bootstraps WHERE project_id='project'",
            [],
        )
        .unwrap();
        let candidate = capture_legacy_candidate(&mut db, ACCOUNT, "project", NOW).unwrap();
        let (bootstrap,unsupported): (Option<String>,String) = db.query_row(
            "SELECT bootstrap_id,unsupported_json FROM cloud_sync_metadata_candidates WHERE candidate_id=?1",
            [&candidate],|r|Ok((r.get(0)?,r.get(1)?))).unwrap();
        assert!(bootstrap.is_none());
        assert_eq!(unsupported, r#"["bootstrap_lineage_missing"]"#);
        assert!(matches!(
            prepare_metadata_genesis(&mut db, ACCOUNT, &candidate, NOW),
            Err(MetadataError::Scope)
        ));
        drop(db);
        std::fs::remove_file(path).unwrap();
    }
    #[test]
    fn project_metadata_two_parentless_genesis_preserves_both_without_winner() {
        let (mut db, path) = database();
        let id1 = "123e4567-e89b-42d3-a456-426614174010";
        let id2 = "123e4567-e89b-42d3-a456-426614174011";
        let device2 = "123e4567-e89b-42d3-a456-426614174004";
        inbound(&db, id1, DEVICE, 1);
        let first = event(id1, DEVICE, "First");
        assert_eq!(
            preserve_authenticated_event(&mut db, ACCOUNT, "project", &first, NOW).unwrap(),
            "applied"
        );
        assert_eq!(
            preserve_authenticated_event(&mut db, ACCOUNT, "project", &first, NOW).unwrap(),
            "applied"
        );
        inbound(&db, id2, device2, 2);
        let second = event(id2, device2, "Second");
        assert_eq!(
            preserve_authenticated_event(&mut db, ACCOUNT, "project", &second, NOW).unwrap(),
            "conflict_preserved"
        );
        assert_eq!(
            db.query_row("SELECT COUNT(*) FROM cloud_sync_metadata_tips", [], |r| r
                .get::<_, i64>(
                0
            ))
            .unwrap(),
            2
        );
        assert_eq!(
            db.query_row(
                "SELECT COUNT(*) FROM cloud_sync_metadata_projection",
                [],
                |r| r.get::<_, i64>(0)
            )
            .unwrap(),
            0
        );
        assert!(matches!(
            preserve_authenticated_event(
                &mut db,
                ACCOUNT,
                "project",
                &event(id1, DEVICE, "Tampered"),
                NOW
            ),
            Err(MetadataError::Conflict)
        ));
        assert_eq!(
            db.query_row("SELECT name FROM projects WHERE id='project'", [], |r| {
                r.get::<_, String>(0)
            })
            .unwrap(),
            "Local name"
        );
        drop(db);
        std::fs::remove_file(path).unwrap();
    }
    #[test]
    fn project_metadata_self_echo_requires_receipt_and_never_rewrites_visible_project() {
        let (mut db, path) = database();
        let candidate = capture_legacy_candidate(&mut db, ACCOUNT, "project", NOW).unwrap();
        let id = prepare_metadata_genesis(&mut db, ACCOUNT, &candidate, NOW).unwrap();
        inbound(&db, &id, DEVICE, 1);
        let payload = event(&id, DEVICE, "Local name");
        assert!(matches!(
            preserve_authenticated_event(&mut db, ACCOUNT, "project", &payload, NOW),
            Err(MetadataError::Scope)
        ));
        db.execute(
            "UPDATE cloud_sync_outbox SET lifecycle='sealed' WHERE event_id=?1",
            [&id],
        )
        .unwrap();
        db.execute("INSERT INTO cloud_sync_upload_receipts(account_id,event_id,device_id,server_sequence,duplicate,accepted_at) VALUES(?1,?2,?3,1,0,?4)",params![ACCOUNT,id,DEVICE,NOW]).unwrap();
        assert_eq!(
            preserve_authenticated_event(&mut db, ACCOUNT, "project", &payload, NOW).unwrap(),
            "applied"
        );
        assert_eq!(
            preserve_authenticated_event(&mut db, ACCOUNT, "project", &payload, NOW).unwrap(),
            "applied"
        );
        assert_eq!(
            db.query_row("SELECT name FROM projects WHERE id='project'", [], |r| {
                r.get::<_, String>(0)
            })
            .unwrap(),
            "Local name"
        );
        drop(db);
        std::fs::remove_file(path).unwrap();
    }
    #[test]
    fn project_metadata_malformed_scope_and_orphan_roll_back() {
        let (mut db, path) = database();
        let id = "123e4567-e89b-42d3-a456-426614174012";
        inbound(&db, id, DEVICE, 1);
        let mut value: Value = serde_json::from_slice(&event(id, DEVICE, "Good")).unwrap();
        value["metadata"]["secret"] = json!("leak");
        assert!(matches!(
            preserve_authenticated_event(
                &mut db,
                ACCOUNT,
                "project",
                &serde_json::to_vec(&value).unwrap(),
                NOW
            ),
            Err(MetadataError::Invalid)
        ));
        let mut value: Value = serde_json::from_slice(&event(id, DEVICE, "Good")).unwrap();
        value["header"]["account_id"] = json!("other");
        assert!(matches!(
            preserve_authenticated_event(
                &mut db,
                ACCOUNT,
                "project",
                &serde_json::to_vec(&value).unwrap(),
                NOW
            ),
            Err(MetadataError::Scope)
        ));
        value["header"]["account_id"] = json!(USER);
        value["header"]["operation"] = json!("update");
        value["header"]["revision"] = json!(2);
        value["header"]["parent_event_ids"] = json!(["123e4567-e89b-42d3-a456-426614174099"]);
        db.execute(
            "UPDATE cloud_sync_inbox SET sync_revision=2 WHERE event_id=?1",
            [id],
        )
        .unwrap();
        let orphan_bytes = serde_json::to_vec(&value).unwrap();
        assert_eq!(
            preserve_authenticated_event(&mut db, ACCOUNT, "project", &orphan_bytes, NOW).unwrap(),
            "orphan"
        );
        assert_eq!(
            preserve_authenticated_event(&mut db, ACCOUNT, "project", &orphan_bytes, NOW).unwrap(),
            "orphan"
        );
        assert_eq!(
            db.query_row(
                "SELECT state FROM cloud_sync_inbox WHERE event_id=?1",
                [id],
                |r| r.get::<_, String>(0)
            )
            .unwrap(),
            "orphan"
        );
        assert_eq!(
            db.query_row(
                "SELECT COUNT(*) FROM cloud_sync_metadata_apply_ledger",
                [],
                |r| r.get::<_, i64>(0)
            )
            .unwrap(),
            0
        );
        drop(db);
        let mut db = sqlite::open_database(&path).unwrap();
        inbound(&db, USER, DEVICE, 2);
        assert_eq!(
            preserve_authenticated_event(
                &mut db,
                ACCOUNT,
                "project",
                &event(USER, DEVICE, "Parent"),
                NOW
            )
            .unwrap(),
            "applied"
        );
        assert_eq!(
            preserve_authenticated_event(&mut db, ACCOUNT, "project", &orphan_bytes, NOW).unwrap(),
            "applied"
        );
        assert_eq!(
            db.query_row("SELECT COUNT(*) FROM cloud_sync_metadata_tips", [], |r| r
                .get::<_, i64>(
                0
            ))
            .unwrap(),
            1
        );
        drop(db);
        std::fs::remove_file(path).unwrap();
    }
}
