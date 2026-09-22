//! Transaction-scoped durable Note sync-intent primitives.
//!
//! This module does not seal or upload events. Callers prepare an intent on
//! the same SQLite transaction that will mutate `notes`; schema guards reject
//! bound-project Note writes that do not have an exact prepared intent.

use std::fmt::Write as _;

use rusqlite::{OptionalExtension, Transaction};

const MAX_SYNC_INTEGER: i64 = 9_007_199_254_740_991;

#[derive(Debug)]
pub(crate) enum NoteSyncError {
    Database(rusqlite::Error),
    InvalidSnapshot(&'static str),
    RevisionOverflow,
    LocalOrdinalOverflow,
    MutationGenerationOverflow,
    ConflictingHeads,
    Random(String),
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
            Self::ConflictingHeads => write!(formatter, "Note sync entity has conflicting heads"),
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
            Self::ConflictingHeads => "Обнаружено конфликтующее локальное состояние синхронизации.",
            Self::Database(_) | Self::InvalidSnapshot(_) | Self::Random(_) => {
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

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) enum NoteSyncOperation {
    Upsert,
    Delete,
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

#[cfg(test)]
mod tests {
    use super::*;
    use rusqlite::Connection;

    const DEVICE_ID: &str = "123e4567-e89b-42d3-a456-426614174000";

    fn database() -> Connection {
        let connection = Connection::open_in_memory().unwrap();
        crate::sqlite::apply_migrations(&connection).unwrap();
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
        connection
    }

    fn note(content: &str, revision: i64) -> String {
        serde_json::json!({
            "id":"n", "project_id":"p", "stage_id":null, "title":"",
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
        PrepareNoteIntent {
            project_id: "p",
            entity_id: "n",
            operation: NoteSyncOperation::Upsert,
            updated_at: "2026-09-22T00:00:00Z",
            deleted_at: None,
            snapshot_json: snapshot,
            state_updated_at: "2026-09-22T00:00:00Z",
        }
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
}
