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
}
