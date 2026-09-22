//! Authoritative local-account to backend-user binding primitives.

use rusqlite::{Connection, OptionalExtension, TransactionBehavior};
use serde::{Deserialize, Serialize};

#[derive(Debug)]
pub(crate) enum AccountBindingError {
    Database(rusqlite::Error),
    InvalidIdentity,
    MissingLocalAccount,
    IdentityMismatch,
    UserAlreadyBound,
}

impl std::fmt::Display for AccountBindingError {
    fn fmt(&self, formatter: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::Database(error) => write!(formatter, "SQLite error: {error}"),
            Self::InvalidIdentity => write!(formatter, "Invalid cloud account binding identity"),
            Self::MissingLocalAccount => write!(formatter, "Local cloud account does not exist"),
            Self::IdentityMismatch => write!(formatter, "Cloud account binding identity mismatch"),
            Self::UserAlreadyBound => write!(
                formatter,
                "Backend user is already bound to another local account"
            ),
        }
    }
}

impl From<rusqlite::Error> for AccountBindingError {
    fn from(error: rusqlite::Error) -> Self {
        Self::Database(error)
    }
}

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
pub(crate) struct EnsureCloudAccountBindingCommand {
    pub local_account_id: String,
    pub canonical_user_id: String,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize)]
#[serde(rename_all = "snake_case")]
pub(crate) enum EnsureCloudAccountBindingResult {
    Created,
    Validated,
}

fn canonical_backend_user_id(value: &str) -> bool {
    if value.len() != 36 || value != value.to_ascii_lowercase() {
        return false;
    }
    value.bytes().enumerate().all(|(index, byte)| {
        if matches!(index, 8 | 13 | 18 | 23) {
            byte == b'-'
        } else {
            byte.is_ascii_hexdigit()
        }
    })
}

pub(crate) fn ensure_cloud_account_binding(
    connection: &mut Connection,
    command: &EnsureCloudAccountBindingCommand,
) -> Result<EnsureCloudAccountBindingResult, AccountBindingError> {
    if command.local_account_id.is_empty()
        || command.local_account_id.len() > 512
        || !canonical_backend_user_id(&command.canonical_user_id)
    {
        return Err(AccountBindingError::InvalidIdentity);
    }
    let transaction = connection.transaction_with_behavior(TransactionBehavior::Immediate)?;
    let local_exists = transaction
        .query_row(
            "SELECT 1 FROM cloud_sync_state WHERE account_id=?1",
            [&command.local_account_id],
            |_| Ok(()),
        )
        .optional()?
        .is_some();
    if !local_exists {
        return Err(AccountBindingError::MissingLocalAccount);
    }
    let existing = transaction
        .query_row(
            "SELECT canonical_user_id FROM cloud_account_bindings WHERE local_account_id=?1",
            [&command.local_account_id],
            |row| row.get::<_, String>(0),
        )
        .optional()?;
    if let Some(existing) = existing {
        if existing != command.canonical_user_id {
            return Err(AccountBindingError::IdentityMismatch);
        }
        transaction.execute(
            "UPDATE cloud_account_bindings
             SET validated_at=strftime('%Y-%m-%dT%H:%M:%fZ','now')
             WHERE local_account_id=?1 AND canonical_user_id=?2",
            rusqlite::params![command.local_account_id, command.canonical_user_id],
        )?;
        transaction.commit()?;
        return Ok(EnsureCloudAccountBindingResult::Validated);
    }
    let user_binding = transaction
        .query_row(
            "SELECT local_account_id FROM cloud_account_bindings WHERE canonical_user_id=?1",
            [&command.canonical_user_id],
            |row| row.get::<_, String>(0),
        )
        .optional()?;
    if user_binding.is_some() {
        return Err(AccountBindingError::UserAlreadyBound);
    }
    transaction.execute(
        "INSERT INTO cloud_account_bindings(
            local_account_id,canonical_user_id,created_at,validated_at
         ) VALUES(?1,?2,strftime('%Y-%m-%dT%H:%M:%fZ','now'),strftime('%Y-%m-%dT%H:%M:%fZ','now'))",
        rusqlite::params![command.local_account_id, command.canonical_user_id],
    )?;
    transaction.commit()?;
    Ok(EnsureCloudAccountBindingResult::Created)
}

#[cfg(test)]
mod tests {
    use super::*;

    const DEVICE_ID: &str = "123e4567-e89b-42d3-a456-426614174000";
    const USER_ONE: &str = "abcdefab-0000-0000-0000-000000000101";
    const USER_TWO: &str = "00000000-0000-0000-0000-000000000102";

    fn database() -> Connection {
        let connection = Connection::open_in_memory().unwrap();
        crate::sqlite::apply_migrations(&connection).unwrap();
        connection.execute(
            "INSERT INTO cloud_sync_state(account_id,device_id,pull_cursor,ack_cursor,created_at,updated_at)
             VALUES('local-account',?1,0,0,'now','now')",
            [DEVICE_ID],
        ).unwrap();
        connection
    }

    fn command(user_id: &str) -> EnsureCloudAccountBindingCommand {
        EnsureCloudAccountBindingCommand {
            local_account_id: "local-account".to_string(),
            canonical_user_id: user_id.to_string(),
        }
    }

    #[test]
    fn authenticated_identity_creates_and_revalidates_an_immutable_binding() {
        let mut connection = database();
        assert_eq!(
            ensure_cloud_account_binding(&mut connection, &command(USER_ONE)).unwrap(),
            EnsureCloudAccountBindingResult::Created
        );
        assert_eq!(
            ensure_cloud_account_binding(&mut connection, &command(USER_ONE)).unwrap(),
            EnsureCloudAccountBindingResult::Validated
        );
        assert_eq!(
            connection
                .query_row(
                    "SELECT local_account_id,canonical_user_id FROM cloud_account_bindings",
                    [],
                    |row| Ok((row.get::<_, String>(0)?, row.get::<_, String>(1)?)),
                )
                .unwrap(),
            ("local-account".to_string(), USER_ONE.to_string())
        );
    }

    #[test]
    fn mismatched_identity_fails_without_rewriting_the_binding() {
        let mut connection = database();
        ensure_cloud_account_binding(&mut connection, &command(USER_ONE)).unwrap();
        assert!(matches!(
            ensure_cloud_account_binding(&mut connection, &command(USER_TWO)),
            Err(AccountBindingError::IdentityMismatch)
        ));
        assert_eq!(connection.query_row(
            "SELECT canonical_user_id FROM cloud_account_bindings WHERE local_account_id='local-account'",
            [], |row| row.get::<_, String>(0),
        ).unwrap(), USER_ONE);
    }

    #[test]
    fn missing_account_and_noncanonical_user_are_rejected() {
        let mut connection = database();
        let missing = EnsureCloudAccountBindingCommand {
            local_account_id: "missing".to_string(),
            canonical_user_id: USER_ONE.to_string(),
        };
        assert!(matches!(
            ensure_cloud_account_binding(&mut connection, &missing),
            Err(AccountBindingError::MissingLocalAccount)
        ));
        assert!(matches!(
            ensure_cloud_account_binding(&mut connection, &command(&USER_ONE.to_ascii_uppercase())),
            Err(AccountBindingError::InvalidIdentity)
        ));
        assert_eq!(
            connection
                .query_row("SELECT count(*) FROM cloud_account_bindings", [], |row| row
                    .get::<_, i64>(0))
                .unwrap(),
            0
        );
    }
}
