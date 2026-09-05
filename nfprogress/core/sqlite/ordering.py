"""Semantic invariants for the normalized SQLite order relations."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Any


class OrderInvariantError(RuntimeError):
    """The normalized order relations do not represent their source rows."""


@dataclass(frozen=True, slots=True)
class ProjectOrderProposal:
    """Read-only proposal for repairing a project order relation."""

    project_ids: tuple[str, ...]
    existing_order: tuple[str, ...]
    proposed_order: tuple[str, ...]

    @property
    def requires_recovery(self) -> bool:
        return self.existing_order != self.proposed_order

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_ids": list(self.project_ids),
            "existing_order": list(self.existing_order),
            "proposed_order": list(self.proposed_order),
            "requires_recovery": self.requires_recovery,
        }


@dataclass(frozen=True, slots=True)
class OrderTableProposal:
    """Existing and proposed IDs for one non-project order relation."""

    existing_order: Any
    proposed_order: Any


def validate_project_order(connection: sqlite3.Connection) -> None:
    """Require a one-to-one, contiguous project order relation."""
    project_ids = [row[0] for row in connection.execute("SELECT id FROM projects")]
    order_rows = connection.execute(
        "SELECT project_id, position FROM project_order ORDER BY position, project_id"
    ).fetchall()
    order_ids = [row[0] for row in order_rows]
    positions = [row[1] for row in order_rows]
    if positions != list(range(len(positions))):
        raise OrderInvariantError("project ordering positions are not contiguous")
    if len(order_ids) != len(set(order_ids)):
        raise OrderInvariantError("project ordering contains duplicate projects")
    if set(order_ids) != set(project_ids) or len(order_ids) != len(project_ids):
        raise OrderInvariantError("project ordering is incomplete")


def validate_stage_order(connection: sqlite3.Connection) -> None:
    """Require every stage to have one order row under its owning project."""
    stages = {
        row[0]: row[1]
        for row in connection.execute("SELECT id, project_id FROM stages")
    }
    rows = connection.execute(
        "SELECT stage_id, project_id, position FROM stage_order "
        "ORDER BY project_id, position, stage_id"
    ).fetchall()
    if len(rows) != len(stages) or {row[0] for row in rows} != set(stages):
        raise OrderInvariantError("stage ordering is incomplete")
    if len({row[0] for row in rows}) != len(rows):
        raise OrderInvariantError("stage ordering contains duplicate stages")
    if any(row[0] not in stages or stages[row[0]] != row[1] for row in rows):
        raise OrderInvariantError("stage ordering has an invalid project owner")
    for project_id in {row[1] for row in rows}:
        positions = [row[2] for row in rows if row[1] == project_id]
        if positions != list(range(len(positions))):
            raise OrderInvariantError("stage ordering positions are not contiguous")


def validate_progress_order(connection: sqlite3.Connection) -> None:
    """Require every progress entry to have one globally ordered row."""
    progress_ids = {
        row[0] for row in connection.execute("SELECT id FROM progress_entries")
    }
    rows = connection.execute(
        "SELECT entry_id, position FROM progress_order ORDER BY position, entry_id"
    ).fetchall()
    order_ids = [row[0] for row in rows]
    positions = [row[1] for row in rows]
    if len(order_ids) != len(set(order_ids)):
        raise OrderInvariantError("progress ordering contains duplicate entries")
    if set(order_ids) != progress_ids or len(order_ids) != len(progress_ids):
        raise OrderInvariantError("progress ordering is incomplete")
    if positions != list(range(len(positions))):
        raise OrderInvariantError("progress ordering positions are not contiguous")


def validate_order_invariants(connection: sqlite3.Connection) -> None:
    """Validate all order relations used by the v6 SQLite representation."""
    validate_project_order(connection)
    validate_stage_order(connection)
    validate_progress_order(connection)


def propose_project_order_recovery(connection: sqlite3.Connection) -> ProjectOrderProposal:
    """Build a deterministic, non-mutating project order proposal.

    Existing rows are retained in their stored relative order. Missing or
    invalid references are appended by real project fields: creation time,
    update time, and finally stable ID.  This is the documented fallback when
    no complete legacy order is available.
    """
    project_rows = connection.execute(
        "SELECT id, created_at, updated_at FROM projects ORDER BY id"
    ).fetchall()
    project_ids = tuple(row[0] for row in project_rows)
    known = set(project_ids)
    existing_rows = connection.execute(
        "SELECT project_id, position FROM project_order ORDER BY position, project_id"
    ).fetchall()
    existing_order = tuple(row[0] for row in existing_rows)
    retained: list[str] = []
    for project_id in existing_order:
        if project_id in known and project_id not in retained:
            retained.append(project_id)
    project_by_id = {row[0]: row for row in project_rows}
    missing = sorted(
        (project_id for project_id in known if project_id not in retained),
        key=lambda project_id: (
            project_by_id[project_id][1] or "",
            project_by_id[project_id][2] or "",
            project_id,
        ),
    )
    proposed = tuple(retained + missing)
    return ProjectOrderProposal(project_ids, existing_order, proposed)


def propose_stage_order_recovery(connection: sqlite3.Connection) -> OrderTableProposal:
    """Propose per-project stage orders using persisted stage fields as fallback."""
    stage_rows = connection.execute(
        "SELECT id, project_id, created_at, updated_at FROM stages"
    ).fetchall()
    stage_by_id = {row[0]: row for row in stage_rows}
    existing: dict[str, list[str]] = {}
    for stage_id, project_id, _position in connection.execute(
        "SELECT stage_id, project_id, position FROM stage_order ORDER BY project_id, position, stage_id"
    ):
        existing.setdefault(project_id, []).append(stage_id)
    proposed: dict[str, list[str]] = {}
    project_ids = {row[1] for row in stage_rows}
    for project_id in sorted(project_ids):
        retained = [
            stage_id for stage_id in existing.get(project_id, [])
            if stage_id in stage_by_id and stage_by_id[stage_id][1] == project_id
        ]
        retained = list(dict.fromkeys(retained))
        missing = sorted(
            (stage_id for stage_id, row in stage_by_id.items()
             if row[1] == project_id and stage_id not in retained),
            key=lambda stage_id: (
                stage_by_id[stage_id][2] or "",
                stage_by_id[stage_id][3] or "",
                stage_id,
            ),
        )
        proposed[project_id] = retained + missing
    return OrderTableProposal(existing, proposed)


def propose_progress_order_recovery(connection: sqlite3.Connection) -> OrderTableProposal:
    """Propose a global progress order using creation time and stable ID."""
    progress_rows = connection.execute(
        "SELECT id, created_at FROM progress_entries"
    ).fetchall()
    known = {row[0] for row in progress_rows}
    existing = tuple(
        row[0] for row in connection.execute(
            "SELECT entry_id, position FROM progress_order ORDER BY position, entry_id"
        )
    )
    retained = list(dict.fromkeys(entry_id for entry_id in existing if entry_id in known))
    progress_by_id = {row[0]: row for row in progress_rows}
    missing = sorted(
        (entry_id for entry_id in known if entry_id not in retained),
        key=lambda entry_id: (progress_by_id[entry_id][1] or "", entry_id),
    )
    return OrderTableProposal(existing, tuple(retained + missing))


def apply_project_order_recovery(
    connection: sqlite3.Connection,
    proposal: ProjectOrderProposal,
) -> None:
    """Apply a previously inspected proposal to a staging database only."""
    if set(proposal.proposed_order) != set(proposal.project_ids):
        raise OrderInvariantError("project recovery proposal is incomplete")
    connection.execute("DELETE FROM project_order")
    connection.executemany(
        "INSERT INTO project_order(project_id, position) VALUES(?, ?)",
        [(project_id, position) for position, project_id in enumerate(proposal.proposed_order)],
    )


def apply_order_recovery(
    connection: sqlite3.Connection,
    project_proposal: ProjectOrderProposal,
    stage_proposal: OrderTableProposal,
    progress_proposal: OrderTableProposal,
) -> None:
    """Apply all three proposals to a staging database."""
    apply_project_order_recovery(connection, project_proposal)
    connection.execute("DELETE FROM stage_order")
    connection.executemany(
        "INSERT INTO stage_order(stage_id, project_id, position) VALUES(?, ?, ?)",
        [
            (stage_id, project_id, position)
            for project_id, stage_ids in stage_proposal.proposed_order.items()
            for position, stage_id in enumerate(stage_ids)
        ],
    )
    connection.execute("DELETE FROM progress_order")
    connection.executemany(
        "INSERT INTO progress_order(entry_id, position) VALUES(?, ?)",
        [(entry_id, position) for position, entry_id in enumerate(progress_proposal.proposed_order)],
    )
