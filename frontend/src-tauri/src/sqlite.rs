//! Rust-owned SQLite opening and versioned migration runner.
//!
//! The SQL files are shared with the transitional Python runtime.  Keeping a
//! single set of files prevents the two runtimes from silently creating
//! incompatible databases while Projects ownership is being cut over.

use std::path::Path;

use rusqlite::{Connection, OpenFlags};

pub const CURRENT_SCHEMA_VERSION: i64 = 5;

#[derive(Debug)]
pub enum StorageError {
    Database(rusqlite::Error),
    UnsupportedSchema(i64),
    CorruptSchema(String),
}

impl std::fmt::Display for StorageError {
    fn fmt(&self, formatter: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::Database(error) => write!(formatter, "SQLite error: {error}"),
            Self::UnsupportedSchema(version) => {
                write!(formatter, "Unsupported SQLite schema version: {version}")
            }
            Self::CorruptSchema(message) => write!(formatter, "Corrupt SQLite schema: {message}"),
        }
    }
}

impl std::error::Error for StorageError {}

impl From<rusqlite::Error> for StorageError {
    fn from(error: rusqlite::Error) -> Self {
        Self::Database(error)
    }
}

const MIGRATIONS: [(i64, &str); 5] = [
    (
        1,
        include_str!("../../../nfprogress/core/sqlite/migrations/001_initial.sql"),
    ),
    (
        2,
        include_str!("../../../nfprogress/core/sqlite/migrations/002_storage_ownership.sql"),
    ),
    (
        3,
        include_str!("../../../nfprogress/core/sqlite/migrations/003_project_order.sql"),
    ),
    (
        4,
        include_str!("../../../nfprogress/core/sqlite/migrations/004_projects_authority.sql"),
    ),
    (
        5,
        include_str!("../../../nfprogress/core/sqlite/migrations/005_game_authority.sql"),
    ),
];

pub fn open_database(path: &Path) -> Result<Connection, StorageError> {
    let connection = Connection::open_with_flags(
        path,
        OpenFlags::SQLITE_OPEN_READ_WRITE | OpenFlags::SQLITE_OPEN_CREATE,
    )?;
    connection.busy_timeout(std::time::Duration::from_secs(5))?;
    connection.execute_batch("PRAGMA foreign_keys = ON;")?;
    // F3 migration 005 extends the F2 outbox, so it must exist before the
    // versioned scripts are applied on an existing v4 database.
    connection.execute_batch(DOMAIN_EVENTS_SCHEMA)?;
    apply_migrations(&connection)?;
    connection.execute_batch(DOMAIN_EVENTS_SCHEMA)?;
    Ok(connection)
}

const DOMAIN_EVENTS_SCHEMA: &str = "CREATE TABLE IF NOT EXISTS domain_events (event_id TEXT PRIMARY KEY, event_type TEXT NOT NULL, project_id TEXT NOT NULL, stage_id TEXT, progress_id TEXT, effective_date TEXT, delta_symbols REAL, context_json TEXT NOT NULL, created_at TEXT NOT NULL, processed_at TEXT, consumer TEXT NOT NULL DEFAULT 'game', version INTEGER NOT NULL DEFAULT 1); CREATE INDEX IF NOT EXISTS idx_domain_events_pending ON domain_events(consumer, processed_at, created_at);";

pub fn apply_migrations(connection: &Connection) -> Result<i64, StorageError> {
    connection.execute_batch("PRAGMA foreign_keys = ON;")?;
    connection.execute_batch(
        "CREATE TABLE IF NOT EXISTS schema_info (schema_version INTEGER NOT NULL);",
    )?;
    let versions: Vec<i64> = {
        let mut statement = connection.prepare("SELECT schema_version FROM schema_info")?;
        let result = statement
            .query_map([], |row| row.get(0))?
            .collect::<Result<Vec<i64>, _>>()?;
        result
    };
    if versions.len() > 1 {
        return Err(StorageError::CorruptSchema(
            "schema_info contains more than one version".to_string(),
        ));
    }
    let version = versions.first().copied().unwrap_or(0);
    if version > CURRENT_SCHEMA_VERSION {
        return Err(StorageError::UnsupportedSchema(version));
    }
    for (next_version, sql) in MIGRATIONS
        .iter()
        .filter(|(migration_version, _)| *migration_version > version)
    {
        let transaction = connection.unchecked_transaction()?;
        transaction.execute_batch(sql)?;
        transaction.execute("DELETE FROM schema_info", [])?;
        transaction.execute(
            "INSERT INTO schema_info(schema_version) VALUES (?1)",
            [next_version],
        )?;
        transaction.commit()?;
    }
    Ok(CURRENT_SCHEMA_VERSION)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn fresh_database_reaches_latest_schema() {
        let connection = Connection::open_in_memory().unwrap();
        assert_eq!(apply_migrations(&connection).unwrap(), 5);
        assert_eq!(
            connection
                .query_row("SELECT schema_version FROM schema_info", [], |row| row
                    .get::<_, i64>(0))
                .unwrap(),
            5
        );
        assert!(
            connection
                .query_row(
                    "SELECT owner FROM storage_ownership WHERE subsystem='projects'",
                    [],
                    |row| row.get::<_, String>(0),
                )
                .unwrap()
                == "pickle"
        );
    }

    #[test]
    fn future_schema_is_rejected() {
        let connection = Connection::open_in_memory().unwrap();
        connection
            .execute(
                "CREATE TABLE schema_info(schema_version INTEGER NOT NULL)",
                [],
            )
            .unwrap();
        connection
            .execute("INSERT INTO schema_info VALUES(99)", [])
            .unwrap();
        assert!(matches!(
            apply_migrations(&connection),
            Err(StorageError::UnsupportedSchema(99))
        ));
    }

    #[test]
    fn populated_v3_upgrade_preserves_settings_notes_and_pickle_owner() {
        let connection = Connection::open_in_memory().unwrap();
        connection.execute_batch(MIGRATIONS[0].1).unwrap();
        connection.execute_batch(MIGRATIONS[1].1).unwrap();
        connection.execute_batch(MIGRATIONS[2].1).unwrap();
        connection
            .execute_batch("CREATE TABLE schema_info(schema_version INTEGER NOT NULL);")
            .unwrap();
        connection
            .execute("INSERT INTO schema_info VALUES(3)", [])
            .unwrap();
        connection
            .execute(
                "INSERT INTO projects VALUES('p', 'P', 1, 0, 'symbols', 'активен', NULL, NULL, '{}')",
                [],
            )
            .unwrap();
        connection
            .execute("INSERT INTO settings VALUES('preserve', 'true')", [])
            .unwrap();
        connection
            .execute("INSERT INTO notes VALUES('n', 'p', NULL, 'old', '{}')", [])
            .unwrap();

        apply_migrations(&connection).unwrap();

        assert_eq!(
            connection
                .query_row("SELECT schema_version FROM schema_info", [], |row| row
                    .get::<_, i64>(0))
                .unwrap(),
            5
        );
        assert_eq!(
            connection
                .query_row(
                    "SELECT value_json FROM settings WHERE key='preserve'",
                    [],
                    |row| row.get::<_, String>(0)
                )
                .unwrap(),
            "true"
        );
        assert_eq!(
            connection
                .query_row("SELECT id FROM notes", [], |row| row.get::<_, String>(0))
                .unwrap(),
            "n"
        );
        assert_eq!(
            connection
                .query_row(
                    "SELECT owner FROM storage_ownership WHERE subsystem='projects'",
                    [],
                    |row| row.get::<_, String>(0)
                )
                .unwrap(),
            "pickle"
        );
    }
}
