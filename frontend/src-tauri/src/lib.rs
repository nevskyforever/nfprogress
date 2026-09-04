use std::collections::HashSet;
use std::fmt::Write as _;
use std::fs;
use std::io::{Read, Write};
use std::net::{TcpListener, TcpStream};
use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};
use std::sync::Mutex;
use std::thread;
use std::time::{Duration, Instant};

use rusqlite::OptionalExtension;
use serde::de::{self, Visitor};
use serde::{Deserialize, Serialize};
use tauri::{Emitter, Manager, PhysicalPosition, PhysicalSize, RunEvent, State};
use tauri_plugin_shell::process::{CommandChild, CommandEvent};
use tauri_plugin_shell::ShellExt;

mod game;
#[allow(dead_code)]
mod project_repository;
mod sqlite;

use project_repository::{
    ProgressRecord, ProjectAggregate, ProjectMetadataUpdate, ProjectRecord, ProjectsRepository,
    StageRecord, StageUpdate,
};

#[derive(Serialize)]
struct SqliteEntityRow {
    id: String,
    project_id: Option<String>,
    name: Option<String>,
    goal: Option<f64>,
    infinite: i64,
    unit: String,
    status: String,
    created_at: Option<String>,
    updated_at: Option<String>,
    payload_json: String,
}

#[derive(Serialize)]
struct SqliteProgressRow {
    id: String,
    project_id: String,
    stage_id: Option<String>,
    created_at: Option<String>,
    added_symbols: Option<f64>,
    added_progress: Option<f64>,
    payload_json: String,
}

#[derive(Serialize)]
struct SqliteProjectReadModel {
    mirror_status: String,
    project_order: Vec<String>,
    projects: Vec<SqliteEntityRow>,
    stages: Vec<SqliteEntityRow>,
    progress_entries: Vec<SqliteProgressRow>,
}

pub(crate) fn open_projects_database() -> Result<rusqlite::Connection, String> {
    sqlite::open_database(&sqlite_data_root()?.join("nfprogress.db"))
        .map_err(|error| error.to_string())
}

#[tauri::command]
fn process_game_events() -> Result<game::ProcessSummary, String> {
    let mut connection = open_projects_database()?;
    let owner: String = connection
        .query_row(
            "SELECT owner FROM storage_ownership WHERE subsystem='game'",
            [],
            |row| row.get(0),
        )
        .map_err(|error| error.to_string())?;
    if owner != "sqlite" {
        return Err("Игра ещё не переведена в SQLite authoritative storage.".to_string());
    }
    game::process_pending_events(&mut connection, 100)
}

// Explicit Game commands.  These are deliberately one command per use case;
// the frontend cannot inject an arbitrary operation name or JSON payload.
#[tauri::command]
fn game_state() -> Result<serde_json::Value, game::GameError> {
    game::GameApplicationService::state()
}

#[tauri::command]
fn game_notifications() -> Result<serde_json::Value, game::GameError> {
    game::GameApplicationService::notifications()
}

#[tauri::command]
fn mark_game_notification_read(
    payload: game::NotificationRequest,
) -> Result<serde_json::Value, game::GameError> {
    game::GameApplicationService::mark_notification(payload.notification_id, false)
}

#[tauri::command]
fn mark_all_game_notifications_read() -> Result<serde_json::Value, game::GameError> {
    game::GameApplicationService::mark_notification(String::new(), true)
}

#[tauri::command]
fn game_catalog() -> Result<serde_json::Value, game::GameError> {
    let state = game::GameApplicationService::state()?;
    Ok(state["shop"].clone())
}

#[tauri::command]
fn game_developer_state() -> Result<serde_json::Value, game::GameError> {
    game::GameApplicationService::developer_state()
}

#[tauri::command]
fn game_update_developer_profile(
    payload: game::DeveloperProfileRequest,
) -> Result<game::GameCommandResponse, game::GameError> {
    game::GameApplicationService::update_developer(payload)
}

#[tauri::command]
fn game_grant_developer_inventory_item(
    payload: game::InventoryRequest,
) -> Result<game::GameCommandResponse, game::GameError> {
    game::GameApplicationService::grant_inventory(payload)
}

#[tauri::command]
fn game_start_writing_session(
    payload: game::WritingSessionRequest,
) -> Result<game::GameCommandResponse, game::GameError> {
    game::GameApplicationService::start_session(payload)
}
#[tauri::command]
fn game_finish_writing_session() -> Result<game::GameCommandResponse, game::GameError> {
    game::GameApplicationService::finish_session()
}
#[tauri::command]
fn game_cancel_writing_session() -> Result<game::GameCommandResponse, game::GameError> {
    game::GameApplicationService::cancel_session()
}
#[tauri::command]
fn game_select_daily_challenge(
    payload: game::DailyChallengeRequest,
) -> Result<game::GameCommandResponse, game::GameError> {
    game::GameApplicationService::select_daily(payload)
}
#[tauri::command]
fn game_start_weekly_challenge(
    payload: game::WeeklyChallengeRequest,
) -> Result<game::GameCommandResponse, game::GameError> {
    game::GameApplicationService::start_weekly(payload)
}
#[tauri::command]
fn game_activate_inspiration_ability(
    payload: game::AbilityRequest,
) -> Result<game::GameCommandResponse, game::GameError> {
    game::GameApplicationService::activate_inspiration(payload.ability_id)
}
#[tauri::command]
fn game_resolve_creative_event(
    payload: game::ChoiceRequest,
) -> Result<game::GameCommandResponse, game::GameError> {
    game::GameApplicationService::resolve_creative(payload)
}
#[tauri::command]
fn game_select_specialization(
    payload: game::SpecializationRequest,
) -> Result<game::GameCommandResponse, game::GameError> {
    game::GameApplicationService::select_specialization(payload.specialization_id)
}
#[tauri::command]
fn game_activate_specialization_ability() -> Result<game::GameCommandResponse, game::GameError> {
    game::GameApplicationService::activate_specialization()
}
#[tauri::command]
fn game_increase_skill(
    payload: game::SkillRequest,
) -> Result<game::GameCommandResponse, game::GameError> {
    game::GameApplicationService::increase_skill(payload)
}
#[tauri::command]
fn game_start_quest(
    payload: game::QuestRequest,
) -> Result<game::GameCommandResponse, game::GameError> {
    game::GameApplicationService::quest(payload.quest_id, true)
}
#[tauri::command]
fn game_abandon_quest(
    payload: game::QuestRequest,
) -> Result<game::GameCommandResponse, game::GameError> {
    game::GameApplicationService::quest(payload.quest_id, false)
}
#[tauri::command]
fn game_buy_item(
    payload: game::InventoryRequest,
) -> Result<game::GameCommandResponse, game::GameError> {
    game::GameApplicationService::inventory(payload.category, payload.item_id, payload.count, "buy")
}
#[tauri::command]
fn game_sell_item(
    payload: game::InventoryRequest,
) -> Result<game::GameCommandResponse, game::GameError> {
    game::GameApplicationService::inventory(
        payload.category,
        payload.item_id,
        payload.count,
        "sell",
    )
}
#[tauri::command]
fn game_use_item(
    payload: game::InventoryRequest,
) -> Result<game::GameCommandResponse, game::GameError> {
    game::GameApplicationService::inventory(payload.category, payload.item_id, payload.count, "use")
}
#[tauri::command]
fn game_apply_streak_freeze(
    payload: game::FreezeRequest,
) -> Result<game::GameCommandResponse, game::GameError> {
    game::GameApplicationService::freeze(payload)
}
#[tauri::command]
fn game_run_lottery() -> Result<game::GameCommandResponse, game::GameError> {
    game::GameApplicationService::run_lottery()
}
#[tauri::command]
fn game_create_custom_award(
    payload: game::CustomAwardRequest,
) -> Result<game::GameCommandResponse, game::GameError> {
    game::GameApplicationService::custom_award(payload)
}
#[tauri::command]
fn game_update_custom_award(
    payload: game::CustomAwardUpdateRequest,
) -> Result<game::GameCommandResponse, game::GameError> {
    game::GameApplicationService::update_custom_award(payload)
}
#[tauri::command]
fn game_delete_custom_award(
    payload: game::AwardIdRequest,
) -> Result<game::GameCommandResponse, game::GameError> {
    game::GameApplicationService::delete_custom_award(payload.award_id)
}
#[tauri::command]
fn game_buy_custom_award(
    payload: game::AwardCountRequest,
) -> Result<game::GameCommandResponse, game::GameError> {
    game::GameApplicationService::custom_inventory(payload.award_id, payload.count, "buy")
}
#[tauri::command]
fn game_sell_custom_award(
    payload: game::AwardCountRequest,
) -> Result<game::GameCommandResponse, game::GameError> {
    game::GameApplicationService::custom_inventory(payload.award_id, payload.count, "sell")
}
#[tauri::command]
fn game_use_custom_award(
    payload: game::AwardCountRequest,
) -> Result<game::GameCommandResponse, game::GameError> {
    game::GameApplicationService::custom_inventory(payload.award_id, payload.count, "use")
}
#[tauri::command]
fn game_preview_bank_product(
    payload: game::BankProductRequest,
) -> Result<game::GameCommandResponse, game::GameError> {
    game::GameApplicationService::preview_bank_product(payload)
}
#[tauri::command]
fn game_open_bank_credit(
    payload: game::BankProductRequest,
) -> Result<game::GameCommandResponse, game::GameError> {
    game::GameApplicationService::bank_open(payload, false)
}
#[tauri::command]
fn game_open_bank_deposit(
    payload: game::BankProductRequest,
) -> Result<game::GameCommandResponse, game::GameError> {
    game::GameApplicationService::bank_open(payload, true)
}
#[tauri::command]
fn game_process_bank_events(
    payload: game::BankProcessRequest,
) -> Result<game::GameCommandResponse, game::GameError> {
    game::GameApplicationService::process_bank_events(payload.auto_pay)
}
#[tauri::command]
fn game_make_bank_loan_payment() -> Result<game::GameCommandResponse, game::GameError> {
    game::GameApplicationService::bank_close(false, false, false)
}
#[tauri::command]
fn game_partially_repay_bank_credit(
    payload: game::BankAmountRequest,
) -> Result<game::GameCommandResponse, game::GameError> {
    game::GameApplicationService::bank_amount(payload, false)
}
#[tauri::command]
fn game_repay_bank_credit() -> Result<game::GameCommandResponse, game::GameError> {
    game::GameApplicationService::bank_close(false, false, false)
}
#[tauri::command]
fn game_top_up_bank_deposit(
    payload: game::BankAmountRequest,
) -> Result<game::GameCommandResponse, game::GameError> {
    game::GameApplicationService::bank_amount(payload, true)
}
#[tauri::command]
fn game_withdraw_bank_deposit(
    payload: game::BankWithdrawRequest,
) -> Result<game::GameCommandResponse, game::GameError> {
    game::GameApplicationService::bank_close(true, false, payload.allow_early)
}
#[tauri::command]
fn game_withdraw_bank_interest() -> Result<game::GameCommandResponse, game::GameError> {
    game::GameApplicationService::bank_close(true, true, false)
}

fn require_projects_owner(connection: &rusqlite::Connection) -> Result<(), String> {
    let owner: String = connection
        .query_row(
            "SELECT owner FROM storage_ownership WHERE subsystem='projects'",
            [],
            |row| row.get(0),
        )
        .map_err(|error| format!("Не удалось проверить ownership проектов: {error}"))?;
    if owner != "sqlite" {
        return Err("Проекты ещё не переведены в SQLite authoritative storage.".to_string());
    }
    Ok(())
}

fn now_from_database(connection: &rusqlite::Connection) -> Result<String, String> {
    connection
        .query_row("SELECT strftime('%Y-%m-%dT%H:%M:%SZ','now')", [], |row| {
            row.get(0)
        })
        .map_err(|error| error.to_string())
}

fn project_payload(
    connection: &mut rusqlite::Connection,
    project_id: &str,
) -> Result<serde_json::Value, String> {
    let mut repository = ProjectsRepository::new(connection);
    let project = repository
        .get_project(project_id)
        .map_err(|error| error.to_string())?
        .ok_or_else(|| "Проект не найден.".to_string())?;
    let stages = repository
        .list_stages(project_id)
        .map_err(|error| error.to_string())?;
    let mut payload = project.payload;
    let stages_payload = stages
        .into_iter()
        .map(|stage| {
            let mut value = stage.payload;
            let entries = repository
                .list_progress(project_id, Some(&stage.id))
                .map_err(|error| error.to_string())?;
            value["progress_entries"] =
                serde_json::Value::Array(entries.into_iter().map(|entry| entry.payload).collect());
            value["parent_project_id"] = serde_json::Value::String(project_id.to_string());
            Ok(value)
        })
        .collect::<Result<Vec<_>, String>>()?;
    let project_entries = repository
        .list_progress(project_id, None)
        .map_err(|error| error.to_string())?;
    payload["progress_entries"] = serde_json::Value::Array(
        project_entries
            .into_iter()
            .map(|entry| entry.payload)
            .collect(),
    );
    payload["stages"] = serde_json::Value::Array(stages_payload);
    Ok(payload)
}

fn refresh_project_totals(
    connection: &mut rusqlite::Connection,
    project_id: &str,
) -> Result<(), String> {
    let mut repository = ProjectsRepository::new(connection);
    let project = repository
        .get_project(project_id)
        .map_err(|error| error.to_string())?
        .ok_or_else(|| "Проект не найден.".to_string())?;
    let stages = repository
        .list_stages(project_id)
        .map_err(|error| error.to_string())?;
    let total: f64 = stages
        .iter()
        .map(|stage| {
            stage
                .payload
                .get("total")
                .and_then(|value| value.as_f64())
                .unwrap_or(0.0)
        })
        .sum();
    let mut payload = project.payload;
    payload["stages"] =
        serde_json::Value::Array(stages.into_iter().map(|stage| stage.payload).collect());
    let stages_enabled = payload
        .get("stages")
        .and_then(serde_json::Value::as_array)
        .is_some_and(|stages| !stages.is_empty());
    payload["stages_enabled"] = stages_enabled.into();
    payload["total"] = total.into();
    payload["progress"] = if project.infinite || project.goal.unwrap_or(0.0) <= 0.0 {
        0.0.into()
    } else {
        (total / project.goal.unwrap_or(1.0) * 100.0).into()
    };
    repository
        .update_project_payload(project_id, &payload)
        .map_err(|error| error.to_string())?;
    Ok(())
}

fn refresh_project_totals_in_transaction(
    transaction: &rusqlite::Transaction<'_>,
    project_id: &str,
) -> Result<(), String> {
    let (payload_json, goal, infinite): (String, Option<f64>, bool) = transaction
        .query_row(
            "SELECT payload_json, goal, infinite FROM projects WHERE id=?1",
            [project_id],
            |row| Ok((row.get(0)?, row.get(1)?, row.get(2)?)),
        )
        .map_err(|error| error.to_string())?;
    let mut payload: serde_json::Value = serde_json::from_str(&payload_json)
        .map_err(|error| format!("Некорректный payload проекта: {error}"))?;
    let mut stages = transaction
        .prepare("SELECT payload_json FROM stages WHERE project_id=?1 ORDER BY id")
        .map_err(|error| error.to_string())?
        .query_map([project_id], |row| row.get::<_, String>(0))
        .map_err(|error| error.to_string())?
        .map(|row| {
            row.map_err(|error| error.to_string())
                .and_then(|json| serde_json::from_str(&json).map_err(|error| error.to_string()))
        })
        .collect::<Result<Vec<serde_json::Value>, String>>()?;
    let total = stages.iter().fold(0.0, |sum, stage| {
        sum + stage
            .get("total")
            .and_then(serde_json::Value::as_f64)
            .unwrap_or(0.0)
    });
    payload["stages"] = serde_json::Value::Array(std::mem::take(&mut stages));
    payload["stages_enabled"] = payload
        .get("stages")
        .and_then(serde_json::Value::as_array)
        .is_some_and(|items| !items.is_empty())
        .into();
    payload["total"] = total.into();
    payload["progress"] = if infinite || goal.unwrap_or(0.0) <= 0.0 {
        0.0.into()
    } else {
        (total / goal.unwrap_or(1.0) * 100.0).into()
    };
    transaction
        .execute(
            "UPDATE projects SET updated_at=strftime('%Y-%m-%dT%H:%M:%SZ','now'), payload_json=?1 WHERE id=?2",
            rusqlite::params![payload.to_string(), project_id],
        )
        .map_err(|error| error.to_string())?;
    Ok(())
}

fn append_event(
    repository: &mut ProjectsRepository<'_>,
    event_id: &str,
    event_type: &str,
    project_id: &str,
    stage_id: Option<&str>,
    progress_id: Option<&str>,
    delta_symbols: Option<f64>,
) -> Result<(), String> {
    append_event_with_context(
        repository,
        event_id,
        event_type,
        project_id,
        stage_id,
        progress_id,
        delta_symbols,
        serde_json::json!({"source": "desktop", "version": 1}),
    )
}

fn append_event_with_context(
    repository: &mut ProjectsRepository<'_>,
    event_id: &str,
    event_type: &str,
    project_id: &str,
    stage_id: Option<&str>,
    progress_id: Option<&str>,
    delta_symbols: Option<f64>,
    context: serde_json::Value,
) -> Result<(), String> {
    repository
        .append_domain_event(
            event_id,
            event_type,
            project_id,
            stage_id,
            progress_id,
            None,
            delta_symbols,
            &context,
        )
        .map_err(|error| error.to_string())
}

fn open_settings_database() -> Result<rusqlite::Connection, String> {
    let database = sqlite_data_root()?.join("nfprogress.db");
    sqlite::open_database(&database).map_err(|error| error.to_string())
}

fn open_notes_database(write: bool) -> Result<rusqlite::Connection, String> {
    let database = sqlite_data_root()?.join("nfprogress.db");
    let _ = write;
    sqlite::open_database(&database)
        .map_err(|error| format!("Не удалось открыть базу данных Notes: {error}"))
}

fn require_sqlite_notes_owner(connection: &rusqlite::Connection) -> Result<(), String> {
    let owner: String = connection
        .query_row(
            "SELECT owner FROM storage_ownership WHERE subsystem = 'notes'",
            [],
            |row| row.get(0),
        )
        .map_err(|error| format!("Не удалось проверить ownership заметок: {error}"))?;
    if owner != "sqlite" {
        return Err("Прямая запись заметок недоступна до завершения миграции.".to_string());
    }
    Ok(())
}

fn require_note_relation(
    connection: &rusqlite::Connection,
    project_id: &str,
    stage_id: Option<&str>,
) -> Result<(), String> {
    let healthy: String = connection
        .query_row(
            "SELECT sync_status FROM mirror_state WHERE id = 1",
            [],
            |row| row.get(0),
        )
        .map_err(|error| format!("Не удалось проверить состояние SQLite mirror: {error}"))?;
    if healthy != "healthy" {
        return Err("SQLite mirror проектов недоступен для проверки связи заметки.".to_string());
    }
    connection
        .query_row(
            "SELECT 1 FROM projects WHERE id = ?1",
            [project_id],
            |_row| Ok(()),
        )
        .map_err(|_| "Проект больше не существует.".to_string())?;
    if let Some(stage_id) = stage_id {
        let parent: String = connection
            .query_row(
                "SELECT project_id FROM stages WHERE id = ?1",
                [stage_id],
                |row| row.get(0),
            )
            .map_err(|_| "Этап больше не существует.".to_string())?;
        if parent != project_id {
            return Err("Этап не относится к указанному проекту.".to_string());
        }
    }
    Ok(())
}

fn require_note_writable(
    connection: &rusqlite::Connection,
    project_id: &str,
    stage_id: Option<&str>,
) -> Result<(), String> {
    let project_status: String = connection
        .query_row(
            "SELECT status FROM projects WHERE id = ?1",
            [project_id],
            |row| row.get(0),
        )
        .map_err(|error| error.to_string())?;
    if project_status == "завершен" {
        return Err("Заметки завершённого проекта доступны только для просмотра.".to_string());
    }
    if let Some(stage_id) = stage_id {
        let stage_status: String = connection
            .query_row(
                "SELECT status FROM stages WHERE id = ?1",
                [stage_id],
                |row| row.get(0),
            )
            .map_err(|error| error.to_string())?;
        if stage_status == "завершен" {
            return Err("Заметки завершённого этапа доступны только для просмотра.".to_string());
        }
    }
    Ok(())
}

fn note_time(connection: &rusqlite::Connection) -> Result<String, String> {
    connection
        .query_row("SELECT strftime('%Y-%m-%dT%H:%M:%SZ', 'now')", [], |row| {
            row.get(0)
        })
        .map_err(|error| error.to_string())
}

fn raw_note_id(note_id: &str, aggregate: bool) -> &str {
    if aggregate {
        note_id.rsplit(':').next().unwrap_or(note_id)
    } else {
        note_id
    }
}

fn new_note_id() -> Result<String, String> {
    let mut bytes = [0_u8; 16];
    getrandom::fill(&mut bytes).map_err(|error| error.to_string())?;
    let mut value = String::with_capacity(32);
    for byte in bytes {
        write!(&mut value, "{byte:02x}").expect("writing to a String cannot fail");
    }
    Ok(value)
}

fn decorate_note(
    connection: &rusqlite::Connection,
    mut note: serde_json::Value,
    aggregate: bool,
) -> Result<serde_json::Value, String> {
    let object = note
        .as_object_mut()
        .ok_or_else(|| "Некорректный payload заметки.".to_string())?;
    let project_id = object
        .get("project_id")
        .and_then(|value| value.as_str())
        .ok_or_else(|| "У заметки отсутствует project_id.".to_string())?;
    let stage_id = object
        .get("stage_id")
        .and_then(|value| value.as_str())
        .map(str::to_string);
    let project_status: String = connection
        .query_row(
            "SELECT status FROM projects WHERE id = ?1",
            [project_id],
            |row| row.get(0),
        )
        .map_err(|error| error.to_string())?;
    let (owner_type, owner_id, stage_name, owner_order, stage_status) = if let Some(stage_id) =
        stage_id.as_deref()
    {
        let (name, status): (String, String) = connection
            .query_row(
                "SELECT name, status FROM stages WHERE id = ?1",
                [stage_id],
                |row| Ok((row.get(0)?, row.get(1)?)),
            )
            .map_err(|error| error.to_string())?;
        let order: i64 = connection
            .query_row(
                "SELECT COUNT(*) FROM stages WHERE project_id = ?1 AND rowid <= (SELECT rowid FROM stages WHERE id = ?2)",
                rusqlite::params![project_id, stage_id],
                |row| row.get(0),
            )
            .map_err(|error| error.to_string())?;
        (
            "stage",
            stage_id.to_string(),
            Some(name),
            order,
            Some(status),
        )
    } else {
        ("project", project_id.to_string(), None, 0, None)
    };
    if aggregate {
        let raw_id = object
            .get("id")
            .and_then(|value| value.as_str())
            .unwrap_or_default();
        object.insert(
            "id".to_string(),
            serde_json::Value::String(format!("{owner_type}:{owner_id}:{raw_id}")),
        );
    }
    object.insert(
        "owner_type".to_string(),
        serde_json::Value::String(owner_type.to_string()),
    );
    object.insert("owner_id".to_string(), serde_json::Value::String(owner_id));
    object.insert(
        "owner_order".to_string(),
        serde_json::Value::Number(owner_order.into()),
    );
    object.insert(
        "stage_name".to_string(),
        stage_name.map_or(serde_json::Value::Null, serde_json::Value::String),
    );
    let content = object
        .get("content")
        .and_then(|value| value.as_str())
        .unwrap_or_default();
    if object.get("source_type").and_then(|value| value.as_str()) == Some("mindmap") {
        let title = object
            .get("title")
            .and_then(|value| value.as_str())
            .unwrap_or_default();
        let display = if title.is_empty() {
            content
                .lines()
                .find(|line| !line.trim().is_empty())
                .unwrap_or("Заметка карты")
                .chars()
                .take(100)
                .collect()
        } else {
            title.to_string()
        };
        object.insert(
            "display_title".to_string(),
            serde_json::Value::String(display),
        );
        object.insert("system_tags".to_string(), serde_json::json!(["карта"]));
    } else {
        object.insert(
            "display_title".to_string(),
            object
                .get("title")
                .cloned()
                .unwrap_or(serde_json::Value::String(String::new())),
        );
        object.insert("system_tags".to_string(), serde_json::json!([]));
    }
    object.insert(
        "read_only".to_string(),
        serde_json::Value::Bool(
            project_status == "завершен" || stage_status.as_deref() == Some("завершен"),
        ),
    );
    Ok(note)
}

#[tauri::command]
fn list_notes(project_id: String, stage_id: Option<String>) -> Result<serde_json::Value, String> {
    let connection = open_notes_database(false)?;
    require_sqlite_notes_owner(&connection)?;
    let mut notes = Vec::new();
    if let Some(stage_id) = stage_id.as_deref() {
        let mut statement = connection.prepare("SELECT payload_json FROM notes WHERE project_id = ?1 AND stage_id = ?2 ORDER BY json_extract(payload_json, '$.archived'), json_extract(payload_json, '$.pinned') DESC, json_extract(payload_json, '$.sort_order'), json_extract(payload_json, '$.created_at'), rowid").map_err(|error| error.to_string())?;
        for row in statement
            .query_map(rusqlite::params![project_id, stage_id], |row| {
                row.get::<_, String>(0)
            })
            .map_err(|error| error.to_string())?
        {
            let payload = row.map_err(|error| error.to_string())?;
            notes.push(
                serde_json::from_str::<serde_json::Value>(&payload)
                    .map_err(|error| error.to_string())?,
            );
        }
    } else {
        let mut statement = connection.prepare("SELECT payload_json FROM notes WHERE project_id = ?1 ORDER BY json_extract(payload_json, '$.archived'), json_extract(payload_json, '$.pinned') DESC, json_extract(payload_json, '$.sort_order'), json_extract(payload_json, '$.created_at'), rowid").map_err(|error| error.to_string())?;
        for row in statement
            .query_map(rusqlite::params![project_id], |row| row.get::<_, String>(0))
            .map_err(|error| error.to_string())?
        {
            let payload = row.map_err(|error| error.to_string())?;
            notes.push(
                serde_json::from_str::<serde_json::Value>(&payload)
                    .map_err(|error| error.to_string())?,
            );
        }
    }
    let aggregate = stage_id.is_none();
    let notes = notes
        .into_iter()
        .map(|note| decorate_note(&connection, note, aggregate))
        .collect::<Result<Vec<_>, _>>()?;
    let stages = if aggregate {
        let mut rows = connection
            .prepare("SELECT id, name FROM stages WHERE project_id = ?1 ORDER BY rowid")
            .map_err(|error| error.to_string())?;
        let values = rows.query_map([&project_id], |row| Ok(serde_json::json!({"id": row.get::<_, String>(0)?, "name": row.get::<_, String>(1)?})))
            .map_err(|error| error.to_string())?.map(|row| row.map_err(|error| error.to_string())).collect::<Result<Vec<_>, _>>()?
            ;
        values
    } else {
        Vec::new()
    };
    let status: String = connection
        .query_row(
            "SELECT status FROM projects WHERE id = ?1",
            [&project_id],
            |row| row.get(0),
        )
        .map_err(|error| error.to_string())?;
    Ok(
        serde_json::json!({"notes": notes, "read_only": status == "завершен", "context": {"hasStages": !stages.is_empty(), "stages": stages}}),
    )
}

#[tauri::command]
fn get_note(
    project_id: String,
    note_id: String,
    stage_id: Option<String>,
) -> Result<Option<serde_json::Value>, String> {
    let response = list_notes(project_id, stage_id.clone())?;
    let notes = response
        .get("notes")
        .and_then(|value| value.as_array())
        .cloned()
        .unwrap_or_default();
    Ok(notes.into_iter().find(|note| {
        let id = note.get("id").and_then(|value| value.as_str());
        id == Some(note_id.as_str())
            || (stage_id.is_none()
                && id.is_some_and(|value| value.ends_with(&format!(":{note_id}"))))
    }))
}

#[tauri::command]
fn create_note(project_id: String, stage_id: Option<String>) -> Result<serde_json::Value, String> {
    let mut connection = open_notes_database(true)?;
    require_sqlite_notes_owner(&connection)?;
    require_note_relation(&connection, &project_id, stage_id.as_deref())?;
    require_note_writable(&connection, &project_id, stage_id.as_deref())?;
    let now = note_time(&connection)?;
    let id = new_note_id()?;
    let sort_order: i64 = connection.query_row(
        "SELECT COALESCE(MAX(json_extract(payload_json, '$.sort_order')), -1) + 1 FROM notes WHERE project_id = ?1",
        [&project_id], |row| row.get(0),
    ).map_err(|error| error.to_string())?;
    let payload = serde_json::json!({"id": id, "project_id": project_id, "stage_id": stage_id, "title": "", "content": "", "content_format": "html", "checklist": [], "color": "default", "pinned": false, "archived": false, "sort_order": sort_order, "tags": [], "source_type": "project", "source_map_id": null, "source_node_id": null, "created_at": now, "updated_at": now, "revision": 0, "metadata": {}});
    let tx = connection
        .transaction()
        .map_err(|error| error.to_string())?;
    tx.execute("INSERT INTO notes(id, project_id, stage_id, updated_at, payload_json) VALUES(?1, ?2, ?3, ?4, ?5)", rusqlite::params![id, project_id, stage_id, now, payload.to_string()]).map_err(|error| error.to_string())?;
    tx.commit().map_err(|error| error.to_string())?;
    get_note(project_id, id, stage_id)?.ok_or_else(|| "Созданная заметка не найдена.".to_string())
}

#[tauri::command]
fn update_note(
    project_id: String,
    note_id: String,
    patch: serde_json::Value,
    stage_id: Option<String>,
) -> Result<serde_json::Value, String> {
    let mut connection = open_notes_database(true)?;
    require_sqlite_notes_owner(&connection)?;
    require_note_relation(&connection, &project_id, stage_id.as_deref())?;
    require_note_writable(&connection, &project_id, stage_id.as_deref())?;
    let raw_id = raw_note_id(&note_id, stage_id.is_none()).to_string();
    let mut note: serde_json::Value = connection
        .query_row(
            "SELECT payload_json FROM notes WHERE id = ?1 AND project_id = ?2",
            rusqlite::params![raw_id, project_id],
            |row| row.get::<_, String>(0),
        )
        .map_err(|_| "Заметка больше не существует.".to_string())
        .and_then(|value| serde_json::from_str(&value).map_err(|error| error.to_string()))?;
    let note_stage_id = note
        .get("stage_id")
        .and_then(|value| value.as_str())
        .map(str::to_string);
    require_note_relation(&connection, &project_id, note_stage_id.as_deref())?;
    require_note_writable(&connection, &project_id, note_stage_id.as_deref())?;
    let patch = patch
        .as_object()
        .ok_or_else(|| "Некорректные данные заметки.".to_string())?;
    let target = note
        .as_object_mut()
        .ok_or_else(|| "Некорректный payload заметки.".to_string())?;
    for key in patch.keys() {
        if !matches!(
            key.as_str(),
            "title" | "content" | "tags" | "checklist" | "color" | "pinned" | "archived"
        ) {
            return Err(format!("Недопустимое поле заметки: {key}"));
        }
    }
    for (key, value) in patch {
        match key.as_str() {
            "title" | "content" | "color" => {
                let text = value
                    .as_str()
                    .unwrap_or_else(|| if value.is_null() { "" } else { "\0" });
                if text.contains('\0') {
                    return Err(format!("Поле {key} имеет неверный тип."));
                }
                let limit = if key == "title" { 500 } else { 300_000 };
                if text.chars().count() > limit {
                    return Err(if key == "content" {
                        "Текст заметки слишком длинный.".to_string()
                    } else {
                        "Заголовок заметки слишком длинный.".to_string()
                    });
                }
                let normalized = if key == "color"
                    && !matches!(
                        text,
                        "default"
                            | "coral"
                            | "orange"
                            | "yellow"
                            | "green"
                            | "teal"
                            | "blue"
                            | "purple"
                            | "pink"
                            | "brown"
                            | "gray"
                    ) {
                    "default"
                } else {
                    text
                };
                target.insert(
                    key.clone(),
                    serde_json::Value::String(normalized.to_string()),
                );
            }
            "tags" => {
                if value.is_null() {
                    target.insert(key.clone(), serde_json::json!([]));
                } else if let Some(tags) = value.as_array() {
                    if tags.iter().any(|tag| !tag.is_string()) {
                        return Err(format!("Поле {key} имеет неверный тип."));
                    }
                    target.insert(key.clone(), value.clone());
                } else {
                    return Err(format!("Поле {key} имеет неверный тип."));
                }
            }
            "checklist" => {
                if value.is_null() || value.is_array() {
                    target.insert(
                        key.clone(),
                        if value.is_null() {
                            serde_json::json!([])
                        } else {
                            value.clone()
                        },
                    );
                } else {
                    return Err(format!("Поле {key} имеет неверный тип."));
                }
            }
            "pinned" | "archived" => {
                if value.is_null() {
                    target.insert(key.clone(), serde_json::Value::Bool(false));
                } else if value.is_boolean() {
                    target.insert(key.clone(), value.clone());
                } else {
                    return Err(format!("Поле {key} имеет неверный тип."));
                }
            }
            _ => unreachable!("validated note patch key"),
        }
    }
    let now = note_time(&connection)?;
    let revision = target
        .get("revision")
        .and_then(|value| value.as_i64())
        .unwrap_or(0)
        .saturating_add(1);
    target.insert("revision".to_string(), revision.into());
    target.insert(
        "updated_at".to_string(),
        serde_json::Value::String(now.clone()),
    );
    let tx = connection
        .transaction()
        .map_err(|error| error.to_string())?;
    tx.execute(
        "UPDATE notes SET updated_at = ?1, payload_json = ?2 WHERE id = ?3 AND project_id = ?4",
        rusqlite::params![now, note.to_string(), raw_id, project_id],
    )
    .map_err(|error| error.to_string())?;
    tx.commit().map_err(|error| error.to_string())?;
    get_note(project_id, note_id, stage_id)?
        .ok_or_else(|| "Изменённая заметка не найдена.".to_string())
}

#[tauri::command]
fn delete_note(
    project_id: String,
    note_id: String,
    stage_id: Option<String>,
) -> Result<(), String> {
    let mut connection = open_notes_database(true)?;
    require_sqlite_notes_owner(&connection)?;
    require_note_relation(&connection, &project_id, stage_id.as_deref())?;
    require_note_writable(&connection, &project_id, stage_id.as_deref())?;
    let raw_id = raw_note_id(&note_id, stage_id.is_none()).to_string();
    let note_payload: String = connection
        .query_row(
            "SELECT payload_json FROM notes WHERE id = ?1 AND project_id = ?2",
            rusqlite::params![raw_id, project_id],
            |row| row.get(0),
        )
        .map_err(|_| "Заметка больше не существует.".to_string())?;
    let note_stage_id = serde_json::from_str::<serde_json::Value>(&note_payload)
        .map_err(|error| error.to_string())?
        .get("stage_id")
        .and_then(|value| value.as_str())
        .map(str::to_string);
    require_note_relation(&connection, &project_id, note_stage_id.as_deref())?;
    require_note_writable(&connection, &project_id, note_stage_id.as_deref())?;
    let tx = connection
        .transaction()
        .map_err(|error| error.to_string())?;
    let deleted = tx
        .execute(
            "DELETE FROM notes WHERE id = ?1 AND project_id = ?2",
            rusqlite::params![raw_id, project_id],
        )
        .map_err(|error| error.to_string())?;
    if deleted != 1 {
        return Err("Заметка больше не существует.".to_string());
    }
    tx.commit().map_err(|error| error.to_string())
}

#[tauri::command]
fn reorder_notes(
    project_id: String,
    note_ids: Vec<String>,
    stage_id: Option<String>,
) -> Result<serde_json::Value, String> {
    let mut connection = open_notes_database(true)?;
    require_sqlite_notes_owner(&connection)?;
    require_note_relation(&connection, &project_id, stage_id.as_deref())?;
    require_note_writable(&connection, &project_id, stage_id.as_deref())?;
    let aggregate = stage_id.is_none();
    for note_id in &note_ids {
        let raw_id = raw_note_id(note_id, aggregate);
        let payload: Option<String> = connection
            .query_row(
                "SELECT payload_json FROM notes WHERE id = ?1 AND project_id = ?2",
                rusqlite::params![raw_id, project_id],
                |row| row.get(0),
            )
            .optional()
            .map_err(|error| error.to_string())?;
        if let Some(payload) = payload {
            let note = serde_json::from_str::<serde_json::Value>(&payload)
                .map_err(|error| error.to_string())?;
            let note_stage_id = note
                .get("stage_id")
                .and_then(|value| value.as_str())
                .map(str::to_string);
            require_note_relation(&connection, &project_id, note_stage_id.as_deref())?;
            require_note_writable(&connection, &project_id, note_stage_id.as_deref())?;
        }
    }
    let tx = connection
        .transaction()
        .map_err(|error| error.to_string())?;
    for (index, note_id) in note_ids.iter().enumerate() {
        let raw_id = raw_note_id(note_id, aggregate);
        tx.execute(
            "UPDATE notes SET updated_at = strftime('%Y-%m-%dT%H:%M:%SZ', 'now'), payload_json = json_set(payload_json, '$.sort_order', ?1, '$.revision', COALESCE(json_extract(payload_json, '$.revision'), 0) + 1) WHERE id = ?2 AND project_id = ?3",
            rusqlite::params![index as i64, raw_id, project_id],
        ).map_err(|error| error.to_string())?;
    }
    tx.commit().map_err(|error| error.to_string())?;
    list_notes(project_id, stage_id)
}

fn require_sqlite_settings_owner(connection: &rusqlite::Connection) -> Result<(), String> {
    let owner: String = connection
        .query_row(
            "SELECT owner FROM storage_ownership WHERE subsystem = 'settings'",
            [],
            |row| row.get(0),
        )
        .map_err(|error| format!("Не удалось проверить ownership настроек: {error}"))?;
    if owner != "sqlite" {
        return Err("Прямая запись настроек недоступна до завершения миграции.".to_string());
    }
    Ok(())
}

#[tauri::command]
fn get_settings() -> Result<serde_json::Map<String, serde_json::Value>, String> {
    let connection = open_settings_database()?;
    let mut statement = connection
        .prepare("SELECT key, value_json FROM settings")
        .map_err(|error| error.to_string())?;
    let rows = statement
        .query_map([], |row| {
            let key: String = row.get(0)?;
            let value: String = row.get(1)?;
            Ok((key, value))
        })
        .map_err(|error| error.to_string())?;
    let mut values = serde_json::Map::new();
    for row in rows {
        let (key, value) = row.map_err(|error| error.to_string())?;
        let parsed = serde_json::from_str(&value)
            .map_err(|error| format!("Некорректное значение настройки {key}: {error}"))?;
        values.insert(key, parsed);
    }
    Ok(values)
}

#[tauri::command]
fn set_settings(values: serde_json::Map<String, serde_json::Value>) -> Result<(), String> {
    let mut connection = open_settings_database()?;
    require_sqlite_settings_owner(&connection)?;
    let transaction = connection
        .transaction()
        .map_err(|error| error.to_string())?;
    for (key, value) in values {
        let encoded = serde_json::to_string(&value).map_err(|error| error.to_string())?;
        transaction
            .execute(
                concat!(
                    "INSERT INTO settings(key, value_json) VALUES(?1, ?2) ",
                    "ON CONFLICT(key) DO UPDATE SET value_json=excluded.value_json",
                ),
                rusqlite::params![key, encoded],
            )
            .map_err(|error| error.to_string())?;
    }
    transaction.commit().map_err(|error| error.to_string())
}

const BACKEND_HOST: &str = "127.0.0.1";
const BACKEND_START_TIMEOUT: Duration = Duration::from_secs(30);
const UPDATE_MANIFEST_URL: &str = "https://nfproject.ru/app/update_manifest.json";
const UPDATE_MANIFEST_TIMEOUT: Duration = Duration::from_secs(10);
const WINDOW_STATE_FILE: &str = "main-window.json";

#[derive(Clone, Deserialize, Serialize)]
struct MainWindowState {
    width: u32,
    height: u32,
    x: i32,
    y: i32,
}

impl MainWindowState {
    fn is_valid(&self) -> bool {
        (820..=10_000).contains(&self.width) && (600..=10_000).contains(&self.height)
    }
}

fn main_window_state_path(app: &tauri::AppHandle) -> Option<PathBuf> {
    app.path()
        .app_config_dir()
        .ok()
        .map(|directory| directory.join(WINDOW_STATE_FILE))
}

fn restore_main_window_state(app: &tauri::AppHandle) {
    let Some(path) = main_window_state_path(app) else {
        return;
    };
    let Ok(contents) = fs::read_to_string(path) else {
        return;
    };
    let Ok(state) = serde_json::from_str::<MainWindowState>(&contents) else {
        return;
    };
    if !state.is_valid() {
        return;
    }
    let Some(window) = app.get_webview_window("main") else {
        return;
    };
    let _ = window.set_size(PhysicalSize::new(state.width, state.height));
    let _ = window.set_position(PhysicalPosition::new(state.x, state.y));
}

fn save_main_window_state(app: &tauri::AppHandle) {
    let Some(window) = app.get_webview_window("main") else {
        return;
    };
    let (Ok(size), Ok(position)) = (window.inner_size(), window.outer_position()) else {
        return;
    };
    let state = MainWindowState {
        width: size.width,
        height: size.height,
        x: position.x,
        y: position.y,
    };
    if !state.is_valid() {
        return;
    }
    let Some(path) = main_window_state_path(app) else {
        return;
    };
    if fs::create_dir_all(path.parent().unwrap_or_else(|| Path::new("."))).is_err() {
        return;
    }
    let Ok(contents) = serde_json::to_string(&state) else {
        return;
    };
    let _ = fs::write(path, contents);
}

#[derive(Clone, Serialize)]
#[serde(rename_all = "camelCase")]
struct BackendConnection {
    api_base_url: String,
    session_token: String,
    native_updates: bool,
    architecture: String,
    development: bool,
}

#[derive(Default, Deserialize)]
#[serde(rename_all = "camelCase")]
#[serde(default)]
#[serde(deny_unknown_fields)]
struct ProjectMetadataPatch {
    name: Option<String>,
    goal: Option<f64>,
    unit: Option<String>,
    // None means omitted; Some(Null) is an explicit JSON null.
    deadline: MetadataDeadline,
    infinite: Option<bool>,
}

#[derive(Default)]
enum MetadataDeadline {
    #[default]
    Absent,
    Null,
    Value(String),
}

impl<'de> Deserialize<'de> for MetadataDeadline {
    fn deserialize<D>(deserializer: D) -> Result<Self, D::Error>
    where
        D: serde::Deserializer<'de>,
    {
        struct DeadlineVisitor;
        impl<'de> Visitor<'de> for DeadlineVisitor {
            type Value = MetadataDeadline;
            fn expecting(&self, formatter: &mut std::fmt::Formatter) -> std::fmt::Result {
                formatter.write_str("a nullable deadline string")
            }
            fn visit_unit<E>(self) -> Result<Self::Value, E>
            where
                E: de::Error,
            {
                Ok(MetadataDeadline::Null)
            }
            fn visit_none<E>(self) -> Result<Self::Value, E>
            where
                E: de::Error,
            {
                Ok(MetadataDeadline::Null)
            }
            fn visit_str<E>(self, value: &str) -> Result<Self::Value, E>
            where
                E: de::Error,
            {
                Ok(MetadataDeadline::Value(value.to_string()))
            }
            fn visit_string<E>(self, value: String) -> Result<Self::Value, E>
            where
                E: de::Error,
            {
                Ok(MetadataDeadline::Value(value))
            }
        }
        deserializer.deserialize_any(DeadlineVisitor)
    }
}

#[derive(Deserialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
struct AddProjectProgressCommand {
    project_id: String,
    new_total: f64,
}

#[derive(Deserialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
struct AddStageProgressCommand {
    project_id: String,
    stage_id: String,
    new_total: f64,
}

#[derive(Deserialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
struct DeleteProgressCommand {
    project_id: String,
    entry_id: String,
    #[serde(default)]
    stage_id: Option<String>,
}

#[derive(Deserialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
struct CreateStageCommand {
    name: String,
    goal: Option<f64>,
    #[serde(default)]
    infinite: bool,
    #[serde(default)]
    total: f64,
    deadline: Option<String>,
    #[serde(default)]
    personal_goal: f64,
    #[serde(default = "default_true")]
    streak_enabled: bool,
    #[serde(default = "default_true")]
    auto_freeze: bool,
    #[serde(default)]
    work_method: String,
}

#[derive(Deserialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
struct CreateProjectCommand {
    name: String,
    goal: Option<f64>,
    #[serde(default)]
    infinite: bool,
    #[serde(default)]
    total: f64,
    deadline: Option<String>,
    #[serde(default)]
    personal_goal: f64,
    #[serde(default = "default_true")]
    streak_enabled: bool,
    #[serde(default = "default_true")]
    auto_freeze: bool,
    #[serde(default)]
    work_method: String,
    #[serde(default = "default_unit")]
    unit: String,
    #[serde(default)]
    stages_enabled: bool,
    #[serde(default)]
    combine_stage_mindmaps: bool,
    cover_image: Option<String>,
    folder_id: Option<String>,
    #[serde(default)]
    stages: Vec<CreateStageCommand>,
}

#[derive(Deserialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
struct EntityUpdateCommand {
    name: Option<String>,
    goal: Option<f64>,
    infinite: Option<bool>,
    total: Option<f64>,
    deadline: Option<String>,
    personal_goal: Option<f64>,
    streak_enabled: Option<bool>,
    auto_freeze: Option<bool>,
    work_method: Option<String>,
    #[serde(default)]
    recalculate_plan: bool,
    #[serde(default)]
    confirm_daily_goal_increase: bool,
}

#[derive(Deserialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
struct ProjectUpdateCommand {
    name: Option<String>,
    goal: Option<f64>,
    infinite: Option<bool>,
    total: Option<f64>,
    deadline: Option<String>,
    personal_goal: Option<f64>,
    streak_enabled: Option<bool>,
    unit: Option<String>,
    auto_freeze: Option<bool>,
    work_method: Option<String>,
    stages_enabled: Option<bool>,
    combine_stage_mindmaps: Option<bool>,
    cover_image: Option<String>,
    folder_id: Option<Option<String>>,
}

#[derive(Deserialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
struct ArchiveProjectCommand {
    project_id: String,
    archived: bool,
}

#[derive(Deserialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
struct ProjectIdCommand {
    project_id: String,
}

#[derive(Deserialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
struct StageIdCommand {
    project_id: String,
    stage_id: String,
}

#[derive(Deserialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
struct ReorderStagesCommand {
    project_id: String,
    stage_ids: Vec<String>,
}

fn default_true() -> bool {
    true
}
fn default_unit() -> String {
    "symbols".to_string()
}

#[derive(Clone, Serialize)]
#[serde(rename_all = "camelCase")]
struct MacosUpdateProgress {
    downloaded_bytes: u64,
    total_bytes: u64,
}

#[derive(Default)]
struct BackendState {
    child: Mutex<Option<CommandChild>>,
    connection: Mutex<Option<BackendConnection>>,
    startup_error: Mutex<Option<String>>,
}

impl BackendState {
    fn record_error(&self, message: String) {
        if let Ok(mut connection) = self.connection.lock() {
            *connection = None;
        }
        if let Ok(mut error) = self.startup_error.lock() {
            *error = Some(message);
        }
    }
}

#[tauri::command]
fn backend_connection(state: State<'_, BackendState>) -> Result<BackendConnection, String> {
    if let Ok(connection) = state.connection.lock() {
        if let Some(connection) = connection.as_ref() {
            return Ok(connection.clone());
        }
    }
    state
        .startup_error
        .lock()
        .ok()
        .and_then(|error| error.clone())
        .map_or_else(
            || Err("Локальный backend nfprogress ещё не готов.".to_string()),
            Err,
        )
}

async fn backend_json_request<T: serde::Serialize>(
    state: State<'_, BackendState>,
    method: reqwest::Method,
    path: String,
    body: T,
) -> Result<serde_json::Value, String> {
    let connection = state
        .connection
        .lock()
        .map_err(|_| "Не удалось получить соединение с локальным backend.".to_string())?
        .clone()
        .ok_or_else(|| "Локальный backend nfprogress ещё не готов.".to_string())?;
    let response = reqwest::Client::new()
        .request(method, format!("{}{path}", connection.api_base_url))
        .header("X-NFProgress-Token", connection.session_token)
        .json(&body)
        .send()
        .await
        .map_err(|error| format!("Не удалось выполнить project metadata command: {error}"))?;
    let status = response.status();
    let payload = response
        .json::<serde_json::Value>()
        .await
        .map_err(|error| format!("Некорректный ответ project metadata command: {error}"))?;
    if !status.is_success() {
        return Err(payload
            .get("detail")
            .and_then(|detail| detail.get("message"))
            .and_then(serde_json::Value::as_str)
            .unwrap_or("Project metadata command завершился ошибкой.")
            .to_string());
    }
    Ok(payload)
}

fn encode_path_segment(value: &str) -> String {
    value.bytes().fold(String::new(), |mut encoded, byte| {
        if byte.is_ascii_alphanumeric() || b"-._~".contains(&byte) {
            encoded.push(byte as char);
        } else {
            write!(&mut encoded, "%{byte:02X}").expect("writing to a String cannot fail");
        }
        encoded
    })
}

#[tauri::command]
fn update_project_metadata(
    project_id: String,
    patch: ProjectMetadataPatch,
) -> Result<serde_json::Value, String> {
    let mut connection = open_projects_database()?;
    require_projects_owner(&connection)?;
    if patch
        .name
        .as_deref()
        .is_some_and(|value| value.trim().is_empty())
    {
        return Err("Название проекта не может быть пустым.".to_string());
    }
    if patch
        .unit
        .as_deref()
        .is_some_and(|value| !valid_unit(value))
    {
        return Err("Неизвестная единица прогресса.".to_string());
    }
    if patch
        .goal
        .is_some_and(|value| !value.is_finite() || value <= 0.0)
    {
        return Err("Цель должна быть конечной и больше нуля.".to_string());
    }
    let deadline = match patch.deadline {
        MetadataDeadline::Absent => None,
        MetadataDeadline::Null => Some(None),
        MetadataDeadline::Value(value) => Some(Some(value)),
    };
    let mut repository = ProjectsRepository::new(&mut connection);
    let updated = repository
        .update_project_metadata(
            &project_id,
            &ProjectMetadataUpdate {
                name: patch.name.map(|value| value.trim().to_string()),
                goal: patch.goal,
                unit: patch.unit,
                status: None,
                infinite: patch.infinite,
                deadline,
            },
        )
        .map_err(|error| error.to_string())?;
    drop(repository);
    let _ = updated;
    project_payload(&mut connection, &project_id)
}

#[tauri::command]
fn reorder_projects(project_ids: Vec<String>) -> Result<serde_json::Value, String> {
    let mut connection = open_projects_database()?;
    require_projects_owner(&connection)?;
    let mut repository = ProjectsRepository::new(&mut connection);
    if project_ids.is_empty()
        || project_ids
            .iter()
            .collect::<std::collections::HashSet<_>>()
            .len()
            != project_ids.len()
    {
        return Err("Порядок должен содержать известные проекты без повторений.".to_string());
    }
    let existing = repository
        .get_project_order()
        .map_err(|error| error.to_string())?;
    if project_ids.iter().any(|id| !existing.contains(id)) {
        return Err("Порядок должен содержать только известные проекты.".to_string());
    }
    let requested: std::collections::HashSet<&str> =
        project_ids.iter().map(String::as_str).collect();
    let mut normalized = existing.clone();
    let visible_positions = normalized
        .iter()
        .enumerate()
        .filter_map(|(index, id)| requested.contains(id.as_str()).then_some(index))
        .collect::<Vec<_>>();
    for (position, project_id) in visible_positions.into_iter().zip(project_ids.iter()) {
        normalized[position] = project_id.clone();
    }
    repository
        .update_project_order(&normalized)
        .map_err(|error| error.to_string())?;
    drop(repository);
    let ids = project_ids
        .iter()
        .map(|id| project_payload(&mut connection, id))
        .collect::<Result<Vec<_>, _>>()?;
    Ok(serde_json::Value::Array(ids))
}

fn validate_progress_command(
    project_id: &str,
    new_total: f64,
    stage_id: Option<&str>,
) -> Result<(), String> {
    if project_id.is_empty() || stage_id.is_some_and(str::is_empty) {
        return Err("Идентификатор проекта или этапа не может быть пустым.".to_string());
    }
    if !new_total.is_finite() || new_total < 0.0 {
        return Err("Новое общее значение должно быть конечным и неотрицательным.".to_string());
    }
    Ok(())
}

fn valid_unit(value: &str) -> bool {
    matches!(value, "symbols" | "A4" | "author_list" | "ficbook_pages")
}

fn unit_factor(value: &str) -> Option<f64> {
    match value {
        "symbols" => Some(1.0),
        "A4" => Some(1800.0),
        "author_list" => Some(40000.0),
        "ficbook_pages" => Some(4500.0),
        _ => None,
    }
}

fn normalized_total(value: f64, unit: &str) -> Result<f64, String> {
    if !value.is_finite() || value < 0.0 {
        return Err("Значение должно быть конечным и неотрицательным.".to_string());
    }
    Ok(if unit == "author_list" {
        value
    } else {
        value.ceil()
    })
}

fn entity_payload(
    id: String,
    name: String,
    goal: Option<f64>,
    infinite: bool,
    total: f64,
    deadline: Option<String>,
    unit: String,
    work_method: String,
    personal_goal: f64,
    project_id: Option<String>,
) -> serde_json::Value {
    let progress = if infinite || goal.unwrap_or(0.0) <= 0.0 {
        0.0
    } else {
        total / goal.unwrap_or(1.0) * 100.0
    };
    serde_json::json!({
        "id": id, "name": name, "goal": if infinite { serde_json::Value::Null } else { goal.map_or(serde_json::Value::Null, serde_json::Value::from) },
        "infinite": infinite, "total": total, "progress": progress, "deadline": deadline,
        "status": "активен", "unit": unit, "created_at": null, "updated_at": null,
        "notes_updated_at": null, "mindmap_updated_at": null, "completed_at": null,
        "personal_goal": personal_goal, "today_goal": null, "planning_date": null,
        "plan_daily_goal": null, "added_today": 0, "remaining": if infinite { serde_json::Value::Null } else { serde_json::json!((goal.unwrap_or(total) - total).max(0.0)) },
        "streak_enabled": true, "streak_status": "No", "streak_length": 0, "max_streak": 0,
        "auto_freeze": true, "progress_entries": [], "project_notes": [], "mindmap": null,
        "stages": [], "stages_enabled": false, "combine_stage_mindmaps": false,
        "cover_image": null, "folder_id": null, "sync_available": work_method == "sync",
        "work_method": work_method, "parent_project_id": project_id
    })
}

#[tauri::command]
fn create_project(command: CreateProjectCommand) -> Result<serde_json::Value, String> {
    let mut connection = open_projects_database()?;
    require_projects_owner(&connection)?;
    let name = command.name.trim().to_string();
    if name.is_empty() {
        return Err("Название проекта не может быть пустым.".to_string());
    }
    if connection
        .query_row("SELECT 1 FROM projects WHERE name=?1", [&name], |_| Ok(()))
        .optional()
        .map_err(|error| error.to_string())?
        .is_some()
    {
        return Err("Проект с таким названием уже существует.".to_string());
    }
    if let Some(folder_id) = command.folder_id.as_deref() {
        if connection
            .query_row(
                "SELECT 1 FROM project_folders WHERE id=?1",
                [folder_id],
                |_| Ok(()),
            )
            .optional()
            .map_err(|error| error.to_string())?
            .is_none()
        {
            return Err("Папка не найдена.".to_string());
        }
    }
    if !valid_unit(&command.unit) {
        return Err("Неизвестная единица прогресса.".to_string());
    }
    if !matches!(command.work_method.as_str(), "" | "manual" | "sync" | "app") {
        return Err("Неизвестный метод работы с проектом.".to_string());
    }
    let work_method = if command.work_method.is_empty() {
        "manual".to_string()
    } else {
        command.work_method.clone()
    };
    let total = normalized_total(command.total, &command.unit)?;
    let goal = if command.infinite {
        None
    } else {
        Some(
            command
                .goal
                .ok_or_else(|| "Цель должна быть больше нуля.".to_string())?,
        )
    };
    let goal = goal
        .map(|value| normalized_total(value, &command.unit))
        .transpose()?;
    if goal.is_some_and(|value| value <= 0.0) {
        return Err("Цель должна быть больше нуля.".to_string());
    }
    let personal_goal = normalized_total(command.personal_goal, &command.unit)?;
    let id = new_note_id()?;
    let now = now_from_database(&connection)?;
    let mut payload = entity_payload(
        id.clone(),
        name.clone(),
        goal,
        command.infinite,
        total,
        command.deadline.clone(),
        command.unit.clone(),
        work_method.clone(),
        personal_goal,
        None,
    );
    payload["created_at"] = serde_json::Value::String(now.clone());
    payload["updated_at"] = serde_json::Value::String(now.clone());
    payload["streak_enabled"] = serde_json::Value::Bool(command.streak_enabled);
    payload["auto_freeze"] = serde_json::Value::Bool(command.auto_freeze);
    payload["stages_enabled"] =
        serde_json::Value::Bool(command.stages_enabled || !command.stages.is_empty());
    payload["combine_stage_mindmaps"] = serde_json::Value::Bool(
        command.combine_stage_mindmaps && (!command.stages.is_empty() || command.stages_enabled),
    );
    payload["cover_image"] = command
        .cover_image
        .clone()
        .map_or(serde_json::Value::Null, serde_json::Value::String);
    payload["folder_id"] = command
        .folder_id
        .clone()
        .map_or(serde_json::Value::Null, serde_json::Value::String);
    let mut stages = Vec::new();
    let mut stage_records = Vec::new();
    for stage in command.stages {
        let stage_name = stage.name.trim().to_string();
        if stage_name.is_empty() {
            return Err("Название этапа не может быть пустым.".to_string());
        }
        let stage_total = normalized_total(stage.total, &command.unit)?;
        let stage_goal = if stage.infinite {
            None
        } else {
            Some(normalized_total(
                stage
                    .goal
                    .ok_or_else(|| "Цель этапа должна быть больше нуля.".to_string())?,
                &command.unit,
            )?)
        };
        let stage_id = new_note_id()?;
        let mut stage_payload = entity_payload(
            stage_id.clone(),
            stage_name,
            stage_goal,
            stage.infinite,
            stage_total,
            stage.deadline,
            command.unit.clone(),
            if stage.work_method.is_empty() {
                "manual".to_string()
            } else {
                stage.work_method
            },
            stage.personal_goal,
            Some(id.clone()),
        );
        stage_payload["created_at"] = serde_json::Value::String(now.clone());
        stage_payload["updated_at"] = serde_json::Value::String(now.clone());
        stage_payload["streak_enabled"] = serde_json::Value::Bool(stage.streak_enabled);
        stage_payload["auto_freeze"] = serde_json::Value::Bool(stage.auto_freeze);
        stages.push(stage_payload.clone());
        stage_records.push(StageRecord {
            id: stage_id,
            project_id: id.clone(),
            name: stage_payload["name"]
                .as_str()
                .unwrap_or_default()
                .to_string(),
            goal: stage_goal,
            infinite: stage.infinite,
            unit: command.unit.clone(),
            status: "активен".to_string(),
            created_at: Some(now.clone()),
            updated_at: Some(now.clone()),
            payload: stage_payload,
        });
    }
    payload["stages"] = serde_json::Value::Array(stages);
    let order_position: i64 = connection
        .query_row(
            "SELECT COALESCE(MAX(position), -1) + 1 FROM project_order",
            [],
            |row| row.get(0),
        )
        .map_err(|error| error.to_string())?;
    let mut repository = ProjectsRepository::new(&mut connection);
    repository
        .insert_aggregate(&ProjectAggregate {
            project: ProjectRecord {
                id: id.clone(),
                name,
                goal,
                infinite: command.infinite,
                unit: command.unit,
                status: "активен".to_string(),
                created_at: Some(now.clone()),
                updated_at: Some(now),
                payload,
            },
            stages: stage_records,
            progress: Vec::<ProgressRecord>::new(),
            order_position,
        })
        .map_err(|error| error.to_string())?;
    if let Some(folder_id) = command.folder_id {
        repository
            .set_project_folder(&id, Some(&folder_id))
            .map_err(|error| error.to_string())?;
    }
    drop(repository);
    project_payload(&mut connection, &id)
}

#[tauri::command]
fn update_project(
    project_id: String,
    patch: ProjectUpdateCommand,
) -> Result<serde_json::Value, String> {
    let mut connection = open_projects_database()?;
    require_projects_owner(&connection)?;
    let mut repository = ProjectsRepository::new(&mut connection);
    let current = repository
        .get_project(&project_id)
        .map_err(|error| error.to_string())?
        .ok_or_else(|| "Проект не найден.".to_string())?;
    let folder_id = patch.folder_id;
    if let Some(Some(folder_id)) = folder_id.as_ref() {
        if !repository
            .project_folder_exists(folder_id)
            .map_err(|error| error.to_string())?
        {
            return Err("Папка не найдена.".to_string());
        }
    }
    let mut payload = current.payload;
    let object = payload
        .as_object_mut()
        .ok_or_else(|| "Некорректный payload проекта.".to_string())?;
    if let Some(name) = patch.name {
        if name.trim().is_empty() {
            return Err("Название проекта не может быть пустым.".to_string());
        }
        object.insert("name".into(), name.trim().into());
    }
    if let Some(unit) = patch.unit {
        if !valid_unit(&unit) {
            return Err("Неизвестная единица прогресса.".to_string());
        }
        object.insert("unit".into(), unit.into());
    }
    for (key, value) in [
        ("goal", patch.goal.map(serde_json::Value::from)),
        ("total", patch.total.map(serde_json::Value::from)),
        (
            "personal_goal",
            patch.personal_goal.map(serde_json::Value::from),
        ),
    ] {
        if let Some(value) = value {
            if !value
                .as_f64()
                .is_some_and(|number| number.is_finite() && number >= 0.0)
            {
                return Err("Значение должно быть конечным и неотрицательным.".to_string());
            }
            object.insert(key.into(), value);
        }
    }
    if let Some(infinite) = patch.infinite {
        object.insert("infinite".into(), infinite.into());
        if infinite {
            object.insert("goal".into(), serde_json::Value::Null);
        }
    }
    if let Some(deadline) = patch.deadline {
        object.insert("deadline".into(), deadline.into());
    }
    if let Some(value) = patch.personal_goal {
        object.insert("personal_goal".into(), value.into());
    }
    if let Some(value) = patch.streak_enabled {
        object.insert("streak_enabled".into(), value.into());
    }
    if let Some(value) = patch.auto_freeze {
        object.insert("auto_freeze".into(), value.into());
    }
    if let Some(value) = patch.work_method {
        if !matches!(value.as_str(), "manual" | "sync" | "app") {
            return Err("Неизвестный метод работы с проектом.".to_string());
        }
        object.insert("work_method".into(), value.clone().into());
        object.insert("sync_available".into(), (value == "sync").into());
    }
    if let Some(value) = patch.stages_enabled {
        object.insert("stages_enabled".into(), value.into());
    }
    if let Some(value) = patch.combine_stage_mindmaps {
        object.insert("combine_stage_mindmaps".into(), value.into());
    }
    if let Some(value) = patch.cover_image {
        object.insert("cover_image".into(), value.into());
    }
    if let Some(folder_id) = folder_id.as_ref() {
        object.insert(
            "folder_id".into(),
            folder_id
                .clone()
                .map_or(serde_json::Value::Null, serde_json::Value::String),
        );
    }
    repository
        .update_project_payload(&project_id, &payload)
        .map_err(|error| error.to_string())?;
    if let Some(folder_id) = folder_id {
        repository
            .set_project_folder(&project_id, folder_id.as_deref())
            .map_err(|error| error.to_string())?;
    }
    drop(repository);
    project_payload(&mut connection, &project_id)
}

#[tauri::command]
fn create_stage(
    project_id: String,
    command: CreateStageCommand,
) -> Result<serde_json::Value, String> {
    let mut connection = open_projects_database()?;
    require_projects_owner(&connection)?;
    let now = now_from_database(&connection)?;
    let mut repository = ProjectsRepository::new(&mut connection);
    let project = repository
        .get_project(&project_id)
        .map_err(|error| error.to_string())?
        .ok_or_else(|| "Проект не найден.".to_string())?;
    if project.status == "завершен" {
        return Err("Завершённый проект доступен только для просмотра.".to_string());
    }
    let name = command.name.trim().to_string();
    if name.is_empty() {
        return Err("Название этапа не может быть пустым.".to_string());
    }
    if repository
        .list_stages(&project_id)
        .map_err(|error| error.to_string())?
        .iter()
        .any(|stage| stage.name == name)
    {
        return Err("Этап с таким названием уже существует.".to_string());
    }
    if !valid_unit(&project.unit) {
        return Err("Неизвестная единица прогресса.".to_string());
    }
    let stage_id = new_note_id()?;
    let total = normalized_total(command.total, &project.unit)?;
    let goal = if command.infinite {
        None
    } else {
        Some(normalized_total(
            command
                .goal
                .ok_or_else(|| "Цель этапа должна быть больше нуля.".to_string())?,
            &project.unit,
        )?)
    };
    let method = if command.work_method.is_empty() {
        "manual".to_string()
    } else {
        command.work_method
    };
    if !matches!(method.as_str(), "manual" | "sync" | "app") {
        return Err("Неизвестный метод работы с этапом.".to_string());
    }
    let mut payload = entity_payload(
        stage_id.clone(),
        name.clone(),
        goal,
        command.infinite,
        total,
        command.deadline,
        project.unit.clone(),
        method.clone(),
        command.personal_goal,
        Some(project_id.clone()),
    );
    payload["created_at"] = now.clone().into();
    payload["updated_at"] = now.clone().into();
    payload["streak_enabled"] = command.streak_enabled.into();
    payload["auto_freeze"] = command.auto_freeze.into();
    let stage = StageRecord {
        id: stage_id,
        project_id: project_id.clone(),
        name,
        goal,
        infinite: command.infinite,
        unit: project.unit.clone(),
        status: "активен".to_string(),
        created_at: Some(now.clone()),
        updated_at: Some(now),
        payload,
    };
    repository
        .insert_stage(&stage)
        .map_err(|error| error.to_string())?;
    let mut project_payload_value = project.payload;
    project_payload_value["stages_enabled"] = true.into();
    project_payload_value["stages"] = serde_json::Value::Array(
        repository
            .list_stages(&project_id)
            .map_err(|error| error.to_string())?
            .into_iter()
            .map(|stage| stage.payload)
            .collect(),
    );
    repository
        .update_project_payload(&project_id, &project_payload_value)
        .map_err(|error| error.to_string())?;
    drop(repository);
    refresh_project_totals(&mut connection, &project_id)?;
    project_payload(&mut connection, &project_id)
}

#[tauri::command]
fn update_stage(
    project_id: String,
    stage_id: String,
    patch: EntityUpdateCommand,
) -> Result<serde_json::Value, String> {
    let mut connection = open_projects_database()?;
    require_projects_owner(&connection)?;
    let mut repository = ProjectsRepository::new(&mut connection);
    let _project = repository
        .get_project(&project_id)
        .map_err(|error| error.to_string())?
        .ok_or_else(|| "Проект не найден.".to_string())?;
    let current = repository
        .get_stage(&stage_id)
        .map_err(|error| error.to_string())?
        .ok_or_else(|| "Этап не найден.".to_string())?;
    if current.project_id != project_id {
        return Err("Этап не относится к указанному проекту.".to_string());
    }
    let mut payload = current.payload;
    if let Some(name) = patch.name {
        if name.trim().is_empty() {
            return Err("Название этапа не может быть пустым.".to_string());
        }
        payload["name"] = name.trim().into();
    }
    if let Some(goal) = patch.goal {
        payload["goal"] = normalized_total(goal, &current.unit)?.into();
    }
    if let Some(infinite) = patch.infinite {
        payload["infinite"] = infinite.into();
        if infinite {
            payload["goal"] = serde_json::Value::Null;
        }
    }
    if let Some(total) = patch.total {
        payload["total"] = normalized_total(total, &current.unit)?.into();
    }
    if let Some(value) = patch.deadline {
        payload["deadline"] = value.into();
    }
    if let Some(value) = patch.personal_goal {
        payload["personal_goal"] = normalized_total(value, &current.unit)?.into();
    }
    if let Some(value) = patch.streak_enabled {
        payload["streak_enabled"] = value.into();
    }
    if let Some(value) = patch.auto_freeze {
        payload["auto_freeze"] = value.into();
    }
    if let Some(value) = patch.work_method {
        if !matches!(value.as_str(), "manual" | "sync" | "app") {
            return Err("Неизвестный метод работы с этапом.".to_string());
        }
        payload["work_method"] = value.clone().into();
        payload["sync_available"] = (value == "sync").into();
    }
    let infinite = payload
        .get("infinite")
        .and_then(|value| value.as_bool())
        .unwrap_or(current.infinite);
    let goal = if infinite {
        None
    } else {
        payload
            .get("goal")
            .and_then(|value| value.as_f64())
            .or(current.goal)
    };
    let update = StageUpdate {
        name: payload
            .get("name")
            .and_then(|value| value.as_str())
            .unwrap_or(&current.name)
            .to_string(),
        goal,
        infinite,
        unit: current.unit.clone(),
        status: current.status.clone(),
        payload,
    };
    repository
        .update_stage(&stage_id, &update)
        .map_err(|error| error.to_string())?;
    drop(repository);
    refresh_project_totals(&mut connection, &project_id)?;
    project_payload(&mut connection, &project_id)
}

#[tauri::command]
fn delete_stage(command: StageIdCommand) -> Result<(), String> {
    let mut connection = open_projects_database()?;
    require_projects_owner(&connection)?;
    let mut repository = ProjectsRepository::new(&mut connection);
    let stage = repository
        .get_stage(&command.stage_id)
        .map_err(|error| error.to_string())?
        .ok_or_else(|| "Этап не найден.".to_string())?;
    if stage.project_id != command.project_id {
        return Err("Этап не относится к указанному проекту.".to_string());
    }
    repository
        .delete_stage_with_notes(&command.stage_id, &command.project_id)
        .map_err(|error| error.to_string())?;
    drop(repository);
    refresh_project_totals(&mut connection, &command.project_id)
}

#[tauri::command]
fn reorder_stages(command: ReorderStagesCommand) -> Result<serde_json::Value, String> {
    let mut connection = open_projects_database()?;
    require_projects_owner(&connection)?;
    let mut repository = ProjectsRepository::new(&mut connection);
    repository
        .update_stage_order(&command.project_id, &command.stage_ids)
        .map_err(|error| error.to_string())?;
    drop(repository);
    project_payload(&mut connection, &command.project_id)
}

#[tauri::command]
fn set_project_archived(command: ArchiveProjectCommand) -> Result<serde_json::Value, String> {
    let mut connection = open_projects_database()?;
    require_projects_owner(&connection)?;
    let mut repository = ProjectsRepository::new(&mut connection);
    let current = repository
        .get_project(&command.project_id)
        .map_err(|error| error.to_string())?
        .ok_or_else(|| "Проект не найден.".to_string())?;
    if current.status == "завершен" {
        return Err("Завершённый проект нельзя архивировать или активировать.".to_string());
    }
    let mut payload = current.payload;
    payload["status"] = if command.archived {
        "в архиве".into()
    } else {
        "активен".into()
    };
    if command.archived {
        payload["deadline"] = serde_json::Value::Null;
        payload["streaks"] = serde_json::json!([]);
    }
    repository
        .update_project_payload(&command.project_id, &payload)
        .map_err(|error| error.to_string())?;
    append_event(
        &mut repository,
        &format!(
            "project-status:{}:{}",
            command.project_id,
            if command.archived {
                "archived"
            } else {
                "active"
            }
        ),
        "ProjectStatusChanged",
        &command.project_id,
        None,
        None,
        None,
    )?;
    drop(repository);
    project_payload(&mut connection, &command.project_id)
}

#[tauri::command]
fn complete_project(command: ProjectIdCommand) -> Result<serde_json::Value, String> {
    let mut connection = open_projects_database()?;
    require_projects_owner(&connection)?;
    let now = now_from_database(&connection)?;
    let mut repository = ProjectsRepository::new(&mut connection);
    let current = repository
        .get_project(&command.project_id)
        .map_err(|error| error.to_string())?
        .ok_or_else(|| "Проект не найден.".to_string())?;
    if current.infinite {
        return Err("Бесконечный проект нельзя завершить по числовой цели.".to_string());
    }
    if current.goal.is_some_and(|goal| {
        current
            .payload
            .get("total")
            .and_then(|value| value.as_f64())
            .unwrap_or(0.0)
            < goal
    }) {
        return Err("Сначала достигните цели проекта.".to_string());
    }
    let mut payload = current.payload;
    payload["status"] = "завершен".into();
    payload["completed_at"] = now.clone().into();
    repository
        .update_project_payload(&command.project_id, &payload)
        .map_err(|error| error.to_string())?;
    append_event_with_context(
        &mut repository,
        &format!("project-completed:{}", command.project_id),
        "ProjectCompleted",
        &command.project_id,
        None,
        None,
        None,
        serde_json::json!({
            "source": "desktop",
            "version": 1,
            "key": format!("project:{}", command.project_id),
            "total_symbols": payload.get("total").and_then(serde_json::Value::as_f64).unwrap_or(0.0),
        }),
    )?;
    drop(repository);
    project_payload(&mut connection, &command.project_id)
}

#[tauri::command]
fn complete_stage(command: StageIdCommand) -> Result<serde_json::Value, String> {
    let mut connection = open_projects_database()?;
    require_projects_owner(&connection)?;
    let now = now_from_database(&connection)?;
    let mut repository = ProjectsRepository::new(&mut connection);
    let stage = repository
        .get_stage(&command.stage_id)
        .map_err(|error| error.to_string())?
        .ok_or_else(|| "Этап не найден.".to_string())?;
    if stage.project_id != command.project_id {
        return Err("Этап не относится к указанному проекту.".to_string());
    }
    if stage.infinite {
        return Err("Бесконечный этап нельзя завершить по числовой цели.".to_string());
    }
    if stage.goal.is_some_and(|goal| {
        stage
            .payload
            .get("total")
            .and_then(|value| value.as_f64())
            .unwrap_or(0.0)
            < goal
    }) {
        return Err("Сначала достигните цели этапа.".to_string());
    }
    let mut payload = stage.payload;
    payload["status"] = "завершен".into();
    payload["completed_at"] = now.into();
    let total_symbols = payload
        .get("total")
        .and_then(serde_json::Value::as_f64)
        .unwrap_or(0.0);
    let update = StageUpdate {
        name: payload["name"].as_str().unwrap_or_default().to_string(),
        goal: stage.goal,
        infinite: stage.infinite,
        unit: stage.unit,
        status: "завершен".to_string(),
        payload,
    };
    repository
        .update_stage(&command.stage_id, &update)
        .map_err(|error| error.to_string())?;
    append_event_with_context(
        &mut repository,
        &format!("stage-completed:{}", command.stage_id),
        "StageCompleted",
        &command.project_id,
        Some(&command.stage_id),
        None,
        None,
        serde_json::json!({
            "source": "desktop",
            "version": 1,
            "key": format!("stage:{}:{}", command.project_id, command.stage_id),
            "total_symbols": total_symbols,
        }),
    )?;
    drop(repository);
    project_payload(&mut connection, &command.project_id)
}

#[tauri::command]
fn delete_project(command: ProjectIdCommand) -> Result<(), String> {
    let mut connection = open_projects_database()?;
    require_projects_owner(&connection)?;
    ProjectsRepository::new(&mut connection)
        .delete_project_with_notes(&command.project_id)
        .map_err(|error| error.to_string())
}

#[tauri::command]
fn list_project_folders() -> Result<Vec<serde_json::Value>, String> {
    let connection = open_projects_database()?;
    require_projects_owner(&connection)?;
    let mut statement = connection
        .prepare("SELECT id,name FROM project_folders ORDER BY position,id")
        .map_err(|error| error.to_string())?;
    let rows = statement
        .query_map([], |row| {
            Ok(serde_json::json!({"id": row.get::<_, String>(0)?, "name": row.get::<_, String>(1)?}))
        })
        .map_err(|error| error.to_string())?
        .map(|row| row.map_err(|error| error.to_string()))
        .collect();
    rows
}

#[tauri::command]
fn create_project_folder(name: String) -> Result<serde_json::Value, String> {
    let mut connection = open_projects_database()?;
    require_projects_owner(&connection)?;
    let name = name.trim().to_string();
    if name.is_empty() || name.chars().count() > 120 {
        return Err("Название папки некорректно.".to_string());
    }
    let id = new_note_id()?;
    let position: i64 = connection
        .query_row(
            "SELECT COALESCE(MAX(position),-1)+1 FROM project_folders",
            [],
            |row| row.get(0),
        )
        .map_err(|error| error.to_string())?;
    connection
        .execute(
            "INSERT INTO project_folders(id,name,position,payload_json) VALUES(?1,?2,?3,?4)",
            rusqlite::params![
                id,
                name,
                position,
                serde_json::json!({"id":id,"name":name}).to_string()
            ],
        )
        .map_err(|error| error.to_string())?;
    Ok(serde_json::json!({"id": id, "name": name}))
}

#[tauri::command]
fn update_project_folder(folder_id: String, name: String) -> Result<serde_json::Value, String> {
    let mut connection = open_projects_database()?;
    require_projects_owner(&connection)?;
    let name = name.trim().to_string();
    if name.is_empty() || name.chars().count() > 120 {
        return Err("Название папки некорректно.".to_string());
    }
    let changed = connection.execute("UPDATE project_folders SET name=?1,payload_json=json_set(payload_json,'$.name',?1) WHERE id=?2", rusqlite::params![name,folder_id]).map_err(|error| error.to_string())?;
    if changed != 1 {
        return Err("Папка не найдена.".to_string());
    }
    Ok(serde_json::json!({"id":folder_id,"name":name}))
}

#[tauri::command]
fn delete_project_folder(folder_id: String) -> Result<(), String> {
    let mut connection = open_projects_database()?;
    require_projects_owner(&connection)?;
    let tx = connection
        .transaction()
        .map_err(|error| error.to_string())?;
    tx.execute("UPDATE projects SET payload_json=json_set(payload_json,'$.folder_id',NULL) WHERE id IN (SELECT project_id FROM project_folder_members WHERE folder_id=?1)", [&folder_id]).map_err(|error| error.to_string())?;
    tx.execute(
        "DELETE FROM project_folder_members WHERE folder_id=?1",
        [&folder_id],
    )
    .map_err(|error| error.to_string())?;
    let changed = tx
        .execute("DELETE FROM project_folders WHERE id=?1", [&folder_id])
        .map_err(|error| error.to_string())?;
    if changed != 1 {
        return Err("Папка не найдена.".to_string());
    }
    tx.commit().map_err(|error| error.to_string())
}

#[tauri::command]
fn add_project_progress(command: AddProjectProgressCommand) -> Result<serde_json::Value, String> {
    validate_progress_command(&command.project_id, command.new_total, None)?;
    add_progress_sqlite(command.project_id, None, command.new_total)
}

#[tauri::command]
fn add_stage_progress(command: AddStageProgressCommand) -> Result<serde_json::Value, String> {
    validate_progress_command(
        &command.project_id,
        command.new_total,
        Some(&command.stage_id),
    )?;
    add_progress_sqlite(
        command.project_id,
        Some(command.stage_id),
        command.new_total,
    )
}

#[tauri::command]
fn delete_progress(command: DeleteProgressCommand) -> Result<serde_json::Value, String> {
    if command.project_id.is_empty() || command.entry_id.is_empty() {
        return Err("Идентификаторы проекта и записи не могут быть пустыми.".to_string());
    }
    if command.stage_id.as_deref().is_some_and(str::is_empty) {
        return Err("Идентификатор этапа не может быть пустым.".to_string());
    }
    delete_progress_sqlite(command.project_id, command.entry_id, command.stage_id)
}

fn convert_to_symbols(value: f64, unit: &str) -> Result<f64, String> {
    unit_factor(unit)
        .map(|factor| value * factor)
        .ok_or_else(|| "Неизвестная единица прогресса.".to_string())
}

fn add_progress_sqlite(
    project_id: String,
    stage_id: Option<String>,
    submitted_total: f64,
) -> Result<serde_json::Value, String> {
    let mut connection = open_projects_database()?;
    require_projects_owner(&connection)?;
    let now = now_from_database(&connection)?;
    let repository = ProjectsRepository::new(&mut connection);
    let project = repository
        .get_project(&project_id)
        .map_err(|error| error.to_string())?
        .ok_or_else(|| "Проект не найден.".to_string())?;
    let entity = if let Some(stage_id) = stage_id.as_deref() {
        repository
            .get_stage(stage_id)
            .map_err(|error| error.to_string())?
            .ok_or_else(|| "Этап не найден.".to_string())?
    } else {
        StageRecord {
            id: project.id.clone(),
            project_id: project.id.clone(),
            name: project.name.clone(),
            goal: project.goal,
            infinite: project.infinite,
            unit: project.unit.clone(),
            status: project.status.clone(),
            created_at: project.created_at.clone(),
            updated_at: project.updated_at.clone(),
            payload: project.payload.clone(),
        }
    };
    if entity.project_id != project_id {
        return Err("Этап не относится к указанному проекту.".to_string());
    }
    if entity.status == "завершен" {
        return Err("Завершённая сущность доступна только для просмотра.".to_string());
    }
    let method = entity
        .payload
        .get("work_method")
        .and_then(|value| value.as_str())
        .unwrap_or("manual");
    let binding_exists = repository
        .has_sync_binding(&project_id, stage_id.as_deref())
        .map_err(|error| error.to_string())?;
    if method == "sync" || binding_exists {
        return Err("Включена синхронизация. Ручная запись прогресса недоступна.".to_string());
    }
    if method != "manual" && method != "app" {
        return Err("Этот способ добавления записей сейчас не выбран.".to_string());
    }
    let total = normalized_total(submitted_total, &entity.unit)?;
    let previous = entity
        .payload
        .get("total")
        .and_then(|value| value.as_f64())
        .unwrap_or(0.0);
    let next_symbols = convert_to_symbols(total, &entity.unit)?;
    let previous_symbols = convert_to_symbols(previous, &entity.unit)?;
    let delta = next_symbols - previous_symbols;
    if delta.abs() < 0.009 {
        return Err("Значение не изменилось.".to_string());
    }
    let entry_id = new_note_id()?;
    let goal_symbols = entity
        .goal
        .map(|goal| convert_to_symbols(goal, &entity.unit))
        .transpose()?
        .unwrap_or(0.0);
    let added_progress = if goal_symbols <= 0.0 {
        0.0
    } else {
        delta / goal_symbols * 100.0
    };
    let entry = serde_json::json!({"id": entry_id, "new_total": total, "new_total_symbols": next_symbols, "added": total - previous, "added_symbols": delta, "added_progress": added_progress, "created_at": now});
    let mut payload = entity.payload;
    let entries = payload
        .get("progress_entries")
        .and_then(|value| value.as_array())
        .cloned()
        .unwrap_or_default();
    let mut entries = entries;
    entries.push(entry.clone());
    payload["progress_entries"] = serde_json::Value::Array(entries);
    payload["total"] = total.into();
    payload["progress"] = if entity.infinite || entity.goal.unwrap_or(0.0) <= 0.0 {
        0.0.into()
    } else {
        (total / entity.goal.unwrap_or(1.0) * 100.0).into()
    };
    payload["updated_at"] = now.clone().into();
    drop(repository);
    let tx = connection
        .transaction()
        .map_err(|error| error.to_string())?;
    tx.execute("INSERT INTO progress_entries(id,project_id,stage_id,created_at,added_symbols,added_progress,payload_json) VALUES(?1,?2,?3,?4,?5,?6,?7)", rusqlite::params![entry_id, project_id, stage_id, now, delta, added_progress, entry.to_string()]).map_err(|error| error.to_string())?;
    let position: i64 = tx
        .query_row(
            "SELECT COALESCE(MAX(position),-1)+1 FROM progress_order",
            [],
            |row| row.get(0),
        )
        .map_err(|error| error.to_string())?;
    tx.execute(
        "INSERT INTO progress_order(entry_id,position) VALUES(?1,?2)",
        rusqlite::params![entry_id, position],
    )
    .map_err(|error| error.to_string())?;
    let table = if stage_id.is_some() {
        "stages"
    } else {
        "projects"
    };
    tx.execute(&format!("UPDATE {table} SET goal=?1, infinite=?2, unit=?3, updated_at=?4, payload_json=?5 WHERE id=?6"), rusqlite::params![entity.goal, entity.infinite, entity.unit, now, payload.to_string(), entity.id]).map_err(|error| error.to_string())?;
    if stage_id.is_some() {
        refresh_project_totals_in_transaction(&tx, &project_id)?;
    }
    let game_key = stage_id
        .as_deref()
        .map(|stage| format!("stage:{project_id}:{stage}"))
        .unwrap_or_else(|| format!("project:{project_id}"));
    tx.execute("INSERT OR IGNORE INTO domain_events(event_id,event_type,project_id,stage_id,progress_id,delta_symbols,context_json,created_at) VALUES(?1,'ProgressAdded',?2,?3,?4,?5,?6,?7)", rusqlite::params![format!("progress-added:{entry_id}"), project_id, stage_id, entry_id, delta, serde_json::json!({"source":"desktop","version":1,"key":game_key,"project_progress":payload["progress"]}).to_string(), now]).map_err(|error| error.to_string())?;
    tx.commit().map_err(|error| error.to_string())?;
    let project_value = project_payload(&mut connection, &project_id)?;
    Ok(
        serde_json::json!({"project": project_value, "entry": entry, "added_symbols": delta, "game": null, "warning": null}),
    )
}

fn delete_progress_sqlite(
    project_id: String,
    entry_id: String,
    stage_id: Option<String>,
) -> Result<serde_json::Value, String> {
    let mut connection = open_projects_database()?;
    require_projects_owner(&connection)?;
    let now = now_from_database(&connection)?;
    let mut repository = ProjectsRepository::new(&mut connection);
    let project = repository
        .get_project(&project_id)
        .map_err(|error| error.to_string())?
        .ok_or_else(|| "Проект не найден.".to_string())?;
    let entity_id = stage_id.clone().unwrap_or_else(|| project_id.clone());
    let entity = if let Some(stage_id) = stage_id.as_deref() {
        repository
            .get_stage(stage_id)
            .map_err(|error| error.to_string())?
            .ok_or_else(|| "Этап не найден.".to_string())?
    } else {
        StageRecord {
            id: project.id.clone(),
            project_id: project.id.clone(),
            name: project.name.clone(),
            goal: project.goal,
            infinite: project.infinite,
            unit: project.unit.clone(),
            status: project.status.clone(),
            created_at: project.created_at.clone(),
            updated_at: project.updated_at.clone(),
            payload: project.payload.clone(),
        }
    };
    if entity.project_id != project_id {
        return Err("Этап не относится к указанному проекту.".to_string());
    }
    let mut entries = entity
        .payload
        .get("progress_entries")
        .and_then(|value| value.as_array())
        .cloned()
        .unwrap_or_default();
    let before = entries.len();
    entries.retain(|entry| {
        entry.get("id").and_then(|value| value.as_str()) != Some(entry_id.as_str())
    });
    if entries.len() == before {
        return Err("Запись прогресса не найдена.".to_string());
    }
    let total = entries
        .last()
        .and_then(|entry| entry.get("new_total"))
        .and_then(|value| value.as_f64())
        .unwrap_or(0.0);
    let mut payload = entity.payload;
    payload["progress_entries"] = serde_json::Value::Array(entries);
    payload["total"] = total.into();
    payload["progress"] = if entity.infinite || entity.goal.unwrap_or(0.0) <= 0.0 {
        0.0.into()
    } else {
        (total / entity.goal.unwrap_or(1.0) * 100.0).into()
    };
    drop(repository);
    let tx = connection
        .transaction()
        .map_err(|error| error.to_string())?;
    let deleted = tx.execute("DELETE FROM progress_entries WHERE id=?1 AND project_id=?2 AND (?3 IS NULL OR stage_id=?3)", rusqlite::params![entry_id, project_id, stage_id]).map_err(|error| error.to_string())?;
    if deleted != 1 {
        return Err("Запись прогресса не найдена.".to_string());
    }
    let table = if stage_id.is_some() {
        "stages"
    } else {
        "projects"
    };
    tx.execute(
        &format!("UPDATE {table} SET updated_at=?1,payload_json=?2 WHERE id=?3"),
        rusqlite::params![now, payload.to_string(), entity_id],
    )
    .map_err(|error| error.to_string())?;
    if stage_id.is_some() {
        refresh_project_totals_in_transaction(&tx, &project_id)?;
    }
    tx.execute("INSERT OR IGNORE INTO domain_events(event_id,event_type,project_id,stage_id,progress_id,context_json,created_at) VALUES(?1,'ProgressDeleted',?2,?3,?4,?5,?6)", rusqlite::params![format!("progress-deleted:{entry_id}"), project_id, stage_id, entry_id, serde_json::json!({"source":"desktop","version":1}).to_string(), now]).map_err(|error| error.to_string())?;
    tx.commit().map_err(|error| error.to_string())?;
    Ok(project_payload(&mut connection, &project_id)?)
}

fn sqlite_data_root() -> Result<PathBuf, String> {
    if let Ok(path) = std::env::var("NFPROGRESS_DATA_DIR") {
        return Ok(PathBuf::from(path));
    }
    let home = dirs_fallback_home()?;
    let root = if cfg!(target_os = "windows") {
        std::env::var_os("APPDATA")
            .map(PathBuf::from)
            .unwrap_or_else(|| home.join("AppData").join("Roaming"))
            .join("nfprogress")
    } else if cfg!(target_os = "macos") {
        home.join("Documents").join("nfprogress")
    } else {
        let documents = home.join("Documents");
        if documents.exists() {
            documents.join("nfprogress")
        } else {
            home.join(".local").join("share").join("nfprogress")
        }
    };
    if cfg!(debug_assertions) {
        Ok(root.join("test_data"))
    } else {
        Ok(root)
    }
}

fn dirs_fallback_home() -> Result<PathBuf, String> {
    std::env::var_os("HOME")
        .or_else(|| std::env::var_os("USERPROFILE"))
        .map(PathBuf::from)
        .ok_or_else(|| "Не удалось определить домашнюю директорию пользователя.".to_string())
}

fn read_sqlite_entity_rows(
    connection: &rusqlite::Connection,
    table: &str,
) -> Result<Vec<SqliteEntityRow>, String> {
    let sql = match table {
        "projects" => "SELECT p.id, NULL, p.name, p.goal, p.infinite, p.unit, p.status, p.created_at, p.updated_at, p.payload_json FROM projects p JOIN project_order o ON o.project_id = p.id ORDER BY o.position",
        "stages" => "SELECT s.id, s.project_id, s.name, s.goal, s.infinite, s.unit, s.status, s.created_at, s.updated_at, s.payload_json FROM stages s JOIN stage_order o ON o.stage_id=s.id ORDER BY o.project_id,o.position",
        _ => return Err("Недопустимая таблица SQLite.".to_string()),
    };
    let mut statement = connection.prepare(sql).map_err(|error| error.to_string())?;
    let rows = statement
        .query_map([], |row| {
            Ok(SqliteEntityRow {
                id: row.get(0)?,
                project_id: row.get(1)?,
                name: row.get(2)?,
                goal: row.get(3)?,
                infinite: row.get(4)?,
                unit: row.get(5)?,
                status: row.get(6)?,
                created_at: row.get(7)?,
                updated_at: row.get(8)?,
                payload_json: row.get(9)?,
            })
        })
        .map_err(|error| error.to_string())?;
    rows.map(|row| row.map_err(|error| error.to_string()))
        .collect()
}

#[tauri::command]
fn read_sqlite_projects() -> Result<SqliteProjectReadModel, String> {
    let database = sqlite_data_root()?.join("nfprogress.db");
    let connection = sqlite::open_database(&database).map_err(|error| error.to_string())?;
    require_projects_owner(&connection)?;
    let status: String = connection
        .query_row(
            "SELECT sync_status FROM mirror_state WHERE id = 1",
            [],
            |row| row.get(0),
        )
        .map_err(|error| error.to_string())?;
    if status != "healthy" {
        return Err(format!("SQLite mirror status is {status}"));
    }
    let mut progress = connection
        .prepare("SELECT p.id, p.project_id, p.stage_id, p.created_at, p.added_symbols, p.added_progress, p.payload_json FROM progress_entries p JOIN progress_order o ON o.entry_id=p.id ORDER BY o.position")
        .map_err(|error| error.to_string())?;
    let progress_entries = progress
        .query_map([], |row| {
            Ok(SqliteProgressRow {
                id: row.get(0)?,
                project_id: row.get(1)?,
                stage_id: row.get(2)?,
                created_at: row.get(3)?,
                added_symbols: row.get(4)?,
                added_progress: row.get(5)?,
                payload_json: row.get(6)?,
            })
        })
        .map_err(|error| error.to_string())?
        .map(|row| row.map_err(|error| error.to_string()))
        .collect::<Result<Vec<_>, _>>()?;
    let project_order_rows = connection
        .prepare("SELECT project_id, position FROM project_order ORDER BY position, project_id")
        .map_err(|error| error.to_string())?
        .query_map([], |row| {
            Ok((row.get::<_, i64>(1)?, row.get::<_, String>(0)?))
        })
        .map_err(|error| error.to_string())?
        .collect::<Result<Vec<_>, _>>()
        .map_err(|error| error.to_string())?;
    if project_order_rows
        .iter()
        .enumerate()
        .any(|(expected, (position, _))| *position != expected as i64)
    {
        return Err("SQLite project ordering positions are invalid.".to_string());
    }
    let project_order: Vec<String> = project_order_rows
        .into_iter()
        .map(|(_, project_id)| project_id)
        .collect();
    let project_ids: HashSet<&str> = project_order.iter().map(String::as_str).collect();
    if project_order.len() != project_ids.len() {
        return Err("SQLite project ordering contains duplicates.".to_string());
    }
    let project_rows = read_sqlite_entity_rows(&connection, "projects")?;
    if project_order.len() != project_rows.len()
        || project_rows
            .iter()
            .any(|row| !project_ids.contains(row.id.as_str()))
    {
        return Err("SQLite project ordering is incomplete.".to_string());
    }
    Ok(SqliteProjectReadModel {
        mirror_status: status,
        project_order,
        projects: project_rows,
        stages: read_sqlite_entity_rows(&connection, "stages")?,
        progress_entries,
    })
}

#[tauri::command]
fn projects_storage_owner() -> Result<String, String> {
    let connection = open_projects_database()?;
    connection
        .query_row(
            "SELECT owner FROM storage_ownership WHERE subsystem='projects'",
            [],
            |row| row.get(0),
        )
        .map_err(|error| error.to_string())
}

fn configure_rustls_provider() {
    // The updater plugin installs a provider in release builds. Tauri dev does
    // not load that plugin, so install ring here before reqwest creates TLS.
    let _ = rustls::crypto::ring::default_provider().install_default();
}

#[tauri::command]
async fn fetch_update_manifest() -> Result<serde_json::Value, String> {
    configure_rustls_provider();
    let client = reqwest::Client::builder()
        .connect_timeout(Duration::from_secs(5))
        .timeout(UPDATE_MANIFEST_TIMEOUT)
        .build()
        .map_err(|error| format!("Не удалось настроить проверку обновлений: {error}"))?;
    let response = client
        .get(UPDATE_MANIFEST_URL)
        .send()
        .await
        .map_err(|error| format!("Не удалось получить манифест обновления: {error}"))?
        .error_for_status()
        .map_err(|error| format!("Сервер обновлений вернул ошибку: {error}"))?;
    response
        .json::<serde_json::Value>()
        .await
        .map_err(|error| format!("Манифест обновления имеет неверный формат: {error}"))
}

#[cfg(test)]
mod tests {
    #[cfg(target_os = "macos")]
    use std::io::Write;
    use std::path::Path;
    #[cfg(target_os = "macos")]
    use std::process::{Command, Stdio};

    use super::{
        build_macos_updater_script, configure_rustls_provider, encode_path_segment,
        macos_update_target, AddProjectProgressCommand, AddStageProgressCommand,
        DeleteProgressCommand, ProjectMetadataPatch,
    };

    #[test]
    fn project_metadata_payload_is_narrow_and_encodes_ids() {
        let patch: ProjectMetadataPatch =
            serde_json::from_value(serde_json::json!({"name": "Новый", "deadline": null}))
                .expect("allow-listed metadata must deserialize");
        assert_eq!(patch.name.as_deref(), Some("Новый"));
        assert!(matches!(patch.deadline, super::MetadataDeadline::Null));
        assert!(
            serde_json::from_value::<ProjectMetadataPatch>(serde_json::json!({
                "total": 10
            }))
            .is_err()
        );
        assert_eq!(encode_path_segment("id/ два"), "id%2F%20%D0%B4%D0%B2%D0%B0");
    }

    #[test]
    fn progress_commands_are_strict_and_keep_stage_target_explicit() {
        let project: AddProjectProgressCommand = serde_json::from_value(serde_json::json!({
            "projectId": "project/1",
            "newTotal": 42.5,
        }))
        .expect("project progress command must deserialize");
        assert_eq!(project.project_id, "project/1");
        assert!(
            serde_json::from_value::<AddProjectProgressCommand>(serde_json::json!({
                "projectId": "p",
                "newTotal": 1,
                "stageId": "unexpected",
            }))
            .is_err()
        );

        let stage: AddStageProgressCommand = serde_json::from_value(serde_json::json!({
            "projectId": "p",
            "stageId": "s",
            "newTotal": 42,
        }))
        .expect("stage progress command must deserialize");
        assert_eq!(stage.stage_id, "s");
        assert!(
            serde_json::from_value::<DeleteProgressCommand>(serde_json::json!({
                "projectId": "p",
                "entryId": "e",
                "arbitrarySql": "DELETE FROM progress_entries",
            }))
            .is_err()
        );
    }

    #[test]
    fn progress_command_validation_rejects_invalid_numeric_values() {
        assert!(super::validate_progress_command("p", -1.0, None).is_err());
        assert!(super::validate_progress_command("p", f64::NAN, None).is_err());
        assert!(super::validate_progress_command("p", f64::INFINITY, None).is_err());
        assert!(super::validate_progress_command("p", 1.0, Some("")).is_err());
        assert!(super::validate_progress_command("p", 1.0, Some("s")).is_ok());
    }

    #[test]
    fn update_client_has_a_rustls_crypto_provider() {
        configure_rustls_provider();
        assert!(reqwest::Client::builder().build().is_ok());
    }

    #[test]
    fn macos_updater_can_install_an_app_from_a_nested_dmg() {
        let script = build_macos_updater_script(
            Path::new("/tmp/nfprogress-update.zip"),
            Path::new("/Applications/nfprogress.app"),
            "aabbcc",
            42,
            Path::new("/tmp/nfprogress-update.log"),
            123,
        );

        assert!(script.contains("DMG_PATH=$(find"));
        assert!(script.contains("hdiutil attach \"$DMG_PATH\""));
        assert!(script.contains("find \"$MOUNT_POINT\""));
        assert!(script.contains("ditto \"$NEW_APP\" \"$TARGET_PATH\""));
        assert!(!script.contains("curl "));
    }

    #[cfg(debug_assertions)]
    #[test]
    fn tauri_dev_updates_the_installed_macos_app() {
        assert_eq!(
            macos_update_target(Path::new("/project/target/debug/nfprogress-desktop")),
            Some(Path::new("/Applications/nfprogress.app").to_path_buf()),
        );
    }

    #[test]
    fn packaged_macos_app_is_resolved_from_the_current_executable() {
        assert_eq!(
            macos_update_target(Path::new(
                "/Applications/nfprogress.app/Contents/MacOS/nfprogress-desktop",
            )),
            Some(Path::new("/Applications/nfprogress.app").to_path_buf()),
        );
    }

    #[cfg(target_os = "macos")]
    #[test]
    fn macos_updater_script_has_valid_shell_syntax() {
        let script = build_macos_updater_script(
            Path::new("/tmp/nfprogress-update.zip"),
            Path::new("/Applications/nfprogress.app"),
            "aabbcc",
            42,
            Path::new("/tmp/nfprogress-update.log"),
            123,
        );
        let mut child = Command::new("/bin/sh")
            .arg("-n")
            .stdin(Stdio::piped())
            .spawn()
            .expect("shell must start");
        child
            .stdin
            .take()
            .expect("shell stdin must be piped")
            .write_all(script.as_bytes())
            .expect("script must be written to shell");

        assert!(child.wait().expect("shell must finish").success());
    }
}

fn shell_literal(value: impl AsRef<str>) -> String {
    format!("'{}'", value.as_ref().replace('\'', "'\\''"))
}

fn macos_app_bundle(executable: &Path) -> Option<PathBuf> {
    executable
        .ancestors()
        .find(|path| path.extension().is_some_and(|extension| extension == "app"))
        .map(Path::to_path_buf)
}

fn macos_update_target(executable: &Path) -> Option<PathBuf> {
    macos_app_bundle(executable)
        .or_else(|| cfg!(debug_assertions).then(|| PathBuf::from("/Applications/nfprogress.app")))
}

fn build_macos_updater_script(
    archive_path: &Path,
    target: &Path,
    sha256: &str,
    size: u64,
    log_path: &Path,
    parent_pid: u32,
) -> String {
    let target_name = target.file_name().unwrap_or_default().to_string_lossy();
    format!(
        r#"#!/bin/sh
set -u
ARCHIVE_PATH={archive}
SHA256={sha256}
SIZE={size}
TARGET_PATH={target}
TARGET_NAME={target_name}
PARENT_PID={pid}
LOG_PATH={log_path}
MOUNT_POINT=""

log() {{
    printf '%s %s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$1" >> "$LOG_PATH"
}}

fail() {{
    log "failed: $1"
    if [ -n "$MOUNT_POINT" ]; then
        hdiutil detach "$MOUNT_POINT" >/dev/null 2>&1 || true
    fi
    osascript -e 'display alert "nfprogress" message "Не удалось установить обновление. Подробности: '"$LOG_PATH"'"' >/dev/null 2>&1 || true
    exit 1
}}

log "waiting for application process $PARENT_PID"
while kill -0 "$PARENT_PID" >/dev/null 2>&1; do sleep 1; done
sleep 1

WORK_DIR=$(mktemp -d "${{TMPDIR:-/tmp/}}nfprogress-update.XXXXXX") || fail "Не удалось создать временную папку."
EXTRACT_DIR="$WORK_DIR/extract"
mkdir -p "$EXTRACT_DIR" || fail "Не удалось создать папку распаковки."

log "using downloaded archive $ARCHIVE_PATH"
[ -f "$ARCHIVE_PATH" ] || fail "Скачанный архив обновления не найден."
[ "$(stat -f %z "$ARCHIVE_PATH")" = "$SIZE" ] || fail "Размер архива обновления не совпадает с манифестом."
[ "$(shasum -a 256 "$ARCHIVE_PATH" | awk '{{print $1}}')" = "$SHA256" ] || fail "Контрольная сумма архива обновления не совпадает с манифестом."
ditto -x -k "$ARCHIVE_PATH" "$EXTRACT_DIR" || unzip -q "$ARCHIVE_PATH" -d "$EXTRACT_DIR" || fail "Не удалось распаковать zip-архив."

NEW_APP=$(find "$EXTRACT_DIR" -maxdepth 4 -name "$TARGET_NAME" -type d -print -quit)
if [ -z "$NEW_APP" ]; then
    NEW_APP=$(find "$EXTRACT_DIR" -maxdepth 4 -name "*.app" -type d -print -quit)
fi

if [ -z "$NEW_APP" ]; then
    DMG_PATH=$(find "$EXTRACT_DIR" -maxdepth 4 -name "*.dmg" -type f -print -quit)
    if [ -n "$DMG_PATH" ]; then
        log "mounting $DMG_PATH"
        MOUNT_OUTPUT=$(hdiutil attach "$DMG_PATH" -nobrowse -readonly 2>>"$LOG_PATH") || fail "Не удалось смонтировать dmg."
        MOUNT_POINT=$(printf '%s\n' "$MOUNT_OUTPUT" | awk '/\/Volumes\// {{print substr($0, index($0, "/Volumes/")); exit}}')
        [ -n "$MOUNT_POINT" ] || fail "Не удалось определить точку монтирования dmg."
        NEW_APP=$(find "$MOUNT_POINT" -maxdepth 2 -name "$TARGET_NAME" -type d -print -quit)
        if [ -z "$NEW_APP" ]; then
            NEW_APP=$(find "$MOUNT_POINT" -maxdepth 2 -name "*.app" -type d -print -quit)
        fi
    fi
fi

[ -n "$NEW_APP" ] || fail "В архиве обновления не найден .app."

BACKUP_PATH="$TARGET_PATH.old"
rm -rf "$BACKUP_PATH" || fail "Не удалось удалить старую резервную копию."
if [ -d "$TARGET_PATH" ]; then
    mv "$TARGET_PATH" "$BACKUP_PATH" || fail "Не удалось убрать старое приложение."
fi
ditto "$NEW_APP" "$TARGET_PATH" || {{
    rm -rf "$TARGET_PATH"
    if [ -d "$BACKUP_PATH" ]; then
        mv "$BACKUP_PATH" "$TARGET_PATH"
    fi
    fail "Не удалось скопировать новую версию."
}}
rm -rf "$BACKUP_PATH"

if [ -n "$MOUNT_POINT" ]; then
    hdiutil detach "$MOUNT_POINT" >/dev/null 2>&1 || true
fi
rm -rf "$WORK_DIR"
rm -f "$ARCHIVE_PATH"
log "updated $TARGET_PATH"
open "$TARGET_PATH" || log "failed to reopen $TARGET_PATH"
"#,
        archive = shell_literal(archive_path.to_string_lossy()),
        sha256 = shell_literal(sha256),
        size = size,
        target = shell_literal(target.to_string_lossy()),
        target_name = shell_literal(target_name),
        pid = parent_pid,
        log_path = shell_literal(log_path.to_string_lossy()),
    )
}

fn archive_sha256(path: &Path) -> Result<String, String> {
    let output = Command::new("/usr/bin/shasum")
        .args(["-a", "256"])
        .arg(path)
        .output()
        .map_err(|error| format!("Не удалось проверить SHA-256 обновления: {error}"))?;
    if !output.status.success() {
        return Err("Не удалось проверить SHA-256 обновления.".to_string());
    }
    String::from_utf8(output.stdout)
        .map_err(|error| format!("Некорректный результат проверки SHA-256: {error}"))?
        .split_whitespace()
        .next()
        .map(str::to_string)
        .ok_or_else(|| "Не удалось получить SHA-256 обновления.".to_string())
}

async fn download_macos_update(
    app: &tauri::AppHandle,
    url: &str,
    archive_path: &Path,
    expected_size: u64,
) -> Result<(), String> {
    configure_rustls_provider();
    let result = async {
        let client = reqwest::Client::builder()
            .connect_timeout(Duration::from_secs(20))
            .build()
            .map_err(|error| format!("Не удалось настроить загрузку обновления: {error}"))?;
        let mut response = client
            .get(url)
            .send()
            .await
            .map_err(|error| format!("Не удалось скачать обновление: {error}"))?
            .error_for_status()
            .map_err(|error| format!("Сервер обновлений вернул ошибку: {error}"))?;
        if response
            .content_length()
            .is_some_and(|content_length| content_length > expected_size)
        {
            return Err("Сервер объявил слишком большой размер обновления.".to_string());
        }

        let mut archive = fs::File::create(archive_path)
            .map_err(|error| format!("Не удалось создать архив обновления: {error}"))?;
        let mut downloaded = 0_u64;
        app.emit(
            "macos-update-progress",
            MacosUpdateProgress {
                downloaded_bytes: 0,
                total_bytes: expected_size,
            },
        )
        .map_err(|error| error.to_string())?;
        while let Some(chunk) = response
            .chunk()
            .await
            .map_err(|error| format!("Ошибка загрузки обновления: {error}"))?
        {
            downloaded = downloaded.saturating_add(chunk.len() as u64);
            if downloaded > expected_size {
                return Err("Загрузка превышает размер из манифеста.".to_string());
            }
            archive
                .write_all(&chunk)
                .map_err(|error| format!("Не удалось записать архив обновления: {error}"))?;
            app.emit(
                "macos-update-progress",
                MacosUpdateProgress {
                    downloaded_bytes: downloaded,
                    total_bytes: expected_size,
                },
            )
            .map_err(|error| error.to_string())?;
        }
        archive
            .sync_all()
            .map_err(|error| format!("Не удалось сохранить архив обновления: {error}"))?;
        if downloaded != expected_size {
            return Err(format!(
                "Размер обновления не совпадает: ожидалось {expected_size}, получено {downloaded}."
            ));
        }
        Ok(())
    }
    .await;
    if result.is_err() {
        let _ = fs::remove_file(archive_path);
    }
    result
}

#[tauri::command]
async fn install_macos_update(
    app: tauri::AppHandle,
    url: String,
    sha256: String,
    size: u64,
) -> Result<bool, String> {
    if !url.starts_with("https://nfproject.ru/app/") {
        return Err("Недопустимый адрес обновления macOS.".to_string());
    }
    if sha256.len() != 64 || !sha256.bytes().all(|byte| byte.is_ascii_hexdigit()) || size == 0 {
        return Err("В манифесте отсутствуют данные проверки архива macOS.".to_string());
    }
    // Tauri's PathResolver::executable_dir is the user's bin directory and is
    // unsupported on macOS; current_exe resolves the running app bundle.
    let executable = std::env::current_exe().map_err(|error| error.to_string())?;
    let Some(target) = macos_update_target(&executable) else {
        return Ok(false);
    };
    let update_dir = app
        .path()
        .app_local_data_dir()
        .map_err(|error| error.to_string())?;
    fs::create_dir_all(&update_dir).map_err(|error| error.to_string())?;
    let script_path = update_dir.join("install-update.sh");
    let log_path = update_dir.join("update.log");
    let archive_path = update_dir.join("update.zip");
    download_macos_update(&app, &url, &archive_path, size).await?;
    let actual_sha256 = match archive_sha256(&archive_path) {
        Ok(value) => value,
        Err(error) => {
            let _ = fs::remove_file(&archive_path);
            return Err(error);
        }
    };
    if !actual_sha256.eq_ignore_ascii_case(&sha256) {
        let _ = fs::remove_file(&archive_path);
        return Err("Контрольная сумма архива обновления не совпадает с манифестом.".to_string());
    }
    let script = build_macos_updater_script(
        &archive_path,
        &target,
        &sha256,
        size,
        &log_path,
        std::process::id(),
    );
    if let Err(error) = fs::write(&script_path, script) {
        let _ = fs::remove_file(&archive_path);
        return Err(error.to_string());
    }
    // Keep the updater alive after plugin-process exits the application, matching
    // the detached process used by the legacy macOS updater.
    if let Err(error) = Command::new("/usr/bin/nohup")
        .arg("/bin/sh")
        .arg(&script_path)
        .stdin(Stdio::null())
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .spawn()
    {
        let _ = fs::remove_file(&archive_path);
        return Err(error.to_string());
    }
    Ok(true)
}

fn reserve_loopback_port() -> Result<u16, String> {
    let listener = TcpListener::bind((BACKEND_HOST, 0))
        .map_err(|error| format!("Не удалось выбрать локальный порт: {error}"))?;
    listener
        .local_addr()
        .map(|address| address.port())
        .map_err(|error| format!("Не удалось определить локальный порт: {error}"))
}

fn create_session_token() -> Result<String, String> {
    let mut bytes = [0_u8; 32];
    getrandom::fill(&mut bytes)
        .map_err(|error| format!("Не удалось создать ключ локальной сессии: {error}"))?;
    let mut token = String::with_capacity(bytes.len() * 2);
    for byte in bytes {
        write!(&mut token, "{byte:02x}").expect("writing to a String cannot fail");
    }
    Ok(token)
}

fn native_updates_enabled() -> bool {
    matches!(
        option_env!("NFPROGRESS_UPDATER_ENABLED"),
        Some("1") | Some("true")
    )
}

fn backend_is_healthy(port: u16) -> bool {
    let address = format!("{BACKEND_HOST}:{port}");
    let Ok(socket_address) = address.parse() else {
        return false;
    };
    let Ok(mut stream) = TcpStream::connect_timeout(&socket_address, Duration::from_millis(250))
    else {
        return false;
    };
    let _ = stream.set_read_timeout(Some(Duration::from_millis(500)));
    if stream
        .write_all(b"GET /health HTTP/1.1\r\nHost: 127.0.0.1\r\nConnection: close\r\n\r\n")
        .is_err()
    {
        return false;
    }
    let mut response = [0_u8; 128];
    match stream.read(&mut response) {
        Ok(size) => {
            let status = &response[..size];
            status.starts_with(b"HTTP/1.1 200") || status.starts_with(b"HTTP/1.0 200")
        }
        Err(_) => false,
    }
}

fn wait_for_backend(port: u16) -> Result<(), String> {
    let deadline = Instant::now() + BACKEND_START_TIMEOUT;
    while Instant::now() < deadline {
        if backend_is_healthy(port) {
            return Ok(());
        }
        thread::sleep(Duration::from_millis(100));
    }
    Err("Локальный backend nfprogress не ответил на /health за 30 секунд.".to_string())
}

fn stop_backend(app_handle: &tauri::AppHandle) {
    let state = app_handle.state::<BackendState>();
    if let Ok(mut child) = state.child.lock() {
        if let Some(child) = child.take() {
            let _ = child.kill();
        }
    };
}

pub fn run() {
    let mut builder = tauri::Builder::default()
        .manage(BackendState::default())
        .plugin(tauri_plugin_single_instance::init(|app, _arguments, _cwd| {
            if let Some(window) = app.get_webview_window("main") {
                let _ = window.show();
                let _ = window.set_focus();
            }
        }))
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_clipboard_manager::init())
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_process::init())
        .setup(|app| {
            restore_main_window_state(&app.handle());
            let state = app.state::<BackendState>();
            // F1 makes Rust the canonical schema migrator. Projects remain
            // pickle-authoritative; this only upgrades the shared database.
            if let Err(error) = sqlite::open_database(&sqlite_data_root()?.join("nfprogress.db")) {
                state.record_error(format!("Не удалось подготовить SQLite schema: {error}"));
            }
            let port = match reserve_loopback_port() {
                Ok(port) => port,
                Err(error) => {
                    state.record_error(error);
                    return Ok(());
                }
            };
            let token = match create_session_token() {
                Ok(token) => token,
                Err(error) => {
                    state.record_error(error);
                    return Ok(());
                }
            };

            let command = match app.shell().sidecar("nfprogress-backend") {
                Ok(command) => command,
                Err(error) => {
                    state.record_error(format!("Не удалось найти локальный backend: {error}"));
                    return Ok(());
                }
            };
            let mut arguments = vec![
                "--host".to_string(),
                BACKEND_HOST.to_string(),
                "--port".to_string(),
                port.to_string(),
                "--platform".to_string(),
                "desktop".to_string(),
                "--parent-pid".to_string(),
                std::process::id().to_string(),
                "--log-level".to_string(),
                "warning".to_string(),
            ];
            if cfg!(debug_assertions) {
                // Tauri dev must use the same synchronized test_data copy as
                // ``python main_UI.py``. Release bundles intentionally keep
                // their normal per-user app-data behavior.
                arguments.push("--dev-data".to_string());
            }
            let spawn_result = command
                .args(arguments)
                .env("NFPROGRESS_SESSION_TOKEN", &token)
                .env("NFPROGRESS_TAURI_RUNTIME", "1")
                .env(
                    "NFPROGRESS_ALLOWED_ORIGINS",
                    "tauri://localhost,http://tauri.localhost,https://tauri.localhost,http://localhost:5173,http://127.0.0.1:5173",
                )
                .spawn();
            let (mut events, child) = match spawn_result {
                Ok(result) => result,
                Err(error) => {
                    state.record_error(format!("Не удалось запустить локальный backend: {error}"));
                    return Ok(());
                }
            };

            if let Err(error) = wait_for_backend(port) {
                let _ = child.kill();
                state.record_error(error);
                return Ok(());
            }

            if let Ok(mut connection) = state.connection.lock() {
                *connection = Some(BackendConnection {
                    api_base_url: format!("http://{BACKEND_HOST}:{port}"),
                    session_token: token,
                    native_updates: native_updates_enabled(),
                    architecture: std::env::consts::ARCH.to_string(),
                    development: cfg!(debug_assertions),
                });
            }
            if let Ok(mut managed_child) = state.child.lock() {
                *managed_child = Some(child);
            }

            let app_handle = app.handle().clone();
            tauri::async_runtime::spawn(async move {
                while let Some(event) = events.recv().await {
                    if let CommandEvent::Terminated(payload) = event {
                        let state = app_handle.state::<BackendState>();
                        state.record_error(format!(
                            "Локальный backend завершился (код: {:?}, сигнал: {:?}).",
                            payload.code, payload.signal
                        ));
                        break;
                    }
                }
            });
            Ok(())
        });

    if native_updates_enabled() {
        builder = builder.plugin(tauri_plugin_updater::Builder::new().build());
    }

    let app = builder
        .invoke_handler(tauri::generate_handler![
            backend_connection,
            process_game_events,
            game_state,
            game_notifications,
            mark_game_notification_read,
            mark_all_game_notifications_read,
            game_catalog,
            game_developer_state,
            game_update_developer_profile,
            game_grant_developer_inventory_item,
            game_start_writing_session,
            game_finish_writing_session,
            game_cancel_writing_session,
            game_select_daily_challenge,
            game_start_weekly_challenge,
            game_activate_inspiration_ability,
            game_resolve_creative_event,
            game_select_specialization,
            game_activate_specialization_ability,
            game_increase_skill,
            game_start_quest,
            game_abandon_quest,
            game_buy_item,
            game_sell_item,
            game_use_item,
            game_apply_streak_freeze,
            game_run_lottery,
            game_create_custom_award,
            game_update_custom_award,
            game_delete_custom_award,
            game_buy_custom_award,
            game_sell_custom_award,
            game_use_custom_award,
            game_preview_bank_product,
            game_open_bank_credit,
            game_open_bank_deposit,
            game_process_bank_events,
            game_make_bank_loan_payment,
            game_partially_repay_bank_credit,
            game_repay_bank_credit,
            game_top_up_bank_deposit,
            game_withdraw_bank_deposit,
            game_withdraw_bank_interest,
            read_sqlite_projects,
            projects_storage_owner,
            create_project,
            update_project,
            delete_project,
            set_project_archived,
            complete_project,
            complete_stage,
            create_stage,
            update_stage,
            delete_stage,
            reorder_stages,
            list_project_folders,
            create_project_folder,
            update_project_folder,
            delete_project_folder,
            update_project_metadata,
            reorder_projects,
            add_project_progress,
            add_stage_progress,
            delete_progress,
            get_settings,
            set_settings,
            list_notes,
            get_note,
            create_note,
            update_note,
            delete_note,
            reorder_notes,
            fetch_update_manifest,
            install_macos_update
        ])
        .build(tauri::generate_context!())
        .expect("failed to build the nfprogress desktop application");

    app.run(|app_handle, event| {
        if matches!(event, RunEvent::Exit | RunEvent::ExitRequested { .. }) {
            save_main_window_state(app_handle);
            stop_backend(app_handle);
        }
    });
}
