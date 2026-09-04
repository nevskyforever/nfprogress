//! Deterministic Game event application at the trusted desktop boundary.
//!
//! The event consumer deliberately accepts the versioned JSON DTO rather than
//! a Rust-struct serialization.  This keeps migration payloads compatible with
//! the Python oracle and makes unknown Game fields round-trip untouched.

use rusqlite::{params, Connection};
use serde_json::{json, Map, Value};

const EVENT_VERSION: i64 = 1;
const STATE_VERSION: i64 = 2;

#[derive(Debug, Default, serde::Serialize)]
pub struct ProcessSummary {
    pub processed: usize,
    pub failed: usize,
}

fn number(value: Option<&Value>) -> f64 {
    value.and_then(Value::as_f64).unwrap_or(0.0)
}

fn gamer_cf(gamer: &Map<String, Value>, key: &str) -> f64 {
    gamer
        .get("cf")
        .and_then(Value::as_object)
        .and_then(|coefficients| coefficients.get(key))
        .map(|value| value.get("value").unwrap_or(value))
        .and_then(Value::as_f64)
        .unwrap_or(1.0)
}

fn rounded_increment(value: f64) -> f64 {
    ((value - 1e-9) * 10.0).ceil() / 10.0
}

fn apply_event(
    state: &mut Value,
    event_type: &str,
    event_id: &str,
    delta: f64,
    context: &Map<String, Value>,
    project_id: &str,
) -> Result<(), String> {
    let root = state
        .as_object_mut()
        .ok_or_else(|| "canonical Game state is not an object".to_string())?;
    let gamer = root
        .entry("gamer")
        .or_insert_with(|| Value::Object(Map::new()))
        .as_object_mut()
        .ok_or_else(|| "canonical Gamer state is not an object".to_string())?;
    match event_type {
        "ProgressAdded" if delta > 0.0 => {
            let multiplier = (1.0 + number(gamer.get("inspiration")) / 100.0 * 0.1)
                * (1.0 + number(gamer.get("writing_reward_bonus")));
            let coins = rounded_increment(
                number(gamer.get("coins"))
                    + rounded_increment(
                        delta / 100.0 * 10.0 * gamer_cf(gamer, "coins") * multiplier,
                    ),
            );
            let experience = number(gamer.get("exp"))
                + rounded_increment(delta / 100.0 * 500.0 * gamer_cf(gamer, "exp") * multiplier);
            gamer.insert("coins".to_string(), json!(coins));
            gamer.insert("exp".to_string(), json!(experience));
            gamer.insert("writing_reward_bonus".to_string(), json!(0.0));
        }
        "ProgressDeleted" => {
            root.entry("extensions")
                .or_insert_with(|| Value::Object(Map::new()))
                .as_object_mut()
                .ok_or_else(|| "Game extensions are not an object".to_string())?
                .entry("progress_deletions")
                .or_insert_with(|| Value::Array(Vec::new()))
                .as_array_mut()
                .ok_or_else(|| "Game deletion journal is not an array".to_string())?
                .push(Value::String(event_id.to_string()));
        }
        "ProjectCompleted" | "StageCompleted" => {
            let key = context
                .get("key")
                .and_then(Value::as_str)
                .unwrap_or(project_id);
            let claimed = gamer
                .entry("complete_bonus_projects")
                .or_insert_with(|| Value::Array(Vec::new()))
                .as_array_mut()
                .ok_or_else(|| "completion marker is not an array".to_string())?;
            if !claimed.iter().any(|value| value.as_str() == Some(key)) {
                claimed.push(Value::String(key.to_string()));
                let total = number(context.get("total_symbols"));
                let multiplier = if event_type == "StageCompleted" {
                    0.25
                } else {
                    1.0
                };
                let reward = (total / 1000.0 + 0.5).round() * 100.0 * multiplier;
                gamer.insert(
                    "coins".to_string(),
                    json!(number(gamer.get("coins")) + reward),
                );
                gamer.insert(
                    "exp".to_string(),
                    json!(number(gamer.get("exp")) + reward * 100.0),
                );
            }
        }
        "ProjectStatusChanged" | "ProjectDeleted" => {
            root.entry("extensions")
                .or_insert_with(|| Value::Object(Map::new()))
                .as_object_mut()
                .ok_or_else(|| "Game extensions are not an object".to_string())?
                .entry("lifecycle_events")
                .or_insert_with(|| Value::Array(Vec::new()))
                .as_array_mut()
                .ok_or_else(|| "Game lifecycle journal is not an array".to_string())?
                .push(Value::String(event_id.to_string()));
        }
        other => return Err(format!("unsupported Game event: {other}")),
    }
    Ok(())
}

pub fn process_pending_events(
    connection: &mut Connection,
    limit: i64,
) -> Result<ProcessSummary, String> {
    let transaction = connection
        .transaction()
        .map_err(|error| error.to_string())?;
    let mut statement = transaction
        .prepare("SELECT event_id,event_type,project_id,delta_symbols,context_json,version,attempt_count FROM domain_events WHERE consumer='game' AND processed_at IS NULL AND status != 'failed' ORDER BY created_at,event_id LIMIT ?1")
        .map_err(|error| error.to_string())?;
    let rows: Vec<(String, String, String, Option<f64>, String, i64, i64)> = statement
        .query_map([limit.max(1)], |row| {
            Ok((
                row.get(0)?,
                row.get(1)?,
                row.get(2)?,
                row.get(3)?,
                row.get(4)?,
                row.get(5)?,
                row.get(6)?,
            ))
        })
        .map_err(|error| error.to_string())?
        .collect::<Result<_, _>>()
        .map_err(|error| error.to_string())?;
    drop(statement);

    let mut summary = ProcessSummary::default();
    for (event_id, event_type, project_id, delta, context_json, version, attempts) in rows {
        let result = (|| {
            if version != EVENT_VERSION {
                return Err(format!("unsupported event version: {version}"));
            }
            let context: Value =
                serde_json::from_str(&context_json).map_err(|error| error.to_string())?;
            let context = context
                .as_object()
                .ok_or_else(|| "event context is not an object".to_string())?;
            let raw_state: String = transaction
                .query_row(
                    "SELECT payload_json FROM game_state WHERE id=1",
                    [],
                    |row| row.get(0),
                )
                .map_err(|error| error.to_string())?;
            let mut state: Value =
                serde_json::from_str(&raw_state).map_err(|error| error.to_string())?;
            apply_event(
                &mut state,
                &event_type,
                &event_id,
                delta.unwrap_or(0.0),
                context,
                &project_id,
            )?;
            transaction.execute(
                "UPDATE game_state SET schema_version=?1,payload_json=?2,updated_at=strftime('%Y-%m-%dT%H:%M:%SZ','now') WHERE id=1",
                params![STATE_VERSION, state.to_string()],
            ).map_err(|error| error.to_string())?;
            transaction.execute(
                "UPDATE domain_events SET processed_at=strftime('%Y-%m-%dT%H:%M:%SZ','now'),status='processed',last_error=NULL WHERE event_id=?1 AND processed_at IS NULL",
                [&event_id],
            ).map_err(|error| error.to_string())?;
            Ok(())
        })();
        match result {
            Ok(()) => summary.processed += 1,
            Err(error) => {
                let next_attempt = attempts + 1;
                let poison = next_attempt >= 3;
                transaction.execute(
                    "UPDATE domain_events SET attempt_count=?1,last_error=?2,failed_at=CASE WHEN ?3 THEN strftime('%Y-%m-%dT%H:%M:%SZ','now') ELSE failed_at END,status=CASE WHEN ?3 THEN 'failed' ELSE 'pending' END WHERE event_id=?4",
                    params![next_attempt, error.chars().take(1000).collect::<String>(), poison as i64, event_id],
                ).map_err(|db_error| db_error.to_string())?;
                summary.failed += 1;
            }
        }
    }
    transaction.commit().map_err(|error| error.to_string())?;
    Ok(summary)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn progress_event_is_deterministic_and_completion_is_idempotent() {
        let mut state = json!({"gamer":{"coins":0,"exp":0,"complete_bonus_projects":[]}});
        apply_event(
            &mut state,
            "ProgressAdded",
            "p",
            100.0,
            &Map::new(),
            "project",
        )
        .unwrap();
        let context =
            serde_json::from_value(json!({"key":"project","total_symbols":1000})).unwrap();
        apply_event(
            &mut state,
            "ProjectCompleted",
            "c",
            0.0,
            &context,
            "project",
        )
        .unwrap();
        let once = state.clone();
        apply_event(
            &mut state,
            "ProjectCompleted",
            "c",
            0.0,
            &context,
            "project",
        )
        .unwrap();
        assert_eq!(state, once);
    }
}
