"""Shadow SQLite persistence for the legacy pickle stores."""

from nfprogress.core.sqlite.repository import SQLiteMirrorRepository
from nfprogress.core.sqlite.ownership import (
    StorageOwner,
    StorageOwnershipRepository,
    Subsystem,
)
from nfprogress.core.sqlite.settings import SQLiteSettingsRepository, cutover_settings
from nfprogress.core.sqlite.notes import (
    SQLiteNotesRepository,
    canonical_notes_from_projects,
    cutover_notes,
)
from nfprogress.core.game_state import SQLiteGameRepository, GameEventConsumer

__all__ = [
    'SQLiteMirrorRepository',
    'StorageOwner',
    'StorageOwnershipRepository',
    'Subsystem',
    'SQLiteSettingsRepository',
    'cutover_settings',
    'SQLiteNotesRepository',
    'canonical_notes_from_projects',
    'cutover_notes',
    'SQLiteGameRepository',
    'GameEventConsumer',
]
