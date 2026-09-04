//! Deterministic Game event application at the trusted desktop boundary.
//!
//! The event consumer deliberately accepts the versioned JSON DTO rather than
//! a Rust-struct serialization.  This keeps migration payloads compatible with
//! the Python oracle and makes unknown Game fields round-trip untouched.

use rusqlite::{params, Connection};
use serde_json::{json, Map, Value};

const EVENT_VERSION: i64 = 1;
const STATE_VERSION: i64 = 2;
const MAX_ITEM_COUNT: i64 = 10_000;
const MAX_MONEY: f64 = 1_000_000_000_000.0;

/// The only randomness used by the native Game application layer is supplied
/// through this small port. Production uses the OS provider; unit tests can
/// pass a fixed sequence without touching a global RNG.
pub trait GameRng {
    fn uniform_u32(&mut self, upper_exclusive: u32) -> u32;
}

#[derive(Default)]
pub struct OsGameRng;

impl GameRng for OsGameRng {
    fn uniform_u32(&mut self, upper_exclusive: u32) -> u32 {
        if upper_exclusive == 0 {
            return 0;
        }
        let mut bytes = [0_u8; 4];
        if getrandom::fill(&mut bytes).is_err() {
            return 0;
        }
        u32::from_le_bytes(bytes) % upper_exclusive
    }
}

#[derive(Debug, Clone, serde::Serialize)]
#[serde(tag = "code", content = "message")]
pub enum GameError {
    InsufficientFunds(String),
    InvalidQuantity(String),
    AlreadyClaimed(String),
    PrerequisiteMissing(String),
    NotFound(String),
    CooldownActive(String),
    InvalidState(String),
    Database(String),
    Validation(String),
}

impl std::fmt::Display for GameError {
    fn fmt(&self, formatter: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::InsufficientFunds(message)
            | Self::InvalidQuantity(message)
            | Self::AlreadyClaimed(message)
            | Self::PrerequisiteMissing(message)
            | Self::NotFound(message)
            | Self::CooldownActive(message)
            | Self::InvalidState(message)
            | Self::Database(message)
            | Self::Validation(message) => formatter.write_str(message),
        }
    }
}

type GameResult<T> = Result<T, GameError>;

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
            gamer.insert("coins".to_string(), json!(coins));
            add_experience(
                gamer,
                rounded_increment(delta / 100.0 * 500.0 * gamer_cf(gamer, "exp") * multiplier),
            );
            gamer.insert("writing_reward_bonus".to_string(), json!(0.0));
            if let Some(session) = gamer
                .get_mut("writing_session")
                .and_then(Value::as_object_mut)
            {
                let progress = number_field(session, "progress", 0.0) + delta;
                session.insert("progress".into(), json!(progress));
            }
            if let Some(daily) = gamer
                .get_mut("daily_challenge")
                .and_then(Value::as_object_mut)
            {
                if daily
                    .get("type")
                    .and_then(Value::as_str)
                    .unwrap_or("symbols")
                    == "symbols"
                    && daily.get("completed").and_then(Value::as_bool) != Some(true)
                {
                    let progress = number_field(daily, "progress", 0.0) + delta;
                    let target = number_field(daily, "target", f64::MAX);
                    daily.insert("progress".into(), json!(progress));
                    if progress >= target {
                        daily.insert("completed".into(), json!(true));
                        add_number(gamer, "coins", 100.0);
                        add_experience(gamer, 300.0);
                        add_capped(gamer, "inspiration", 10.0, 100.0);
                    }
                }
            }
            if let Some(weekly) = gamer
                .get_mut("weekly_challenge")
                .and_then(Value::as_object_mut)
            {
                if weekly.get("key").and_then(Value::as_str).unwrap_or("") == "symbols"
                    && weekly.get("completed").and_then(Value::as_bool) != Some(true)
                {
                    let progress = number_field(weekly, "progress", 0.0) + delta;
                    let target = 10_000.0;
                    weekly.insert("progress".into(), json!(progress));
                    if progress >= target {
                        weekly.insert("completed".into(), json!(true));
                        add_number(gamer, "coins", 500.0);
                        add_experience(gamer, 1500.0);
                        add_capped(gamer, "inspiration", 20.0, 100.0);
                    }
                }
            }
            let productive = integer_field(gamer, "productive_actions_since_event", 0) + 1;
            if productive >= 3 && gamer.get("pending_creative_event").is_none() {
                gamer.insert("pending_creative_event".into(), json!("unexpected_idea"));
                gamer.insert("productive_actions_since_event".into(), json!(0));
            } else {
                gamer.insert("productive_actions_since_event".into(), json!(productive));
            }
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
                add_experience(gamer, reward * 100.0);
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

#[derive(Clone, Copy)]
struct CatalogItem {
    category: &'static str,
    key: &'static str,
    price: f64,
    level: i64,
    maximum: Option<i64>,
    usable: bool,
    buyable: bool,
    sellable: bool,
    credit_allowed: bool,
}

// Catalog keys are save-format data. Display metadata may evolve, while this
// list intentionally remains a Rust-owned, immutable catalog during F4.
const CATALOG: &[CatalogItem] = &[
    CatalogItem {
        category: "Зелья",
        key: "Микро зелье здоровья",
        price: 29.0,
        level: 1,
        maximum: None,
        usable: true,
        buyable: true,
        sellable: true,
        credit_allowed: true,
    },
    CatalogItem {
        category: "Зелья",
        key: "Малое зелье здоровья",
        price: 58.0,
        level: 1,
        maximum: None,
        usable: true,
        buyable: true,
        sellable: true,
        credit_allowed: true,
    },
    CatalogItem {
        category: "Зелья",
        key: "Среднее зелье здоровья",
        price: 145.0,
        level: 1,
        maximum: None,
        usable: true,
        buyable: true,
        sellable: true,
        credit_allowed: true,
    },
    CatalogItem {
        category: "Зелья",
        key: "Большое зелье здоровья",
        price: 290.0,
        level: 1,
        maximum: None,
        usable: true,
        buyable: true,
        sellable: true,
        credit_allowed: true,
    },
    CatalogItem {
        category: "Зелья",
        key: "Зелье воскрешения",
        price: 580.0,
        level: 3,
        maximum: None,
        usable: true,
        buyable: true,
        sellable: true,
        credit_allowed: true,
    },
    CatalogItem {
        category: "Зелья",
        key: "Зелье вдохновения",
        price: 217.5,
        level: 2,
        maximum: None,
        usable: true,
        buyable: true,
        sellable: true,
        credit_allowed: true,
    },
    CatalogItem {
        category: "Зелья",
        key: "Искра вдохновения",
        price: 101.5,
        level: 1,
        maximum: Some(10),
        usable: true,
        buyable: true,
        sellable: true,
        credit_allowed: true,
    },
    CatalogItem {
        category: "Зелья",
        key: "Большое зелье вдохновения",
        price: 507.5,
        level: 5,
        maximum: None,
        usable: true,
        buyable: true,
        sellable: true,
        credit_allowed: true,
    },
    CatalogItem {
        category: "Зелья",
        key: "Эликсир вдохновения",
        price: 942.5,
        level: 8,
        maximum: Some(3),
        usable: true,
        buyable: true,
        sellable: true,
        credit_allowed: true,
    },
    CatalogItem {
        category: "Зелья",
        key: "Часовое зелье познания",
        price: 290.0,
        level: 2,
        maximum: None,
        usable: true,
        buyable: true,
        sellable: true,
        credit_allowed: true,
    },
    CatalogItem {
        category: "Зелья",
        key: "Суточное зелье познания",
        price: 3480.0,
        level: 4,
        maximum: None,
        usable: true,
        buyable: true,
        sellable: true,
        credit_allowed: true,
    },
    CatalogItem {
        category: "Зелья",
        key: "Недельное зелье познания",
        price: 15660.0,
        level: 6,
        maximum: None,
        usable: true,
        buyable: true,
        sellable: true,
        credit_allowed: true,
    },
    CatalogItem {
        category: "Зелья",
        key: "Часовое зелье доходности",
        price: 3185.7,
        level: 2,
        maximum: None,
        usable: true,
        buyable: true,
        sellable: true,
        credit_allowed: true,
    },
    CatalogItem {
        category: "Зелья",
        key: "Суточное зелье доходности",
        price: 4411.0,
        level: 4,
        maximum: None,
        usable: true,
        buyable: true,
        sellable: true,
        credit_allowed: true,
    },
    CatalogItem {
        category: "Зелья",
        key: "Недельное зелье доходности",
        price: 29759.1,
        level: 6,
        maximum: None,
        usable: true,
        buyable: true,
        sellable: true,
        credit_allowed: true,
    },
    CatalogItem {
        category: "Зелья",
        key: "Часовое зелье просвещения",
        price: 2900.0,
        level: 8,
        maximum: None,
        usable: true,
        buyable: true,
        sellable: true,
        credit_allowed: true,
    },
    CatalogItem {
        category: "Зелья",
        key: "Суточное зелье просвещения",
        price: 34800.0,
        level: 10,
        maximum: None,
        usable: true,
        buyable: true,
        sellable: true,
        credit_allowed: true,
    },
    CatalogItem {
        category: "Зелья",
        key: "Недельное зелье просвещения",
        price: 156600.0,
        level: 12,
        maximum: None,
        usable: true,
        buyable: true,
        sellable: true,
        credit_allowed: true,
    },
    CatalogItem {
        category: "Зелья",
        key: "Часовое зелье супердоходности",
        price: 63713.2,
        level: 15,
        maximum: None,
        usable: true,
        buyable: true,
        sellable: true,
        credit_allowed: true,
    },
    CatalogItem {
        category: "Зелья",
        key: "Суточное зелье супердоходности",
        price: 88218.3,
        level: 18,
        maximum: None,
        usable: true,
        buyable: true,
        sellable: true,
        credit_allowed: true,
    },
    CatalogItem {
        category: "Зелья",
        key: "Недельное зелье супердоходности",
        price: 595180.3,
        level: 21,
        maximum: None,
        usable: true,
        buyable: true,
        sellable: true,
        credit_allowed: true,
    },
    CatalogItem {
        category: "Предметы",
        key: "Заморозка",
        price: 85074.3,
        level: 3,
        maximum: Some(2),
        usable: true,
        buyable: true,
        sellable: true,
        credit_allowed: true,
    },
    CatalogItem {
        category: "Предметы",
        key: "Чернильница потока",
        price: 435.0,
        level: 3,
        maximum: None,
        usable: true,
        buyable: true,
        sellable: true,
        credit_allowed: true,
    },
    CatalogItem {
        category: "Предметы",
        key: "Компас рукописи",
        price: 652.5,
        level: 4,
        maximum: None,
        usable: true,
        buyable: true,
        sellable: true,
        credit_allowed: true,
    },
    CatalogItem {
        category: "Предметы",
        key: "Учебник мастерства",
        price: 696.0,
        level: 4,
        maximum: Some(5),
        usable: true,
        buyable: true,
        sellable: true,
        credit_allowed: true,
    },
    CatalogItem {
        category: "Предметы",
        key: "Жетон новой цели",
        price: 261.0,
        level: 2,
        maximum: Some(3),
        usable: true,
        buyable: true,
        sellable: true,
        credit_allowed: true,
    },
    CatalogItem {
        category: "Предметы",
        key: "Нить ритуала",
        price: 522.0,
        level: 3,
        maximum: Some(3),
        usable: true,
        buyable: true,
        sellable: true,
        credit_allowed: true,
    },
    CatalogItem {
        category: "Предметы",
        key: "Медаль качества",
        price: 754.0,
        level: 5,
        maximum: Some(2),
        usable: true,
        buyable: true,
        sellable: true,
        credit_allowed: true,
    },
    CatalogItem {
        category: "Предметы",
        key: "Лотерейный билет",
        price: 29.0,
        level: 3,
        maximum: None,
        usable: true,
        buyable: true,
        sellable: true,
        credit_allowed: false,
    },
    CatalogItem {
        category: "Предметы",
        key: "Печатная машинка Хемингуэя",
        price: 14500.0,
        level: 5,
        maximum: Some(1),
        usable: false,
        buyable: true,
        sellable: true,
        credit_allowed: true,
    },
    CatalogItem {
        category: "Предметы",
        key: "Ноутбук Роалинг",
        price: 72500.0,
        level: 10,
        maximum: Some(1),
        usable: false,
        buyable: true,
        sellable: true,
        credit_allowed: true,
    },
    CatalogItem {
        category: "Предметы",
        key: "Литературный раб",
        price: 145000.0,
        level: 20,
        maximum: None,
        usable: false,
        buyable: true,
        sellable: true,
        credit_allowed: true,
    },
    CatalogItem {
        category: "Предметы",
        key: "Амулет восстановления",
        price: 29000.0,
        level: 10,
        maximum: Some(1),
        usable: false,
        buyable: true,
        sellable: true,
        credit_allowed: true,
    },
];

fn game_object(value: &mut Value) -> GameResult<&mut Map<String, Value>> {
    value
        .as_object_mut()
        .ok_or_else(|| GameError::InvalidState("Game state is not an object".into()))
}

fn gamer_object(root: &mut Value) -> GameResult<&mut Map<String, Value>> {
    let root = game_object(root)?;
    let gamer = root
        .entry("gamer")
        .or_insert_with(|| Value::Object(Map::new()));
    game_object(gamer)
}

fn number_field(object: &Map<String, Value>, key: &str, default: f64) -> f64 {
    object
        .get(key)
        .and_then(Value::as_f64)
        .filter(|value| value.is_finite())
        .unwrap_or(default)
}

fn integer_field(object: &Map<String, Value>, key: &str, default: i64) -> i64 {
    number_field(object, key, default as f64).round() as i64
}

fn rounded_money(value: f64) -> f64 {
    (value * 10.0).round() / 10.0
}

fn checked_positive(value: f64, label: &str) -> GameResult<f64> {
    if value.is_finite() && value > 0.0 && value <= MAX_MONEY {
        Ok(rounded_money(value))
    } else {
        Err(GameError::Validation(format!(
            "{label} must be finite, positive and bounded"
        )))
    }
}

fn checked_nonnegative(value: f64, label: &str) -> GameResult<f64> {
    if value.is_finite() && value >= 0.0 && value <= MAX_MONEY {
        Ok(rounded_money(value))
    } else {
        Err(GameError::Validation(format!(
            "{label} must be finite, non-negative and bounded"
        )))
    }
}

fn checked_count(value: i64) -> GameResult<i64> {
    if (1..=MAX_ITEM_COUNT).contains(&value) {
        Ok(value)
    } else {
        Err(GameError::InvalidQuantity(
            "Количество должно быть от 1 до 10000.".into(),
        ))
    }
}

fn object_map<'a>(object: &'a mut Map<String, Value>, key: &str) -> &'a mut Map<String, Value> {
    object
        .entry(key.to_string())
        .or_insert_with(|| Value::Object(Map::new()))
        .as_object_mut()
        .expect("new object")
}

fn item_map<'a>(gamer: &'a mut Map<String, Value>, category: &str) -> &'a mut Map<String, Value> {
    object_map(object_map(gamer, "items"), category)
}

fn item_count(gamer: &Map<String, Value>, category: &str, key: &str) -> i64 {
    gamer
        .get("items")
        .and_then(Value::as_object)
        .and_then(|items| items.get(category))
        .and_then(Value::as_object)
        .and_then(|items| items.get(key))
        .and_then(Value::as_i64)
        .unwrap_or(0)
        .max(0)
}

fn tagged_fields<'a>(value: &'a mut Value) -> Option<&'a mut Map<String, Value>> {
    value.as_object_mut()?.get_mut("fields")?.as_object_mut()
}

fn tagged_field<'a>(value: &'a Value, key: &str) -> Option<&'a Value> {
    value.as_object()?.get("fields")?.as_object()?.get(key)
}

fn tagged_fields_immutable(value: &Value) -> Option<&Map<String, Value>> {
    value.as_object()?.get("fields")?.as_object()
}

fn text_value(value: Option<&Value>, default: &str) -> String {
    value
        .and_then(|value| {
            value
                .as_str()
                .or_else(|| value.get("value").and_then(Value::as_str))
        })
        .unwrap_or(default)
        .to_string()
}

fn iso_epoch_seconds(value: &str) -> Option<i64> {
    let date_time = value.get(..19)?;
    let year = date_time.get(0..4)?.parse::<i64>().ok()?;
    let month = date_time.get(5..7)?.parse::<i64>().ok()?;
    let day = date_time.get(8..10)?.parse::<i64>().ok()?;
    let hour = date_time.get(11..13)?.parse::<i64>().ok()?;
    let minute = date_time.get(14..16)?.parse::<i64>().ok()?;
    let second = date_time.get(17..19)?.parse::<i64>().ok()?;
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
    let days = era * 146097 + day_of_era - 719468;
    Some(days * 86_400 + hour * 3_600 + minute * 60 + second)
}

fn iso_date_from_days(days: i64) -> String {
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

fn iso_timestamp_from_epoch(seconds: i64) -> String {
    let days = seconds.div_euclid(86_400);
    let day_seconds = seconds.rem_euclid(86_400);
    format!(
        "{}T{:02}:{:02}:{:02}Z",
        iso_date_from_days(days),
        day_seconds / 3_600,
        day_seconds / 60 % 60,
        day_seconds % 60
    )
}

fn session_projection(value: Option<&Value>, now: &str) -> Value {
    let Some(value) = value.filter(|value| !value.is_null()) else {
        return Value::Null;
    };
    let Some(object) = value.as_object() else {
        return Value::Null;
    };
    let started_at = text_value(object.get("started_at"), "");
    let duration = integer_field(object, "duration_minutes", 0).max(0);
    let started_epoch = iso_epoch_seconds(&started_at);
    let remaining = started_epoch
        .zip(iso_epoch_seconds(now))
        .map(|(started, current)| (started + duration * 60 - current).max(0))
        .unwrap_or(duration * 60);
    json!({
        "started_at": if started_at.is_empty() { Value::Null } else { json!(started_at) },
        "ends_at": started_epoch
            .map(|started| iso_timestamp_from_epoch(started + duration * 60))
            .map_or(Value::Null, Value::String),
        "duration_minutes": duration,
        "target_symbols": integer_field(object, "target_symbols", 0).max(0),
        "progress": number_field(object, "progress", 0.0).max(0.0),
        "intention": text_value(object.get("intention"), ""),
        "mode": text_value(object.get("mode"), "flow"),
        "remaining_seconds": remaining,
    })
}

fn bank_projection(gamer: &Map<String, Value>, level: i64) -> Value {
    let account = gamer.get("bank_account").and_then(tagged_fields_immutable);
    let credit = account
        .and_then(|fields| fields.get("credit"))
        .filter(|value| !value.is_null())
        .and_then(tagged_fields_immutable)
        .map(|fields| {
            let principal = number_field(fields, "credit_sum", 0.0).max(0.0);
            let paid = number_field(fields, "paid_amount", 0.0).max(0.0);
            let rate = number_field(fields, "interest_rate_on_loan", 2.0).max(0.0);
            let days = integer_field(fields, "days_until_return", 1).max(1);
            let daily_rate: f64 = rate / 100.0;
            let interest = if daily_rate == 0.0 {
                0.0
            } else {
                let growth = (1.0 + daily_rate).powi(days as i32);
                rounded_money(
                    (rounded_money(principal * daily_rate * growth / (growth - 1.0))
                        * days as f64)
                        - principal,
                )
            };
            let total = rounded_money(principal + interest);
            json!({"principal":principal,"interest_rate":rate,"interest":interest,"total":total,"remaining":(total-paid).max(0.0),"daily_payment":rounded_money((total/days as f64).max(0.0)),"status":"OK","opened_at":fields.get("take_date").map(|value| text_value(Some(value), "")),"return_date":Value::Null,"paid_amount":paid,"overdue_days":integer_field(fields,"total_overdue_days",0).max(0)})
        });
    let deposit = account
        .and_then(|fields| fields.get("deposit"))
        .filter(|value| !value.is_null())
        .and_then(tagged_fields_immutable)
        .map(|fields| {
            let principal = number_field(fields, "deposit_sum", 0.0).max(0.0);
            let rate = number_field(fields, "interest_rate_on_deposit", 1.0).max(0.0);
            let days = integer_field(fields, "days_until_return", 1).max(1);
            let interest = rounded_money(principal * ((1.0 + rate / 100.0).powi(days as i32) - 1.0));
            let available = number_field(fields, "interest", interest).max(0.0);
            json!({"principal":principal,"interest_rate":rate,"interest":interest,"total":rounded_money(principal+interest),"available_interest":available,"allow_interest_withdrawal":fields.get("allow_interest_withdrawal").and_then(Value::as_bool).unwrap_or(true),"status":"OK","opened_at":fields.get("give_date").map(|value| text_value(Some(value), "")),"return_date":Value::Null})
        });
    let credit_score = account
        .and_then(|fields| fields.get("credit_score"))
        .and_then(Value::as_i64)
        .unwrap_or(600);
    json!({"credit_score":credit_score,"credit_limit":0,"max_credit_days":36500,"credit_rate":2,"deposit_rate":1,"can_open_credit":level>=3 && credit.is_none(),"can_open_deposit":deposit.is_none() && number_field(gamer,"coins",0.0)>0.0,"credit":credit,"deposit":deposit,"credit_history_count":0,"deposit_history_count":0,"overdue_days_total":0})
}

fn skills_projection(gamer: &Map<String, Value>) -> Value {
    let names = [
        ("productivity", "Продуктивность", "exp"),
        ("profitability", "Доходность", "coins"),
        ("endurance", "Выносливость", "health_recovery"),
    ];
    let skills = gamer.get("skills").and_then(Value::as_object);
    let coefficients = gamer.get("cf").and_then(Value::as_object);
    let items = names
        .iter()
        .map(|(key, name, target)| {
            let points = skills
                .and_then(|values| values.get(*key))
                .and_then(Value::as_i64)
                .unwrap_or(0)
                .max(0);
            json!({"key":key,"name":name,"points":points,"target":target,"bonus":points as f64 * 0.25})
        })
        .collect::<Vec<_>>();
    let coefficient_items = ["coins", "exp", "health_recovery"]
        .iter()
        .map(|key| {
            let value = coefficients
                .and_then(|values| values.get(*key))
                .and_then(|value| value.get("value").or(Some(value)))
                .and_then(Value::as_f64)
                .unwrap_or(if *key == "health_recovery" { 0.0 } else { 1.0 });
            json!({"key":key,"name":key,"description":"","value":value,"base_value":value})
        })
        .collect::<Vec<_>>();
    json!({"available_points":integer_field(gamer,"available_skill_points",0).max(0),"points_per_level":2,"items":items,"coefficients":coefficient_items})
}

fn quest_projection(gamer: &Map<String, Value>) -> Value {
    let mut items = Vec::new();
    if let Some(quests) = gamer.get("quests").and_then(Value::as_array) {
        for (index, quest) in quests.iter().enumerate() {
            let fields = tagged_fields_immutable(quest).or_else(|| quest.as_object());
            let Some(fields) = fields else { continue };
            let id = text_value(fields.get("quest_id"), &format!("quest-{index}"));
            let status = text_value(fields.get("status"), "available").to_lowercase();
            items.push(json!({"id":id,"name":text_value(fields.get("name"),&id),"description":text_value(fields.get("description"),""),"status":status,"required_level":integer_field(fields,"level",1).max(1),"started_at":fields.get("start_date").map(|value| text_value(Some(value), "")),"finished_at":fields.get("end_date").map(|value| text_value(Some(value), "")),"reward":{"coins":number_field(fields,"reward_coins",0.0).max(0.0),"experience":number_field(fields,"reward_exp",0.0).max(0.0),"items":fields.get("reward_items").cloned().unwrap_or(json!([])),"buffs":fields.get("reward_buffs").cloned().unwrap_or(json!([]))}}));
        }
    }
    let mut by_status = Map::new();
    for status in ["available", "active", "completed"] {
        by_status.insert(
            status.into(),
            Value::Array(
                items
                    .iter()
                    .filter(|item| item["status"].as_str() == Some(status))
                    .cloned()
                    .collect(),
            ),
        );
    }
    json!({"items":items,"by_status":by_status})
}

fn custom_awards_projection(gamer: &Map<String, Value>) -> Value {
    let inventory = gamer
        .get("custom_awards_inventory")
        .and_then(Value::as_object);
    let items = gamer
        .get("custom_awards")
        .and_then(Value::as_array)
        .into_iter()
        .flat_map(|values| values.iter())
        .enumerate()
        .filter_map(|(index, award)| {
            let fields = tagged_fields_immutable(award)?;
            let id = text_value(fields.get("award_id"), &format!("custom-{index}"));
            let name = text_value(fields.get("name"), "Награда");
            let price = number_field(fields, "_price", 0.0).max(0.0);
            let count = inventory
                .and_then(|values| values.get(&name))
                .and_then(Value::as_i64)
                .unwrap_or(0)
                .max(0);
            Some(json!({"id":id,"name":name,"description":text_value(fields.get("description"),"Кастомная награда без эффекта"),"price":price,"sell_price":rounded_money(price*0.75),"count":count,"available_in_shop":fields.get("available_in_shop").and_then(Value::as_bool).unwrap_or(true),"sellable":fields.get("sellable").and_then(Value::as_bool).unwrap_or(true),"usable":true,"can_buy":number_field(gamer,"coins",0.0)>=price}))
        })
        .collect::<Vec<_>>();
    json!({"items":items})
}

fn buffs_projection(gamer: &Map<String, Value>, now: &str) -> Value {
    let mut positive = Vec::new();
    let mut negative = Vec::new();
    if let Some(buffs) = gamer.get("buffs").and_then(Value::as_array) {
        for buff in buffs {
            let Some(fields) = tagged_fields_immutable(buff) else {
                continue;
            };
            let started_at = fields
                .get("start_time")
                .map(|value| text_value(Some(value), ""));
            let duration = integer_field(fields, "duration_minutes", 0).max(0);
            let remaining = started_at
                .as_deref()
                .and_then(iso_epoch_seconds)
                .zip(iso_epoch_seconds(now))
                .map(|(start, current)| (start + duration * 60 - current).max(0));
            if duration > 0 && remaining == Some(0) {
                continue;
            }
            let entry = json!({"name":text_value(fields.get("name"),"Эффект"),"description":text_value(fields.get("description"),""),"type":text_value(fields.get("buff_type"),"positive"),"target":text_value(fields.get("target_cf"),""),"value":number_field(fields,"value",0.0),"stacks":1,"duration_minutes":if duration > 0 { Some(duration) } else { None },"started_at":started_at,"expires_at":Value::Null,"remaining_seconds":remaining,"source":fields.get("source").map(|value| text_value(Some(value),"")),"stackable":fields.get("stackable").and_then(Value::as_bool).unwrap_or(false)});
            if text_value(fields.get("buff_type"), "positive") == "negative" {
                negative.push(entry);
            } else {
                positive.push(entry);
            }
        }
    }
    json!({"server_time":now,"positive":positive,"negative":negative})
}

fn catalog_item(category: &str, key: &str) -> Option<CatalogItem> {
    CATALOG
        .iter()
        .copied()
        .find(|item| item.category == category && item.key == key)
}

fn catalog_item_json(gamer: &Map<String, Value>, item: CatalogItem, include_count: bool) -> Value {
    let count = item_count(gamer, item.category, item.key);
    let mut result = json!({
        "id": format!("{}:{}", item.category, item.key), "key": item.key,
        "category": item.category, "name": item.key,
        "description": null, "price": item.price, "sell_price": rounded_money(item.price * 0.75),
        "level": item.level, "sellable": item.sellable, "usable": item.usable,
        "buy": item.buyable, "credit_allowed": item.credit_allowed,
        "maximum_quantity": item.maximum, "available_for_level": integer_field(gamer, "level", 1) >= item.level,
        "can_buy": item.buyable && integer_field(gamer, "level", 1) >= item.level
            && number_field(gamer, "coins", 0.0) >= item.price
            && item.maximum.map_or(true, |maximum| count < maximum), "known": true,
    });
    if include_count {
        result["count"] = json!(count);
    }
    result
}

fn notification_json(value: &Value, status: &str, index: usize) -> Value {
    let fields = value
        .as_object()
        .and_then(|object| object.get("fields"))
        .and_then(Value::as_object);
    json!({"id": text_value(fields.and_then(|fields| fields.get("notification_id")).or_else(|| fields.and_then(|fields| fields.get("id"))), &format!("legacy-{status}-{index}")), "text": text_value(fields.and_then(|fields| fields.get("text")), ""), "tag": fields.and_then(|fields| fields.get("tag")).and_then(Value::as_str), "created_at": fields.and_then(|fields| fields.get("date_create")).map(|value| value.to_string().trim_matches('"').to_string()), "status": status})
}

fn notifications_state(root: &Map<String, Value>) -> Value {
    let source = root.get("notifications").and_then(Value::as_object);
    let empty: Vec<Value> = Vec::new();
    let unread = source
        .and_then(|value| value.get("new"))
        .and_then(Value::as_array)
        .unwrap_or(&empty);
    let read = source
        .and_then(|value| value.get("read"))
        .and_then(Value::as_array)
        .unwrap_or(&empty);
    json!({"unread": unread.iter().enumerate().map(|(i, value)| notification_json(value, "new", i)).collect::<Vec<_>>(), "read": read.iter().enumerate().map(|(i, value)| notification_json(value, "read", i)).collect::<Vec<_>>(), "unread_count": unread.len()})
}

fn catalog_state(gamer: &Map<String, Value>, include_count: bool) -> Value {
    let mut categories: Vec<Value> = Vec::new();
    for category in ["Зелья", "Предметы"] {
        let items: Vec<Value> = CATALOG
            .iter()
            .filter(|item| item.category == category)
            .map(|item| catalog_item_json(gamer, *item, include_count))
            .collect();
        categories.push(json!({"key": category, "name": category, "items": items}));
    }
    json!({"categories": categories, "custom_awards": {"items": []}})
}

fn project_state(root: &Value, now: &str, enabled: bool) -> GameResult<Value> {
    let root_object = root
        .as_object()
        .ok_or_else(|| GameError::InvalidState("Game state is not an object".into()))?;
    let gamer = root_object
        .get("gamer")
        .and_then(Value::as_object)
        .ok_or_else(|| GameError::InvalidState("Gamer state is not an object".into()))?;
    let level = integer_field(gamer, "level", 1).clamp(1, 999);
    let max_health = integer_field(gamer, "max_health", 100).max(100);
    let next_level_experience = if level < 99 {
        Some(8_000.0 * (level as f64).powi(2))
    } else {
        None
    };
    let inventory = catalog_state(gamer, true);
    let notifications = notifications_state(root_object);
    let mut state = json!({
        "enabled": enabled, "server_time": now,
        "profile": {"level": level, "experience": number_field(gamer, "exp", 0.0).max(0.0), "next_level_experience": next_level_experience, "coins": number_field(gamer, "coins", 0.0).max(0.0), "inflation": number_field(gamer, "inflation", 1.0).max(1.0), "health": number_field(gamer, "health", max_health as f64).clamp(0.0, max_health as f64), "max_health": max_health, "inspiration": number_field(gamer, "inspiration", 0.0).clamp(0.0, 100.0), "max_inspiration": 100, "writing_session_streak": integer_field(gamer, "writing_session_streak", 0).max(0), "session_streak_shields": integer_field(gamer, "session_streak_shields", 0).clamp(0, 3), "session_grade_boosts": integer_field(gamer, "session_grade_boosts", 0).clamp(0, 1), "pending_bonuses": {"writing": number_field(gamer, "writing_reward_bonus", 0.0), "session": number_field(gamer, "session_reward_bonus", 0.0), "challenge": number_field(gamer, "challenge_reward_bonus", 0.0), "manuscript": number_field(gamer, "manuscript_reward_bonus", 0.0)}},
        "skills": skills_projection(gamer),
        "buffs": buffs_projection(gamer, now), "streak_freezes": {"date": now.get(..10).unwrap_or(now), "inventory_count": item_count(gamer, "Предметы", "Заморозка"), "global_available": false, "projects": []},
        "notifications": notifications, "inventory": inventory, "quests": quest_projection(gamer), "daily_challenge": {"change_cost": 15, "current": gamer.get("daily_challenge").cloned().unwrap_or(Value::Null), "options": gamer.get("daily_challenge_options").cloned().unwrap_or(json!([])), "history": gamer.get("daily_challenge_history").cloned().unwrap_or(json!([]))},
        "weekly_challenge": {"current": gamer.get("weekly_challenge").cloned().unwrap_or(Value::Null), "catalog": [{"key":"symbols","name":"Марафон","description":"Написать 10 000 символов за неделю.","target":10000,"reward":{"coins":500,"experience":1500,"inspiration":20}},{"key":"days","name":"Ритм","description":"Писать в четыре разных дня за неделю.","target":4,"reward":{"coins":400,"experience":1200,"inspiration":20}},{"key":"sessions","name":"Чистый поток","description":"Завершить пять успешных писательских сессий.","target":5,"reward":{"coins":450,"experience":1350,"inspiration":20}},{"key":"editing","name":"Редакторская неделя","description":"Завершить три успешные редакторские сессии.","target":3,"reward":{"coins":425,"experience":1300,"inspiration":20}}]},
        "writing_session": {"server_time": now, "active": session_projection(gamer.get("writing_session"), now), "streak": integer_field(gamer, "writing_session_streak", 0), "history": gamer.get("writing_session_history").cloned().unwrap_or(json!([])), "modes": [{"key":"sprint","name":"Спринт","description":"15 минут.","reward_bonus":0.15},{"key":"flow","name":"Поток","description":"Сбалансированный режим.","reward_bonus":0.0},{"key":"deep","name":"Глубокая работа","description":"45 или 60 минут.","reward_bonus":0.25},{"key":"editing","name":"Редакторский проход","description":"Учитывает изменение текста.","reward_bonus":0.20}], "grades": [{"key":"gold","name":"Золото","target_ratio":1.5,"reward_multiplier":1.3},{"key":"silver","name":"Серебро","target_ratio":1.25,"reward_multiplier":1.15},{"key":"bronze","name":"Бронза","target_ratio":1.0,"reward_multiplier":1.0}], "allowed_durations_minutes":[15,25,45,60]},
        "inspiration": {"abilities": [{"key":"creative_surge","name":"Творческий импульс","description":"+25% к следующей записи.","cost":30,"bonus":0.25,"active":number_field(gamer,"writing_reward_bonus",0.0)>0.0},{"key":"session_spark","name":"Искра сессии","description":"+25% к следующей сессии.","cost":25,"bonus":0.25,"active":number_field(gamer,"session_reward_bonus",0.0)>0.0},{"key":"challenge_focus","name":"Фокус испытания","description":"+25% к следующему испытанию.","cost":40,"bonus":0.25,"active":number_field(gamer,"challenge_reward_bonus",0.0)>0.0}], "creative_event": gamer.get("pending_creative_event").cloned().unwrap_or(Value::Null), "creative_event_history": gamer.get("creative_event_history").cloned().unwrap_or(json!([]))},
        "specializations": {"selected": gamer.get("specialization").cloned().unwrap_or(Value::Null), "unlocks_at_level":3,"change_cooldown_days":14,"change_days_remaining":0,"mastery_thresholds":[0,3,8,15,25],"items":[]}, "manuscripts":{"journeys":[],"milestones":[],"cabinet":{"relics":[],"sets":[]}}, "bank":bank_projection(gamer, level), "custom_awards":custom_awards_projection(gamer), "shop": catalog_state(gamer, true)
    });
    if let Some(items) = gamer.get("items").and_then(Value::as_object) {
        let inventory_categories = state["inventory"]["categories"]
            .as_array_mut()
            .expect("catalog categories");
        for (category, values) in items {
            if inventory_categories
                .iter()
                .any(|value| value["key"].as_str() == Some(category))
            {
                continue;
            }
            let rows: Vec<Value> = values.as_object().into_iter().flat_map(|values| values.iter()).filter(|(_, count)| count.as_i64().unwrap_or(0) > 0).map(|(key, count)| json!({"id":format!("{category}:{key}"),"key":key,"category":category,"name":key,"description":null,"count":count,"known":false,"usable":false,"buy":false,"sellable":false})).collect();
            inventory_categories.push(json!({"key":category,"name":category,"items":rows}));
        }
    }
    Ok(state)
}

pub struct GameApplicationService;

impl GameApplicationService {
    fn owner(connection: &Connection) -> GameResult<()> {
        let owner: String = connection
            .query_row(
                "SELECT owner FROM storage_ownership WHERE subsystem='game'",
                [],
                |row| row.get(0),
            )
            .map_err(|error| GameError::Database(error.to_string()))?;
        if owner == "sqlite" {
            Ok(())
        } else {
            Err(GameError::InvalidState(
                "Игра ещё не переведена в SQLite authoritative storage.".into(),
            ))
        }
    }

    fn load(connection: &Connection) -> GameResult<Value> {
        let raw: String = connection
            .query_row(
                "SELECT payload_json FROM game_state WHERE id=1",
                [],
                |row| row.get(0),
            )
            .map_err(|error| GameError::Database(error.to_string()))?;
        serde_json::from_str(&raw).map_err(|error| {
            GameError::InvalidState(format!("Некорректное состояние игры: {error}"))
        })
    }

    fn now(connection: &Connection) -> GameResult<String> {
        if let Ok(raw_state) = connection.query_row(
            "SELECT payload_json FROM game_state WHERE id=1",
            [],
            |row| row.get::<_, String>(0),
        ) {
            if let Ok(state) = serde_json::from_str::<Value>(&raw_state) {
                if let Some(datetime) = state
                    .get("game")
                    .and_then(|value| value.get("extensions"))
                    .and_then(|value| value.get("developer_clock"))
                    .filter(|value| value.get("enabled").and_then(Value::as_bool) == Some(true))
                    .and_then(|value| value.get("datetime"))
                    .and_then(Value::as_str)
                {
                    if iso_epoch_seconds(datetime).is_some() {
                        return Ok(datetime.to_string());
                    }
                }
            }
        }
        connection
            .query_row("SELECT strftime('%Y-%m-%dT%H:%M:%SZ','now')", [], |row| {
                row.get(0)
            })
            .map_err(|error| GameError::Database(error.to_string()))
    }

    fn enabled(connection: &Connection) -> bool {
        connection
            .query_row(
                "SELECT value_json FROM settings WHERE key='game_mode'",
                [],
                |row| row.get::<_, String>(0),
            )
            .ok()
            .and_then(|value| serde_json::from_str::<Value>(&value).ok())
            .and_then(|value| value.as_bool())
            .unwrap_or(true)
    }

    fn mutate<F>(mutator: F) -> GameResult<GameCommandResponse>
    where
        F: FnOnce(&mut Value, &mut OsGameRng, &str) -> GameResult<(Option<String>, Option<Value>)>,
    {
        let mut connection = crate::open_projects_database().map_err(GameError::Database)?;
        Self::owner(&connection)?;
        process_pending_events(&mut connection, 100).map_err(GameError::Database)?;
        if !Self::enabled(&connection) {
            return Err(GameError::PrerequisiteMissing(
                "Игровой режим отключён.".into(),
            ));
        }
        let tx = connection
            .transaction()
            .map_err(|error| GameError::Database(error.to_string()))?;
        let mut state = Self::load(&tx)?;
        let now = Self::now(&tx)?;
        let mut rng = OsGameRng;
        let (message, result) = mutator(&mut state, &mut rng, &now)?;
        tx.execute(
            "UPDATE game_state SET schema_version=?1,payload_json=?2,updated_at=?3 WHERE id=1",
            params![STATE_VERSION, state.to_string(), now],
        )
        .map_err(|error| GameError::Database(error.to_string()))?;
        let enabled = Self::enabled(&tx);
        tx.commit()
            .map_err(|error| GameError::Database(error.to_string()))?;
        let state = project_state(&state, &now, enabled)?;
        let messages = message.clone().into_iter().collect::<Vec<_>>();
        Ok(GameCommandResponse {
            ok: true,
            message,
            messages,
            result,
            state,
        })
    }

    pub fn state() -> GameResult<Value> {
        let mut connection = crate::open_projects_database().map_err(GameError::Database)?;
        Self::owner(&connection)?;
        process_pending_events(&mut connection, 100).map_err(GameError::Database)?;
        let now = Self::now(&connection)?;
        let enabled = Self::enabled(&connection);
        project_state(&Self::load(&connection)?, &now, enabled)
    }

    pub fn notifications() -> GameResult<Value> {
        let state = Self::state()?;
        Ok(state["notifications"].clone())
    }

    pub fn process_bank_events(_auto_pay: bool) -> GameResult<GameCommandResponse> {
        Self::mutate(|state, _rng, now| {
            let gamer = gamer_object(state)?;
            let matured = gamer
                .get("bank_account")
                .and_then(tagged_fields_immutable)
                .and_then(|fields| fields.get("deposit"))
                .filter(|value| !value.is_null())
                .and_then(tagged_fields_immutable)
                .and_then(|fields| {
                    let opened = text_value(fields.get("give_date"), "");
                    let days = integer_field(fields, "days_until_return", 1).max(1);
                    let principal = number_field(fields, "deposit_sum", 0.0).max(0.0);
                    let rate = number_field(fields, "interest_rate_on_deposit", 1.0).max(0.0);
                    let interest =
                        rounded_money(principal * ((1.0 + rate / 100.0).powi(days as i32) - 1.0));
                    iso_epoch_seconds(&opened)
                        .zip(iso_epoch_seconds(now))
                        .filter(|(opened, current)| *current >= *opened + days * 86_400)
                        .map(|_| (principal, interest))
                });

            let Some((principal, interest)) = matured else {
                return Ok((None, None));
            };
            let total = rounded_money(principal + interest);
            add_number(gamer, "coins", total);
            let bank = gamer
                .get_mut("bank_account")
                .and_then(tagged_fields)
                .ok_or_else(|| GameError::InvalidState("Некорректный банковский счёт.".into()))?;
            bank.insert("deposit".into(), Value::Null);
            array_mut(bank, "deposit_history").push(json!({
                "sum": principal,
                "interest": interest,
                "status": "auto_returned",
                "returned_date": now,
            }));
            Ok((
                Some(format!(
                    "Срок вклада завершен. На счет возвращено {total} монет."
                )),
                Some(json!({"amount":total,"interest":interest})),
            ))
        })
    }

    pub fn preview_bank_product(request: BankProductRequest) -> GameResult<GameCommandResponse> {
        let state = Self::state()?;
        let profile = state
            .get("profile")
            .and_then(Value::as_object)
            .ok_or_else(|| GameError::InvalidState("Профиль игры не найден.".into()))?;
        let amount = checked_positive(request.amount, "Сумма")?;
        if request.days <= 0 || request.days > 36_500 {
            return Err(GameError::Validation("Некорректный срок продукта.".into()));
        }
        let product_type = request.product_type.as_deref().unwrap_or("deposit");
        let rate = if product_type == "credit" { 2.0 } else { 1.0 };
        let interest = if product_type == "credit" {
            let daily_rate: f64 = rate / 100.0;
            let growth = (1.0 + daily_rate).powi(request.days as i32);
            rounded_money(
                rounded_money(amount * daily_rate * growth / (growth - 1.0)) * request.days as f64
                    - amount,
            )
        } else {
            rounded_money(amount * ((1.0 + rate / 100.0).powi(request.days as i32) - 1.0))
        };
        Ok(GameCommandResponse {
            ok: true,
            message: None,
            messages: Vec::new(),
            result: Some(
                json!({"amount":amount,"rate":rate,"interest":interest,"total":rounded_money(amount+interest),"limit":if product_type == "credit" { Some(number_field(profile,"coins",0.0)*10.0) } else { None }}),
            ),
            state,
        })
    }

    pub fn inventory(
        category: String,
        item_id: String,
        count: i64,
        operation: &str,
    ) -> GameResult<GameCommandResponse> {
        let count = checked_count(count)?;
        Self::mutate(move |state, rng, now| {
            let gamer = gamer_object(state)?;
            let item = catalog_item(&category, &item_id)
                .ok_or_else(|| GameError::NotFound("Предмет не найден.".into()))?;
            let current = item_count(gamer, &category, &item_id);
            match operation {
                "buy" => {
                    if !item.buyable {
                        return Err(GameError::PrerequisiteMissing(
                            "Этот предмет нельзя купить.".into(),
                        ));
                    }
                    if integer_field(gamer, "level", 1) < item.level {
                        return Err(GameError::PrerequisiteMissing(format!(
                            "Предмет доступен с {} уровня.",
                            item.level
                        )));
                    }
                    if item
                        .maximum
                        .is_some_and(|maximum| current + count > maximum)
                    {
                        return Err(GameError::InvalidQuantity(
                            "Достигнут лимит предмета в инвентаре.".into(),
                        ));
                    }
                    let total = rounded_money(item.price * count as f64);
                    let coins = number_field(gamer, "coins", 0.0);
                    if coins < total {
                        return Err(GameError::InsufficientFunds("Недостаточно монет!".into()));
                    }
                    gamer.insert("coins".into(), json!(rounded_money(coins - total)));
                    item_map(gamer, &category).insert(item_id.clone(), json!(current + count));
                    Ok((
                        Some(format!("Куплено: {} x{}.", item.key, count)),
                        Some(
                            json!({"category":category,"item_key":item.key,"count":count,"unit_price":item.price,"total_price":total}),
                        ),
                    ))
                }
                "sell" => {
                    if !item.sellable {
                        return Err(GameError::PrerequisiteMissing(
                            "Этот предмет нельзя продать.".into(),
                        ));
                    }
                    if current < count {
                        return Err(GameError::InvalidQuantity(format!(
                            "В инвентаре только {current} шт."
                        )));
                    }
                    let total = rounded_money(item.price * 0.75 * count as f64);
                    gamer.insert(
                        "coins".into(),
                        json!(rounded_money(number_field(gamer, "coins", 0.0) + total)),
                    );
                    let items = item_map(gamer, &category);
                    if current == count {
                        items.remove(&item_id);
                    } else {
                        items.insert(item_id.clone(), json!(current - count));
                    }
                    Ok((
                        Some(format!("Продано: {} x{}.", item.key, count)),
                        Some(
                            json!({"category":category,"item_key":item.key,"count":count,"unit_price":rounded_money(item.price*0.75),"total_price":total}),
                        ),
                    ))
                }
                "use" => Self::use_item_mutation(gamer, item, count, rng, now),
                _ => Err(GameError::Validation("Unknown inventory operation".into())),
            }
        })
    }

    fn use_item_mutation<R: GameRng>(
        gamer: &mut Map<String, Value>,
        item: CatalogItem,
        count: i64,
        rng: &mut R,
        now: &str,
    ) -> GameResult<(Option<String>, Option<Value>)> {
        let current = item_count(gamer, item.category, item.key);
        if !item.usable {
            return Err(GameError::PrerequisiteMissing(
                "Этот предмет нельзя использовать напрямую.".into(),
            ));
        }
        if current < count {
            return Err(GameError::InvalidQuantity(format!(
                "В инвентаре только {current} шт."
            )));
        }
        let items = item_map(gamer, item.category);
        if current == count {
            items.remove(item.key);
        } else {
            items.insert(item.key.into(), json!(current - count));
        }
        let mut result = json!({"category":item.category,"item_key":item.key,"count":count});
        for _ in 0..count {
            match item.key {
                "Микро зелье здоровья"
                | "Малое зелье здоровья"
                | "Среднее зелье здоровья"
                | "Большое зелье здоровья"
                | "Зелье воскрешения" => {
                    let amount = match item.key {
                        "Микро зелье здоровья" => 5.0,
                        "Малое зелье здоровья" => 10.0,
                        "Среднее зелье здоровья" => 25.0,
                        "Большое зелье здоровья" => 50.0,
                        _ => number_field(gamer, "max_health", 100.0),
                    };
                    let max = number_field(gamer, "max_health", 100.0);
                    gamer.insert(
                        "health".into(),
                        json!((number_field(gamer, "health", max) + amount).min(max)),
                    );
                }
                "Зелье вдохновения" => {
                    add_capped(gamer, "inspiration", 25.0, 100.0)
                }
                "Искра вдохновения" => {
                    add_capped(gamer, "inspiration", 10.0, 100.0)
                }
                "Большое зелье вдохновения" => {
                    add_capped(gamer, "inspiration", 50.0, 100.0)
                }
                "Эликсир вдохновения" => {
                    add_capped(gamer, "inspiration", 100.0, 100.0)
                }
                "Часовое зелье познания"
                | "Суточное зелье познания"
                | "Недельное зелье познания"
                | "Часовое зелье просвещения"
                | "Суточное зелье просвещения"
                | "Недельное зелье просвещения"
                | "Часовое зелье доходности"
                | "Суточное зелье доходности"
                | "Недельное зелье доходности"
                | "Часовое зелье супердоходности"
                | "Суточное зелье супердоходности"
                | "Недельное зелье супердоходности" => {
                    let (target, value) = if item.key.contains("доходности") {
                        if item.key.contains("супер") {
                            ("coins", 10.0)
                        } else {
                            ("coins", 0.5)
                        }
                    } else if item.key.contains("просвещения") {
                        ("exp", 10.0)
                    } else {
                        ("exp", 1.0)
                    };
                    let duration_minutes = if item.key.contains("Часовое") {
                        60
                    } else if item.key.contains("Суточное") {
                        1_440
                    } else {
                        10_080
                    };
                    array_mut(gamer, "buffs").push(json!({"__type__":"game_data.Buff","fields":{"name":item.key,"description":"Временный бонус предмета.","buff_type":"positive","target_cf":target,"value":value,"duration_minutes":duration_minutes,"start_time":now,"end_time":Value::Null,"source":item.key,"stackable":false}}));
                }
                "Чернильница потока" => {
                    add_capped(gamer, "session_reward_bonus", 0.25, 1.0)
                }
                "Компас рукописи" => {
                    add_capped(gamer, "manuscript_reward_bonus", 0.25, 1.0)
                }
                "Нить ритуала" => add_capped(gamer, "session_streak_shields", 1.0, 3.0),
                "Медаль качества" => {
                    add_capped(gamer, "session_grade_boosts", 1.0, 1.0)
                }
                "Учебник мастерства" => {
                    add_capped(gamer, "specialization_mastery_book_bonus", 2.0, 1000000.0)
                }
                "Лотерейный билет" => {
                    if !result.get("lottery_draws").is_some_and(Value::is_array) {
                        result["lottery_draws"] = json!([]);
                    }
                    let draw = lottery_draw(rng);
                    let prize = draw["prize"].as_f64().unwrap_or(0.0);
                    if prize > 0.0 {
                        add_number(gamer, "coins", prize);
                    }
                    result["lottery_draws"]
                        .as_array_mut()
                        .expect("array")
                        .push(draw.clone());
                    array_mut(gamer, "lottery_history").push(draw);
                }
                _ => {}
            }
        }
        let message = format!("Использовано: {} x{}.", item.key, count);
        Ok((Some(message), Some(result)))
    }

    pub fn run_lottery() -> GameResult<GameCommandResponse> {
        Self::inventory("Предметы".into(), "Лотерейный билет".into(), 1, "use")
    }
}

#[derive(Debug, serde::Deserialize)]
#[serde(deny_unknown_fields, rename_all = "camelCase")]
pub struct WritingSessionRequest {
    pub duration_minutes: i64,
    pub target_symbols: i64,
    pub intention: String,
    pub mode: String,
}

#[derive(Debug, serde::Deserialize)]
#[serde(deny_unknown_fields, rename_all = "camelCase")]
pub struct InventoryRequest {
    pub category: String,
    pub item_id: String,
    pub count: i64,
}

#[derive(Debug, serde::Deserialize)]
#[serde(deny_unknown_fields, rename_all = "camelCase")]
pub struct DailyChallengeRequest {
    pub option_id: String,
}

#[derive(Debug, serde::Deserialize)]
#[serde(deny_unknown_fields, rename_all = "camelCase")]
pub struct WeeklyChallengeRequest {
    pub challenge_id: String,
}

#[derive(Debug, serde::Deserialize)]
#[serde(deny_unknown_fields, rename_all = "camelCase")]
pub struct ChoiceRequest {
    pub choice: String,
}

#[derive(Debug, serde::Deserialize)]
#[serde(deny_unknown_fields, rename_all = "camelCase")]
pub struct NotificationRequest {
    pub notification_id: String,
}

#[derive(Debug, serde::Deserialize)]
#[serde(deny_unknown_fields, rename_all = "camelCase")]
pub struct AbilityRequest {
    pub ability_id: String,
}

#[derive(Debug, serde::Deserialize)]
#[serde(deny_unknown_fields, rename_all = "camelCase")]
pub struct SpecializationRequest {
    pub specialization_id: String,
}

#[derive(Debug, serde::Deserialize)]
#[serde(deny_unknown_fields, rename_all = "camelCase")]
pub struct QuestRequest {
    pub quest_id: String,
}

#[derive(Debug, serde::Deserialize)]
#[serde(deny_unknown_fields, rename_all = "camelCase")]
pub struct AwardCountRequest {
    pub award_id: String,
    pub count: i64,
}

#[derive(Debug, serde::Deserialize)]
#[serde(deny_unknown_fields, rename_all = "camelCase")]
pub struct AwardIdRequest {
    pub award_id: String,
}

#[derive(Debug, serde::Deserialize)]
#[serde(deny_unknown_fields, rename_all = "camelCase")]
pub struct SkillRequest {
    pub skill_id: String,
    pub points: i64,
}

#[derive(Debug, serde::Deserialize)]
#[serde(deny_unknown_fields, rename_all = "camelCase")]
pub struct FreezeRequest {
    pub target: String,
    pub project_id: Option<String>,
}

#[derive(Debug, serde::Deserialize)]
#[serde(deny_unknown_fields, rename_all = "camelCase")]
pub struct BankProductRequest {
    pub product_type: Option<String>,
    pub amount: f64,
    pub days: i64,
    pub allow_interest_withdrawal: Option<bool>,
}

#[derive(Debug, serde::Deserialize)]
#[serde(deny_unknown_fields, rename_all = "camelCase")]
pub struct BankAmountRequest {
    pub amount: f64,
}

#[derive(Debug, serde::Deserialize)]
#[serde(deny_unknown_fields, rename_all = "camelCase")]
pub struct BankProcessRequest {
    pub auto_pay: bool,
}

#[derive(Debug, serde::Deserialize)]
#[serde(deny_unknown_fields, rename_all = "camelCase")]
pub struct BankWithdrawRequest {
    pub allow_early: bool,
}

#[derive(Debug, serde::Deserialize)]
#[serde(deny_unknown_fields, rename_all = "camelCase")]
pub struct CustomAwardRequest {
    pub name: String,
    pub price: f64,
}

#[derive(Debug, serde::Deserialize)]
#[serde(deny_unknown_fields, rename_all = "camelCase")]
pub struct CustomAwardUpdateRequest {
    pub award_id: String,
    pub name: Option<String>,
    pub price: Option<f64>,
}

#[derive(Debug, serde::Deserialize)]
#[serde(deny_unknown_fields, rename_all = "camelCase")]
pub struct DeveloperProfileRequest {
    pub level: i64,
    pub health: f64,
    pub coins: f64,
    pub exp: f64,
    pub test_date_enabled: bool,
    pub test_datetime: Option<String>,
}

fn array_mut<'a>(object: &'a mut Map<String, Value>, key: &str) -> &'a mut Vec<Value> {
    object
        .entry(key.to_string())
        .or_insert_with(|| Value::Array(Vec::new()))
        .as_array_mut()
        .expect("new array")
}

fn add_number(gamer: &mut Map<String, Value>, key: &str, amount: f64) {
    let value = number_field(gamer, key, 0.0) + amount;
    gamer.insert(key.to_string(), json!(value));
}

fn add_experience(gamer: &mut Map<String, Value>, amount: f64) {
    let accrued = ((amount.max(0.0) - 1e-9) * 10.0).ceil() / 10.0;
    add_number(gamer, "exp", accrued.max(0.0));
    loop {
        let level = integer_field(gamer, "level", 1).clamp(1, 99);
        let threshold = 8_000.0 * (level as f64).powi(2);
        if level >= 99 || number_field(gamer, "exp", 0.0) < threshold {
            break;
        }
        gamer.insert("level".into(), json!(level + 1));
        add_number(gamer, "exp", -threshold);
        let inflation = 1.0 + (level as f64 - 1.0) * 0.15;
        add_number(gamer, "coins", level as f64 * 250.0 * inflation);
        let points = integer_field(gamer, "available_skill_points", 0) + 2;
        gamer.insert("available_skill_points".into(), json!(points));
        let max_health = 100 + ((level / 5) * 10);
        gamer.insert("max_health".into(), json!(max_health));
        gamer.insert("health".into(), json!(max_health));
    }
}

impl GameApplicationService {
    pub fn developer_state() -> GameResult<Value> {
        if !cfg!(debug_assertions) {
            return Err(GameError::PrerequisiteMissing(
                "Режим разработчика недоступен в release-сборке.".into(),
            ));
        }
        Ok(json!({"state":Self::state()?,"test_date_enabled":false,"test_datetime":null}))
    }

    pub fn update_developer(request: DeveloperProfileRequest) -> GameResult<GameCommandResponse> {
        if !cfg!(debug_assertions) {
            return Err(GameError::PrerequisiteMissing(
                "Режим разработчика недоступен в release-сборке.".into(),
            ));
        }
        let coins = checked_nonnegative(request.coins, "Монеты")?;
        if !request.health.is_finite()
            || !request.exp.is_finite()
            || request.health < 0.0
            || request.exp < 0.0
        {
            return Err(GameError::Validation(
                "Значения режима разработчика некорректны.".into(),
            ));
        }
        if request.test_date_enabled && request.test_datetime.is_none() {
            return Err(GameError::Validation(
                "Укажите дату и время для тестового режима.".into(),
            ));
        }
        let test_date_enabled = request.test_date_enabled;
        let test_datetime = request.test_datetime.clone();
        Self::mutate(move |state, _rng, _now| {
            let gamer = gamer_object(state)?;
            gamer.insert("level".into(), json!(request.level.clamp(1, 999)));
            gamer.insert("coins".into(), json!(coins));
            gamer.insert("exp".into(), json!(request.exp));
            let max = 100.0 + (((request.level.max(1) - 1) / 5) * 10) as f64;
            gamer.insert("max_health".into(), json!(max));
            gamer.insert("health".into(), json!(request.health.min(max)));
            let root = game_object(state)?;
            object_map(root, "extensions").insert(
                "developer_clock".into(),
                json!({"enabled":test_date_enabled,"datetime":test_datetime}),
            );
            Ok((
                Some("Настройки режима разработчика сохранены.".into()),
                None,
            ))
        })
    }

    pub fn grant_inventory(request: InventoryRequest) -> GameResult<GameCommandResponse> {
        let count = checked_count(request.count)?;
        Self::mutate(move |state, _rng, _now| {
            let gamer = gamer_object(state)?;
            let item = catalog_item(&request.category, &request.item_id)
                .ok_or_else(|| GameError::NotFound("Предмет не найден.".into()))?;
            let current = item_count(gamer, &request.category, &request.item_id);
            item_map(gamer, &request.category)
                .insert(request.item_id.clone(), json!(current + count));
            Ok((
                Some(format!("Получено: {} x{}.", item.key, count)),
                Some(json!({"category":request.category,"item_key":item.key,"count":count})),
            ))
        })
    }

    pub fn start_session(request: WritingSessionRequest) -> GameResult<GameCommandResponse> {
        if ![15, 25, 45, 60].contains(&request.duration_minutes)
            || request.target_symbols <= 0
            || request.target_symbols > 100_000_000
            || request.intention.chars().count() > 200
        {
            return Err(GameError::Validation(
                "Выберите длительность и положительную цель сессии.".into(),
            ));
        }
        if !["flow", "sprint", "deep", "editing"].contains(&request.mode.as_str()) {
            return Err(GameError::NotFound(
                "Неизвестный режим писательской сессии.".into(),
            ));
        }
        if request.mode == "sprint" && request.duration_minutes != 15 {
            return Err(GameError::Validation(
                "Спринт рассчитан только на 15 минут.".into(),
            ));
        }
        if request.mode == "deep" && ![45, 60].contains(&request.duration_minutes) {
            return Err(GameError::Validation(
                "Глубокая работа рассчитана на 45 или 60 минут.".into(),
            ));
        }
        if request.mode == "editing" && request.intention != "Отредактировать текст"
        {
            return Err(GameError::Validation(
                "Редакторский проход требует намерения отредактировать текст.".into(),
            ));
        }
        Self::mutate(move |state, _rng, now| {
            let gamer = gamer_object(state)?;
            if gamer
                .get("writing_session")
                .is_some_and(|value| !value.is_null())
            {
                return Err(GameError::InvalidState(
                    "Сначала завершите текущую писательскую сессию.".into(),
                ));
            }
            gamer.insert("writing_session".into(), json!({"started_at":now,"clock_source":"wall","duration_minutes":request.duration_minutes,"target_symbols":request.target_symbols,"progress":0,"intention":request.intention,"mode":request.mode}));
            Ok((Some("Писательская сессия начата.".into()), None))
        })
    }

    pub fn finish_session() -> GameResult<GameCommandResponse> {
        Self::mutate(|state, _rng, now| {
            let gamer = gamer_object(state)?;
            let session = gamer
                .remove("writing_session")
                .filter(|value| !value.is_null())
                .ok_or_else(|| {
                    GameError::InvalidState("Нет активной писательской сессии.".into())
                })?;
            let session_object = session
                .as_object()
                .ok_or_else(|| GameError::InvalidState("Некорректная сессия.".into()))?;
            let progress = number_field(session_object, "progress", 0.0).max(0.0);
            let target = number_field(session_object, "target_symbols", 1.0).max(1.0);
            let ratio = progress / target;
            let (grade, multiplier, successful) = if ratio >= 1.5 {
                ("gold", 1.30, true)
            } else if ratio >= 1.25 {
                ("silver", 1.15, true)
            } else if ratio >= 1.0 {
                ("bronze", 1.0, true)
            } else {
                ("failed", 0.0, false)
            };
            let (grade, multiplier) = if successful
                && integer_field(gamer, "session_grade_boosts", 0) > 0
                && grade != "gold"
            {
                gamer.insert("session_grade_boosts".into(), json!(0));
                if grade == "bronze" {
                    ("silver", 1.15)
                } else {
                    ("gold", 1.30)
                }
            } else {
                (grade, multiplier)
            };
            let mut protected = false;
            if !successful {
                let ritualist_protection = gamer.get("specialization").and_then(Value::as_str)
                    == Some("ritualist")
                    && gamer
                        .get("specialization_ability_effects")
                        .and_then(Value::as_object)
                        .and_then(|effects| effects.get("ritualist"))
                        .and_then(Value::as_bool)
                        == Some(true);
                if ritualist_protection {
                    object_map(gamer, "specialization_ability_effects")
                        .insert("ritualist".into(), json!(false));
                    protected = true;
                } else {
                    let shields = integer_field(gamer, "session_streak_shields", 0);
                    if shields > 0 {
                        gamer.insert("session_streak_shields".into(), json!(shields - 1));
                        protected = true;
                    } else {
                        gamer.insert("writing_session_streak".into(), json!(0));
                    }
                }
            }
            let mut coins = 0.0;
            let mut exp = 0.0;
            if successful {
                let mode = text_value(session_object.get("mode"), "flow");
                let mode_bonus = match mode.as_str() {
                    "sprint" => 0.15,
                    "deep" => 0.25,
                    "editing" => 0.20,
                    _ => 0.0,
                };
                let streak = integer_field(gamer, "writing_session_streak", 0) + 1;
                let streak_multiplier = 1.0 + (streak.saturating_sub(1).min(5) as f64) * 0.03;
                let bonus = number_field(gamer, "session_reward_bonus", 0.0);
                let specialization = text_value(gamer.get("specialization"), "");
                let ability_active = gamer
                    .get("specialization_ability_effects")
                    .and_then(Value::as_object)
                    .and_then(|effects| effects.get(&specialization))
                    .and_then(Value::as_bool)
                    == Some(true)
                    && matches!(specialization.as_str(), "ritualist" | "editor");
                let ability_multiplier = if ability_active { 1.30 } else { 1.0 };
                if ability_active {
                    object_map(gamer, "specialization_ability_effects")
                        .insert(specialization, json!(false));
                }
                let reward = (1.0 + bonus)
                    * (1.0 + mode_bonus)
                    * multiplier
                    * streak_multiplier
                    * ability_multiplier;
                coins = rounded_money(25.0 * reward);
                exp = (250.0 * reward).round();
                add_number(gamer, "coins", coins);
                add_experience(gamer, exp);
                add_capped(gamer, "inspiration", 10.0, 100.0);
                gamer.insert("writing_session_streak".into(), json!(streak));
                gamer.insert("session_reward_bonus".into(), json!(0.0));
            }
            let history = array_mut(gamer, "writing_session_history");
            history.push(json!({"finished_at":now,"mode":session_object.get("mode").cloned().unwrap_or(json!("flow")),"intention":session_object.get("intention").cloned().unwrap_or(json!("")),"duration_minutes":session_object.get("duration_minutes").cloned().unwrap_or(json!(0)),"target_symbols":session_object.get("target_symbols").cloned().unwrap_or(json!(0)),"progress":progress,"grade":grade,"successful":successful,"coins":coins,"exp":exp}));
            if history.len() > 20 {
                history.drain(0..history.len() - 20);
            }
            let message = if successful {
                format!(
                    "Сессия завершена! Получено {} монет, {} опыта и 10 вдохновения.",
                    coins, exp
                )
            } else if protected {
                "Сессия завершена. Цель не достигнута — Нить ритуала сохранила серию.".into()
            } else {
                "Сессия завершена. Цель не достигнута — штрафа нет.".into()
            };
            Ok((
                Some(message),
                Some(json!({"successful":successful,"grade":grade,"coins":coins,"experience":exp})),
            ))
        })
    }

    pub fn cancel_session() -> GameResult<GameCommandResponse> {
        Self::mutate(|state, _rng, _now| {
            gamer_object(state)?
                .remove("writing_session")
                .filter(|value| !value.is_null())
                .ok_or_else(|| {
                    GameError::InvalidState("Нет активной писательской сессии.".into())
                })?;
            Ok((
                Some("Писательская сессия отменена без штрафа.".into()),
                None,
            ))
        })
    }

    pub fn select_daily(request: DailyChallengeRequest) -> GameResult<GameCommandResponse> {
        Self::mutate(move |state, _rng, _now| {
            let gamer = gamer_object(state)?;
            let options = gamer
                .get("daily_challenge_options")
                .and_then(Value::as_array)
                .ok_or_else(|| GameError::NotFound("Неизвестный вариант цели дня.".into()))?;
            let option = options
                .iter()
                .find(|value| {
                    value.get("option_id").and_then(Value::as_str)
                        == Some(request.option_id.as_str())
                })
                .cloned()
                .ok_or_else(|| GameError::NotFound("Неизвестный вариант цели дня.".into()))?;
            let current = gamer.get("daily_challenge").and_then(Value::as_object);
            if current
                .and_then(|value| value.get("completed"))
                .and_then(Value::as_bool)
                == Some(true)
            {
                return Err(GameError::AlreadyClaimed(
                    "Выполненную цель дня заменить нельзя.".into(),
                ));
            }
            if current
                .and_then(|value| value.get("option_id"))
                .and_then(Value::as_str)
                == Some(request.option_id.as_str())
            {
                return Err(GameError::InvalidState(
                    "Этот вариант цели дня уже выбран.".into(),
                ));
            }
            if number_field(gamer, "inspiration", 0.0) < 15.0 {
                return Err(GameError::InsufficientFunds(
                    "Недостаточно вдохновения для смены цели дня.".into(),
                ));
            }
            add_number(gamer, "inspiration", -15.0);
            gamer.insert("daily_challenge".into(), option);
            Ok((Some("Выбрана новая цель дня.".into()), None))
        })
    }

    pub fn start_weekly(request: WeeklyChallengeRequest) -> GameResult<GameCommandResponse> {
        if !["symbols", "days", "sessions", "editing"].contains(&request.challenge_id.as_str()) {
            return Err(GameError::NotFound(
                "Неизвестное недельное испытание.".into(),
            ));
        }
        Self::mutate(move |state, _rng, now| {
            let gamer = gamer_object(state)?;
            if gamer
                .get("weekly_challenge")
                .is_some_and(|value| !value.is_null())
            {
                return Err(GameError::AlreadyClaimed(
                    "Недельное испытание уже выбрано.".into(),
                ));
            }
            let week_start = iso_epoch_seconds(now)
                .map(|seconds| {
                    let days = seconds.div_euclid(86_400);
                    let monday = days - (days + 3).rem_euclid(7);
                    iso_date_from_days(monday)
                })
                .unwrap_or_else(|| now.get(..10).unwrap_or(now).to_string());
            gamer.insert("weekly_challenge".into(),json!({"key":request.challenge_id,"week_start":week_start,"progress":0,"writing_days":[],"completed":false}));
            Ok((Some("Начато недельное испытание.".into()), None))
        })
    }

    pub fn activate_inspiration(ability_id: String) -> GameResult<GameCommandResponse> {
        let (cost, field) = match ability_id.as_str() {
            "creative_surge" => (30, "writing_reward_bonus"),
            "session_spark" => (25, "session_reward_bonus"),
            "challenge_focus" => (40, "challenge_reward_bonus"),
            _ => {
                return Err(GameError::NotFound(
                    "Неизвестная способность вдохновения.".into(),
                ))
            }
        };
        Self::mutate(move |state, _rng, _now| {
            let gamer = gamer_object(state)?;
            if number_field(gamer, field, 0.0) > 0.0 {
                return Err(GameError::AlreadyClaimed(
                    "Этот эффект вдохновения уже активен.".into(),
                ));
            }
            if number_field(gamer, "inspiration", 0.0) < cost as f64 {
                return Err(GameError::InsufficientFunds(
                    "Недостаточно вдохновения для этой способности.".into(),
                ));
            }
            add_number(gamer, "inspiration", -(cost as f64));
            gamer.insert(field.into(), json!(0.25));
            Ok((Some("Способность вдохновения активирована.".into()), None))
        })
    }

    pub fn resolve_creative(request: ChoiceRequest) -> GameResult<GameCommandResponse> {
        if request.choice != "safe" && request.choice != "risk" {
            return Err(GameError::Validation(
                "Неизвестный выбор творческого события.".into(),
            ));
        }
        Self::mutate(move |state, rng, now| {
            let gamer = gamer_object(state)?;
            let event = gamer
                .get("pending_creative_event")
                .and_then(Value::as_str)
                .ok_or_else(|| {
                    GameError::InvalidState("Нет творческого события, ожидающего решения.".into())
                })?
                .to_string();
            let success = request.choice == "safe" || rng.uniform_u32(100) < 55;
            if success {
                add_capped(
                    gamer,
                    "inspiration",
                    if request.choice == "safe" { 10.0 } else { 5.0 },
                    100.0,
                );
            } else {
                add_number(
                    gamer,
                    "inspiration",
                    -number_field(gamer, "inspiration", 0.0).min(5.0),
                );
            }
            let history = array_mut(gamer, "creative_event_history");
            history.push(
                json!({"event":event,"choice":request.choice,"success":success,"resolved_at":now}),
            );
            if history.len() > 20 {
                history.drain(0..history.len() - 20);
            }
            gamer.remove("pending_creative_event");
            Ok((
                Some("Творческое событие завершено.".into()),
                Some(json!({"success":success})),
            ))
        })
    }

    pub fn select_specialization(id: String) -> GameResult<GameCommandResponse> {
        if !["marathoner", "ritualist", "finisher", "explorer", "editor"].contains(&id.as_str()) {
            return Err(GameError::NotFound("Неизвестная специализация.".into()));
        }
        Self::mutate(move |state, _rng, now| {
            let gamer = gamer_object(state)?;
            if integer_field(gamer, "level", 1) < 3 {
                return Err(GameError::PrerequisiteMissing(
                    "Специализации открываются на 3 уровне.".into(),
                ));
            }
            if let Some(changed_at) = gamer
                .get("specialization_changed_at")
                .map(|value| text_value(Some(value), ""))
                .filter(|value| !value.is_empty())
            {
                if iso_epoch_seconds(now)
                    .zip(iso_epoch_seconds(&changed_at))
                    .is_some_and(|(current, previous)| current < previous + 14 * 86_400)
                {
                    return Err(GameError::CooldownActive(
                        "Сменить специализацию можно через 14 дней.".into(),
                    ));
                }
            }
            if gamer.get("specialization").and_then(Value::as_str) == Some(id.as_str()) {
                return Err(GameError::AlreadyClaimed(
                    "Эта специализация уже выбрана.".into(),
                ));
            }
            gamer.insert("specialization".into(), json!(id));
            gamer.insert("specialization_changed_at".into(), json!(now));
            object_map(gamer, "specialization_mastery")
                .entry(id.clone())
                .or_insert(json!(0));
            Ok((Some("Специализация выбрана.".into()), None))
        })
    }

    pub fn activate_specialization() -> GameResult<GameCommandResponse> {
        Self::mutate(|state, _rng, now| {
            let gamer = gamer_object(state)?;
            let specialization = text_value(gamer.get("specialization"), "");
            if specialization.is_empty() {
                return Err(GameError::PrerequisiteMissing(
                    "Сначала выберите специализацию.".into(),
                ));
            }
            if let Some(ready_at) = gamer
                .get("specialization_ability_ready_at")
                .and_then(Value::as_object)
                .and_then(|ready| ready.get(&specialization))
                .map(|value| text_value(Some(value), ""))
                .filter(|value| !value.is_empty())
            {
                if iso_epoch_seconds(now)
                    .zip(iso_epoch_seconds(&ready_at))
                    .is_some_and(|(current, activated)| current < activated + 86_400)
                {
                    return Err(GameError::CooldownActive(
                        "Умение специализации ещё не восстановилось.".into(),
                    ));
                }
            }
            let effects = object_map(gamer, "specialization_ability_effects");
            if effects
                .get(&specialization)
                .is_some_and(|value| value.as_bool().unwrap_or(false))
            {
                return Err(GameError::AlreadyClaimed(
                    "Эффект активного умения уже ожидает применения.".into(),
                ));
            }
            effects.insert(specialization.clone(), json!(true));
            object_map(gamer, "specialization_ability_ready_at").insert(specialization, json!(now));
            Ok((Some("Умение специализации активировано.".into()), None))
        })
    }

    pub fn increase_skill(request: SkillRequest) -> GameResult<GameCommandResponse> {
        let points = checked_count(request.points)?;
        Self::mutate(move |state, _rng, _now| {
            let gamer = gamer_object(state)?;
            if !["productivity", "discipline", "creativity"].contains(&request.skill_id.as_str()) {
                return Err(GameError::NotFound("Неизвестное умение.".into()));
            }
            if integer_field(gamer, "available_skill_points", 0) < points {
                return Err(GameError::InsufficientFunds(
                    "Недостаточно доступных баллов умений.".into(),
                ));
            }
            let skills = object_map(gamer, "skills");
            let old = skills
                .get(&request.skill_id)
                .and_then(Value::as_i64)
                .unwrap_or(0);
            skills.insert(request.skill_id.clone(), json!(old + points));
            gamer.insert(
                "available_skill_points".into(),
                json!(integer_field(gamer, "available_skill_points", 0) - points),
            );
            Ok((Some(format!("Умение увеличено на {points}.")), None))
        })
    }

    pub fn quest(id: String, start: bool) -> GameResult<GameCommandResponse> {
        Self::mutate(move |state, _rng, now| {
            let gamer = gamer_object(state)?;
            let quests = array_mut(gamer, "quests");
            let quest = quests
                .iter_mut()
                .find(|value| {
                    tagged_field(value, "quest_id").and_then(Value::as_str) == Some(id.as_str())
                })
                .ok_or_else(|| GameError::NotFound("Квест не найден.".into()))?;
            let fields = tagged_fields(quest)
                .ok_or_else(|| GameError::InvalidState("Некорректный квест.".into()))?;
            let status = text_value(fields.get("status"), "Available");
            if start {
                if status != "Available" {
                    return Err(GameError::AlreadyClaimed(
                        "Квест уже запущен или завершен.".into(),
                    ));
                }
                fields.insert("status".into(), json!("Active"));
                fields.insert("start_date".into(), json!(now));
                Ok((Some("Квест начат.".into()), None))
            } else {
                if status != "Active" {
                    return Err(GameError::InvalidState("Активный квест не найден.".into()));
                }
                fields.insert("status".into(), json!("Available"));
                fields.insert("start_date".into(), Value::Null);
                Ok((Some("Квест возвращен в доступные.".into()), None))
            }
        })
    }

    pub fn freeze(request: FreezeRequest) -> GameResult<GameCommandResponse> {
        if request.target != "global" && request.target != "project" {
            return Err(GameError::Validation(
                "Неизвестная цель заморозки стрика.".into(),
            ));
        }
        if request.target == "project" && request.project_id.as_deref().unwrap_or("").is_empty() {
            return Err(GameError::Validation(
                "Выберите проект для заморозки.".into(),
            ));
        }
        Self::mutate(move |state, _rng, now| {
            let gamer = gamer_object(state)?;
            let count = item_count(gamer, "Предметы", "Заморозка");
            if count < 1 {
                return Err(GameError::InsufficientFunds(
                    "В инвентаре нет заморозки.".into(),
                ));
            }
            let items = item_map(gamer, "Предметы");
            if count == 1 {
                items.remove("Заморозка")
            } else {
                items.insert("Заморозка".into(), json!(count - 1))
            };
            Ok((
                Some(if request.target == "global" {
                    "Глобальный стрик заморожен!".into()
                } else {
                    "Проект заморожен!".into()
                }),
                Some(
                    json!({"target":request.target,"project_id":request.project_id,"date":now.get(..10).unwrap_or(now)}),
                ),
            ))
        })
    }

    pub fn mark_notification(id: String, all: bool) -> GameResult<Value> {
        let response = Self::mutate(move |state, _rng, _now| {
            let root = game_object(state)?;
            let notifications = object_map(root, "notifications");
            let mut unread_values = std::mem::take(array_mut(notifications, "new"));
            let read = array_mut(notifications, "read");
            if all {
                while let Some(value) = unread_values.pop() {
                    read.insert(0, value);
                }
            } else {
                let index = unread_values
                    .iter()
                    .enumerate()
                    .find(|(index, value)| {
                        notification_json(value, "new", *index)["id"].as_str() == Some(id.as_str())
                    })
                    .map(|(index, _)| index)
                    .ok_or_else(|| GameError::NotFound("Уведомление не найдено.".into()))?;
                let value = unread_values.remove(index);
                read.insert(0, value);
            }
            *array_mut(notifications, "new") = unread_values;
            Ok((None, None))
        })?;
        Ok(response.state["notifications"].clone())
    }

    pub fn custom_award(request: CustomAwardRequest) -> GameResult<GameCommandResponse> {
        if request.name.trim().is_empty() || request.name.chars().count() > 200 {
            return Err(GameError::Validation(
                "Название награды должно содержать от 1 до 200 символов.".into(),
            ));
        }
        let price = checked_positive(request.price, "Цена награды")?;
        Self::mutate(move |state, _rng, _now| {
            let gamer = gamer_object(state)?;
            let awards = array_mut(gamer, "custom_awards");
            let id = format!("custom-{}", awards.len() + 1);
            awards.push(json!({"__type__":"game_data.Item","fields":{"award_id":id,"name":request.name,"_price":price,"description":"Кастомная награда без эффекта","available_in_shop":true,"sellable":true,"item_type":"Награды"}}));
            object_map(gamer, "custom_awards_inventory")
                .entry(request.name.clone())
                .or_insert(json!(0));
            Ok((
                Some("Награда создана.".into()),
                Some(json!({"award_id":id,"name":request.name,"price":price})),
            ))
        })
    }

    pub fn update_custom_award(
        request: CustomAwardUpdateRequest,
    ) -> GameResult<GameCommandResponse> {
        let price = match request.price {
            Some(value) => Some(checked_positive(value, "Цена награды")?),
            None => None,
        };
        if request
            .name
            .as_ref()
            .is_some_and(|name| name.trim().is_empty())
        {
            return Err(GameError::Validation(
                "Название награды не может быть пустым.".into(),
            ));
        }
        Self::mutate(move |state, _rng, _now| {
            let gamer = gamer_object(state)?;
            let awards = array_mut(gamer, "custom_awards");
            let award = awards
                .iter_mut()
                .find(|value| {
                    tagged_field(value, "award_id").and_then(Value::as_str)
                        == Some(request.award_id.as_str())
                })
                .ok_or_else(|| GameError::NotFound("Кастомная награда не найдена.".into()))?;
            let fields = tagged_fields(award)
                .ok_or_else(|| GameError::InvalidState("Некорректная кастомная награда.".into()))?;
            if let Some(name) = request.name {
                fields.insert("name".into(), json!(name));
            }
            if let Some(price) = price {
                fields.insert("_price".into(), json!(price));
            }
            Ok((Some("Награда изменена.".into()), None))
        })
    }

    pub fn delete_custom_award(id: String) -> GameResult<GameCommandResponse> {
        Self::mutate(move |state, _rng, _now| {
            let gamer = gamer_object(state)?;
            let awards = array_mut(gamer, "custom_awards");
            let index = awards
                .iter()
                .position(|value| {
                    tagged_field(value, "award_id").and_then(Value::as_str) == Some(id.as_str())
                })
                .ok_or_else(|| GameError::NotFound("Кастомная награда не найдена.".into()))?;
            awards.remove(index);
            Ok((Some("Награда удалена.".into()), None))
        })
    }

    pub fn custom_inventory(
        id: String,
        count: i64,
        operation: &str,
    ) -> GameResult<GameCommandResponse> {
        let count = checked_count(count)?;
        Self::mutate(move |state, _rng, _now| {
            let gamer = gamer_object(state)?;
            let (name, price) = gamer
                .get("custom_awards")
                .and_then(Value::as_array)
                .and_then(|items| {
                    items.iter().find(|value| {
                        tagged_field(value, "award_id").and_then(Value::as_str) == Some(id.as_str())
                    })
                })
                .map(|value| {
                    (
                        text_value(tagged_field(value, "name"), ""),
                        tagged_field(value, "_price")
                            .and_then(Value::as_f64)
                            .unwrap_or(1.0),
                    )
                })
                .ok_or_else(|| GameError::NotFound("Кастомная награда не найдена.".into()))?;
            let current = gamer
                .get("custom_awards_inventory")
                .and_then(Value::as_object)
                .and_then(|inventory| inventory.get(&name))
                .and_then(Value::as_i64)
                .unwrap_or(0);
            match operation {
                "buy" => {
                    let total = rounded_money(price * count as f64);
                    if number_field(gamer, "coins", 0.0) < total {
                        return Err(GameError::InsufficientFunds("Недостаточно монет!".into()));
                    }
                    add_number(gamer, "coins", -total);
                    object_map(gamer, "custom_awards_inventory")
                        .insert(name, json!(current + count));
                }
                "sell" => {
                    if current < count {
                        return Err(GameError::InvalidQuantity(
                            "Недостаточно наград в инвентаре.".into(),
                        ));
                    }
                    object_map(gamer, "custom_awards_inventory")
                        .insert(name, json!(current - count));
                    add_number(gamer, "coins", rounded_money(price * 0.75 * count as f64));
                }
                "use" => {
                    if current < count {
                        return Err(GameError::InvalidQuantity(
                            "Недостаточно наград в инвентаре.".into(),
                        ));
                    }
                    object_map(gamer, "custom_awards_inventory")
                        .insert(name, json!(current - count));
                }
                _ => {
                    return Err(GameError::Validation(
                        "Unknown custom award operation".into(),
                    ))
                }
            }
            Ok((Some("Операция с наградой выполнена.".into()), None))
        })
    }

    pub fn bank_open(
        request: BankProductRequest,
        deposit: bool,
    ) -> GameResult<GameCommandResponse> {
        let amount = checked_positive(request.amount, "Сумма")?;
        if request.days <= 0 || request.days > 36500 {
            return Err(GameError::Validation(
                "Срок должен быть от 1 до 36500 дней.".into(),
            ));
        }
        Self::mutate(move |state, _rng, now| {
            let gamer = gamer_object(state)?;
            if deposit && number_field(gamer, "coins", 0.0) < amount {
                return Err(GameError::InsufficientFunds("Недостаточно монет.".into()));
            }
            if !deposit && integer_field(gamer, "level", 1) < 3 {
                return Err(GameError::PrerequisiteMissing(
                    "Кредиты доступны с 3 уровня.".into(),
                ));
            }
            let key = if deposit { "deposit" } else { "credit" };
            let active = gamer
                .get("bank_account")
                .and_then(tagged_fields_immutable)
                .and_then(|fields| fields.get(key))
                .is_some_and(|value| !value.is_null());
            if active {
                return Err(GameError::AlreadyClaimed(
                    "Банковский продукт уже активен.".into(),
                ));
            }
            add_number(gamer, "coins", if deposit { -amount } else { amount });
            let product = if deposit {
                json!({"__type__":"game_data.Deposit","fields":{"give_date":now,"deposit_sum":amount,"days_until_return":request.days,"interest_rate_on_deposit":1.0,"allow_interest_withdrawal":request.allow_interest_withdrawal.unwrap_or(true),"interest":0.0}})
            } else {
                json!({"__type__":"game_data.Credit","fields":{"take_date":now,"credit_sum":amount,"days_until_return":request.days,"interest_rate_on_loan":2.0,"paid_amount":0.0,"accrued_penalty":0.0}})
            };
            let account = gamer
                .entry("bank_account")
                .or_insert_with(|| json!({"__type__":"game_data.BankAccount","fields":{}}));
            tagged_fields(account)
                .ok_or_else(|| GameError::InvalidState("Некорректный банковский счёт.".into()))?
                .insert(key.into(), product);
            Ok((
                Some(if deposit {
                    "Вклад открыт.".into()
                } else {
                    "Кредит открыт.".into()
                }),
                Some(json!({"amount":amount,"days":request.days})),
            ))
        })
    }

    pub fn bank_amount(
        request: BankAmountRequest,
        deposit: bool,
    ) -> GameResult<GameCommandResponse> {
        let amount = checked_positive(request.amount, "Сумма")?;
        Self::mutate(move |state, _rng, _now| {
            let gamer = gamer_object(state)?;
            if number_field(gamer, "coins", 0.0) < amount {
                return Err(GameError::InsufficientFunds("Недостаточно монет.".into()));
            }
            let key = if deposit { "deposit" } else { "credit" };
            let new_value = {
                let bank = gamer
                    .get_mut("bank_account")
                    .and_then(tagged_fields)
                    .ok_or_else(|| GameError::InvalidState("Банковский счёт не найден.".into()))?;
                let product = bank
                    .get_mut(key)
                    .filter(|value| !value.is_null())
                    .ok_or_else(|| {
                        GameError::InvalidState("Активный банковский продукт не найден.".into())
                    })?;
                let fields = tagged_fields(product).ok_or_else(|| {
                    GameError::InvalidState("Некорректный банковский продукт.".into())
                })?;
                if deposit {
                    rounded_money(number_field(fields, "deposit_sum", 0.0) + amount)
                } else {
                    rounded_money(number_field(fields, "paid_amount", 0.0) + amount)
                }
            };
            if deposit {
                add_number(gamer, "coins", -amount);
                let fields = gamer
                    .get_mut("bank_account")
                    .and_then(tagged_fields)
                    .expect("bank fields");
                let product = fields.get_mut(key).expect("bank product");
                tagged_fields(product)
                    .expect("product fields")
                    .insert("deposit_sum".into(), json!(new_value));
            } else {
                add_number(gamer, "coins", -amount);
                let fields = gamer
                    .get_mut("bank_account")
                    .and_then(tagged_fields)
                    .expect("bank fields");
                let product = fields.get_mut(key).expect("bank product");
                tagged_fields(product)
                    .expect("product fields")
                    .insert("paid_amount".into(), json!(new_value));
            }
            Ok((
                Some("Банковская операция выполнена.".into()),
                Some(json!({"amount":amount})),
            ))
        })
    }

    pub fn bank_close(
        deposit: bool,
        interest_only: bool,
        allow_early: bool,
    ) -> GameResult<GameCommandResponse> {
        Self::mutate(move |state, _rng, now| {
            let gamer = gamer_object(state)?;
            let key = if deposit { "deposit" } else { "credit" };
            let value = {
                let bank = gamer
                    .get_mut("bank_account")
                    .and_then(tagged_fields)
                    .ok_or_else(|| GameError::InvalidState("Банковский счёт не найден.".into()))?;
                let product = bank
                    .get_mut(key)
                    .filter(|value| !value.is_null())
                    .ok_or_else(|| {
                        GameError::InvalidState("Активный банковский продукт не найден.".into())
                    })?;
                let fields = tagged_fields(product).ok_or_else(|| {
                    GameError::InvalidState("Некорректный банковский продукт.".into())
                })?;
                if deposit {
                    let opened = text_value(fields.get("give_date"), "");
                    let days = integer_field(fields, "days_until_return", 1).max(1);
                    let matured = iso_epoch_seconds(&opened)
                        .zip(iso_epoch_seconds(now))
                        .is_some_and(|(opened, current)| current >= opened + days * 86_400);
                    if !interest_only && !matured && !allow_early {
                        return Err(GameError::CooldownActive(
                            "Срок вклада еще не наступил.".into(),
                        ));
                    }
                    if interest_only {
                        number_field(fields, "interest", 0.0)
                    } else if allow_early && !matured {
                        number_field(fields, "deposit_sum", 0.0)
                    } else {
                        number_field(fields, "deposit_sum", 0.0)
                            + number_field(fields, "interest", 0.0)
                    }
                } else {
                    let principal = number_field(fields, "credit_sum", 0.0);
                    let days = integer_field(fields, "days_until_return", 1).max(1);
                    let rate = number_field(fields, "interest_rate_on_loan", 2.0).max(0.0);
                    let growth = (1.0 + rate / 100.0).powi(days as i32);
                    let interest = rounded_money(
                        rounded_money(principal * (rate / 100.0) * growth / (growth - 1.0))
                            * days as f64
                            - principal,
                    );
                    principal + interest + number_field(fields, "accrued_penalty", 0.0)
                        - number_field(fields, "paid_amount", 0.0)
                }
            };
            if !deposit && number_field(gamer, "coins", 0.0) < value {
                return Err(GameError::InsufficientFunds(
                    "Недостаточно монет для погашения.".into(),
                ));
            }
            if !deposit {
                add_number(gamer, "coins", -value);
            } else {
                add_number(gamer, "coins", value);
            }
            if !interest_only {
                gamer
                    .get_mut("bank_account")
                    .and_then(tagged_fields)
                    .expect("bank fields")
                    .insert(key.into(), Value::Null);
            }
            Ok((
                Some("Банковская операция выполнена.".into()),
                Some(json!({"amount":value})),
            ))
        })
    }
}

fn add_capped(gamer: &mut Map<String, Value>, key: &str, amount: f64, cap: f64) {
    let value = (number_field(gamer, key, 0.0) + amount).min(cap);
    gamer.insert(
        key.into(),
        if key.contains("streak") || key.contains("boost") || key.contains("mastery") {
            json!(value as i64)
        } else {
            json!(value)
        },
    );
}

fn lottery_draw<R: GameRng>(rng: &mut R) -> Value {
    fn draw_numbers<R: GameRng>(rng: &mut R) -> Vec<u32> {
        let mut numbers = Vec::new();
        while numbers.len() < 5 {
            let value = rng.uniform_u32(30) + 1;
            if !numbers.contains(&value) {
                numbers.push(value);
            }
        }
        numbers.sort_unstable();
        numbers
    }

    let player_numbers = draw_numbers(rng);
    let winning_numbers = draw_numbers(rng);
    let matches = player_numbers
        .iter()
        .filter(|number| winning_numbers.contains(number))
        .count() as i64;
    let multiplier = match matches {
        2 => 2,
        3 => 10,
        4 => 250,
        5 => 10_000,
        _ => 0,
    };
    let prize = 10 * multiplier;
    json!({
        "player_numbers": player_numbers,
        "winning_numbers": winning_numbers,
        "matches": matches,
        "prize": prize,
    })
}

#[derive(Debug, serde::Serialize)]
pub struct GameCommandResponse {
    pub ok: bool,
    pub message: Option<String>,
    pub messages: Vec<String>,
    pub result: Option<Value>,
    pub state: Value,
}

#[cfg(test)]
mod tests {
    use super::*;

    struct FixedRng {
        values: Vec<u32>,
        index: usize,
    }

    impl GameRng for FixedRng {
        fn uniform_u32(&mut self, upper_exclusive: u32) -> u32 {
            let value = self.values[self.index % self.values.len()];
            self.index += 1;
            value % upper_exclusive
        }
    }

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

    #[test]
    fn lottery_uses_injected_rng_and_never_duplicates_numbers() {
        let mut rng = FixedRng {
            values: vec![0, 1, 2, 3, 4, 0, 1, 2, 3, 4],
            index: 0,
        };
        let draw = lottery_draw(&mut rng);
        let player_numbers = draw["player_numbers"].as_array().expect("player numbers");
        let winning_numbers = draw["winning_numbers"].as_array().expect("winning numbers");
        assert_eq!(player_numbers.len(), 5);
        assert_eq!(winning_numbers.len(), 5);
        assert_eq!(
            player_numbers
                .iter()
                .collect::<std::collections::HashSet<_>>()
                .len(),
            5
        );
        assert_eq!(draw["matches"], json!(5));
        assert_eq!(draw["prize"], json!(100_000));
        assert!(player_numbers.iter().all(|number| number
            .as_u64()
            .is_some_and(|number| (1..=30).contains(&number))));
    }

    #[test]
    fn inventory_mutation_preserves_unknown_gamer_fields() {
        let mut state = json!({"gamer":{"coins":1000.0,"level":3,"items":{"Предметы":{"Лотерейный билет":1}},"future_extension":{"kept":true}}});
        let item = catalog_item("Предметы", "Лотерейный билет").expect("catalog item");
        let mut rng = FixedRng {
            values: vec![1, 2, 3, 4, 5],
            index: 0,
        };
        let gamer = gamer_object(&mut state).expect("gamer");
        GameApplicationService::use_item_mutation(gamer, item, 1, &mut rng, "2026-01-01T00:00:00Z")
            .expect("use ticket");
        assert_eq!(state["gamer"]["future_extension"], json!({"kept":true}));
        assert_eq!(
            state["gamer"]["items"]["Предметы"]["Лотерейный билет"],
            Value::Null
        );
        assert_eq!(
            state["gamer"]["lottery_history"].as_array().map(Vec::len),
            Some(1)
        );
    }

    #[test]
    fn clock_projection_and_week_boundary_are_deterministic() {
        assert_eq!(iso_date_from_days(0), "1970-01-01");
        assert_eq!(iso_epoch_seconds("1970-01-01T00:00:00Z"), Some(0));
        let session = session_projection(
            Some(&json!({
                "started_at":"2026-09-04T12:00:00Z",
                "duration_minutes":15,
                "target_symbols":100
            })),
            "2026-09-04T12:05:00Z",
        );
        assert_eq!(session["remaining_seconds"], json!(600));
        let day = iso_epoch_seconds("2026-09-04T00:00:00Z")
            .expect("date")
            .div_euclid(86_400);
        let monday = day - (day + 3).rem_euclid(7);
        assert_eq!(iso_date_from_days(monday), "2026-08-31");
    }

    #[test]
    fn game_request_dto_rejects_unknown_fields() {
        let request = serde_json::from_value::<InventoryRequest>(json!({
            "category":"Предметы",
            "itemId":"Лотерейный билет",
            "count":1,
            "inject":"not allowed"
        }));
        assert!(request.is_err());
    }
}
