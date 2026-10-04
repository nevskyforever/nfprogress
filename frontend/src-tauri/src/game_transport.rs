//! Durable Game envelopes reuse the generic project transport. Account envelopes
//! stay in their scoped immutable ledger and use the existing account endpoint.
use crate::{game_codec, game_sync, project_metadata_sync as metadata};
use rusqlite::{params, Connection, OptionalExtension, TransactionBehavior};
use serde_json::{json, Value};
type Result<T> = std::result::Result<T, String>;
fn sql(_: rusqlite::Error) -> String {
    "game_storage_error".into()
}
fn decode(frame: &[u8]) -> Result<Value> {
    game_codec::unframe(frame, frame.get(9) == Some(&12))
}
pub fn pending(
    db: &Connection,
    scope: &metadata::MetadataScope,
    sealed: bool,
) -> Result<Vec<Value>> {
    metadata::assert_runtime_scope(
        db,
        &scope.account_id,
        &scope.canonical_user_id,
        &scope.device_id,
    )
    .map_err(|_| "game_scope_mismatch")?;
    let mut q=db.prepare("SELECT canonical_frame,nonce,ciphertext FROM cloud_game_events WHERE account_id=?1 AND state IN ('unsealed','sealed') AND json_extract(CAST(substr(canonical_frame,21) AS TEXT),'$.header.device_id')=?2 AND ((?3=1 AND nonce IS NOT NULL) OR (?3=0 AND nonce IS NULL)) ORDER BY retry_ordinal,event_id LIMIT 8").map_err(sql)?;
    let rows = q
        .query_map(params![scope.account_id, scope.device_id, sealed], |r| {
            Ok((
                r.get::<_, Vec<u8>>(0)?,
                r.get::<_, Option<Vec<u8>>>(1)?,
                r.get::<_, Option<Vec<u8>>>(2)?,
            ))
        })
        .map_err(sql)?
        .collect::<rusqlite::Result<Vec<_>>>()
        .map_err(sql)?;
    rows.into_iter()
        .map(|(frame, n, c)| {
            let event = decode(&frame)?;
            if event["header"]["account_id"] != scope.canonical_user_id
                || event["header"]["device_id"] != scope.device_id
            {
                return Err("game_scope_mismatch".into());
            }
            Ok(json!({"event":event,"frame":frame,"nonce":n,"ciphertext":c}))
        })
        .collect()
}
pub fn seal(
    db: &mut Connection,
    scope: &metadata::MetadataScope,
    id: &str,
    frame: &[u8],
    nonce: &[u8],
    ciphertext: &[u8],
) -> Result<()> {
    let e = decode(frame)?;
    let h = &e["header"];
    if h["account_id"] != scope.canonical_user_id
        || h["device_id"] != scope.device_id
        || h["event_id"] != id
        || ciphertext.len() != frame.len() + 16
    {
        return Err("game_scope_mismatch".into());
    }
    let tx = db
        .transaction_with_behavior(TransactionBehavior::Immediate)
        .map_err(sql)?;
    metadata::assert_runtime_scope(
        &tx,
        &scope.account_id,
        &scope.canonical_user_id,
        &scope.device_id,
    )
    .map_err(|_| "game_scope_mismatch")?;
    game_sync::seal(&tx, &scope.account_id, id, frame, nonce, ciphertext)?;
    if h["scope"] == "project" {
        let valid:bool=tx.query_row("SELECT EXISTS(SELECT 1 FROM cloud_sync_outbox WHERE EXISTS(SELECT 1 FROM cloud_sync_project_bindings b WHERE b.account_id=?1 AND b.project_id=?4) AND account_id=?1 AND event_id=?2 AND device_id=?3 AND project_id=?4 AND entity_id=?5 AND entity_type='project_game' AND operation='event' AND revision=?6 AND updated_at=?7 AND lifecycle IN ('unsealed','sealed','accepted'))",params![scope.account_id,id,scope.device_id,h["project_id"].as_str(),h["entity_id"].as_str(),h["revision"].as_i64(),h["updated_at"].as_str()],|r|r.get(0)).map_err(sql)?;
        if !valid {
            return Err("game_scope_mismatch".into());
        }
        let old:Option<(i64,i64,Vec<u8>,Vec<u8>)>=tx.query_row("SELECT crypto_version,aad_version,nonce,ciphertext FROM cloud_sync_event_objects WHERE account_id=?1 AND event_id=?2",params![scope.account_id,id],|r|Ok((r.get(0)?,r.get(1)?,r.get(2)?,r.get(3)?))).optional().map_err(sql)?;
        if let Some((cv, av, n, c)) = old {
            if cv != 1 || av != 1 || n != nonce || c != ciphertext {
                return Err("game_exact_replay_mismatch".into());
            }
        } else {
            tx.execute(
                "INSERT INTO cloud_sync_event_objects VALUES(?1,?2,1,1,?3,?4,?5)",
                params![
                    scope.account_id,
                    id,
                    nonce,
                    ciphertext,
                    h["updated_at"].as_str()
                ],
            )
            .map_err(sql)?;
        }
        tx.execute("UPDATE cloud_sync_outbox SET lifecycle='sealed' WHERE account_id=?1 AND event_id=?2 AND lifecycle='unsealed'",params![scope.account_id,id]).map_err(sql)?;
    }
    tx.execute("UPDATE cloud_game_migrations SET lifecycle='self_echo_pending' WHERE account_id=?1 AND candidate_id=?2 AND lifecycle='publication_pending'",params![scope.account_id,id]).map_err(sql)?;
    tx.commit().map_err(sql)
}
pub fn receipt(
    db: &mut Connection,
    scope: &metadata::MetadataScope,
    id: &str,
    seq: i64,
    duplicate: bool,
    now: &str,
) -> Result<()> {
    if !metadata::timestamp(now) {
        return Err("invalid_game_payload".into());
    }
    let tx = db
        .transaction_with_behavior(TransactionBehavior::Immediate)
        .map_err(sql)?;
    metadata::assert_runtime_scope(
        &tx,
        &scope.account_id,
        &scope.canonical_user_id,
        &scope.device_id,
    )
    .map_err(|_| "game_scope_mismatch")?;
    let frame: Vec<u8> = tx
        .query_row(
            "SELECT canonical_frame FROM cloud_game_events WHERE account_id=?1 AND event_id=?2",
            params![scope.account_id, id],
            |r| r.get(0),
        )
        .map_err(sql)?;
    let e = decode(&frame)?;
    let h = &e["header"];
    if h["device_id"] != scope.device_id || h["account_id"] != scope.canonical_user_id {
        return Err("game_scope_mismatch".into());
    }
    game_sync::receipt(&tx, &scope.account_id, id, seq)?;
    if h["scope"] == "project" {
        let old:Option<i64>=tx.query_row("SELECT server_sequence FROM cloud_sync_upload_receipts WHERE account_id=?1 AND event_id=?2",params![scope.account_id,id],|r|r.get(0)).optional().map_err(sql)?;
        if old.is_some_and(|v| v != seq) {
            return Err("game_exact_replay_mismatch".into());
        }
        if old.is_none() {
            tx.execute(
                "INSERT INTO cloud_sync_upload_receipts VALUES(?1,?2,?3,?4,?5,?6)",
                params![scope.account_id, id, scope.device_id, seq, duplicate, now],
            )
            .map_err(sql)?;
        }
        tx.execute("UPDATE cloud_sync_outbox SET lifecycle='accepted' WHERE account_id=?1 AND event_id=?2 AND lifecycle='sealed'",params![scope.account_id,id]).map_err(sql)?;
    }
    let next: i64 = tx
        .query_row(
            "SELECT COALESCE(MAX(retry_ordinal),0) FROM cloud_game_events WHERE account_id=?1",
            [&scope.account_id],
            |r| r.get(0),
        )
        .map_err(sql)?;
    let next = next
        .checked_add(1)
        .filter(|v| *v <= 9007199254740991)
        .ok_or("game_resource_limit")?;
    tx.execute(
        "UPDATE cloud_game_events SET retry_ordinal=?1 WHERE account_id=?2 AND event_id=?3",
        params![next, scope.account_id, id],
    )
    .map_err(sql)?;
    tx.commit().map_err(sql)
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn game_both_domain_envelopes_resume_exact_bytes_after_lost_response() {
        let v: Value = serde_json::from_str(include_str!(
            "../../src/cloud/__fixtures__/gameCodecV1.json"
        ))
        .unwrap();
        for project in [false, true] {
            let e = v["examples"]
                .as_array()
                .unwrap()
                .iter()
                .find(|e| {
                    e["event"]["action"]["kind"] == "genesis"
                        && (e["event"]["header"]["scope"] == "project") == project
                })
                .unwrap()["event"]
                .clone();
            let h = &e["header"];
            let id = h["event_id"].as_str().unwrap();
            let now = h["updated_at"].as_str().unwrap();
            let scope = metadata::MetadataScope {
                account_id: "local".into(),
                canonical_user_id: h["account_id"].as_str().unwrap().into(),
                device_id: h["device_id"].as_str().unwrap().into(),
            };
            let path = std::env::temp_dir().join(format!(
                "game-envelope-{}.db",
                metadata::new_event_id().unwrap()
            ));
            let mut db = crate::sqlite::open_database(&path).unwrap();
            db.execute("INSERT INTO cloud_sync_state(account_id,device_id,created_at,updated_at) VALUES('local',?1,?2,?2)",params![scope.device_id,now]).unwrap();
            db.execute(
                "INSERT INTO cloud_account_bindings VALUES('local',?1,?2,?2)",
                params![scope.canonical_user_id, now],
            )
            .unwrap();
            if project {
                let p = h["project_id"].as_str().unwrap();
                db.execute("INSERT INTO projects(id,name,infinite,unit,status,payload_json) VALUES(?1,'fixture',1,'symbols','active','{}')",[p]).unwrap();
                db.execute("INSERT INTO project_order VALUES(?1,0)", [p])
                    .unwrap();
                db.execute(
                    "INSERT INTO cloud_sync_project_bindings VALUES(?1,'local',?2,?2)",
                    params![p, now],
                )
                .unwrap();
                crate::game_migration::queue_project(&db, "local", &e).unwrap();
            } else {
                game_sync::preserve(&db, "local", &e, "unsealed").unwrap();
            }
            let frame = game_codec::frame(&e).unwrap();
            let n = vec![11; 24];
            let c = vec![12; frame.len() + 16];
            seal(&mut db, &scope, id, &frame, &n, &c).unwrap();
            // A transport timeout leaves no receipt; the persisted envelope is
            // the sole retry source after reopening the actual file.
            drop(db);
            let mut db = crate::sqlite::open_database(&path).unwrap();
            let retry = pending(&db, &scope, true).unwrap();
            assert_eq!(retry.len(), 1);
            assert_eq!(retry[0]["frame"], json!(frame));
            assert_eq!(retry[0]["nonce"], json!(n));
            assert_eq!(retry[0]["ciphertext"], json!(c));
            seal(&mut db, &scope, id, &frame, &n, &c).unwrap();
            receipt(&mut db, &scope, id, 5, true, now).unwrap();
            receipt(&mut db, &scope, id, 5, true, now).unwrap();
            assert_eq!(
                db.query_row("SELECT state FROM cloud_game_events", [], |r| r
                    .get::<_, String>(0))
                    .unwrap(),
                "sealed"
            );
            assert_eq!(
                db.query_row("SELECT count(*) FROM cloud_game_apply_ledger", [], |r| r
                    .get::<_, i64>(0))
                    .unwrap(),
                0
            );
            assert_eq!(
                receipt(&mut db, &scope, id, 6, true, now).unwrap_err(),
                "game_exact_replay_mismatch"
            );
            let mut changed = n.clone();
            changed[0] = 0;
            assert_eq!(
                seal(&mut db, &scope, id, &frame, &changed, &c).unwrap_err(),
                "game_exact_replay_mismatch"
            );
            if project {
                let objects: i64 = db
                    .query_row("SELECT count(*) FROM cloud_sync_event_objects", [], |r| {
                        r.get(0)
                    })
                    .unwrap();
                assert_eq!(objects, 1);
                assert_eq!(
                    db.query_row("SELECT ciphertext FROM cloud_sync_event_objects", [], |r| r
                        .get::<_, Vec<u8>>(0))
                        .unwrap(),
                    c
                );
                assert_eq!(
                    db.query_row("SELECT count(*) FROM cloud_sync_upload_receipts", [], |r| r
                        .get::<_, i64>(0))
                        .unwrap(),
                    1
                );
            }
            drop(db);
            std::fs::remove_file(path).unwrap();
        }
    }
}
