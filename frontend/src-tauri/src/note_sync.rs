//! Durable Note sync-intent and sealing-lifecycle primitives.
//!
//! Callers prepare plaintext intents in the same SQLite transaction that
//! mutates `notes`. Sealing later replaces that sidecar with an opaque object
//! and advances the existing outbox event atomically; uploads remain outside
//! this module.

use std::fmt::Write as _;

use rusqlite::{Connection, OptionalExtension, Transaction, TransactionBehavior};
use serde::{Deserialize, Serialize};

const MAX_SYNC_INTEGER: i64 = 9_007_199_254_740_991;
const MAX_UNSEALED_INTENT_LIST_LIMIT: u32 = 200;
const MAX_ENCRYPTED_SYNC_CIPHERTEXT_BYTES: usize = 8_388_624;
const SUPPORTED_CRYPTO_VERSION: i64 = 1;
const SUPPORTED_AAD_VERSION: i64 = 1;

#[derive(Debug)]
pub(crate) enum NoteSyncError {
    Database(rusqlite::Error),
    InvalidSnapshot(&'static str),
    RevisionOverflow,
    LocalOrdinalOverflow,
    MutationGenerationOverflow,
    SealAttemptOverflow,
    ConflictingHeads,
    InvalidListLimit,
    InvalidEnvelope(&'static str),
    InvalidSealState(&'static str),
    MissingEvent,
    MissingIntent,
    UnexpectedLifecycle,
    SealedObjectMissing,
    ConflictingEncryptedObject,
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
            Self::SealAttemptOverflow => write!(formatter, "Note sync seal attempt overflow"),
            Self::ConflictingHeads => write!(formatter, "Note sync entity has conflicting heads"),
            Self::InvalidListLimit => write!(formatter, "Invalid Note sync intent list limit"),
            Self::InvalidEnvelope(message) => {
                write!(formatter, "Invalid encrypted Note sync envelope: {message}")
            }
            Self::InvalidSealState(message) => {
                write!(formatter, "Invalid durable Note sealing state: {message}")
            }
            Self::MissingEvent => write!(formatter, "Note sync outbox event does not exist"),
            Self::MissingIntent => write!(formatter, "Unsealed Note sync intent is missing"),
            Self::UnexpectedLifecycle => {
                write!(formatter, "Note sync event has an unexpected lifecycle")
            }
            Self::SealedObjectMissing => {
                write!(formatter, "Sealed Note sync event has no encrypted object")
            }
            Self::ConflictingEncryptedObject => {
                write!(
                    formatter,
                    "Note sync event has a conflicting encrypted object"
                )
            }
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
            Self::SealAttemptOverflow => "Исчерпан диапазон попыток шифрования изменения заметки.",
            Self::ConflictingHeads => "Обнаружено конфликтующее локальное состояние синхронизации.",
            Self::Database(_)
            | Self::InvalidSnapshot(_)
            | Self::InvalidListLimit
            | Self::InvalidEnvelope(_)
            | Self::InvalidSealState(_)
            | Self::MissingEvent
            | Self::MissingIntent
            | Self::UnexpectedLifecycle
            | Self::SealedObjectMissing
            | Self::ConflictingEncryptedObject
            | Self::Random(_) => {
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

#[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize)]
#[serde(rename_all = "snake_case")]
pub(crate) enum NoteSyncOperation {
    Upsert,
    Delete,
}

impl NoteSyncOperation {
    fn from_stored(value: &str) -> Result<Self, NoteSyncError> {
        match value {
            "upsert" => Ok(Self::Upsert),
            "delete" => Ok(Self::Delete),
            _ => Err(NoteSyncError::InvalidSealState("invalid operation")),
        }
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize)]
#[serde(rename_all = "snake_case")]
pub(crate) enum NoteSyncSealState {
    Pending,
    RetryableError,
    Blocked,
    InvariantError,
}

impl NoteSyncSealState {
    fn from_stored(value: &str) -> Result<Self, NoteSyncError> {
        match value {
            "pending" => Ok(Self::Pending),
            "retryable_error" => Ok(Self::RetryableError),
            "blocked" => Ok(Self::Blocked),
            "invariant_error" => Ok(Self::InvariantError),
            _ => Err(NoteSyncError::InvalidSealState("invalid seal state")),
        }
    }
}

#[derive(Clone, Copy, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(rename_all = "snake_case")]
pub(crate) enum NoteSyncSealErrorCode {
    KeyUnavailable,
    PayloadTooLarge,
    EncryptedSyncObjectTooLarge,
    DependencyNotSynced,
    UnsupportedContentFormat,
    InvalidNotePayload,
    CryptoContextInvalid,
    InvalidSyncMetadata,
    InvalidEnvelope,
    MetadataMismatch,
    RuntimeUnavailable,
}

impl NoteSyncSealErrorCode {
    fn as_str(self) -> &'static str {
        match self {
            Self::KeyUnavailable => "key_unavailable",
            Self::PayloadTooLarge => "payload_too_large",
            Self::EncryptedSyncObjectTooLarge => "encrypted_sync_object_too_large",
            Self::DependencyNotSynced => "dependency_not_synced",
            Self::UnsupportedContentFormat => "unsupported_content_format",
            Self::InvalidNotePayload => "invalid_note_payload",
            Self::CryptoContextInvalid => "crypto_context_invalid",
            Self::InvalidSyncMetadata => "invalid_sync_metadata",
            Self::InvalidEnvelope => "invalid_envelope",
            Self::MetadataMismatch => "metadata_mismatch",
            Self::RuntimeUnavailable => "runtime_unavailable",
        }
    }

    fn seal_state(self) -> NoteSyncSealState {
        match self {
            Self::KeyUnavailable
            | Self::PayloadTooLarge
            | Self::EncryptedSyncObjectTooLarge
            | Self::DependencyNotSynced
            | Self::UnsupportedContentFormat => NoteSyncSealState::Blocked,
            Self::RuntimeUnavailable => NoteSyncSealState::RetryableError,
            Self::InvalidNotePayload
            | Self::CryptoContextInvalid
            | Self::InvalidSyncMetadata
            | Self::InvalidEnvelope
            | Self::MetadataMismatch => NoteSyncSealState::InvariantError,
        }
    }
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize)]
pub(crate) struct UnsealedNoteSyncIntent {
    pub event_id: String,
    pub account_id: String,
    pub device_id: String,
    pub project_id: String,
    pub entity_id: String,
    pub entity_type: String,
    pub operation: NoteSyncOperation,
    pub revision: i64,
    pub parent_event_id: Option<String>,
    pub updated_at: String,
    pub deleted_at: Option<String>,
    pub local_ordinal: i64,
    pub mutation_generation: i64,
    pub snapshot_json: String,
    pub seal_state: NoteSyncSealState,
    pub seal_attempt_count: i64,
    pub last_error_code: Option<String>,
    pub next_attempt_at: Option<String>,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq)]
#[serde(deny_unknown_fields)]
pub(crate) struct RecordNoteSyncSealFailureCommand {
    pub event_id: String,
    pub expected_mutation_generation: i64,
    pub error_code: NoteSyncSealErrorCode,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq)]
#[serde(deny_unknown_fields)]
pub(crate) struct EncryptedNoteSyncEnvelope {
    pub crypto_version: i64,
    pub aad_version: i64,
    pub nonce: String,
    pub ciphertext: String,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq)]
#[serde(deny_unknown_fields)]
pub(crate) struct CommitSealedNoteSyncEventCommand {
    pub event_id: String,
    pub expected_mutation_generation: i64,
    pub envelope: EncryptedNoteSyncEnvelope,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize)]
#[serde(rename_all = "snake_case")]
pub(crate) enum RecordNoteSyncSealFailureResult {
    Recorded,
    StaleGeneration,
    AlreadySealed,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize)]
#[serde(rename_all = "snake_case")]
pub(crate) enum CommitSealedNoteSyncEventResult {
    Sealed,
    StaleGeneration,
    AlreadySealed,
}

#[derive(Debug, Eq, PartialEq)]
struct DecodedEncryptedNoteSyncEnvelope {
    crypto_version: i64,
    aad_version: i64,
    nonce: Vec<u8>,
    ciphertext: Vec<u8>,
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

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) enum NoteDeleteScope<'a> {
    Project,
    Stage(&'a str),
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

pub(crate) fn prepare_note_delete_intent(
    transaction: &Transaction<'_>,
    project_id: &str,
    note_id: &str,
    note: &serde_json::Value,
    deleted_at: &str,
) -> Result<Option<PreparedNoteIntent>, NoteSyncError> {
    if resolve_project_cloud_binding(transaction, project_id)?.is_none() {
        return Ok(None);
    }
    let tombstone = build_note_tombstone(note, deleted_at)?;
    prepare_unsealed_note_intent(
        transaction,
        PrepareNoteIntent {
            project_id,
            entity_id: note_id,
            operation: NoteSyncOperation::Delete,
            updated_at: deleted_at,
            deleted_at: Some(deleted_at),
            snapshot_json: &tombstone,
            state_updated_at: deleted_at,
        },
    )
}

pub(crate) fn prepare_note_delete_intents_for_scope(
    transaction: &Transaction<'_>,
    project_id: &str,
    scope: NoteDeleteScope<'_>,
    deleted_at: &str,
) -> Result<usize, NoteSyncError> {
    // Preserve the pre-sync local-only deletion behavior, including for legacy
    // rows whose payload cannot form a cloud tombstone.
    if resolve_project_cloud_binding(transaction, project_id)?.is_none() {
        return Ok(0);
    }
    let mut notes = Vec::new();
    match scope {
        NoteDeleteScope::Project => {
            let mut statement = transaction
                .prepare("SELECT id,payload_json FROM notes WHERE project_id=?1 ORDER BY rowid")?;
            let rows = statement.query_map([project_id], |row| {
                Ok((row.get::<_, String>(0)?, row.get::<_, String>(1)?))
            })?;
            notes.extend(rows.collect::<Result<Vec<_>, _>>()?);
        }
        NoteDeleteScope::Stage(stage_id) => {
            let mut statement = transaction.prepare(
                "SELECT id,payload_json FROM notes
                 WHERE project_id=?1 AND stage_id=?2 ORDER BY rowid",
            )?;
            let rows = statement.query_map(rusqlite::params![project_id, stage_id], |row| {
                Ok((row.get::<_, String>(0)?, row.get::<_, String>(1)?))
            })?;
            notes.extend(rows.collect::<Result<Vec<_>, _>>()?);
        }
    }
    for (note_id, raw) in &notes {
        let note: serde_json::Value = serde_json::from_str(raw)
            .map_err(|_| NoteSyncError::InvalidSnapshot("snapshot is not valid JSON"))?;
        prepare_note_delete_intent(transaction, project_id, note_id, &note, deleted_at)?;
    }
    Ok(notes.len())
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

pub(crate) fn list_unsealed_note_sync_intents(
    connection: &Connection,
    limit: u32,
) -> Result<Vec<UnsealedNoteSyncIntent>, NoteSyncError> {
    if !(1..=MAX_UNSEALED_INTENT_LIST_LIMIT).contains(&limit) {
        return Err(NoteSyncError::InvalidListLimit);
    }
    let mut statement = connection.prepare(
        "SELECT event.event_id,event.account_id,event.device_id,event.project_id,
                event.entity_id,event.entity_type,event.operation,event.revision,
                event.parent_event_id,event.updated_at,event.deleted_at,event.local_ordinal,
                intent.mutation_generation,intent.snapshot_json,intent.seal_state,
                intent.seal_attempt_count,intent.last_error_code,intent.next_attempt_at
         FROM cloud_sync_outbox AS event
         JOIN cloud_sync_note_intents AS intent ON intent.event_id=event.event_id
         WHERE event.entity_type='note' AND event.lifecycle='unsealed'
           AND (
               intent.seal_state IN ('pending','blocked')
               OR (
                   intent.seal_state='retryable_error'
                   AND (
                       intent.next_attempt_at IS NULL
                       OR intent.next_attempt_at <= strftime('%Y-%m-%dT%H:%M:%fZ','now')
                   )
               )
           )
         ORDER BY CASE WHEN intent.seal_state='blocked' THEN 1 ELSE 0 END,
                  event.account_id,event.device_id,event.local_ordinal,event.event_id
         LIMIT ?1",
    )?;
    let rows = statement.query_map([i64::from(limit)], |row| {
        Ok((
            row.get::<_, String>(0)?,
            row.get::<_, String>(1)?,
            row.get::<_, String>(2)?,
            row.get::<_, String>(3)?,
            row.get::<_, String>(4)?,
            row.get::<_, String>(5)?,
            row.get::<_, String>(6)?,
            row.get::<_, i64>(7)?,
            row.get::<_, Option<String>>(8)?,
            row.get::<_, String>(9)?,
            row.get::<_, Option<String>>(10)?,
            row.get::<_, i64>(11)?,
            row.get::<_, i64>(12)?,
            row.get::<_, String>(13)?,
            row.get::<_, String>(14)?,
            row.get::<_, i64>(15)?,
            row.get::<_, Option<String>>(16)?,
            row.get::<_, Option<String>>(17)?,
        ))
    })?;
    rows.map(|row| {
        let (
            event_id,
            account_id,
            device_id,
            project_id,
            entity_id,
            entity_type,
            operation,
            revision,
            parent_event_id,
            updated_at,
            deleted_at,
            local_ordinal,
            mutation_generation,
            snapshot_json,
            seal_state,
            seal_attempt_count,
            last_error_code,
            next_attempt_at,
        ) = row?;
        Ok(UnsealedNoteSyncIntent {
            event_id,
            account_id,
            device_id,
            project_id,
            entity_id,
            entity_type,
            operation: NoteSyncOperation::from_stored(&operation)?,
            revision,
            parent_event_id,
            updated_at,
            deleted_at,
            local_ordinal,
            mutation_generation,
            snapshot_json,
            seal_state: NoteSyncSealState::from_stored(&seal_state)?,
            seal_attempt_count,
            last_error_code,
            next_attempt_at,
        })
    })
    .collect()
}

pub(crate) fn record_note_sync_seal_failure(
    connection: &mut Connection,
    command: &RecordNoteSyncSealFailureCommand,
) -> Result<RecordNoteSyncSealFailureResult, NoteSyncError> {
    if command.event_id.is_empty() || command.expected_mutation_generation < 1 {
        return Err(NoteSyncError::InvalidSealState("invalid failure identity"));
    }
    let transaction = connection.transaction_with_behavior(TransactionBehavior::Immediate)?;
    let lifecycle = transaction
        .query_row(
            "SELECT lifecycle FROM cloud_sync_outbox
             WHERE event_id=?1 AND entity_type='note'",
            [&command.event_id],
            |row| row.get::<_, String>(0),
        )
        .optional()?
        .ok_or(NoteSyncError::MissingEvent)?;
    if lifecycle == "sealed" {
        ensure_consistent_sealed_event(&transaction, &command.event_id)?;
        transaction.commit()?;
        return Ok(RecordNoteSyncSealFailureResult::AlreadySealed);
    }
    if lifecycle != "unsealed" {
        return Err(NoteSyncError::UnexpectedLifecycle);
    }
    let current_generation = transaction
        .query_row(
            "SELECT mutation_generation FROM cloud_sync_note_intents WHERE event_id=?1",
            [&command.event_id],
            |row| row.get::<_, i64>(0),
        )
        .optional()?
        .ok_or(NoteSyncError::MissingIntent)?;
    if current_generation != command.expected_mutation_generation {
        transaction.commit()?;
        return Ok(RecordNoteSyncSealFailureResult::StaleGeneration);
    }
    let attempt_count = transaction.query_row(
        "SELECT seal_attempt_count FROM cloud_sync_note_intents WHERE event_id=?1",
        [&command.event_id],
        |row| row.get::<_, i64>(0),
    )?;
    let next_attempt_count = attempt_count
        .checked_add(1)
        .filter(|value| *value <= MAX_SYNC_INTEGER)
        .ok_or(NoteSyncError::SealAttemptOverflow)?;
    let seal_state = command.error_code.seal_state();
    let next_attempt_seconds = (seal_state == NoteSyncSealState::RetryableError)
        .then(|| retry_backoff_seconds(next_attempt_count));
    let changed = transaction.execute(
        "UPDATE cloud_sync_note_intents
         SET seal_state=?1,seal_attempt_count=?2,last_error_code=?3,
             next_attempt_at=CASE WHEN ?4 IS NULL THEN NULL ELSE
                 strftime('%Y-%m-%dT%H:%M:%fZ','now',printf('+%d seconds',?4)) END,
             state_updated_at=strftime('%Y-%m-%dT%H:%M:%fZ','now')
         WHERE event_id=?5 AND mutation_generation=?6",
        rusqlite::params![
            match seal_state {
                NoteSyncSealState::Pending => "pending",
                NoteSyncSealState::RetryableError => "retryable_error",
                NoteSyncSealState::Blocked => "blocked",
                NoteSyncSealState::InvariantError => "invariant_error",
            },
            next_attempt_count,
            command.error_code.as_str(),
            next_attempt_seconds,
            command.event_id,
            command.expected_mutation_generation,
        ],
    )?;
    if changed != 1 {
        return Err(NoteSyncError::MissingIntent);
    }
    transaction.commit()?;
    Ok(RecordNoteSyncSealFailureResult::Recorded)
}

pub(crate) fn commit_sealed_note_sync_event(
    connection: &mut Connection,
    command: &CommitSealedNoteSyncEventCommand,
) -> Result<CommitSealedNoteSyncEventResult, NoteSyncError> {
    if command.event_id.is_empty() || command.expected_mutation_generation < 1 {
        return Err(NoteSyncError::InvalidSealState("invalid sealing identity"));
    }
    let envelope = decode_encrypted_note_sync_envelope(&command.envelope)?;
    let transaction = connection.transaction_with_behavior(TransactionBehavior::Immediate)?;
    let event = transaction
        .query_row(
            "SELECT account_id,entity_type,lifecycle FROM cloud_sync_outbox WHERE event_id=?1",
            [&command.event_id],
            |row| {
                Ok((
                    row.get::<_, String>(0)?,
                    row.get::<_, String>(1)?,
                    row.get::<_, String>(2)?,
                ))
            },
        )
        .optional()?
        .ok_or(NoteSyncError::MissingEvent)?;
    let (account_id, entity_type, lifecycle) = event;
    if entity_type != "note" {
        return Err(NoteSyncError::UnexpectedLifecycle);
    }
    if lifecycle == "sealed" {
        ensure_matching_sealed_envelope(&transaction, &account_id, &command.event_id, &envelope)?;
        transaction.commit()?;
        return Ok(CommitSealedNoteSyncEventResult::AlreadySealed);
    }
    if lifecycle != "unsealed" {
        return Err(NoteSyncError::UnexpectedLifecycle);
    }
    let current_generation = transaction
        .query_row(
            "SELECT mutation_generation FROM cloud_sync_note_intents WHERE event_id=?1",
            [&command.event_id],
            |row| row.get::<_, i64>(0),
        )
        .optional()?
        .ok_or(NoteSyncError::MissingIntent)?;
    if current_generation != command.expected_mutation_generation {
        transaction.commit()?;
        return Ok(CommitSealedNoteSyncEventResult::StaleGeneration);
    }
    if transaction
        .query_row(
            "SELECT 1 FROM cloud_sync_event_objects WHERE event_id=?1",
            [&command.event_id],
            |_| Ok(()),
        )
        .optional()?
        .is_some()
    {
        return Err(NoteSyncError::ConflictingEncryptedObject);
    }
    transaction.execute(
        "INSERT INTO cloud_sync_event_objects(
            account_id,event_id,crypto_version,aad_version,nonce,ciphertext,stored_at
         ) VALUES(?1,?2,?3,?4,?5,?6,strftime('%Y-%m-%dT%H:%M:%fZ','now'))",
        rusqlite::params![
            account_id,
            command.event_id,
            envelope.crypto_version,
            envelope.aad_version,
            envelope.nonce,
            envelope.ciphertext,
        ],
    )?;
    let deleted = transaction.execute(
        "DELETE FROM cloud_sync_note_intents
         WHERE event_id=?1 AND mutation_generation=?2",
        rusqlite::params![command.event_id, command.expected_mutation_generation],
    )?;
    if deleted != 1 {
        return Err(NoteSyncError::MissingIntent);
    }
    let updated = transaction.execute(
        "UPDATE cloud_sync_outbox SET lifecycle='sealed'
         WHERE event_id=?1 AND entity_type='note' AND lifecycle='unsealed'",
        [&command.event_id],
    )?;
    if updated != 1 {
        return Err(NoteSyncError::UnexpectedLifecycle);
    }
    transaction.commit()?;
    Ok(CommitSealedNoteSyncEventResult::Sealed)
}

fn retry_backoff_seconds(attempt_count: i64) -> i64 {
    let exponent = u32::try_from(attempt_count.saturating_sub(1).min(6)).unwrap_or(6);
    5_i64
        .saturating_mul(2_i64.saturating_pow(exponent))
        .min(300)
}

fn ensure_consistent_sealed_event(
    transaction: &Transaction<'_>,
    event_id: &str,
) -> Result<(), NoteSyncError> {
    let (account_id, sidecar_count): (String, i64) = transaction.query_row(
        "SELECT event.account_id,
                (SELECT count(*) FROM cloud_sync_note_intents AS intent
                 WHERE intent.event_id=event.event_id)
         FROM cloud_sync_outbox AS event WHERE event.event_id=?1",
        [event_id],
        |row| Ok((row.get(0)?, row.get(1)?)),
    )?;
    if sidecar_count != 0 {
        return Err(NoteSyncError::InvalidSealState(
            "sealed event retains plaintext intent",
        ));
    }
    let object = transaction
        .query_row(
            "SELECT crypto_version,aad_version,length(nonce),length(ciphertext)
             FROM cloud_sync_event_objects WHERE account_id=?1 AND event_id=?2",
            rusqlite::params![account_id, event_id],
            |row| {
                Ok((
                    row.get::<_, i64>(0)?,
                    row.get::<_, i64>(1)?,
                    row.get::<_, i64>(2)?,
                    row.get::<_, i64>(3)?,
                ))
            },
        )
        .optional()?
        .ok_or(NoteSyncError::SealedObjectMissing)?;
    if object.0 != SUPPORTED_CRYPTO_VERSION
        || object.1 != SUPPORTED_AAD_VERSION
        || object.2 != 24
        || !(16..=MAX_ENCRYPTED_SYNC_CIPHERTEXT_BYTES as i64).contains(&object.3)
    {
        return Err(NoteSyncError::InvalidSealState(
            "sealed event has an invalid encrypted object",
        ));
    }
    ensure_single_encrypted_object(transaction, event_id)?;
    Ok(())
}

fn ensure_matching_sealed_envelope(
    transaction: &Transaction<'_>,
    account_id: &str,
    event_id: &str,
    envelope: &DecodedEncryptedNoteSyncEnvelope,
) -> Result<(), NoteSyncError> {
    let sidecar_exists = transaction
        .query_row(
            "SELECT 1 FROM cloud_sync_note_intents WHERE event_id=?1",
            [event_id],
            |_| Ok(()),
        )
        .optional()?
        .is_some();
    if sidecar_exists {
        return Err(NoteSyncError::InvalidSealState(
            "sealed event retains plaintext intent",
        ));
    }
    let stored = transaction
        .query_row(
            "SELECT crypto_version,aad_version,nonce,ciphertext
             FROM cloud_sync_event_objects WHERE account_id=?1 AND event_id=?2",
            rusqlite::params![account_id, event_id],
            |row| {
                Ok(DecodedEncryptedNoteSyncEnvelope {
                    crypto_version: row.get(0)?,
                    aad_version: row.get(1)?,
                    nonce: row.get(2)?,
                    ciphertext: row.get(3)?,
                })
            },
        )
        .optional()?
        .ok_or(NoteSyncError::SealedObjectMissing)?;
    ensure_single_encrypted_object(transaction, event_id)?;
    if stored != *envelope {
        return Err(NoteSyncError::ConflictingEncryptedObject);
    }
    Ok(())
}

fn ensure_single_encrypted_object(
    transaction: &Transaction<'_>,
    event_id: &str,
) -> Result<(), NoteSyncError> {
    let object_count = transaction.query_row(
        "SELECT count(*) FROM cloud_sync_event_objects WHERE event_id=?1",
        [event_id],
        |row| row.get::<_, i64>(0),
    )?;
    if object_count != 1 {
        return Err(NoteSyncError::ConflictingEncryptedObject);
    }
    Ok(())
}

fn decode_encrypted_note_sync_envelope(
    envelope: &EncryptedNoteSyncEnvelope,
) -> Result<DecodedEncryptedNoteSyncEnvelope, NoteSyncError> {
    if envelope.crypto_version != SUPPORTED_CRYPTO_VERSION {
        return Err(NoteSyncError::InvalidEnvelope("unsupported crypto version"));
    }
    if envelope.aad_version != SUPPORTED_AAD_VERSION {
        return Err(NoteSyncError::InvalidEnvelope("unsupported AAD version"));
    }
    let nonce = decode_canonical_base64url(&envelope.nonce, 24, 24)?;
    let ciphertext = decode_canonical_base64url(
        &envelope.ciphertext,
        16,
        MAX_ENCRYPTED_SYNC_CIPHERTEXT_BYTES,
    )?;
    Ok(DecodedEncryptedNoteSyncEnvelope {
        crypto_version: envelope.crypto_version,
        aad_version: envelope.aad_version,
        nonce,
        ciphertext,
    })
}

fn decode_canonical_base64url(
    input: &str,
    minimum_length: usize,
    maximum_length: usize,
) -> Result<Vec<u8>, NoteSyncError> {
    let maximum_encoded_length = base64url_encoded_length(maximum_length).ok_or(
        NoteSyncError::InvalidEnvelope("encoded payload is too large"),
    )?;
    if input.len() > maximum_encoded_length || input.len() % 4 == 1 {
        return Err(NoteSyncError::InvalidEnvelope("invalid base64url length"));
    }
    let remainder = input.len() % 4;
    let decoded_length = input.len() / 4 * 3
        + match remainder {
            0 => 0,
            2 => 1,
            3 => 2,
            _ => unreachable!(),
        };
    if !(minimum_length..=maximum_length).contains(&decoded_length) {
        return Err(NoteSyncError::InvalidEnvelope(
            "decoded payload length is out of bounds",
        ));
    }
    let bytes = input.as_bytes();
    let mut decoded = Vec::with_capacity(decoded_length);
    let complete_length = input.len() - remainder;
    for chunk in bytes[..complete_length].chunks_exact(4) {
        let a = base64url_value(chunk[0])?;
        let b = base64url_value(chunk[1])?;
        let c = base64url_value(chunk[2])?;
        let d = base64url_value(chunk[3])?;
        decoded.push((a << 2) | (b >> 4));
        decoded.push(((b & 0x0f) << 4) | (c >> 2));
        decoded.push(((c & 0x03) << 6) | d);
    }
    if remainder == 2 {
        let a = base64url_value(bytes[complete_length])?;
        let b = base64url_value(bytes[complete_length + 1])?;
        if b & 0x0f != 0 {
            return Err(NoteSyncError::InvalidEnvelope(
                "non-canonical base64url tail",
            ));
        }
        decoded.push((a << 2) | (b >> 4));
    } else if remainder == 3 {
        let a = base64url_value(bytes[complete_length])?;
        let b = base64url_value(bytes[complete_length + 1])?;
        let c = base64url_value(bytes[complete_length + 2])?;
        if c & 0x03 != 0 {
            return Err(NoteSyncError::InvalidEnvelope(
                "non-canonical base64url tail",
            ));
        }
        decoded.push((a << 2) | (b >> 4));
        decoded.push(((b & 0x0f) << 4) | (c >> 2));
    }
    Ok(decoded)
}

fn base64url_encoded_length(byte_length: usize) -> Option<usize> {
    byte_length
        .checked_div(3)?
        .checked_mul(4)?
        .checked_add(match byte_length % 3 {
            0 => 0,
            1 => 2,
            2 => 3,
            _ => unreachable!(),
        })
}

fn base64url_value(value: u8) -> Result<u8, NoteSyncError> {
    match value {
        b'A'..=b'Z' => Ok(value - b'A'),
        b'a'..=b'z' => Ok(value - b'a' + 26),
        b'0'..=b'9' => Ok(value - b'0' + 52),
        b'-' => Ok(62),
        b'_' => Ok(63),
        _ => Err(NoteSyncError::InvalidEnvelope(
            "invalid base64url character",
        )),
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use rusqlite::Connection;

    const DEVICE_ID: &str = "123e4567-e89b-42d3-a456-426614174000";

    fn database() -> Connection {
        let connection = Connection::open_in_memory().unwrap();
        crate::sqlite::apply_migrations(&connection).unwrap();
        configure_database(&connection);
        connection
    }

    fn configure_database(connection: &Connection) {
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
    }

    fn note(content: &str, revision: i64) -> String {
        note_for("n", content, revision)
    }

    fn note_for(note_id: &str, content: &str, revision: i64) -> String {
        serde_json::json!({
            "id":note_id, "project_id":"p", "stage_id":null, "title":"",
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
        prepare_for("n", snapshot)
    }

    fn prepare_for<'a>(note_id: &'a str, snapshot: &'a str) -> PrepareNoteIntent<'a> {
        PrepareNoteIntent {
            project_id: "p",
            entity_id: note_id,
            operation: NoteSyncOperation::Upsert,
            updated_at: "2026-09-22T00:00:00Z",
            deleted_at: None,
            snapshot_json: snapshot,
            state_updated_at: "2026-09-22T00:00:00Z",
        }
    }

    fn persist_note_intent(
        connection: &mut Connection,
        note_id: &str,
        content: &str,
    ) -> (PreparedNoteIntent, String) {
        let snapshot = note_for(note_id, content, 0);
        let transaction = connection.transaction().unwrap();
        let intent = prepare_unsealed_note_intent(&transaction, prepare_for(note_id, &snapshot))
            .unwrap()
            .unwrap();
        let exists = transaction
            .query_row("SELECT 1 FROM notes WHERE id=?1", [note_id], |_| Ok(()))
            .optional()
            .unwrap()
            .is_some();
        if exists {
            transaction
                .execute(
                    "UPDATE notes SET updated_at='2026-09-22T00:00:00Z',payload_json=?1
                     WHERE id=?2",
                    rusqlite::params![snapshot, note_id],
                )
                .unwrap();
        } else {
            transaction
                .execute(
                    "INSERT INTO notes(id,project_id,stage_id,updated_at,payload_json)
                     VALUES(?1,'p',NULL,'2026-09-22T00:00:00Z',?2)",
                    rusqlite::params![note_id, snapshot],
                )
                .unwrap();
        }
        transaction.commit().unwrap();
        (intent, snapshot)
    }

    fn encode_base64url(bytes: &[u8]) -> String {
        const ALPHABET: &[u8; 64] =
            b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_";
        let mut encoded = String::with_capacity(base64url_encoded_length(bytes.len()).unwrap());
        let complete_length = bytes.len() / 3 * 3;
        for chunk in bytes[..complete_length].chunks_exact(3) {
            encoded.push(ALPHABET[(chunk[0] >> 2) as usize] as char);
            encoded.push(ALPHABET[(((chunk[0] & 0x03) << 4) | (chunk[1] >> 4)) as usize] as char);
            encoded.push(ALPHABET[(((chunk[1] & 0x0f) << 2) | (chunk[2] >> 6)) as usize] as char);
            encoded.push(ALPHABET[(chunk[2] & 0x3f) as usize] as char);
        }
        match bytes.len() - complete_length {
            1 => {
                encoded.push(ALPHABET[(bytes[complete_length] >> 2) as usize] as char);
                encoded.push(ALPHABET[((bytes[complete_length] & 0x03) << 4) as usize] as char);
            }
            2 => {
                encoded.push(ALPHABET[(bytes[complete_length] >> 2) as usize] as char);
                encoded.push(
                    ALPHABET[(((bytes[complete_length] & 0x03) << 4)
                        | (bytes[complete_length + 1] >> 4)) as usize] as char,
                );
                encoded.push(ALPHABET[((bytes[complete_length + 1] & 0x0f) << 2) as usize] as char);
            }
            _ => {}
        }
        encoded
    }

    fn envelope(fill: u8) -> EncryptedNoteSyncEnvelope {
        EncryptedNoteSyncEnvelope {
            crypto_version: 1,
            aad_version: 1,
            nonce: encode_base64url(&vec![fill; 24]),
            ciphertext: encode_base64url(&vec![fill.wrapping_add(1); 16]),
        }
    }

    fn seal_command(
        event_id: &str,
        mutation_generation: i64,
        envelope: EncryptedNoteSyncEnvelope,
    ) -> CommitSealedNoteSyncEventCommand {
        CommitSealedNoteSyncEventCommand {
            event_id: event_id.to_string(),
            expected_mutation_generation: mutation_generation,
            envelope,
        }
    }

    fn failure_command(
        event_id: &str,
        mutation_generation: i64,
        error_code: NoteSyncSealErrorCode,
    ) -> RecordNoteSyncSealFailureCommand {
        RecordNoteSyncSealFailureCommand {
            event_id: event_id.to_string(),
            expected_mutation_generation: mutation_generation,
            error_code,
        }
    }

    fn temporary_database_path(label: &str) -> (std::path::PathBuf, std::path::PathBuf) {
        let root = std::env::temp_dir().join(format!(
            "nfprogress-note-sync-{label}-{}-{}",
            std::process::id(),
            std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_nanos()
        ));
        std::fs::create_dir_all(&root).unwrap();
        let path = root.join("nfprogress.db");
        (root, path)
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
    fn note_sync_lists_pending_intents_bounded_in_stable_order_without_project_binding() {
        let mut connection = database();
        let (first, first_snapshot) = persist_note_intent(&mut connection, "later-name", "first");
        let (second, _) = persist_note_intent(&mut connection, "earlier-name", "second");
        connection
            .execute("DELETE FROM cloud_sync_project_bindings", [])
            .unwrap();

        let limited = list_unsealed_note_sync_intents(&connection, 1).unwrap();
        assert_eq!(limited.len(), 1);
        assert_eq!(limited[0].event_id, first.event_id);
        assert_eq!(limited[0].account_id, "account");
        assert_eq!(limited[0].device_id, DEVICE_ID);
        assert_eq!(limited[0].project_id, "p");
        assert_eq!(limited[0].entity_id, "later-name");
        assert_eq!(limited[0].entity_type, "note");
        assert_eq!(limited[0].operation, NoteSyncOperation::Upsert);
        assert_eq!(limited[0].revision, 1);
        assert_eq!(limited[0].parent_event_id, None);
        assert_eq!(limited[0].local_ordinal, 1);
        assert_eq!(limited[0].mutation_generation, 1);
        assert_eq!(limited[0].snapshot_json, first_snapshot);
        assert_eq!(limited[0].seal_state, NoteSyncSealState::Pending);
        assert_eq!(limited[0].seal_attempt_count, 0);
        assert_eq!(limited[0].last_error_code, None);
        assert_eq!(limited[0].next_attempt_at, None);

        let all = list_unsealed_note_sync_intents(&connection, 10).unwrap();
        assert_eq!(
            all.iter()
                .map(|intent| intent.event_id.as_str())
                .collect::<Vec<_>>(),
            vec![first.event_id.as_str(), second.event_id.as_str()]
        );
        assert!(list_unsealed_note_sync_intents(&connection, 0).is_err());
        assert!(list_unsealed_note_sync_intents(&connection, 201).is_err());
    }

    #[test]
    fn note_sync_blocked_failure_is_durable_after_database_reopen() {
        let (root, path) = temporary_database_path("blocked-reopen");
        let mut connection = crate::sqlite::open_database(&path).unwrap();
        configure_database(&connection);
        let (intent, snapshot) = persist_note_intent(&mut connection, "n", "blocked");
        assert_eq!(
            record_note_sync_seal_failure(
                &mut connection,
                &failure_command(
                    &intent.event_id,
                    intent.mutation_generation,
                    NoteSyncSealErrorCode::KeyUnavailable,
                ),
            )
            .unwrap(),
            RecordNoteSyncSealFailureResult::Recorded
        );
        drop(connection);

        let connection = crate::sqlite::open_database(&path).unwrap();
        let intents = list_unsealed_note_sync_intents(&connection, 10).unwrap();
        assert_eq!(intents.len(), 1);
        assert_eq!(intents[0].seal_state, NoteSyncSealState::Blocked);
        assert_eq!(intents[0].seal_attempt_count, 1);
        assert_eq!(
            intents[0].last_error_code.as_deref(),
            Some("key_unavailable")
        );
        assert_eq!(intents[0].snapshot_json, snapshot);
        assert_eq!(intents[0].next_attempt_at, None);
        assert_eq!(
            connection
                .query_row("SELECT count(*) FROM cloud_sync_outbox", [], |row| row
                    .get::<_, i64>(0))
                .unwrap(),
            1
        );
        drop(connection);
        std::fs::remove_dir_all(root).unwrap();
    }

    #[test]
    fn note_sync_retryable_failure_has_durable_bounded_backoff() {
        let mut connection = database();
        let (intent, _) = persist_note_intent(&mut connection, "n", "retry");
        record_note_sync_seal_failure(
            &mut connection,
            &failure_command(
                &intent.event_id,
                intent.mutation_generation,
                NoteSyncSealErrorCode::RuntimeUnavailable,
            ),
        )
        .unwrap();

        let stored = connection
            .query_row(
                "SELECT seal_state,seal_attempt_count,last_error_code,next_attempt_at,
                        state_updated_at,next_attempt_at > state_updated_at
                 FROM cloud_sync_note_intents WHERE event_id=?1",
                [&intent.event_id],
                |row| {
                    Ok((
                        row.get::<_, String>(0)?,
                        row.get::<_, i64>(1)?,
                        row.get::<_, String>(2)?,
                        row.get::<_, Option<String>>(3)?,
                        row.get::<_, String>(4)?,
                        row.get::<_, i64>(5)?,
                    ))
                },
            )
            .unwrap();
        assert_eq!(stored.0, "retryable_error");
        assert_eq!(stored.1, 1);
        assert_eq!(stored.2, "runtime_unavailable");
        assert!(stored.3.is_some());
        assert_eq!(stored.5, 1);
        assert!(list_unsealed_note_sync_intents(&connection, 10)
            .unwrap()
            .is_empty());
    }

    #[test]
    fn note_sync_new_mutation_resets_sealing_failure() {
        let mut connection = database();
        let (first, _) = persist_note_intent(&mut connection, "n", "first");
        record_note_sync_seal_failure(
            &mut connection,
            &failure_command(
                &first.event_id,
                first.mutation_generation,
                NoteSyncSealErrorCode::PayloadTooLarge,
            ),
        )
        .unwrap();
        let (second, second_snapshot) = persist_note_intent(&mut connection, "n", "second");

        assert_eq!(second.event_id, first.event_id);
        assert_eq!(second.mutation_generation, 2);
        let stored = connection
            .query_row(
                "SELECT seal_state,seal_attempt_count,last_error_code,next_attempt_at,snapshot_json
                 FROM cloud_sync_note_intents WHERE event_id=?1",
                [&first.event_id],
                |row| {
                    Ok((
                        row.get::<_, String>(0)?,
                        row.get::<_, i64>(1)?,
                        row.get::<_, Option<String>>(2)?,
                        row.get::<_, Option<String>>(3)?,
                        row.get::<_, String>(4)?,
                    ))
                },
            )
            .unwrap();
        assert_eq!(stored.0, "pending");
        assert_eq!(stored.1, 0);
        assert_eq!(stored.2, None);
        assert_eq!(stored.3, None);
        assert_eq!(stored.4, second_snapshot);
    }

    #[test]
    fn note_sync_stale_failure_cannot_overwrite_new_generation() {
        let mut connection = database();
        let (first, _) = persist_note_intent(&mut connection, "n", "first");
        let (second, second_snapshot) = persist_note_intent(&mut connection, "n", "second");
        assert_eq!(
            record_note_sync_seal_failure(
                &mut connection,
                &failure_command(
                    &first.event_id,
                    first.mutation_generation,
                    NoteSyncSealErrorCode::CryptoContextInvalid,
                ),
            )
            .unwrap(),
            RecordNoteSyncSealFailureResult::StaleGeneration
        );
        let intent = list_unsealed_note_sync_intents(&connection, 10)
            .unwrap()
            .pop()
            .unwrap();
        assert_eq!(intent.mutation_generation, second.mutation_generation);
        assert_eq!(intent.snapshot_json, second_snapshot);
        assert_eq!(intent.seal_state, NoteSyncSealState::Pending);
        assert_eq!(intent.seal_attempt_count, 0);
    }

    #[test]
    fn note_sync_failure_codes_have_bounded_lifecycle_classification() {
        for code in [
            NoteSyncSealErrorCode::KeyUnavailable,
            NoteSyncSealErrorCode::PayloadTooLarge,
            NoteSyncSealErrorCode::EncryptedSyncObjectTooLarge,
            NoteSyncSealErrorCode::DependencyNotSynced,
            NoteSyncSealErrorCode::UnsupportedContentFormat,
        ] {
            assert_eq!(code.seal_state(), NoteSyncSealState::Blocked);
        }
        assert_eq!(
            NoteSyncSealErrorCode::RuntimeUnavailable.seal_state(),
            NoteSyncSealState::RetryableError
        );
        for code in [
            NoteSyncSealErrorCode::InvalidNotePayload,
            NoteSyncSealErrorCode::CryptoContextInvalid,
            NoteSyncSealErrorCode::InvalidSyncMetadata,
            NoteSyncSealErrorCode::InvalidEnvelope,
            NoteSyncSealErrorCode::MetadataMismatch,
        ] {
            assert_eq!(code.seal_state(), NoteSyncSealState::InvariantError);
        }
    }

    #[test]
    fn note_sync_envelope_requires_canonical_unpadded_base64url() {
        assert_eq!(decode_canonical_base64url("_w", 1, 1).unwrap(), vec![0xff]);
        assert!(decode_canonical_base64url("_x", 1, 1).is_err());
        assert!(decode_canonical_base64url("_w=", 1, 1).is_err());
        assert!(decode_canonical_base64url("+w", 1, 1).is_err());
    }

    #[test]
    fn note_sync_sealing_command_rejects_plaintext_and_unknown_fields() {
        let value = serde_json::json!({
            "event_id": "123e4567-e89b-42d3-a456-426614174001",
            "expected_mutation_generation": 1,
            "envelope": {
                "crypto_version": 1,
                "aad_version": 1,
                "nonce": encode_base64url(&[0_u8; 24]),
                "ciphertext": encode_base64url(&[0_u8; 16]),
            },
            "plaintext": {"content": "must not be accepted"},
        });
        assert!(serde_json::from_value::<CommitSealedNoteSyncEventCommand>(value).is_err());
    }

    #[test]
    fn note_sync_successful_sealing_stores_object_and_removes_plaintext() {
        let mut connection = database();
        let (intent, _) = persist_note_intent(&mut connection, "n", "sealed");
        let command = seal_command(&intent.event_id, intent.mutation_generation, envelope(7));
        assert_eq!(
            commit_sealed_note_sync_event(&mut connection, &command).unwrap(),
            CommitSealedNoteSyncEventResult::Sealed
        );

        let stored = connection
            .query_row(
                "SELECT event.lifecycle,object.account_id,object.crypto_version,
                        object.aad_version,length(object.nonce),length(object.ciphertext)
                 FROM cloud_sync_outbox AS event
                 JOIN cloud_sync_event_objects AS object ON object.event_id=event.event_id
                    AND object.account_id=event.account_id
                 WHERE event.event_id=?1",
                [&intent.event_id],
                |row| {
                    Ok((
                        row.get::<_, String>(0)?,
                        row.get::<_, String>(1)?,
                        row.get::<_, i64>(2)?,
                        row.get::<_, i64>(3)?,
                        row.get::<_, i64>(4)?,
                        row.get::<_, i64>(5)?,
                    ))
                },
            )
            .unwrap();
        assert_eq!(
            stored,
            ("sealed".to_string(), "account".to_string(), 1, 1, 24, 16)
        );
        assert_eq!(
            connection
                .query_row(
                    "SELECT count(*) FROM cloud_sync_note_intents WHERE event_id=?1",
                    [&intent.event_id],
                    |row| row.get::<_, i64>(0),
                )
                .unwrap(),
            0
        );
        assert!(list_unsealed_note_sync_intents(&connection, 10)
            .unwrap()
            .is_empty());
    }

    #[test]
    fn note_sync_ciphertext_survives_database_reopen() {
        let (root, path) = temporary_database_path("ciphertext-reopen");
        let mut connection = crate::sqlite::open_database(&path).unwrap();
        configure_database(&connection);
        let (intent, _) = persist_note_intent(&mut connection, "n", "reopen");
        let expected = vec![10_u8; 16];
        commit_sealed_note_sync_event(
            &mut connection,
            &seal_command(&intent.event_id, intent.mutation_generation, envelope(9)),
        )
        .unwrap();
        drop(connection);

        let connection = crate::sqlite::open_database(&path).unwrap();
        let ciphertext = connection
            .query_row(
                "SELECT ciphertext FROM cloud_sync_event_objects WHERE event_id=?1",
                [&intent.event_id],
                |row| row.get::<_, Vec<u8>>(0),
            )
            .unwrap();
        assert_eq!(ciphertext, expected);
        assert!(list_unsealed_note_sync_intents(&connection, 10)
            .unwrap()
            .is_empty());
        drop(connection);
        std::fs::remove_dir_all(root).unwrap();
    }

    #[test]
    fn note_sync_generation_race_rejects_stale_ciphertext() {
        let mut connection = database();
        let (first, _) = persist_note_intent(&mut connection, "n", "snapshot-a");
        let listed = list_unsealed_note_sync_intents(&connection, 10)
            .unwrap()
            .pop()
            .unwrap();
        let (second, second_snapshot) = persist_note_intent(&mut connection, "n", "snapshot-b");
        assert_eq!(
            commit_sealed_note_sync_event(
                &mut connection,
                &seal_command(&first.event_id, listed.mutation_generation, envelope(1)),
            )
            .unwrap(),
            CommitSealedNoteSyncEventResult::StaleGeneration
        );
        assert_eq!(
            connection
                .query_row("SELECT count(*) FROM cloud_sync_event_objects", [], |row| {
                    row.get::<_, i64>(0)
                })
                .unwrap(),
            0
        );
        let remaining = list_unsealed_note_sync_intents(&connection, 10)
            .unwrap()
            .pop()
            .unwrap();
        assert_eq!(remaining.event_id, first.event_id);
        assert_eq!(remaining.mutation_generation, second.mutation_generation);
        assert_eq!(remaining.snapshot_json, second_snapshot);
    }

    #[test]
    fn note_sync_sealing_rolls_back_when_object_insert_is_followed_by_failure() {
        let mut connection = database();
        let (intent, snapshot) = persist_note_intent(&mut connection, "n", "rollback-object");
        connection
            .execute_batch(
                "CREATE TRIGGER note_sync_test_fail_after_object
             BEFORE DELETE ON cloud_sync_note_intents
             BEGIN SELECT RAISE(ABORT,'injected_after_object_insert'); END;",
            )
            .unwrap();
        assert!(commit_sealed_note_sync_event(
            &mut connection,
            &seal_command(&intent.event_id, intent.mutation_generation, envelope(2)),
        )
        .is_err());
        connection
            .execute_batch("DROP TRIGGER note_sync_test_fail_after_object;")
            .unwrap();

        assert_eq!(
            connection
                .query_row("SELECT count(*) FROM cloud_sync_event_objects", [], |row| {
                    row.get::<_, i64>(0)
                })
                .unwrap(),
            0
        );
        let remaining = list_unsealed_note_sync_intents(&connection, 10)
            .unwrap()
            .pop()
            .unwrap();
        assert_eq!(remaining.snapshot_json, snapshot);
    }

    #[test]
    fn note_sync_sealing_rolls_back_temporary_sidecar_delete() {
        let mut connection = database();
        let (intent, snapshot) = persist_note_intent(&mut connection, "n", "rollback-sidecar");
        connection
            .execute_batch(
                "CREATE TRIGGER note_sync_test_fail_lifecycle
             BEFORE UPDATE OF lifecycle ON cloud_sync_outbox
             WHEN NEW.lifecycle='sealed'
             BEGIN SELECT RAISE(ABORT,'injected_before_lifecycle_update'); END;",
            )
            .unwrap();
        assert!(commit_sealed_note_sync_event(
            &mut connection,
            &seal_command(&intent.event_id, intent.mutation_generation, envelope(3)),
        )
        .is_err());
        connection
            .execute_batch("DROP TRIGGER note_sync_test_fail_lifecycle;")
            .unwrap();

        assert_eq!(
            connection
                .query_row("SELECT count(*) FROM cloud_sync_event_objects", [], |row| {
                    row.get::<_, i64>(0)
                })
                .unwrap(),
            0
        );
        let remaining = list_unsealed_note_sync_intents(&connection, 10)
            .unwrap()
            .pop()
            .unwrap();
        assert_eq!(remaining.snapshot_json, snapshot);
    }

    #[test]
    fn note_sync_duplicate_sealing_is_idempotent_only_for_matching_envelope() {
        let mut connection = database();
        let (intent, _) = persist_note_intent(&mut connection, "n", "duplicate");
        let command = seal_command(&intent.event_id, intent.mutation_generation, envelope(4));
        assert_eq!(
            commit_sealed_note_sync_event(&mut connection, &command).unwrap(),
            CommitSealedNoteSyncEventResult::Sealed
        );
        assert_eq!(
            commit_sealed_note_sync_event(&mut connection, &command).unwrap(),
            CommitSealedNoteSyncEventResult::AlreadySealed
        );
        let conflicting = seal_command(&intent.event_id, intent.mutation_generation, envelope(5));
        assert!(matches!(
            commit_sealed_note_sync_event(&mut connection, &conflicting),
            Err(NoteSyncError::ConflictingEncryptedObject)
        ));
        let stored: Vec<u8> = connection
            .query_row(
                "SELECT ciphertext FROM cloud_sync_event_objects WHERE event_id=?1",
                [&intent.event_id],
                |row| row.get(0),
            )
            .unwrap();
        assert_eq!(stored, vec![5_u8; 16]);
    }

    #[test]
    fn note_sync_rejects_invalid_nonce_and_ciphertext_lengths() {
        let mut connection = database();
        let (intent, _) = persist_note_intent(&mut connection, "n", "invalid-envelope");
        let invalid_envelopes = [
            EncryptedNoteSyncEnvelope {
                crypto_version: 1,
                aad_version: 1,
                nonce: encode_base64url(&[0_u8; 23]),
                ciphertext: encode_base64url(&[0_u8; 16]),
            },
            EncryptedNoteSyncEnvelope {
                crypto_version: 1,
                aad_version: 1,
                nonce: encode_base64url(&[0_u8; 24]),
                ciphertext: encode_base64url(&[0_u8; 15]),
            },
            EncryptedNoteSyncEnvelope {
                crypto_version: 2,
                aad_version: 1,
                nonce: encode_base64url(&[0_u8; 24]),
                ciphertext: encode_base64url(&[0_u8; 16]),
            },
        ];
        for invalid in invalid_envelopes {
            assert!(matches!(
                commit_sealed_note_sync_event(
                    &mut connection,
                    &seal_command(&intent.event_id, intent.mutation_generation, invalid),
                ),
                Err(NoteSyncError::InvalidEnvelope(_))
            ));
        }
        let oversized = EncryptedNoteSyncEnvelope {
            crypto_version: 1,
            aad_version: 1,
            nonce: encode_base64url(&[0_u8; 24]),
            ciphertext: encode_base64url(&vec![0_u8; MAX_ENCRYPTED_SYNC_CIPHERTEXT_BYTES + 1]),
        };
        assert!(matches!(
            commit_sealed_note_sync_event(
                &mut connection,
                &seal_command(&intent.event_id, intent.mutation_generation, oversized),
            ),
            Err(NoteSyncError::InvalidEnvelope(_))
        ));
        assert_eq!(
            connection
                .query_row("SELECT count(*) FROM cloud_sync_event_objects", [], |row| {
                    row.get::<_, i64>(0)
                })
                .unwrap(),
            0
        );
    }

    #[test]
    fn note_sync_sealed_event_without_object_is_an_invariant_error() {
        let mut connection = database();
        let (intent, _) = persist_note_intent(&mut connection, "n", "missing-object");
        connection
            .execute(
                "DELETE FROM cloud_sync_note_intents WHERE event_id=?1",
                [&intent.event_id],
            )
            .unwrap();
        connection
            .execute(
                "UPDATE cloud_sync_outbox SET lifecycle='sealed' WHERE event_id=?1",
                [&intent.event_id],
            )
            .unwrap();

        assert!(matches!(
            commit_sealed_note_sync_event(
                &mut connection,
                &seal_command(&intent.event_id, intent.mutation_generation, envelope(6)),
            ),
            Err(NoteSyncError::SealedObjectMissing)
        ));
        assert!(matches!(
            record_note_sync_seal_failure(
                &mut connection,
                &failure_command(
                    &intent.event_id,
                    intent.mutation_generation,
                    NoteSyncSealErrorCode::RuntimeUnavailable,
                ),
            ),
            Err(NoteSyncError::SealedObjectMissing)
        ));
    }

    #[test]
    fn note_sync_deleted_project_tombstone_can_be_sealed() {
        let mut connection = database();
        let (_, snapshot) = persist_note_intent(&mut connection, "n", "delete-me");
        let note_value: serde_json::Value = serde_json::from_str(&snapshot).unwrap();
        let transaction = connection.transaction().unwrap();
        let tombstone =
            prepare_note_delete_intent(&transaction, "p", "n", &note_value, "2026-09-22T00:01:00Z")
                .unwrap()
                .unwrap();
        transaction
            .execute("DELETE FROM notes WHERE id='n'", [])
            .unwrap();
        transaction
            .execute("DELETE FROM project_order WHERE project_id='p'", [])
            .unwrap();
        transaction
            .execute(
                "DELETE FROM cloud_sync_project_bindings WHERE project_id='p'",
                [],
            )
            .unwrap();
        transaction
            .execute("DELETE FROM projects WHERE id='p'", [])
            .unwrap();
        transaction.commit().unwrap();

        let listed = list_unsealed_note_sync_intents(&connection, 10)
            .unwrap()
            .pop()
            .unwrap();
        assert_eq!(listed.operation, NoteSyncOperation::Delete);
        assert_eq!(listed.event_id, tombstone.event_id);
        assert_eq!(listed.account_id, "account");
        assert_eq!(
            commit_sealed_note_sync_event(
                &mut connection,
                &seal_command(
                    &tombstone.event_id,
                    tombstone.mutation_generation,
                    envelope(8),
                ),
            )
            .unwrap(),
            CommitSealedNoteSyncEventResult::Sealed
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

    fn test_map(notes: &[(&str, &str)]) -> serde_json::Value {
        serde_json::json!({
            "nodeData":{"id":"map-root","topic":"Project","children":[]},
            "freeNodes": notes.iter().map(|(id, topic)| serde_json::json!({
                "id":id,"topic":topic,"children":[],"nfprogressNote":true
            })).collect::<Vec<_>>()
        })
    }

    fn save_test_map(connection: &mut Connection, map: serde_json::Value) -> Result<(), String> {
        let normalized = crate::mindmap::normalize(map.clone())?;
        crate::save_map_in_connection(
            connection,
            &crate::MapCommand {
                project_id: "project".to_string(),
                stage_id: None,
                data: map,
            },
            &normalized,
        )
    }

    #[test]
    fn note_sync_save_map_captures_create_update_and_delete() {
        let mut connection = direct_database(true);
        let note_id = crate::mindmap::linked_note_id("node");

        save_test_map(&mut connection, test_map(&[("node", "First")])).unwrap();
        let created: (String, String, i64, String) = connection
            .query_row(
                "SELECT note.payload_json,intent.snapshot_json,intent.mutation_generation,event.operation
                 FROM notes AS note
                 JOIN cloud_sync_outbox AS event ON event.entity_id=note.id
                 JOIN cloud_sync_note_intents AS intent USING(event_id)
                 WHERE note.id=?1",
                [&note_id],
                |row| Ok((row.get(0)?, row.get(1)?, row.get(2)?, row.get(3)?)),
            )
            .unwrap();
        assert_eq!(created.0, created.1);
        assert_eq!(created.2, 1);
        assert_eq!(created.3, "upsert");

        save_test_map(&mut connection, test_map(&[("node", "Latest")])).unwrap();
        let updated: (String, String, i64, i64, String) = connection
            .query_row(
                "SELECT note.payload_json,intent.snapshot_json,intent.mutation_generation,
                        event.revision,event.event_id
                 FROM notes AS note
                 JOIN cloud_sync_outbox AS event ON event.entity_id=note.id
                 JOIN cloud_sync_note_intents AS intent USING(event_id)
                 WHERE note.id=?1",
                [&note_id],
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
            .unwrap();
        assert_eq!(updated.0, updated.1);
        assert_eq!(updated.2, 2);
        assert_eq!(updated.3, 1);
        assert_eq!(updated.4, outbox_identity(&connection, &note_id).0);
        assert_eq!(
            serde_json::from_str::<serde_json::Value>(&updated.0).unwrap()["content"],
            "Latest"
        );

        save_test_map(&mut connection, test_map(&[])).unwrap();
        assert_eq!(
            connection
                .query_row(
                    "SELECT count(*) FROM notes WHERE id=?1",
                    [&note_id],
                    |row| { row.get::<_, i64>(0) }
                )
                .unwrap(),
            0
        );
        let deleted: (String, i64, String, String, String) = connection
            .query_row(
                "SELECT event.operation,intent.mutation_generation,event.updated_at,
                        event.deleted_at,intent.snapshot_json
                 FROM cloud_sync_outbox AS event
                 JOIN cloud_sync_note_intents AS intent USING(event_id)
                 WHERE event.entity_id=?1",
                [&note_id],
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
            .unwrap();
        let tombstone: serde_json::Value = serde_json::from_str(&deleted.4).unwrap();
        assert_eq!(deleted.0, "delete");
        assert_eq!(deleted.1, 3);
        assert_eq!(deleted.2, deleted.3);
        assert_eq!(tombstone["deleted_at"], deleted.2);
        assert_eq!(tombstone["source_type"], "mindmap");
    }

    #[test]
    fn note_sync_load_map_reconciliation_captures_hidden_write() {
        let mut connection = direct_database(true);
        let map = test_map(&[("loaded-node", "Loaded")]);
        connection
            .execute(
                "UPDATE projects SET payload_json=?1 WHERE id='project'",
                [serde_json::json!({"mindmap":map}).to_string()],
            )
            .unwrap();

        crate::reconcile_loaded_map_view_in_connection(&mut connection, "project", None).unwrap();

        let note_id = crate::mindmap::linked_note_id("loaded-node");
        let (stored, intent): (String, String) = connection
            .query_row(
                "SELECT note.payload_json,intent.snapshot_json
                 FROM notes AS note
                 JOIN cloud_sync_outbox AS event ON event.entity_id=note.id
                 JOIN cloud_sync_note_intents AS intent USING(event_id)
                 WHERE note.id=?1 AND event.lifecycle='unsealed'",
                [&note_id],
                |row| Ok((row.get(0)?, row.get(1)?)),
            )
            .unwrap();
        assert_eq!(stored, intent);
        assert_eq!(
            serde_json::from_str::<serde_json::Value>(&stored).unwrap()["content"],
            "Loaded"
        );
    }

    #[test]
    fn note_sync_local_only_load_and_save_map_create_no_outbox() {
        let mut connection = direct_database(false);
        let loaded = test_map(&[("local-node", "Loaded locally")]);
        connection
            .execute(
                "UPDATE projects SET payload_json=?1 WHERE id='project'",
                [serde_json::json!({"mindmap":loaded}).to_string()],
            )
            .unwrap();
        crate::reconcile_loaded_map_view_in_connection(&mut connection, "project", None).unwrap();
        save_test_map(
            &mut connection,
            test_map(&[("local-node", "Saved locally")]),
        )
        .unwrap();

        let note_id = crate::mindmap::linked_note_id("local-node");
        let payload: String = connection
            .query_row(
                "SELECT payload_json FROM notes WHERE id=?1",
                [&note_id],
                |row| row.get(0),
            )
            .unwrap();
        assert_eq!(
            serde_json::from_str::<serde_json::Value>(&payload).unwrap()["content"],
            "Saved locally"
        );
        assert_eq!(
            connection
                .query_row("SELECT count(*) FROM cloud_sync_outbox", [], |row| {
                    row.get::<_, i64>(0)
                })
                .unwrap(),
            0
        );
    }

    #[test]
    fn note_sync_save_map_rolls_back_all_reconciliation_changes() {
        let mut connection = direct_database(true);
        save_test_map(
            &mut connection,
            test_map(&[("first-node", "First"), ("second-node", "Second")]),
        )
        .unwrap();
        let first_id = crate::mindmap::linked_note_id("first-node");
        let second_id = crate::mindmap::linked_note_id("second-node");
        let owner_before: String = connection
            .query_row(
                "SELECT payload_json FROM projects WHERE id='project'",
                [],
                |row| row.get(0),
            )
            .unwrap();
        let first_before = connection
            .query_row(
                "SELECT note.payload_json,intent.snapshot_json,intent.mutation_generation
                 FROM notes AS note
                 JOIN cloud_sync_outbox AS event ON event.entity_id=note.id
                 JOIN cloud_sync_note_intents AS intent USING(event_id)
                 WHERE note.id=?1",
                [&first_id],
                |row| {
                    Ok((
                        row.get::<_, String>(0)?,
                        row.get::<_, String>(1)?,
                        row.get::<_, i64>(2)?,
                    ))
                },
            )
            .unwrap();
        let second_before = connection
            .query_row(
                "SELECT note.payload_json,intent.snapshot_json,intent.mutation_generation
                 FROM notes AS note
                 JOIN cloud_sync_outbox AS event ON event.entity_id=note.id
                 JOIN cloud_sync_note_intents AS intent USING(event_id)
                 WHERE note.id=?1",
                [&second_id],
                |row| {
                    Ok((
                        row.get::<_, String>(0)?,
                        row.get::<_, String>(1)?,
                        row.get::<_, i64>(2)?,
                    ))
                },
            )
            .unwrap();
        connection
            .execute_batch(&format!(
                "CREATE TRIGGER note_sync_test_fail_map_second BEFORE UPDATE ON notes
                 WHEN NEW.id='{second_id}' BEGIN SELECT RAISE(ABORT,'injected_note_failure'); END;"
            ))
            .unwrap();

        assert!(save_test_map(
            &mut connection,
            test_map(&[
                ("first-node", "Changed first"),
                ("second-node", "Changed second")
            ]),
        )
        .is_err());
        connection
            .execute_batch("DROP TRIGGER note_sync_test_fail_map_second")
            .unwrap();

        let owner_after: String = connection
            .query_row(
                "SELECT payload_json FROM projects WHERE id='project'",
                [],
                |row| row.get(0),
            )
            .unwrap();
        assert_eq!(owner_after, owner_before);
        for (id, before) in [(&first_id, first_before), (&second_id, second_before)] {
            let after = connection
                .query_row(
                    "SELECT note.payload_json,intent.snapshot_json,intent.mutation_generation
                     FROM notes AS note
                     JOIN cloud_sync_outbox AS event ON event.entity_id=note.id
                     JOIN cloud_sync_note_intents AS intent USING(event_id)
                     WHERE note.id=?1",
                    [id],
                    |row| {
                        Ok((
                            row.get::<_, String>(0)?,
                            row.get::<_, String>(1)?,
                            row.get::<_, i64>(2)?,
                        ))
                    },
                )
                .unwrap();
            assert_eq!(after, before);
        }
    }

    #[test]
    fn note_sync_combined_map_failure_rolls_back_prior_owner_and_note_changes() {
        let mut connection = direct_database(true);
        add_stage(&connection);
        connection
            .execute(
                "UPDATE projects SET payload_json=?1 WHERE id='project'",
                [serde_json::json!({
                    "combine_stage_mindmaps":true,
                    "mindmap":test_map(&[("project-existing", "Project old")])
                })
                .to_string()],
            )
            .unwrap();
        let stage_map = serde_json::json!({
            "nodeData":{"id":"stage-root","topic":"Stage","children":[]},
            "freeNodes":[
                {"id":"stage-existing","topic":"Stage old","children":[],"nfprogressNote":true}
            ]
        });
        connection
            .execute(
                "UPDATE stages SET payload_json=?1 WHERE id='stage'",
                [serde_json::json!({"mindmap":stage_map}).to_string()],
            )
            .unwrap();
        crate::reconcile_loaded_map_view_in_connection(&mut connection, "project", None).unwrap();

        let mut changed_stage_map: serde_json::Value = serde_json::from_str::<serde_json::Value>(
            &connection
                .query_row(
                    "SELECT payload_json FROM stages WHERE id='stage'",
                    [],
                    |row| row.get::<_, String>(0),
                )
                .unwrap(),
        )
        .unwrap()["mindmap"]
            .clone();
        changed_stage_map["freeNodes"][0]["topic"] = "Stage changed".into();
        connection
            .execute(
                "UPDATE stages SET payload_json=?1 WHERE id='stage'",
                [serde_json::json!({"mindmap":changed_stage_map}).to_string()],
            )
            .unwrap();

        let (project, stages) = {
            let repository = crate::ProjectsRepository::new(&mut connection);
            (
                repository.get_project("project").unwrap().unwrap(),
                repository.list_stages("project").unwrap(),
            )
        };
        let mut combined = crate::compose_combined_map(&project, &stages).unwrap();
        combined["freeNodes"][0]["topic"] = "Project changed".into();
        let normalized = crate::mindmap::normalize(combined.clone()).unwrap();
        let project_owner_before: String = connection
            .query_row(
                "SELECT payload_json FROM projects WHERE id='project'",
                [],
                |row| row.get(0),
            )
            .unwrap();
        let stage_owner_before: String = connection
            .query_row(
                "SELECT payload_json FROM stages WHERE id='stage'",
                [],
                |row| row.get(0),
            )
            .unwrap();
        let project_note_id = crate::mindmap::linked_note_id("project-existing");
        let stage_note_id = crate::mindmap::linked_note_id("stage-existing");
        let note_state = |connection: &Connection, note_id: &str| {
            connection
                .query_row(
                    "SELECT note.payload_json,intent.snapshot_json,intent.mutation_generation
                     FROM notes AS note
                     JOIN cloud_sync_outbox AS event ON event.entity_id=note.id
                     JOIN cloud_sync_note_intents AS intent USING(event_id)
                     WHERE note.id=?1",
                    [note_id],
                    |row| {
                        Ok((
                            row.get::<_, String>(0)?,
                            row.get::<_, String>(1)?,
                            row.get::<_, i64>(2)?,
                        ))
                    },
                )
                .unwrap()
        };
        let project_note_before = note_state(&connection, &project_note_id);
        let stage_note_before = note_state(&connection, &stage_note_id);
        connection
            .execute_batch(&format!(
                "CREATE TRIGGER note_sync_test_fail_combined_stage BEFORE UPDATE ON notes
                 WHEN NEW.id='{stage_note_id}' BEGIN SELECT RAISE(ABORT,'injected_note_failure'); END;"
            ))
            .unwrap();

        assert!(crate::save_map_in_connection(
            &mut connection,
            &crate::MapCommand {
                project_id: "project".to_string(),
                stage_id: None,
                data: combined,
            },
            &normalized,
        )
        .is_err());
        connection
            .execute_batch("DROP TRIGGER note_sync_test_fail_combined_stage")
            .unwrap();

        assert_eq!(
            connection
                .query_row(
                    "SELECT payload_json FROM projects WHERE id='project'",
                    [],
                    |row| row.get::<_, String>(0)
                )
                .unwrap(),
            project_owner_before
        );
        assert_eq!(
            connection
                .query_row(
                    "SELECT payload_json FROM stages WHERE id='stage'",
                    [],
                    |row| row.get::<_, String>(0)
                )
                .unwrap(),
            stage_owner_before
        );
        assert_eq!(
            note_state(&connection, &project_note_id),
            project_note_before
        );
        assert_eq!(note_state(&connection, &stage_note_id), stage_note_before);
    }

    #[test]
    fn note_sync_combined_save_map_captures_project_and_stage_notes() {
        let mut connection = direct_database(true);
        add_stage(&connection);
        let project_map = test_map(&[]);
        let stage_map = serde_json::json!({
            "nodeData":{"id":"stage-root","topic":"Stage","children":[]},
            "freeNodes":[
                {"id":"stage-node","topic":"Stage note","children":[],"nfprogressNote":true}
            ]
        });
        connection
            .execute(
                "UPDATE projects SET payload_json=?1 WHERE id='project'",
                [serde_json::json!({
                    "combine_stage_mindmaps":true,
                    "mindmap":project_map
                })
                .to_string()],
            )
            .unwrap();
        connection
            .execute(
                "UPDATE stages SET payload_json=?1 WHERE id='stage'",
                [serde_json::json!({"mindmap":stage_map}).to_string()],
            )
            .unwrap();
        let (project, stages) = {
            let repository = crate::ProjectsRepository::new(&mut connection);
            (
                repository.get_project("project").unwrap().unwrap(),
                repository.list_stages("project").unwrap(),
            )
        };
        let mut combined = crate::compose_combined_map(&project, &stages).unwrap();
        combined["freeNodes"] = serde_json::json!([
            {"id":"project-node","topic":"Project note","children":[],"nfprogressNote":true}
        ]);
        let normalized = crate::mindmap::normalize(combined.clone()).unwrap();
        crate::save_map_in_connection(
            &mut connection,
            &crate::MapCommand {
                project_id: "project".to_string(),
                stage_id: None,
                data: combined,
            },
            &normalized,
        )
        .unwrap();

        assert_eq!(
            connection
                .query_row("SELECT count(*) FROM notes", [], |row| row.get::<_, i64>(0))
                .unwrap(),
            2
        );
        assert_eq!(
            connection
                .query_row("SELECT count(*) FROM cloud_sync_note_intents", [], |row| {
                    row.get::<_, i64>(0)
                })
                .unwrap(),
            2
        );
        assert_eq!(
            connection
                .query_row(
                    "SELECT count(*) FROM notes WHERE stage_id='stage'",
                    [],
                    |row| row.get::<_, i64>(0)
                )
                .unwrap(),
            1
        );
    }
}
