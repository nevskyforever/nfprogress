use rusqlite::Connection;
use serde_json::{Map, Value};

fn date_days(value: &str) -> Option<i64> {
    let date = value.get(..10)?;
    let year = date.get(0..4)?.parse::<i64>().ok()?;
    let month = date.get(5..7)?.parse::<i64>().ok()?;
    let day = date.get(8..10)?.parse::<i64>().ok()?;
    if date.as_bytes().get(4) != Some(&b'-')
        || date.as_bytes().get(7) != Some(&b'-')
        || !(1..=12).contains(&month)
        || !(1..=31).contains(&day)
    {
        return None;
    }
    let adjusted_year = year - i64::from(month <= 2);
    let era = (if adjusted_year >= 0 {
        adjusted_year
    } else {
        adjusted_year - 399
    }) / 400;
    let year_of_era = adjusted_year - era * 400;
    let month_prime = month + if month > 2 { -3 } else { 9 };
    let day_of_year = (153 * month_prime + 2) / 5 + day - 1;
    let day_of_era = year_of_era * 365 + year_of_era / 4 - year_of_era / 100 + day_of_year;
    Some(era * 146_097 + day_of_era - 719_468)
}

fn date_from_days(days: i64) -> String {
    let z = days + 719_468;
    let era = (if z >= 0 { z } else { z - 146_096 }) / 146_097;
    let day_of_era = z - era * 146_097;
    let year_of_era =
        (day_of_era - day_of_era / 1_460 + day_of_era / 36_524 - day_of_era / 146_096) / 365;
    let year = year_of_era + era * 400;
    let day_of_year = day_of_era - (365 * year_of_era + year_of_era / 4 - year_of_era / 100);
    let month_prime = (5 * day_of_year + 2) / 153;
    let day = day_of_year - (153 * month_prime + 2) / 5 + 1;
    let month = month_prime + if month_prime < 10 { 3 } else { -9 };
    let year = year + i64::from(month <= 2);
    format!("{year:04}-{month:02}-{day:02}")
}

fn normalized_time(value: &str) -> Option<&str> {
    let time = value.get(..8)?;
    let hour = time.get(0..2)?.parse::<u8>().ok()?;
    let minute = time.get(3..5)?.parse::<u8>().ok()?;
    let second = time.get(6..8)?.parse::<u8>().ok()?;
    (time.as_bytes().get(2) == Some(&b':')
        && time.as_bytes().get(5) == Some(&b':')
        && hour < 24
        && minute < 60
        && second < 60)
        .then_some(time)
}

pub(crate) fn logical_writing_day_from(now: &str, start_day_time: &str) -> Option<String> {
    let calendar_day = now.get(..10)?;
    let current_time = normalized_time(now.get(11..)?)?;
    let start_time = normalized_time(start_day_time).unwrap_or("00:00:00");
    let days = date_days(calendar_day)? - i64::from(current_time < start_time);
    Some(date_from_days(days))
}

fn configured_now(connection: &Connection) -> Option<String> {
    if !crate::developer_mode_available() {
        return None;
    }
    let raw = connection
        .query_row(
            "SELECT payload_json FROM game_state WHERE id=1",
            [],
            |row| row.get::<_, String>(0),
        )
        .ok()?;
    let state = serde_json::from_str::<Value>(&raw).ok()?;
    state
        .get("game")
        .and_then(|value| value.get("extensions"))
        .or_else(|| state.get("extensions"))
        .and_then(|value| value.get("developer_clock"))
        .filter(|value| value.get("enabled").and_then(Value::as_bool) == Some(true))
        .and_then(|value| value.get("datetime"))
        .and_then(Value::as_str)
        .map(str::to_string)
}

pub(crate) fn logical_writing_day(connection: &Connection) -> Result<String, String> {
    let now = if let Some(now) = configured_now(connection) {
        now
    } else {
        connection
            .query_row(
                "SELECT strftime('%Y-%m-%dT%H:%M:%S','now','localtime')",
                [],
                |row| row.get(0),
            )
            .map_err(|error| error.to_string())?
    };
    let start_day_time = connection
        .query_row(
            "SELECT value_json FROM settings WHERE key='start_day_time'",
            [],
            |row| row.get::<_, String>(0),
        )
        .ok()
        .and_then(|value| serde_json::from_str::<String>(&value).ok())
        .unwrap_or_else(|| "00:00:00".to_string());
    logical_writing_day_from(&now, &start_day_time)
        .ok_or_else(|| "Не удалось определить текущий писательский день.".to_string())
}

fn streak_summary(streaks: Option<&Value>) -> (Option<i64>, usize, bool) {
    let mut current_day = None;
    let mut length = 0;
    let mut last_is_freeze = false;
    for entry in streaks.and_then(Value::as_array).into_iter().flatten() {
        match entry.as_str() {
            Some("freeze") if current_day.is_some() => {
                current_day = current_day.map(|day| day + 1);
                length += 1;
                last_is_freeze = true;
            }
            Some(value) => {
                if let Some(day) = date_days(value) {
                    current_day = Some(day);
                    length += 1;
                    last_is_freeze = false;
                }
            }
            None => {}
        }
    }
    (current_day, length, last_is_freeze)
}

fn canonical_status(fields: &Map<String, Value>, logical_day: &str) -> String {
    let saved = fields
        .get("streak_status")
        .and_then(Value::as_str)
        .unwrap_or("No");
    if matches!(saved, "Off" | "Complete") {
        return saved.to_string();
    }
    let Some(today) = date_days(logical_day) else {
        return saved.to_string();
    };
    let (last_day, length, last_is_freeze) = streak_summary(fields.get("streaks"));
    if last_day == Some(today) {
        if last_is_freeze {
            return "Freeze".to_string();
        }
        if saved.starts_with("Lose ") && saved.split_whitespace().count() == 3 {
            return saved.to_string();
        }
        return if length > 1 { "Go" } else { "Start" }.to_string();
    }
    if let Some(last_day) = last_day {
        if last_day == today - 1 || last_day > today {
            return "Active".to_string();
        }
        return format!("Lose {length}");
    }
    let lost_today = fields
        .get("last_streak_lost_date")
        .and_then(Value::as_str)
        .and_then(date_days)
        == Some(today);
    if saved.starts_with("Lose ") && saved.split_whitespace().count() == 2 && lost_today {
        return saved.to_string();
    }
    "No".to_string()
}

pub(crate) fn canonical_local_status(
    fields: &Map<String, Value>,
    logical_day: &str,
    entity: &Map<String, Value>,
) -> String {
    if entity.get("status").and_then(Value::as_str) == Some("завершен") {
        return "Complete".to_string();
    }
    if entity.get("streak_enabled").and_then(Value::as_bool) == Some(false) {
        return "Off".to_string();
    }
    canonical_status(fields, logical_day)
}

pub(crate) fn canonical_global_status(fields: &Map<String, Value>, logical_day: &str) -> String {
    let normalized = Map::from_iter([
        (
            "streak_status".to_string(),
            fields
                .get("global_streak_status")
                .cloned()
                .unwrap_or_else(|| Value::String("No".to_string())),
        ),
        (
            "streaks".to_string(),
            fields
                .get("global_streaks")
                .cloned()
                .unwrap_or_else(|| Value::Array(Vec::new())),
        ),
        (
            "last_streak_lost_date".to_string(),
            fields
                .get("last_global_streak_lost_date")
                .cloned()
                .unwrap_or(Value::Null),
        ),
    ]);
    canonical_status(&normalized, logical_day)
}

#[cfg(test)]
mod tests {
    use super::*;
    use rusqlite::params;
    use serde_json::json;

    fn status(saved: &str, streaks: Value, today: &str) -> String {
        canonical_status(
            json!({"streak_status": saved, "streaks": streaks})
                .as_object()
                .unwrap(),
            today,
        )
    }

    #[test]
    fn daily_statuses_are_valid_only_on_their_logical_day() {
        assert_eq!(status("Go", json!(["2026-09-18"]), "2026-09-19"), "Active");
        assert_eq!(
            status("Start", json!(["2026-09-18"]), "2026-09-19"),
            "Active"
        );
        assert_eq!(
            status("Start", json!(["2026-09-19"]), "2026-09-19"),
            "Start"
        );
        assert_eq!(
            status("Go", json!(["2026-09-18", "2026-09-19"]), "2026-09-19"),
            "Go"
        );
        assert_eq!(status("Go", json!(["2026-09-17"]), "2026-09-19"), "Lose 1");
    }

    #[test]
    fn clock_forward_and_rollback_never_reuse_a_daily_status() {
        assert_eq!(status("Go", json!(["2026-09-19"]), "2026-09-20"), "Active");
        assert_eq!(status("Go", json!(["2026-09-19"]), "2026-09-18"), "Active");
    }

    #[test]
    fn global_status_uses_the_same_logical_day_rule() {
        let global = json!({
            "global_streak_status": "Go",
            "global_streaks": ["2026-09-18"],
        });
        assert_eq!(
            canonical_global_status(global.as_object().unwrap(), "2026-09-19"),
            "Active"
        );
    }

    #[test]
    fn freeze_loss_complete_and_off_keep_canonical_semantics() {
        assert_eq!(
            status("Freeze", json!(["2026-09-18", "freeze"]), "2026-09-19"),
            "Freeze"
        );
        let loss = json!({
            "streak_status": "Lose 4",
            "streaks": [],
            "last_streak_lost_date": "2026-09-19",
        });
        assert_eq!(
            canonical_status(loss.as_object().unwrap(), "2026-09-19"),
            "Lose 4"
        );
        assert_eq!(
            status("Complete", json!(["2026-09-18"]), "2026-09-19"),
            "Complete"
        );
        assert_eq!(status("Off", json!(["2026-09-18"]), "2026-09-19"), "Off");
    }

    #[test]
    fn developer_datetime_defines_the_logical_writing_day() {
        let connection = Connection::open_in_memory().unwrap();
        connection
            .execute_batch(
                "CREATE TABLE settings(key TEXT PRIMARY KEY,value_json TEXT NOT NULL);\
                 CREATE TABLE game_state(id INTEGER PRIMARY KEY,payload_json TEXT NOT NULL);",
            )
            .unwrap();
        connection
            .execute(
                "INSERT INTO settings(key,value_json) VALUES('start_day_time',?1)",
                [json!("06:00:00").to_string()],
            )
            .unwrap();
        connection
            .execute(
                "INSERT INTO game_state(id,payload_json) VALUES(1,?1)",
                params![json!({"extensions":{"developer_clock":{"enabled":true,"datetime":"2040-03-10T05:30:00"}}}).to_string()],
            )
            .unwrap();

        assert_eq!(logical_writing_day(&connection).unwrap(), "2040-03-09");
    }
}
