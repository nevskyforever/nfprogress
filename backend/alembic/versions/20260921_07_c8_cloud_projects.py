"""Create C8 metadata-only cloud project registry.

Revision ID: c8_cloud_projects
Revises: c6_reserved_usernames
Create Date: 2026-09-21
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c8_cloud_projects'
down_revision: Union[str, Sequence[str], None] = 'c6_reserved_usernames'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


UTC_NOW = sa.text("timezone('utc', now())")


def upgrade() -> None:
    op.create_table(
        'cloud_projects',
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('project_id', sa.String(length=512), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=UTC_NOW),
        sa.CheckConstraint('char_length(project_id) >= 1', name='ck_cloud_projects_project_id_not_empty'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('user_id', 'project_id'),
    )


def downgrade() -> None:
    op.drop_table('cloud_projects')
