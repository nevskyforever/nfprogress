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

fn open_settings_database() -> Result<rusqlite::Connection, String> {
    let database = sqlite_data_root()?.join("nfprogress.db");
    rusqlite::Connection::open(database).map_err(|error| error.to_string())
}

fn open_notes_database(write: bool) -> Result<rusqlite::Connection, String> {
    let database = sqlite_data_root()?.join("nfprogress.db");
    if !database.is_file() {
        return Err("База данных nfprogress не найдена.".to_string());
    }
    let flags = if write {
        rusqlite::OpenFlags::SQLITE_OPEN_READ_WRITE
    } else {
        rusqlite::OpenFlags::SQLITE_OPEN_READ_ONLY
    };
    rusqlite::Connection::open_with_flags(database, flags)
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
async fn update_project_metadata(
    state: State<'_, BackendState>,
    project_id: String,
    patch: ProjectMetadataPatch,
) -> Result<serde_json::Value, String> {
    let mut body = serde_json::Map::new();
    if let Some(value) = patch.name {
        body.insert("name".into(), value.into());
    }
    if let Some(value) = patch.goal {
        body.insert("goal".into(), value.into());
    }
    if let Some(value) = patch.unit {
        body.insert("unit".into(), value.into());
    }
    match patch.deadline {
        MetadataDeadline::Null => {
            body.insert("deadline".into(), serde_json::Value::Null);
        }
        MetadataDeadline::Value(value) => {
            body.insert("deadline".into(), value.into());
        }
        MetadataDeadline::Absent => {}
    }
    if let Some(value) = patch.infinite {
        body.insert("infinite".into(), value.into());
    }
    backend_json_request(
        state,
        reqwest::Method::PATCH,
        format!(
            "/api/projects/{}/metadata",
            encode_path_segment(&project_id)
        ),
        body,
    )
    .await
}

#[tauri::command]
async fn reorder_projects(
    state: State<'_, BackendState>,
    project_ids: Vec<String>,
) -> Result<serde_json::Value, String> {
    backend_json_request(
        state,
        reqwest::Method::PUT,
        "/api/projects/order".to_string(),
        serde_json::json!({"project_ids": project_ids}),
    )
    .await
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
        "stages" => "SELECT id, project_id, name, goal, infinite, unit, status, created_at, updated_at, payload_json FROM stages ORDER BY rowid",
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
    let connection =
        rusqlite::Connection::open_with_flags(database, rusqlite::OpenFlags::SQLITE_OPEN_READ_ONLY)
            .map_err(|error| error.to_string())?;
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
        .prepare("SELECT id, project_id, stage_id, created_at, added_symbols, added_progress, payload_json FROM progress_entries ORDER BY rowid")
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
        macos_update_target, ProjectMetadataPatch,
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
            read_sqlite_projects,
            update_project_metadata,
            reorder_projects,
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
