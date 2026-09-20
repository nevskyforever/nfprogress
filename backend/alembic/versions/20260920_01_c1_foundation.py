"""Create the C1 PostgreSQL migration baseline.

Revision ID: c1_postgresql_foundation
Revises:
Create Date: 2026-09-20
"""

from typing import Sequence, Union


revision: str = 'c1_postgresql_foundation'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Establish only Alembic's version state; C1 has no business tables."""


def downgrade() -> None:
    """No application schema exists to remove at the C1 baseline."""
