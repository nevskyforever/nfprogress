from __future__ import annotations

from collections.abc import Generator
from enum import Enum

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker


POSTGRESQL_CONNECT_TIMEOUT_SECONDS = 5


class DatabaseNotConfiguredError(RuntimeError):
    """Raised only at the cloud boundary when PostgreSQL is intentionally absent."""


class DatabaseReadiness(str, Enum):
    READY = 'ready'
    NOT_CONFIGURED = 'not_configured'
    UNAVAILABLE = 'unavailable'


class CloudDatabase:
    """One process-wide synchronous engine and session factory for cloud routes.

    This class has no knowledge of PickleRepository, desktop SQLite, or legacy
    compatibility storage. Constructing an engine does not connect to PostgreSQL;
    connection attempts are limited to explicit request work and readiness checks.
    """

    def __init__(self, database_url: str | None) -> None:
        self._engine: Engine | None = None
        self._session_factory: sessionmaker[Session] | None = None
        if database_url is not None:
            engine_options = {'pool_pre_ping': True}
            if database_url.startswith('postgresql+psycopg://'):
                engine_options['connect_args'] = {
                    'connect_timeout': POSTGRESQL_CONNECT_TIMEOUT_SECONDS,
                }
            self._engine = create_engine(database_url, **engine_options)
            self._session_factory = sessionmaker(
                bind=self._engine,
                autoflush=False,
                expire_on_commit=False,
            )

    @property
    def is_configured(self) -> bool:
        return self._engine is not None

    @property
    def engine(self) -> Engine:
        if self._engine is None:
            raise DatabaseNotConfiguredError('Cloud PostgreSQL is not configured.')
        return self._engine

    def open_session(self) -> Session:
        if self._session_factory is None:
            raise DatabaseNotConfiguredError('Cloud PostgreSQL is not configured.')
        return self._session_factory()

    def session_scope(self) -> Generator[Session, None, None]:
        """Yield one session and always roll back failed work before closing it."""
        session = self.open_session()
        try:
            yield session
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def readiness(self) -> DatabaseReadiness:
        if self._engine is None:
            return DatabaseReadiness.NOT_CONFIGURED
        try:
            with self._engine.connect() as connection:
                connection.execute(text('SELECT 1'))
        except SQLAlchemyError:
            return DatabaseReadiness.UNAVAILABLE
        return DatabaseReadiness.READY

    def dispose(self) -> None:
        if self._engine is not None:
            self._engine.dispose()
