"""JSON-safe projections of legacy domain entities."""

from nfprogress.core.serialization.projections import (
    serialize_note,
    serialize_project,
    serialize_project_note,
    serialize_stage,
    to_json_safe,
)

__all__ = [
    'serialize_note',
    'serialize_project',
    'serialize_project_note',
    'serialize_stage',
    'to_json_safe',
]
