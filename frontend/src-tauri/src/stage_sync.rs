//! C18.4.01 internal structural substrate. No background migration writer.
//! Authentication/unframing starts in stageCodec; native repeats frame, scope,
//! immutable object, dependencies and causal CAS inside BEGIN IMMEDIATE.
use crate::project_metadata_sync::{self as metadata, MetadataError as Error};
use rusqlite::{params, Connection, OptionalExtension, Transaction, TransactionBehavior};
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};

pub(crate) const FIELDS: &[&str] = &[
    "name",
    "goal",
    "infinite",
    "unit",
    "status",
    "deadline",
    "personal_goal",
    "auto_freeze",
    "streak_enabled",
    "work_method",
    "created_at",
    "completed_at",
];
const LEGACY: &[&str] = &[
    "id",
    "total",
    "progress",
    "updated_at",
    "notes_updated_at",
    "mindmap_updated_at",
    "today_goal",
    "planning_date",
    "plan_daily_goal",
    "added_today",
    "remaining",
    "streak_status",
    "streak_length",
    "max_streak",
    "progress_entries",
    "project_notes",
    "mindmap",
    "stages",
    "stages_enabled",
    "combine_stage_mindmaps",
    "cover_image",
    "folder_id",
    "sync_available",
    "parent_project_name",
];
#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub(crate) struct Header {
    pub account_id: String,
    pub project_id: String,
    pub bootstrap_id: String,
    pub device_id: String,
    pub entity_id: String,
    pub entity_type: String,
    pub event_id: String,
    pub operation: String,
    pub revision: i64,
    pub generation: i64,
    pub parent_event_ids: Vec<String>,
    pub updated_at: String,
    pub metadata_event_id: String,
}
#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub(crate) struct Event {
    pub version: i64,
    pub header: Header,
    pub stage: Value,
    pub stage_ids: Value,
    pub stage_heads: Value,
    pub deleted_at: Value,
}
fn text(v: &Value) -> bool {
    v.as_str().is_some_and(|s| !s.is_empty() && s.len() <= 512)
}
fn stage_valid(v: &Value) -> bool {
    let Some(o) = v.as_object() else { return false };
    o.len() == FIELDS.len()
        && FIELDS.iter().all(|k| o.contains_key(*k))
        && ["name", "unit", "status", "work_method"]
            .iter()
            .all(|k| text(&o[*k]))
        && ["infinite", "auto_freeze", "streak_enabled"]
            .iter()
            .all(|k| o[*k].is_boolean())
        && (o["goal"].is_null()
            || o["goal"]
                .as_f64()
                .is_some_and(|n| n.is_finite() && n >= 0.0 && n <= 9_007_199_254_740_991.0))
        && o["personal_goal"]
            .as_f64()
            .is_some_and(|n| n.is_finite() && n >= 0.0 && n <= 9_007_199_254_740_991.0)
        && ["deadline", "created_at", "completed_at"]
            .iter()
            .all(|k| o[*k].is_null() || text(&o[*k]))
}
fn validate(e: &Event) -> Result<(), Error> {
    let h = &e.header;
    if e.version != 1
        || ![
            &h.account_id,
            &h.bootstrap_id,
            &h.device_id,
            &h.event_id,
            &h.metadata_event_id,
        ]
        .iter()
        .all(|s| metadata::uuid(s))
        || !text(&json!(h.project_id))
        || !text(&json!(h.entity_id))
        || !matches!(h.entity_type.as_str(), "stage" | "stage_order")
        || !metadata::timestamp(&h.updated_at)
        || !(1..=9_007_199_254_740_991).contains(&h.revision)
        || !(1..=9_007_199_254_740_991).contains(&h.generation)
        || !matches!(h.operation.as_str(), "create" | "update" | "delete")
        || h.parent_event_ids.len() != if h.operation == "create" { 0 } else { 1 }
        || h.parent_event_ids
            .iter()
            .any(|p| !metadata::uuid(p) || p == &h.event_id)
        || (h.operation == "create" && (h.revision != 1 || h.generation != 1))
        || (h.operation != "create" && (h.revision < 2 || h.generation < 2))
    {
        return Err(Error::Invalid);
    }
    if h.entity_type == "stage" {
        if !e.stage_ids.is_null()
            || !e.stage_heads.is_null()
            || if h.operation == "delete" {
                !e.stage.is_null() || e.deleted_at != json!(h.updated_at)
            } else {
                !stage_valid(&e.stage) || !e.deleted_at.is_null()
            }
        {
            return Err(Error::Invalid);
        }
    } else {
        let ids = e.stage_ids.as_array().ok_or(Error::Invalid)?;
        let heads = e.stage_heads.as_object().ok_or(Error::Invalid)?;
        if h.entity_id != "stage_order"
            || h.operation == "delete"
            || !e.stage.is_null()
            || !e.deleted_at.is_null()
            || ids.len() > 4096
            || heads.len() != ids.len()
            || ids.iter().any(|s| !text(s))
            || ids.iter().any(|s| {
                !heads
                    .get(s.as_str().unwrap())
                    .and_then(Value::as_array)
                    .is_some_and(|a| {
                        !a.is_empty()
                            && a.len() <= 64
                            && a.iter().all(|v| v.as_str().is_some_and(metadata::uuid))
                            && a.windows(2).all(|w| w[0].as_str() < w[1].as_str())
                    })
            })
            || ids.iter().collect::<std::collections::HashSet<_>>().len() != ids.len()
        {
            return Err(Error::Invalid);
        }
    }
    Ok(())
}
// ECMAScript notation and UTF-16 key order match the TS canonical codec.
fn canonical(v: &Value) -> Result<String, Error> {
    match v {
        Value::Array(a) => Ok(format!(
            "[{}]",
            a.iter()
                .map(canonical)
                .collect::<Result<Vec<_>, _>>()?
                .join(",")
        )),
        Value::Object(o) => {
            let mut keys = o.keys().collect::<Vec<_>>();
            keys.sort_by(|a, b| a.encode_utf16().cmp(b.encode_utf16()));
            Ok(format!(
                "{{{}}}",
                keys.into_iter()
                    .map(|k| Ok(format!(
                        "{}:{}",
                        serde_json::to_string(k).map_err(|_| Error::Invalid)?,
                        canonical(&o[k])?
                    )))
                    .collect::<Result<Vec<_>, Error>>()?
                    .join(",")
            ))
        }
        Value::Number(n) => {
            let f = n.as_f64().ok_or(Error::Invalid)?;
            if f == 0.0 {
                return Ok("0".into());
            }
            if f.fract() == 0.0 && f.abs() <= 9_007_199_254_740_991.0 {
                return Ok(format!("{:.0}", f));
            }
            let raw = n.to_string();
            if let Some((mantissa, exponent)) = raw.split_once('e') {
                let exp: i32 = exponent.parse().map_err(|_| Error::Invalid)?;
                if exp >= -6 && exp < 21 {
                    let digits = mantissa.replace('.', "");
                    let point = mantissa.find('.').unwrap_or(mantissa.len()) as i32 + exp;
                    if point <= 0 {
                        return Ok(format!("0.{}{}", "0".repeat((-point) as usize), digits));
                    }
                    if point as usize >= digits.len() {
                        return Ok(format!(
                            "{}{}",
                            digits,
                            "0".repeat(point as usize - digits.len())
                        ));
                    }
                    return Ok(format!(
                        "{}.{}",
                        &digits[..point as usize],
                        &digits[point as usize..]
                    ));
                }
                return Ok(format!(
                    "{}e{}{}",
                    mantissa,
                    if exp >= 0 { "+" } else { "" },
                    exp
                ));
            }
            Ok(raw)
        }
        _ => serde_json::to_string(v).map_err(|_| Error::Invalid),
    }
}
/// Native canonical bytes use serde's sorted map keys and normalized integral
/// numbers; matches stageCodec JSON.stringify for the bounded portable numbers.
pub(crate) fn frame(e: &Event) -> Result<Vec<u8>, Error> {
    validate(e)?;
    let mut v = serde_json::to_value(e).map_err(|_| Error::Invalid)?;
    if !v["stage"].is_null() {
        v["stage"] = metadata::normalize_metadata_numbers(v["stage"].clone());
    }
    let bytes = canonical(&v)?.into_bytes();
    if bytes.len() > 1024 * 1024 {
        return Err(Error::Invalid);
    }
    let mut out = b"WORTA-C1".to_vec();
    out.extend([
        1,
        if e.header.entity_type == "stage" {
            2
        } else {
            3
        },
        1,
        0,
    ]);
    out.extend((bytes.len() as u32).to_be_bytes());
    out.extend((bytes.len() as u32).to_be_bytes());
    out.extend(bytes);
    Ok(out)
}
pub(crate) fn unframe(bytes: &[u8]) -> Result<Event, Error> {
    if bytes.len() < 20
        || bytes.len() > 1024 * 1024 + 20
        || &bytes[..8] != b"WORTA-C1"
        || bytes[8] != 1
        || !matches!(bytes[9], 2 | 3)
        || bytes[10] != 1
        || bytes[11] != 0
        || u32::from_be_bytes(bytes[12..16].try_into().unwrap()) as usize != bytes.len() - 20
        || bytes[12..16] != bytes[16..20]
    {
        return Err(Error::Invalid);
    }
    let e: Event = serde_json::from_slice(&bytes[20..]).map_err(|_| Error::Invalid)?;
    if frame(&e)? != bytes {
        return Err(Error::Invalid);
    }
    Ok(e)
}
fn tips(db: &Connection, a: &str, p: &str, t: &str, id: &str) -> Result<Vec<String>, Error> {
    let mut q=db.prepare("SELECT event_id FROM cloud_sync_structural_tips WHERE account_id=?1 AND project_id=?2 AND entity_type=?3 AND entity_id=?4 ORDER BY event_id")?;
    let rows = q
        .query_map(params![a, p, t, id], |r| r.get(0))?
        .collect::<Result<Vec<_>, _>>()?;
    Ok(rows)
}
/// Active includes reconciliation with visible local metadata; unresolved genesis,
/// differing local shell and tombstoned metadata cannot authorize structural work.
fn dependency(db: &Connection, a: &str, h: &Header) -> Result<Option<&'static str>, Error> {
    let binding:Option<(String,String)>=db.query_row("SELECT u.canonical_user_id,b.bootstrap_id FROM cloud_sync_project_bindings p JOIN cloud_account_bindings u ON u.local_account_id=p.account_id JOIN cloud_sync_project_bootstraps b ON b.account_id=p.account_id AND b.project_id=p.project_id WHERE p.account_id=?1 AND p.project_id=?2",params![a,h.project_id],|r|Ok((r.get(0)?,r.get(1)?))).optional()?;
    let Some((user, boot)) = binding else {
        return Ok(Some("project_metadata_dependency_missing"));
    };
    if user != h.account_id || boot != h.bootstrap_id {
        return Err(Error::Scope);
    }
    let proven:bool=db.query_row("SELECT EXISTS(SELECT 1 FROM cloud_sync_metadata_events e JOIN cloud_sync_metadata_apply_ledger l ON l.account_id=e.account_id AND l.event_id=e.event_id WHERE e.account_id=?1 AND e.project_id=?2 AND e.event_id=?3 AND e.bootstrap_id=?4 AND e.state IN ('applied','conflict_preserved') AND e.operation!='delete')",params![a,h.project_id,h.metadata_event_id,h.bootstrap_id],|r|r.get(0))?;
    if !proven {
        return Ok(Some("project_metadata_head_unknown"));
    }
    if metadata::authority_view(db, a, &h.project_id)?.state != "active" {
        return Ok(Some("project_metadata_authority_unresolved"));
    }
    Ok(None)
}
fn snapshot(
    db: &Connection,
    project: &str,
    id: &str,
) -> Result<(Value, Value, Vec<String>), Error> {
    let (name,goal,infinite,unit,status,created,raw):(String,Option<f64>,bool,String,String,Option<String>,String)=db.query_row("SELECT name,goal,infinite,unit,status,created_at,payload_json FROM stages WHERE id=?1 AND project_id=?2",params![id,project],|r|Ok((r.get(0)?,r.get(1)?,r.get(2)?,r.get(3)?,r.get(4)?,r.get(5)?,r.get(6)?)))?;
    let raw: Value = serde_json::from_str(&raw).map_err(|_| Error::Invalid)?;
    let o = raw.as_object().ok_or(Error::Invalid)?;
    let mut s = json!({"name":name,"goal":goal,"infinite":infinite,"unit":unit,"status":status,"created_at":created,"completed_at":null,"deadline":null,"personal_goal":0,"auto_freeze":true,"streak_enabled":true,"work_method":"manual"});
    for k in [
        "completed_at",
        "deadline",
        "personal_goal",
        "auto_freeze",
        "streak_enabled",
        "work_method",
    ] {
        if let Some(v) = o.get(k) {
            s[k] = v.clone();
        }
    }
    s = metadata::normalize_metadata_numbers(s);
    let ext:Option<String>=db.query_row("SELECT payload_json FROM project_extensions WHERE entity_type='stage' AND entity_id=?1",[id],|r|r.get(0)).optional()?;
    let mut unsupported: Vec<String> = o
        .keys()
        .filter(|k| !FIELDS.contains(&k.as_str()) && !LEGACY.contains(&k.as_str()))
        .cloned()
        .collect();
    let extension: Value = ext
        .map(|s| serde_json::from_str(&s))
        .transpose()
        .map_err(|_| Error::Invalid)?
        .unwrap_or(json!({}));
    if extension.as_object().is_none_or(|o| !o.is_empty()) {
        unsupported.push("stage_extensions".into());
    }
    if !stage_valid(&s) {
        unsupported.push("invalid_stage_portable_fields".into());
    }
    for key in ["name", "goal", "infinite", "unit", "status", "created_at"] {
        if let Some(value) = o.get(key) {
            let same = value == &s[key]
                || (value.is_number() && s[key].is_number() && value.as_f64() == s[key].as_f64());
            if !same {
                unsupported.push(format!("stage_column_payload_mismatch:{key}"));
            }
        }
    }
    if o.get("id").is_some_and(|v| v.as_str() != Some(id)) {
        unsupported.push("stage_identity_mismatch".into());
    }
    for (key, expected) in [
        ("stages", json!([])),
        ("stages_enabled", json!(false)),
        ("combine_stage_mindmaps", json!(false)),
        ("cover_image", Value::Null),
        ("folder_id", Value::Null),
    ] {
        if o.get(key).is_some_and(|v| v != &expected) {
            unsupported.push(format!("unsupported_stage_legacy_field:{key}"));
        }
    }
    unsupported.sort();
    // Raw source includes extension contents, not just the name of a blocker.
    Ok((
        s,
        json!({"payload":raw,"extensions":extension}),
        unsupported,
    ))
}
pub(crate) fn capture_candidate(
    db: &mut Connection,
    a: &str,
    p: &str,
    id: &str,
    now: &str,
) -> Result<String, Error> {
    let tx = db.transaction_with_behavior(TransactionBehavior::Immediate)?;
    let view = metadata::authority_view(&tx, a, p)?;
    if view.state != "active" {
        return Err(Error::Conflict);
    }
    let head = view.head_event_id.ok_or(Error::Scope)?;
    let (device,boot):(String,String)=tx.query_row("SELECT s.device_id,b.bootstrap_id FROM cloud_sync_state s JOIN cloud_sync_project_bootstraps b ON b.account_id=s.account_id WHERE s.account_id=?1 AND b.project_id=?2",params![a,p],|r|Ok((r.get(0)?,r.get(1)?)))?;
    let (s, raw, unsupported) = snapshot(&tx, p, id)?;
    let prior:Option<(String,String,String,String,String)>=tx.query_row("SELECT candidate_id,snapshot_json,source_json,unsupported_json,metadata_event_id FROM cloud_sync_stage_candidates WHERE account_id=?1 AND project_id=?2 AND stage_id=?3 AND device_id=?4 ORDER BY generation DESC LIMIT 1",params![a,p,id,device],|r|Ok((r.get(0)?,r.get(1)?,r.get(2)?,r.get(3)?,r.get(4)?))).optional()?;
    let blocks = json!(unsupported).to_string();
    if let Some((cid, old, source, b, dep)) = prior {
        if old == s.to_string() && source == raw.to_string() && b == blocks && dep == head {
            tx.commit()?;
            return Ok(cid);
        }
    }
    let generation:i64=tx.query_row("SELECT COALESCE(MAX(generation),0)+1 FROM cloud_sync_stage_candidates WHERE account_id=?1 AND project_id=?2 AND stage_id=?3 AND device_id=?4",params![a,p,id,device],|r|r.get(0))?;
    let cid = metadata::new_event_id()?;
    tx.execute(
        "INSERT INTO cloud_sync_stage_candidates VALUES(?1,?2,?3,?4,?5,?6,?7,?8,?9,?10,?11,?12)",
        params![
            cid,
            a,
            p,
            id,
            device,
            boot,
            head,
            generation,
            s.to_string(),
            raw.to_string(),
            blocks,
            now
        ],
    )?;
    tx.commit()?;
    Ok(cid)
}
fn store(
    tx: &Transaction<'_>,
    a: &str,
    e: &Event,
    bytes: &[u8],
    state: &str,
    seq: Option<i64>,
) -> Result<(), Error> {
    let h = &e.header;
    tx.execute("INSERT INTO cloud_sync_structural_events(account_id,event_id,project_id,entity_type,entity_id,canonical_frame,parent_event_id,metadata_event_id,revision,generation,operation,state,server_sequence) VALUES(?1,?2,?3,?4,?5,?6,?7,?8,?9,?10,?11,?12,?13)",params![a,h.event_id,h.project_id,h.entity_type,h.entity_id,bytes,h.parent_event_ids.first(),h.metadata_event_id,h.revision,h.generation,h.operation,state,seq])?;
    Ok(())
}
/// Explicit internal publication only. Exact expected heads avoid capturing a
/// stale local edit as a descendant of a newly received peer branch.
pub(crate) fn prepare(
    db: &mut Connection,
    a: &str,
    e: &Event,
    expected_tips: &[String],
) -> Result<(), Error> {
    let bytes = frame(e)?;
    let h = &e.header;
    let tx = db.transaction_with_behavior(TransactionBehavior::Immediate)?;
    let device: String = tx.query_row(
        "SELECT device_id FROM cloud_sync_state WHERE account_id=?1",
        [a],
        |r| r.get(0),
    )?;
    if device != h.device_id {
        return Err(Error::Scope);
    }
    let previous:Option<Vec<u8>>=tx.query_row("SELECT e.canonical_frame FROM cloud_sync_structural_events e JOIN cloud_sync_outbox o ON o.account_id=e.account_id AND o.event_id=e.event_id WHERE e.account_id=?1 AND e.event_id=?2 AND o.device_id=?3",params![a,h.event_id,h.device_id],|r|r.get(0)).optional()?;
    if let Some(previous) = previous {
        if previous != bytes {
            return Err(Error::Conflict);
        }
        tx.commit()?;
        return Ok(());
    }
    let pending:bool=tx.query_row("SELECT EXISTS(SELECT 1 FROM cloud_sync_structural_events WHERE account_id=?1 AND project_id=?2 AND entity_type=?3 AND entity_id=?4 AND state IN ('unsealed','sealed'))",params![a,h.project_id,h.entity_type,h.entity_id],|r|r.get(0))?;
    if pending {
        return Err(Error::Conflict);
    }
    if dependency(&tx, a, h)?.is_some() {
        return Err(Error::Scope);
    }
    if tips(&tx, a, &h.project_id, &h.entity_type, &h.entity_id)? != expected_tips
        || h.parent_event_ids != expected_tips
    {
        return Err(Error::Conflict);
    }
    if h.entity_type == "stage" && h.operation == "create" {
        let candidate:Option<(String,String)>=tx.query_row("SELECT snapshot_json,unsupported_json FROM cloud_sync_stage_candidates WHERE account_id=?1 AND project_id=?2 AND stage_id=?3 AND device_id=?4 AND metadata_event_id=?5 ORDER BY generation DESC LIMIT 1",params![a,h.project_id,h.entity_id,h.device_id,h.metadata_event_id],|r|Ok((r.get(0)?,r.get(1)?))).optional()?;
        let Some((s, b)) = candidate else {
            return Err(Error::Scope);
        };
        let (current, _, current_blockers) = snapshot(&tx, &h.project_id, &h.entity_id)?;
        if b != "[]"
            || !current_blockers.is_empty()
            || serde_json::from_str::<Value>(&s).map_err(|_| Error::Invalid)? != e.stage
            || current != e.stage
        {
            return Err(Error::Conflict);
        }
    }
    if let Some(parent) = h.parent_event_ids.first() {
        let (revision,generation,operation):(i64,i64,String)=tx.query_row("SELECT revision,generation,operation FROM cloud_sync_structural_events WHERE account_id=?1 AND event_id=?2 AND project_id=?3 AND entity_type=?4 AND entity_id=?5 AND state IN ('applied','conflict_preserved')",params![a,parent,h.project_id,h.entity_type,h.entity_id],|r|Ok((r.get(0)?,r.get(1)?,r.get(2)?)))?;
        if h.revision != revision + 1 || h.generation != generation + 1 || operation == "delete" {
            return Err(Error::Invalid);
        }
    }
    if h.entity_type == "stage_order" && order_dependency(&tx, a, e)?.is_some() {
        return Err(Error::Conflict);
    }
    store(&tx, a, e, &bytes, "unsealed", None)?;
    tx.execute("INSERT INTO cloud_sync_outbox(event_id,account_id,device_id,project_id,entity_id,entity_type,operation,revision,updated_at,deleted_at,created_at,parent_event_id,local_ordinal,lifecycle) VALUES(?1,?2,?3,?4,?5,?6,?7,?8,?9,?10,?9,?11,(SELECT COALESCE(MAX(local_ordinal),0)+1 FROM cloud_sync_outbox WHERE account_id=?2),'unsealed')",params![h.event_id,a,h.device_id,h.project_id,h.entity_id,h.entity_type,if h.operation=="delete"{"delete"}else{"upsert"},h.revision,h.updated_at,e.deleted_at.as_str(),h.parent_event_ids.first()])?;
    tx.commit()?;
    Ok(())
}
pub(crate) fn seal(
    db: &mut Connection,
    a: &str,
    event: &str,
    expected_frame: &[u8],
    nonce: &[u8],
    ciphertext: &[u8],
) -> Result<(), Error> {
    if nonce.len() != 24 || ciphertext.len() < 16 || ciphertext.len() > 1024 * 1024 + 36 {
        return Err(Error::Invalid);
    }
    let tx = db.transaction_with_behavior(TransactionBehavior::Immediate)?;
    let bytes:Vec<u8>=tx.query_row("SELECT e.canonical_frame FROM cloud_sync_structural_events e JOIN cloud_sync_outbox o ON o.account_id=e.account_id AND o.event_id=e.event_id WHERE e.account_id=?1 AND e.event_id=?2 AND o.lifecycle IN ('unsealed','sealed','accepted')",params![a,event],|r|r.get(0))?;
    if bytes != expected_frame {
        return Err(Error::Conflict);
    }
    let existing:Option<(Vec<u8>,Vec<u8>)>=tx.query_row("SELECT nonce,ciphertext FROM cloud_sync_event_objects WHERE account_id=?1 AND event_id=?2",params![a,event],|r|Ok((r.get(0)?,r.get(1)?))).optional()?;
    if let Some((n, c)) = existing {
        if n != nonce || c != ciphertext {
            return Err(Error::Conflict);
        }
    } else {
        tx.execute(
            "INSERT INTO cloud_sync_event_objects VALUES(?1,?2,1,1,?3,?4,?5)",
            params![
                a,
                event,
                nonce,
                ciphertext,
                unframe(&bytes)?.header.updated_at
            ],
        )?;
        tx.execute("UPDATE cloud_sync_structural_events SET state='sealed' WHERE account_id=?1 AND event_id=?2",params![a,event])?;
        tx.execute("UPDATE cloud_sync_outbox SET lifecycle='sealed' WHERE account_id=?1 AND event_id=?2 AND lifecycle='unsealed'",params![a,event])?;
    }
    tx.commit()?;
    Ok(())
}
/// All current local stages must have authenticated live structural tips.
/// A tombstone has no complete child manifest in this slice and cannot remove
/// membership. Delete/edit conflict blocks membership; all-live edit branches prove membership.
fn order_dependency(db: &Connection, a: &str, e: &Event) -> Result<Option<&'static str>, Error> {
    let h = &e.header;
    let ids = e.stage_ids.as_array().ok_or(Error::Invalid)?;
    for id in ids {
        let owner: Option<String> = db
            .query_row(
                "SELECT project_id FROM stages WHERE id=?1",
                [id.as_str().unwrap()],
                |r| r.get(0),
            )
            .optional()?;
        if owner.as_deref().is_some_and(|p| p != h.project_id) {
            return Ok(Some("stage_order_foreign_stage"));
        }
        let ts = tips(db, a, &h.project_id, "stage", id.as_str().unwrap())?;
        if ts.is_empty() {
            return Ok(Some("stage_dependency_missing"));
        }
        for tip in &ts {
            let op:String=db.query_row("SELECT operation FROM cloud_sync_structural_events WHERE account_id=?1 AND event_id=?2",params![a,tip],|r|r.get(0))?;
            if op == "delete" {
                return Ok(Some("stage_tombstone_child_manifest_incomplete"));
            }
        }
        if e.stage_heads[id.as_str().unwrap()] != json!(ts) {
            return Ok(Some("stage_membership_head_changed"));
        }
    }
    let mut q = db.prepare("SELECT id FROM stages WHERE project_id=?1 ORDER BY id")?;
    let local: Vec<String> = q
        .query_map([&h.project_id], |r| r.get(0))?
        .collect::<Result<_, _>>()?;
    let mut members: Vec<String> = ids
        .iter()
        .map(|v| v.as_str().unwrap().to_string())
        .collect();
    members.sort();
    if local != members {
        return Ok(Some("stage_order_membership_mismatch"));
    }
    Ok(None)
}
fn write_stage(tx: &Transaction<'_>, e: &Event) -> Result<(), Error> {
    let h = &e.header;
    let s = &e.stage;
    let existing: Option<String> = tx
        .query_row(
            "SELECT payload_json FROM stages WHERE id=?1 AND project_id=?2",
            params![h.entity_id, h.project_id],
            |r| r.get(0),
        )
        .optional()?;
    let is_new = existing.is_none();
    let mut payload: Value = existing
        .map(|s| serde_json::from_str(&s))
        .transpose()
        .map_err(|_| Error::Invalid)?
        .unwrap_or(json!({"id":h.entity_id}));
    let o = payload.as_object_mut().ok_or(Error::Invalid)?;
    for k in FIELDS {
        o.insert(k.to_string(), s[*k].clone());
    }
    // D, not an independent portable authority.
    let parent_name: String = tx.query_row(
        "SELECT name FROM projects WHERE id=?1",
        [&h.project_id],
        |r| r.get(0),
    )?;
    o.insert("parent_project_name".into(), json!(parent_name));
    tx.execute("INSERT INTO stages(id,project_id,name,goal,infinite,unit,status,created_at,updated_at,payload_json) VALUES(?1,?2,?3,?4,?5,?6,?7,?8,?9,?10) ON CONFLICT(id) DO UPDATE SET name=excluded.name,goal=excluded.goal,infinite=excluded.infinite,unit=excluded.unit,status=excluded.status,created_at=excluded.created_at,updated_at=excluded.updated_at,payload_json=excluded.payload_json",params![h.entity_id,h.project_id,s["name"].as_str(),s["goal"].as_f64(),s["infinite"].as_bool(),s["unit"].as_str(),s["status"].as_str(),s["created_at"].as_str(),h.updated_at,payload.to_string()])?;
    if is_new {
        // Compatibility placement only, never an authenticated order authority.
        // A received Stage-order permutation replaces it in its own transaction.
        tx.execute("INSERT INTO stage_order(stage_id,project_id,position) VALUES(?1,?2,(SELECT COALESCE(MAX(position),-1)+1 FROM stage_order WHERE project_id=?2))",params![h.entity_id,h.project_id])?;
    }
    Ok(())
}
fn block(tx: Transaction<'_>, a: &str, e: &Event, reason: &str) -> Result<&'static str, Error> {
    tx.execute("UPDATE cloud_sync_structural_events SET state='orphan',blocker=?1,retry_ordinal=(SELECT COALESCE(MAX(retry_ordinal),0)+1 FROM cloud_sync_structural_events WHERE account_id=?2) WHERE account_id=?2 AND event_id=?3",params![reason,a,e.header.event_id])?;
    tx.execute("UPDATE cloud_sync_inbox SET state='orphan',error_code=?1 WHERE account_id=?2 AND event_id=?3",params![reason,a,e.header.event_id])?;
    tx.commit()?;
    Ok("orphan")
}
/// expected object is mandatory: binds native verified plaintext to the exact
/// durable inbox object used by the trusted authenticated codec caller.
pub(crate) fn apply(
    db: &mut Connection,
    a: &str,
    bytes: &[u8],
    nonce: &[u8],
    ciphertext: &[u8],
) -> Result<&'static str, Error> {
    let e = unframe(bytes)?;
    let h = &e.header;
    let tx = db.transaction_with_behavior(TransactionBehavior::Immediate)?;
    let user: Option<String> = tx
        .query_row(
            "SELECT canonical_user_id FROM cloud_account_bindings WHERE local_account_id=?1",
            [a],
            |r| r.get(0),
        )
        .optional()?;
    if user.as_deref() != Some(&h.account_id) {
        return Err(Error::Scope);
    }
    let object:bool=tx.query_row("SELECT EXISTS(SELECT 1 FROM cloud_sync_event_objects WHERE account_id=?1 AND event_id=?2 AND crypto_version=1 AND aad_version=1 AND nonce=?3 AND ciphertext=?4)",params![a,h.event_id,nonce,ciphertext],|r|r.get(0))?;
    if !object {
        return Err(Error::Scope);
    }
    let inbox:Option<(i64,String)>=tx.query_row("SELECT server_sequence,state FROM cloud_sync_inbox WHERE account_id=?1 AND event_id=?2 AND project_id=?3 AND entity_id=?4 AND entity_type=?5 AND device_id=?6 AND sync_revision=?7 AND operation=?8 AND updated_at=?9 AND deleted_at IS ?10",params![a,h.event_id,h.project_id,h.entity_id,h.entity_type,h.device_id,h.revision,if h.operation=="delete"{"delete"}else{"upsert"},h.updated_at,e.deleted_at.as_str()],|r|Ok((r.get(0)?,r.get(1)?))).optional()?;
    let Some((seq, _)) = inbox else {
        return Err(Error::Scope);
    };
    let existing:Option<(Vec<u8>,String)>=tx.query_row("SELECT canonical_frame,state FROM cloud_sync_structural_events WHERE account_id=?1 AND event_id=?2",params![a,h.event_id],|r|Ok((r.get(0)?,r.get(1)?))).optional()?;
    if let Some((old, _)) = &existing {
        if old != bytes {
            return Err(Error::Conflict);
        }
    }
    if let Some(outcome)=tx.query_row("SELECT outcome FROM cloud_sync_structural_apply_ledger WHERE account_id=?1 AND event_id=?2 AND nonce=?3 AND ciphertext=?4 AND server_sequence=?5",params![a,h.event_id,nonce,ciphertext,seq],|r|r.get::<_,String>(0)).optional()?{
        return Ok(if outcome=="applied"{"applied"}else{"conflict_preserved"})
    }
    if existing.is_none() {
        store(&tx, a, &e, bytes, "orphan", Some(seq))?;
    } else {
        tx.execute("UPDATE cloud_sync_structural_events SET server_sequence=?1 WHERE account_id=?2 AND event_id=?3",params![seq,a,h.event_id])?;
    }
    if let Some(reason) = dependency(&tx, a, h)? {
        return block(tx, a, &e, reason);
    }
    if let Some(parent) = h.parent_event_ids.first() {
        let prior:Option<(i64,i64,String)>=tx.query_row("SELECT revision,generation,operation FROM cloud_sync_structural_events WHERE account_id=?1 AND event_id=?2 AND project_id=?3 AND entity_type=?4 AND entity_id=?5 AND state IN ('applied','conflict_preserved','tombstone_blocked')",params![a,parent,h.project_id,h.entity_type,h.entity_id],|r|Ok((r.get(0)?,r.get(1)?,r.get(2)?))).optional()?;
        let Some((r, g, op)) = prior else {
            return block(tx, a, &e, "structural_parent_unknown");
        };
        if h.revision != r + 1 || h.generation != g + 1 || op == "delete" {
            return block(tx, a, &e, "structural_parent_revision_invalid");
        }
    }
    if h.entity_type == "stage_order" {
        if let Some(reason) = order_dependency(&tx, a, &e)? {
            return block(tx, a, &e, reason);
        }
    }
    if h.entity_type == "stage" {
        let owner: Option<String> = tx
            .query_row(
                "SELECT project_id FROM stages WHERE id=?1",
                [&h.entity_id],
                |r| r.get(0),
            )
            .optional()?;
        if owner.as_deref().is_some_and(|p| p != h.project_id) {
            return block(tx, a, &e, "stage_scope_collision");
        }
    }
    if h.operation == "delete" && h.parent_event_ids.is_empty() {
        return Err(Error::Invalid);
    }
    let old_tips = tips(&tx, a, &h.project_id, &h.entity_type, &h.entity_id)?;
    let mut conflict = old_tips != h.parent_event_ids;
    // A distinct existing legacy value is never overwritten by remote genesis.
    // Preserve its exact raw source as a durable candidate before ACKing conflict.
    if h.entity_type == "stage" && h.operation == "create" && old_tips.is_empty() {
        let exists: bool = tx.query_row(
            "SELECT EXISTS(SELECT 1 FROM stages WHERE id=?1)",
            [&h.entity_id],
            |r| r.get(0),
        )?;
        if exists {
            let (local, raw, unsupported) = snapshot(&tx, &h.project_id, &h.entity_id)?;
            let self_echo = existing
                .as_ref()
                .is_some_and(|(_, state)| state == "sealed");
            if !self_echo || local != e.stage || !unsupported.is_empty() {
                conflict = true;
                let device: String = tx.query_row(
                    "SELECT device_id FROM cloud_sync_state WHERE account_id=?1",
                    [a],
                    |r| r.get(0),
                )?;
                let generation:i64=tx.query_row("SELECT COALESCE(MAX(generation),0)+1 FROM cloud_sync_stage_candidates WHERE account_id=?1 AND project_id=?2 AND stage_id=?3 AND device_id=?4",params![a,h.project_id,h.entity_id,device],|r|r.get(0))?;
                tx.execute("INSERT INTO cloud_sync_stage_candidates VALUES(?1,?2,?3,?4,?5,?6,?7,?8,?9,?10,?11,?12)",params![metadata::new_event_id()?,a,h.project_id,h.entity_id,device,h.bootstrap_id,h.metadata_event_id,generation,local.to_string(),raw.to_string(),json!(unsupported).to_string(),h.updated_at])?;
            }
        }
    }
    if h.entity_type == "stage" && h.operation == "update" {
        let prior_frame:Option<Vec<u8>>=tx.query_row("SELECT e.canonical_frame FROM cloud_sync_structural_projection p JOIN cloud_sync_structural_events e ON e.account_id=p.account_id AND e.event_id=p.head_event_id WHERE p.account_id=?1 AND p.project_id=?2 AND p.entity_type='stage' AND p.entity_id=?3",params![a,h.project_id,h.entity_id],|r|r.get(0)).optional()?;
        if let Some(prior) = prior_frame {
            let (local, raw, unsupported) = snapshot(&tx, &h.project_id, &h.entity_id)?;
            if local != unframe(&prior)?.stage || !unsupported.is_empty() {
                conflict = true;
                let device: String = tx.query_row(
                    "SELECT device_id FROM cloud_sync_state WHERE account_id=?1",
                    [a],
                    |r| r.get(0),
                )?;
                let generation:i64=tx.query_row("SELECT COALESCE(MAX(generation),0)+1 FROM cloud_sync_stage_candidates WHERE account_id=?1 AND project_id=?2 AND stage_id=?3 AND device_id=?4",params![a,h.project_id,h.entity_id,device],|r|r.get(0))?;
                tx.execute("INSERT INTO cloud_sync_stage_candidates VALUES(?1,?2,?3,?4,?5,?6,?7,?8,?9,?10,?11,?12)",params![metadata::new_event_id()?,a,h.project_id,h.entity_id,device,h.bootstrap_id,h.metadata_event_id,generation,local.to_string(),raw.to_string(),json!(unsupported).to_string(),h.updated_at])?;
            }
        }
    }
    let pending:bool=tx.query_row("SELECT EXISTS(SELECT 1 FROM cloud_sync_structural_events WHERE account_id=?1 AND project_id=?2 AND entity_type=?3 AND entity_id=?4 AND event_id!=?5 AND state IN ('unsealed','sealed'))",params![a,h.project_id,h.entity_type,h.entity_id,h.event_id],|r|r.get(0))?;
    conflict |= pending;
    tx.execute(
        "INSERT OR IGNORE INTO cloud_sync_structural_tips VALUES(?1,?2,?3,?4,?5)",
        params![a, h.project_id, h.entity_type, h.entity_id, h.event_id],
    )?;
    for parent in &h.parent_event_ids {
        tx.execute("DELETE FROM cloud_sync_structural_tips WHERE account_id=?1 AND project_id=?2 AND entity_type=?3 AND entity_id=?4 AND event_id=?5",params![a,h.project_id,h.entity_type,h.entity_id,parent])?;
    }
    if conflict || h.operation == "delete" {
        tx.execute("DELETE FROM cloud_sync_structural_projection WHERE account_id=?1 AND project_id=?2 AND entity_type=?3 AND entity_id=?4",params![a,h.project_id,h.entity_type,h.entity_id])?;
    }
    if h.operation == "delete" {
        tx.execute("UPDATE cloud_sync_structural_events SET state='tombstone_blocked',blocker='stage_tombstone_child_manifest_incomplete' WHERE account_id=?1 AND event_id=?2",params![a,h.event_id])?;
        tx.execute("UPDATE cloud_sync_inbox SET state='orphan',error_code='stage_tombstone_child_manifest_incomplete' WHERE account_id=?1 AND event_id=?2",params![a,h.event_id])?;
        tx.commit()?;
        return Ok("tombstone_blocked");
    }
    let outcome = if conflict {
        "conflict_preserved"
    } else {
        "applied"
    };
    if !conflict {
        if h.entity_type == "stage" {
            write_stage(&tx, &e)?;
        } else {
            tx.execute(
                "DELETE FROM stage_order WHERE project_id=?1",
                [&h.project_id],
            )?;
            for (pos, id) in e.stage_ids.as_array().unwrap().iter().enumerate() {
                tx.execute(
                    "INSERT INTO stage_order VALUES(?1,?2,?3)",
                    params![id.as_str(), h.project_id, pos as i64],
                )?;
            }
        }
        tx.execute("INSERT INTO cloud_sync_structural_projection VALUES(?1,?2,?3,?4,?5) ON CONFLICT(account_id,project_id,entity_type,entity_id) DO UPDATE SET head_event_id=excluded.head_event_id",params![a,h.project_id,h.entity_type,h.entity_id,h.event_id])?;
    }
    tx.execute("UPDATE cloud_sync_structural_events SET state=?1,blocker=NULL WHERE account_id=?2 AND event_id=?3",params![outcome,a,h.event_id])?;
    tx.execute(
        "INSERT INTO cloud_sync_structural_apply_ledger VALUES(?1,?2,?3,?4,?5,?6)",
        params![a, h.event_id, outcome, seq, nonce, ciphertext],
    )?;
    tx.execute("UPDATE cloud_sync_inbox SET state=?1,applied_at=?2,error_code=NULL WHERE account_id=?3 AND event_id=?4",params![if conflict{"conflict"}else{"applied"},h.updated_at,a,h.event_id])?;
    if existing.as_ref().is_some_and(|(_, s)| s == "sealed") {
        tx.execute(
            "INSERT OR IGNORE INTO cloud_sync_upload_receipts VALUES(?1,?2,?3,?4,0,?5)",
            params![a, h.event_id, h.device_id, seq, h.updated_at],
        )?;
        tx.execute("UPDATE cloud_sync_outbox SET lifecycle='accepted' WHERE account_id=?1 AND event_id=?2 AND lifecycle='sealed'",params![a,h.event_id])?;
    }
    tx.commit()?;
    Ok(outcome)
}
/// Entry point for an authenticated caller, including failed codec/frame opens.
/// Rejecting a malformed frame retains inbox/ciphertext and never creates a head.
pub(crate) fn apply_received(
    db: &mut Connection,
    a: &str,
    event_id: &str,
    bytes: &[u8],
    nonce: &[u8],
    ciphertext: &[u8],
) -> Result<&'static str, Error> {
    match unframe(bytes) {
        Ok(e) if e.header.event_id == event_id => apply(db, a, bytes, nonce, ciphertext),
        Ok(_) => Err(Error::Scope),
        Err(_) => {
            let tx = db.transaction_with_behavior(TransactionBehavior::Immediate)?;
            let changed=tx.execute("UPDATE cloud_sync_inbox SET state='orphan',error_code='invalid_stage_frame' WHERE account_id=?1 AND event_id=?2 AND entity_type IN ('stage','stage_order') AND state IN ('received','orphan') AND EXISTS(SELECT 1 FROM cloud_sync_event_objects o WHERE o.account_id=?1 AND o.event_id=?2 AND o.crypto_version=1 AND o.aad_version=1 AND o.nonce=?3 AND o.ciphertext=?4)",params![a,event_id,nonce,ciphertext])?;
            if changed != 1 {
                return Err(Error::Scope);
            }
            tx.commit()?;
            Ok("invalid_stage_frame")
        }
    }
}

/// Fair bounded replay of already authenticated durable orphans; missing
/// dependencies rotate to the back. New inbox events are handled independently.
pub(crate) fn retry(db: &mut Connection, a: &str, limit: usize) -> Result<Vec<String>, Error> {
    if !(1..=32).contains(&limit) {
        return Err(Error::Invalid);
    }
    let rows = {
        let mut q=db.prepare("SELECT e.canonical_frame,o.nonce,o.ciphertext FROM cloud_sync_structural_events e JOIN cloud_sync_event_objects o ON o.account_id=e.account_id AND o.event_id=e.event_id WHERE e.account_id=?1 AND e.state='orphan' ORDER BY e.retry_ordinal,e.event_id LIMIT ?2")?;
        let rows = q
            .query_map(params![a, limit as i64], |r| {
                Ok((
                    r.get::<_, Vec<u8>>(0)?,
                    r.get::<_, Vec<u8>>(1)?,
                    r.get::<_, Vec<u8>>(2)?,
                ))
            })?
            .collect::<Result<Vec<_>, _>>()?;
        rows
    };
    rows.iter()
        .map(|(b, n, c)| apply(db, a, b, n, c).map(str::to_string))
        .collect()
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::{note_sync, sqlite};
    const ACCOUNT: &str = "local-account";
    const NOW: &str = "2026-10-01T00:00:00.000000Z";
    fn event(n: u32) -> Event {
        let fixture: Value = serde_json::from_str(include_str!(
            "../../src/cloud/__fixtures__/stageCodecV1.json"
        ))
        .unwrap();
        let mut e: Event = serde_json::from_value(fixture["event"].clone()).unwrap();
        e.header.event_id = id(n);
        e
    }
    fn id(n: u32) -> String {
        format!("123e4567-e89b-42d3-a456-426614174{n:03}")
    }
    fn database() -> (Connection, std::path::PathBuf) {
        let path =
            std::env::temp_dir().join(format!("c184-{}.db", metadata::new_event_id().unwrap()));
        let db = sqlite::open_database(&path).unwrap();
        let h = event(101).header;
        db.execute("INSERT INTO projects(id,name,infinite,unit,status,payload_json) VALUES('project','Project',1,'symbols','active','{}')",[]).unwrap();
        db.execute("INSERT INTO project_order VALUES('project',0)", [])
            .unwrap();
        db.execute("INSERT INTO cloud_sync_state(account_id,device_id,created_at,updated_at) VALUES(?1,?2,?3,?3)",params![ACCOUNT,h.device_id,NOW]).unwrap();
        db.execute(
            "INSERT INTO cloud_account_bindings VALUES(?1,?2,?3,?3)",
            params![ACCOUNT, h.account_id, NOW],
        )
        .unwrap();
        db.execute(
            "INSERT INTO cloud_sync_project_bindings VALUES('project',?1,?2,?2)",
            params![ACCOUNT, NOW],
        )
        .unwrap();
        db.execute("INSERT INTO cloud_sync_project_bootstraps(project_id,account_id,device_id,bootstrap_id,mode,phase,created_at,updated_at) VALUES('project',?1,?2,?3,'upload_existing','prepared',?4,?4)",params![ACCOUNT,h.device_id,h.bootstrap_id,NOW]).unwrap();
        (db, path)
    }
    fn metadata_active(db: &mut Connection) {
        let h = event(101).header;
        let e = json!({"version":1,"header":{"account_id":h.account_id,"project_id":"project","entity_id":"project","device_id":h.device_id,"bootstrap_id":h.bootstrap_id,"event_id":id(100),"revision":1,"generation":1,"operation":"create","parent_event_ids":[],"updated_at":NOW},"metadata":{"name":"Project","goal":null,"infinite":true,"unit":"symbols","status":"active","deadline":null,"personal_goal":0,"auto_freeze":true,"streak_enabled":true,"work_method":"manual","stages_enabled":false,"combine_stage_mindmaps":false},"deleted_at":null});
        db.execute("INSERT INTO cloud_sync_inbox(account_id,event_id,server_sequence,device_id,project_id,entity_id,entity_type,operation,sync_revision,updated_at,state,received_at) VALUES(?1,?2,1,?3,'project','project','project_metadata','upsert',1,?4,'received',?4)",params![ACCOUNT,id(100),h.device_id,NOW]).unwrap();
        db.execute(
            "INSERT INTO cloud_sync_event_objects VALUES(?1,?2,1,1,zeroblob(24),zeroblob(16),?3)",
            params![ACCOUNT, id(100), NOW],
        )
        .unwrap();
        metadata::preserve_authenticated_event(
            db,
            ACCOUNT,
            "project",
            &serde_json::to_vec(&e).unwrap(),
            NOW,
        )
        .unwrap();
        assert_eq!(
            metadata::authority_view(db, ACCOUNT, "project")
                .unwrap()
                .state,
            "active"
        );
    }
    fn inbox(db: &Connection, e: &Event, seq: i64) {
        let h = &e.header;
        db.execute("INSERT INTO cloud_sync_inbox(account_id,event_id,server_sequence,device_id,project_id,entity_id,entity_type,operation,sync_revision,updated_at,deleted_at,state,received_at) VALUES(?1,?2,?3,?4,?5,?6,?7,?8,?9,?10,?11,'received',?10)",params![ACCOUNT,h.event_id,seq,h.device_id,h.project_id,h.entity_id,h.entity_type,if h.operation=="delete"{"delete"}else{"upsert"},h.revision,NOW,e.deleted_at.as_str()]).unwrap();
        db.execute("INSERT OR IGNORE INTO cloud_sync_event_objects VALUES(?1,?2,1,1,zeroblob(24),zeroblob(16),?3)",params![ACCOUNT,h.event_id,NOW]).unwrap();
        db.execute(
            "UPDATE cloud_sync_state SET pull_cursor=MAX(pull_cursor,?1) WHERE account_id=?2",
            params![seq, ACCOUNT],
        )
        .unwrap();
    }
    fn apply_event(db: &mut Connection, e: &Event, seq: i64) -> String {
        inbox(db, e, seq);
        apply(db, ACCOUNT, &frame(e).unwrap(), &[0; 24], &[0; 16])
            .unwrap()
            .into()
    }
    fn update(base: &Event, n: u32, name: &str) -> Event {
        let mut e = base.clone();
        e.header.event_id = id(n);
        e.header.operation = "update".into();
        e.header.revision += 1;
        e.header.generation += 1;
        e.header.parent_event_ids = vec![base.header.event_id.clone()];
        e.stage["name"] = json!(name);
        e
    }
    fn order(n: u32, stages: &[Event]) -> Event {
        let mut e = event(n);
        e.header.entity_id = "stage_order".into();
        e.header.entity_type = "stage_order".into();
        e.stage = Value::Null;
        e.stage_ids = json!(stages
            .iter()
            .map(|s| s.header.entity_id.clone())
            .collect::<Vec<_>>());
        e.stage_heads = json!(stages
            .iter()
            .map(|s| (s.header.entity_id.clone(), vec![s.header.event_id.clone()]))
            .collect::<std::collections::BTreeMap<_, _>>());
        e
    }
    fn ack(db: &mut Connection) -> i64 {
        let h = event(101).header;
        note_sync::prepare_note_sync_ack(
            db,
            &note_sync::PrepareNoteSyncAckCommand {
                account_id: ACCOUNT.into(),
                device_id: h.device_id,
                canonical_user_id: h.account_id,
            },
        )
        .unwrap()
        .candidate_cursor
    }
    #[test]
    fn stage_sync_codec_golden_and_unknown_frame_keys() {
        let e = event(101);
        let f = frame(&e).unwrap();
        let fixture: Value = serde_json::from_str(include_str!(
            "../../src/cloud/__fixtures__/stageCodecV1.json"
        ))
        .unwrap();
        assert_eq!(
            &f[20..],
            fixture["canonical_json"].as_str().unwrap().as_bytes()
        );
        for sample in fixture["numeric_cases"].as_array().unwrap() {
            let mut e = event(101);
            e.stage["goal"] = sample["goal"].clone();
            let bytes = frame(&e).unwrap();
            assert_eq!(
                &bytes[20..],
                sample["canonical_json"].as_str().unwrap().as_bytes()
            );
            assert!(unframe(&bytes).is_ok());
        }
        for offset in [0, 8, 9, 10, 11, 12, 16] {
            let mut bad = f.clone();
            bad[offset] = 255;
            assert!(unframe(&bad).is_err());
        }
        let mut v = serde_json::to_value(e).unwrap();
        v["stage"]["path"] = json!("/secret");
        assert!(frame(&serde_json::from_value(v).unwrap()).is_err());
        for n in [0.000001, 0.0000001, 1234.5, 9007199254740991.0] {
            let mut e = event(101);
            e.stage["goal"] = json!(n);
            assert!(unframe(&frame(&e).unwrap()).is_ok());
        }
    }
    #[test]
    fn stage_sync_candidates_restart_generation_blocker_and_no_publication() {
        let (mut db, path) = database();
        metadata_active(&mut db);
        let e = event(101);
        db.execute("INSERT INTO stages(id,project_id,name,goal,infinite,unit,status,created_at,payload_json) VALUES('S1','project',?1,1234.5,0,'symbols','активен','2026-09-01',?2)",params![e.stage["name"].as_str(),e.stage.to_string()]).unwrap();
        db.execute("INSERT INTO stage_order VALUES('S1','project',0)", [])
            .unwrap();
        let cid = capture_candidate(&mut db, ACCOUNT, "project", "S1", NOW).unwrap();
        drop(db);
        let mut db = sqlite::open_database(&path).unwrap();
        assert_eq!(
            capture_candidate(&mut db, ACCOUNT, "project", "S1", NOW).unwrap(),
            cid
        );
        let before: String = db
            .query_row("SELECT payload_json FROM stages", [], |r| r.get(0))
            .unwrap();
        prepare(&mut db, ACCOUNT, &e, &[]).unwrap();
        prepare(&mut db, ACCOUNT, &e, &[]).unwrap();
        let mut duplicate = e.clone();
        duplicate.header.event_id = id(198);
        assert!(prepare(&mut db, ACCOUNT, &duplicate, &[]).is_err());
        let bytes = frame(&e).unwrap();
        seal(
            &mut db,
            ACCOUNT,
            &e.header.event_id,
            &bytes,
            &[0; 24],
            &[0; 16],
        )
        .unwrap();
        assert_eq!(apply_event(&mut db, &e, 2), "applied");
        prepare(&mut db, ACCOUNT, &e, &[]).unwrap();
        seal(
            &mut db,
            ACCOUNT,
            &e.header.event_id,
            &bytes,
            &[0; 24],
            &[0; 16],
        )
        .unwrap();
        assert_eq!(ack(&mut db), 2);
        assert_eq!(
            db.query_row("SELECT payload_json FROM stages", [], |r| r
                .get::<_, String>(0))
                .unwrap()
                .contains("Stage Alpha"),
            true
        );
        db.execute(
            "UPDATE stages SET payload_json=json_set(payload_json,'$.unknown',1)",
            [],
        )
        .unwrap();
        let cid2 = capture_candidate(&mut db, ACCOUNT, "project", "S1", NOW).unwrap();
        assert_ne!(cid, cid2);
        assert_eq!(
            db.query_row(
                "SELECT generation FROM cloud_sync_stage_candidates WHERE candidate_id=?1",
                [cid2],
                |r| r.get::<_, i64>(0)
            )
            .unwrap(),
            2
        );
        assert!(!before.is_empty());
        assert_eq!(
            db.query_row("SELECT count(*) FROM cloud_sync_outbox", [], |r| r
                .get::<_, i64>(0))
                .unwrap(),
            1
        );
        let mut later = event(199);
        later.header.entity_id = "S1".into();
        assert!(prepare(&mut db, ACCOUNT, &later, &[]).is_err());
        std::fs::remove_file(path).unwrap();
    }
    #[test]
    fn stage_sync_concurrent_edit_delete_and_tombstone_ack_guard() {
        let (mut db, path) = database();
        metadata_active(&mut db);
        let e = event(101);
        assert_eq!(apply_event(&mut db, &e, 2), "applied");
        let beta = update(&e, 102, "Stage Beta");
        let gamma = update(&e, 103, "Stage Gamma");
        assert_eq!(apply_event(&mut db, &beta, 3), "applied");
        assert_eq!(apply_event(&mut db, &gamma, 4), "conflict_preserved");
        assert_eq!(
            tips(&db, ACCOUNT, "project", "stage", "S1").unwrap(),
            vec![id(102), id(103)]
        );
        assert_eq!(ack(&mut db), 4);
        let mut second = event(104);
        second.header.entity_id = "S2".into();
        apply_event(&mut db, &second, 5);
        let mut delete = update(&second, 105, "unused");
        delete.header.operation = "delete".into();
        delete.stage = Value::Null;
        delete.deleted_at = json!(NOW);
        assert_eq!(apply_event(&mut db, &delete, 6), "tombstone_blocked");
        let edit = update(&second, 106, "Surviving edit");
        assert_eq!(apply_event(&mut db, &edit, 7), "conflict_preserved");
        assert_eq!(ack(&mut db), 5);
        assert_eq!(
            tips(&db, ACCOUNT, "project", "stage", "S2").unwrap().len(),
            2
        );
        assert_eq!(
            db.query_row("SELECT name FROM stages WHERE id='S2'", [], |r| r
                .get::<_, String>(0))
                .unwrap(),
            "Stage Alpha"
        );
        drop(db);
        let mut db = sqlite::open_database(&path).unwrap();
        assert_eq!(ack(&mut db), 5);
        assert_eq!(
            apply(
                &mut db,
                ACCOUNT,
                &frame(&delete).unwrap(),
                &[0; 24],
                &[0; 16]
            )
            .unwrap(),
            "tombstone_blocked"
        );
        std::fs::remove_file(path).unwrap();
    }
    #[test]
    fn stage_sync_metadata_and_stage_order_orphans_retry_after_restart() {
        let (mut db, path) = database();
        let e = event(101);
        assert_eq!(apply_event(&mut db, &e, 2), "orphan");
        assert_eq!(ack(&mut db), 0);
        drop(db);
        let mut db = sqlite::open_database(&path).unwrap();
        metadata_active(&mut db);
        assert_eq!(retry(&mut db, ACCOUNT, 8).unwrap(), vec!["applied"]);
        let mut s2 = event(102);
        s2.header.entity_id = "S2".into();
        let o = order(103, &[e.clone(), s2.clone()]);
        assert_eq!(apply_event(&mut db, &o, 3), "orphan");
        assert_eq!(apply_event(&mut db, &s2, 4), "applied");
        assert_eq!(ack(&mut db), 2);
        drop(db);
        let mut db = sqlite::open_database(&path).unwrap();
        assert_eq!(retry(&mut db, ACCOUNT, 8).unwrap(), vec!["applied"]);
        assert_eq!(ack(&mut db), 4);
        assert_eq!(
            apply(&mut db, ACCOUNT, &frame(&e).unwrap(), &[0; 24], &[0; 16]).unwrap(),
            "applied"
        );
        assert_eq!(
            db.query_row(
                "SELECT count(*) FROM cloud_sync_structural_apply_ledger",
                [],
                |r| r.get::<_, i64>(0)
            )
            .unwrap(),
            3
        );
        std::fs::remove_file(path).unwrap();
    }
    #[test]
    fn stage_sync_concurrent_permutation_and_invalid_membership() {
        let (mut db, path) = database();
        metadata_active(&mut db);
        let mut stages = Vec::new();
        for i in 1..=3 {
            let mut e = event(100 + i);
            e.header.entity_id = format!("S{i}");
            apply_event(&mut db, &e, 1 + i as i64);
            stages.push(e);
        }
        let base = order(104, &stages);
        assert_eq!(apply_event(&mut db, &base, 5), "applied");
        let mut a = base.clone();
        a.header.event_id = id(105);
        a.header.operation = "update".into();
        a.header.revision = 2;
        a.header.generation = 2;
        a.header.parent_event_ids = vec![id(104)];
        a.stage_ids = json!(["S2", "S1", "S3"]);
        let mut b = a.clone();
        b.header.event_id = id(106);
        b.stage_ids = json!(["S1", "S3", "S2"]);
        assert_eq!(apply_event(&mut db, &a, 6), "applied");
        assert_eq!(apply_event(&mut db, &b, 7), "conflict_preserved");
        assert_eq!(
            tips(&db, ACCOUNT, "project", "stage_order", "stage_order")
                .unwrap()
                .len(),
            2
        );
        let mut bad = order(107, &stages);
        bad.stage_ids = json!(["S1", "S1", "S3"]);
        assert!(frame(&bad).is_err());
        bad = order(108, &stages[..2]);
        assert_eq!(apply_event(&mut db, &bad, 8), "orphan");
        let mut foreign = event(109);
        foreign.header.entity_id = "unknown".into();
        bad = order(110, &[foreign]);
        assert_eq!(apply_event(&mut db, &bad, 9), "orphan");
        assert_eq!(ack(&mut db), 7);
        std::fs::remove_file(path).unwrap();
    }
    #[test]
    fn stage_sync_atomic_rollback_and_scope_guards() {
        let (mut db, path) = database();
        metadata_active(&mut db);
        let e = event(101);
        inbox(&db, &e, 2);
        db.execute_batch("CREATE TRIGGER fail_ledger BEFORE INSERT ON cloud_sync_structural_apply_ledger BEGIN SELECT RAISE(ABORT,'injected'); END;").unwrap();
        assert!(apply(&mut db, ACCOUNT, &frame(&e).unwrap(), &[0; 24], &[0; 16]).is_err());
        assert_eq!(
            db.query_row("SELECT count(*) FROM stages", [], |r| r.get::<_, i64>(0))
                .unwrap(),
            0
        );
        assert_eq!(ack(&mut db), 1);
        db.execute_batch("DROP TRIGGER fail_ledger").unwrap();
        assert!(apply(&mut db, ACCOUNT, &frame(&e).unwrap(), &[1; 24], &[0; 16]).is_err());
        assert_eq!(
            apply(&mut db, ACCOUNT, &frame(&e).unwrap(), &[0; 24], &[0; 16]).unwrap(),
            "applied"
        );
        let mut altered = e.clone();
        altered.stage["name"] = json!("Changed replay");
        assert!(apply(
            &mut db,
            ACCOUNT,
            &frame(&altered).unwrap(),
            &[0; 24],
            &[0; 16]
        )
        .is_err());
        std::fs::remove_file(path).unwrap();
    }
    #[test]
    fn stage_sync_tombstone_preserves_children_and_blocks_order_removal() {
        let (mut db, path) = database();
        metadata_active(&mut db);
        let e = event(101);
        apply_event(&mut db, &e, 2);
        db.execute("UPDATE stages SET payload_json=json_set(payload_json,'$.mindmap',json('{\"private\":1}'),'$.total',42)",[]).unwrap();
        db.execute("INSERT INTO progress_entries(id,project_id,stage_id,payload_json) VALUES('progress','project','S1','{}')",[]).unwrap();
        db.execute("INSERT INTO progress_order VALUES('progress',0)", [])
            .unwrap();
        // Note triggers retain their local-only behavior even on a connected stage.
        let before: String = db
            .query_row("SELECT payload_json FROM stages WHERE id='S1'", [], |r| {
                r.get(0)
            })
            .unwrap();
        let mut delete = update(&e, 102, "unused");
        delete.header.operation = "delete".into();
        delete.stage = Value::Null;
        delete.deleted_at = json!(NOW);
        assert_eq!(apply_event(&mut db, &delete, 3), "tombstone_blocked");
        assert_eq!(
            db.query_row("SELECT payload_json FROM stages WHERE id='S1'", [], |r| {
                r.get::<_, String>(0)
            })
            .unwrap(),
            before
        );
        assert_eq!(
            db.query_row("SELECT count(*) FROM progress_entries", [], |r| r
                .get::<_, i64>(0))
                .unwrap(),
            1
        );
        let included = order(103, &[delete]);
        assert_eq!(apply_event(&mut db, &included, 4), "orphan");
        let removed = order(104, &[]);
        assert_eq!(apply_event(&mut db, &removed, 5), "orphan");
        assert_eq!(ack(&mut db), 2);
        assert_eq!(
            db.query_row("SELECT count(*) FROM stage_order", [], |r| r
                .get::<_, i64>(0))
                .unwrap(),
            1
        );
        std::fs::remove_file(path).unwrap();
    }
    #[test]
    fn stage_sync_fair_orphans_foreign_stage_and_invalid_frame_block_shared_ack() {
        let (mut db, path) = database();
        metadata_active(&mut db);
        let mut unknown = event(101);
        unknown.header.project_id = "missing-project".into();
        assert_eq!(apply_event(&mut db, &unknown, 2), "orphan");
        let good = event(102);
        assert_eq!(apply_event(&mut db, &good, 3), "applied");
        assert_eq!(ack(&mut db), 1);
        assert_eq!(retry(&mut db, ACCOUNT, 1).unwrap(), vec!["orphan"]);
        let bad = event(103);
        inbox(&db, &bad, 4);
        let mut bytes = frame(&bad).unwrap();
        bytes[11] = 1;
        assert_eq!(
            apply_received(
                &mut db,
                ACCOUNT,
                &bad.header.event_id,
                &bytes,
                &[0; 24],
                &[0; 16]
            )
            .unwrap(),
            "invalid_stage_frame"
        );
        assert_eq!(
            db.query_row(
                "SELECT error_code FROM cloud_sync_inbox WHERE event_id=?1",
                [id(103)],
                |r| r.get::<_, String>(0)
            )
            .unwrap(),
            "invalid_stage_frame"
        );
        db.execute("INSERT INTO projects(id,name,infinite,unit,status,payload_json) VALUES('foreign','Foreign',1,'symbols','active','{}')",[]).unwrap();
        db.execute("INSERT INTO project_order VALUES('foreign',1)", [])
            .unwrap();
        db.execute("INSERT INTO stages(id,project_id,name,infinite,unit,status,payload_json) VALUES('foreign-stage','foreign','Foreign',1,'symbols','active','{}')",[]).unwrap();
        db.execute(
            "INSERT INTO stage_order VALUES('foreign-stage','foreign',0)",
            [],
        )
        .unwrap();
        let mut foreign = event(104);
        foreign.header.entity_id = "foreign-stage".into();
        let o = order(105, &[foreign]);
        assert_eq!(apply_event(&mut db, &o, 5), "orphan");
        assert_eq!(
            db.query_row(
                "SELECT blocker FROM cloud_sync_structural_events WHERE event_id=?1",
                [id(105)],
                |r| r.get::<_, String>(0)
            )
            .unwrap(),
            "stage_order_foreign_stage"
        );
        drop(db);
        let mut db = sqlite::open_database(&path).unwrap();
        assert_eq!(ack(&mut db), 1);
        assert_eq!(
            db.query_row("SELECT count(*) FROM cloud_sync_inbox", [], |r| r
                .get::<_, i64>(0))
                .unwrap(),
            5
        );
        std::fs::remove_file(path).unwrap();
    }
    #[test]
    fn stage_sync_metadata_genesis_conflict_and_untracked_local_edit_are_preserved() {
        let (mut db, path) = database();
        metadata_active(&mut db);
        let e = event(101);
        apply_event(&mut db, &e, 2);
        db.execute("UPDATE stages SET name='Local untracked',payload_json=json_set(payload_json,'$.private_path','/device/only') WHERE id='S1'",[]).unwrap();
        let remote = update(&e, 102, "Remote edit");
        assert_eq!(apply_event(&mut db, &remote, 3), "conflict_preserved");
        assert_eq!(
            db.query_row("SELECT name FROM stages", [], |r| r.get::<_, String>(0))
                .unwrap(),
            "Local untracked"
        );
        let source: String = db
            .query_row(
                "SELECT source_json FROM cloud_sync_stage_candidates",
                [],
                |r| r.get(0),
            )
            .unwrap();
        assert!(source.contains("/device/only"));
        let raw: Vec<u8> = db
            .query_row(
                "SELECT canonical_payload FROM cloud_sync_metadata_apply_ledger",
                [],
                |r| r.get(0),
            )
            .unwrap();
        let mut meta: Value = serde_json::from_slice(&raw).unwrap();
        meta["header"]["event_id"] = json!(id(199));
        meta["metadata"]["name"] = json!("Other genesis");
        let mut descriptor = e.clone();
        descriptor.header.event_id = id(199);
        descriptor.header.entity_id = "project".into();
        descriptor.header.entity_type = "project_metadata".into();
        inbox(&db, &descriptor, 4);
        metadata::preserve_authenticated_event(
            &mut db,
            ACCOUNT,
            "project",
            &serde_json::to_vec(&meta).unwrap(),
            NOW,
        )
        .unwrap();
        let mut later = event(103);
        later.header.entity_id = "S2".into();
        assert_eq!(apply_event(&mut db, &later, 5), "orphan");
        assert_eq!(ack(&mut db), 4);
        assert_eq!(
            db.query_row(
                "SELECT blocker FROM cloud_sync_structural_events WHERE event_id=?1",
                [id(103)],
                |r| r.get::<_, String>(0)
            )
            .unwrap(),
            "project_metadata_authority_unresolved"
        );
        std::fs::remove_file(path).unwrap();
    }
}
