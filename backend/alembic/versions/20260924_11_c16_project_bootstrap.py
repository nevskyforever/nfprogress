"""Add the C16 cloud-project bootstrap control plane.

Revision ID: c16_project_bootstrap
Revises: c14_encrypted_cover_blobs
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c16_project_bootstrap'
down_revision: Union[str, Sequence[str], None] = 'c14_encrypted_cover_blobs'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('cloud_projects', sa.Column(
        'bootstrap_id', sa.Uuid(), nullable=True,
    ))
    op.add_column('cloud_projects', sa.Column(
        'bootstrap_device_id', sa.Uuid(), nullable=True,
    ))
    op.add_column('cloud_projects', sa.Column(
        'bootstrap_state', sa.String(length=16), nullable=False,
        server_default=sa.text("'legacy'"),
    ))
    op.add_column('cloud_projects', sa.Column(
        'initial_event_count', sa.BigInteger(), nullable=True,
    ))
    op.add_column('cloud_projects', sa.Column(
        'initial_max_server_sequence', sa.BigInteger(), nullable=True,
    ))
    op.add_column('cloud_projects', sa.Column(
        'bootstrap_completed_at', sa.DateTime(timezone=True), nullable=True,
    ))
    op.create_check_constraint(
        'ck_cloud_projects_bootstrap_state', 'cloud_projects',
        "bootstrap_state IN ('legacy', 'initializing', 'active')",
    )
    op.create_check_constraint(
        'ck_cloud_projects_bootstrap_shape', 'cloud_projects',
        "(bootstrap_state = 'legacy' AND bootstrap_id IS NULL AND bootstrap_device_id IS NULL "
        "AND bootstrap_completed_at IS NULL AND initial_event_count IS NULL "
        "AND initial_max_server_sequence IS NULL) OR "
        "(bootstrap_state = 'initializing' AND bootstrap_id IS NOT NULL "
        "AND bootstrap_device_id IS NOT NULL AND bootstrap_completed_at IS NULL "
        "AND initial_event_count IS NULL AND initial_max_server_sequence IS NULL) OR "
        "(bootstrap_state = 'active' AND bootstrap_id IS NOT NULL "
        "AND bootstrap_device_id IS NOT NULL AND bootstrap_completed_at IS NOT NULL "
        "AND initial_event_count IS NOT NULL AND initial_event_count >= 0 "
        "AND initial_max_server_sequence IS NOT NULL AND initial_max_server_sequence >= 0)",
    )
    op.create_unique_constraint(
        'uq_cloud_projects_user_bootstrap_id', 'cloud_projects',
        ['user_id', 'bootstrap_id'],
    )


def downgrade() -> None:
    op.drop_constraint('uq_cloud_projects_user_bootstrap_id', 'cloud_projects', type_='unique')
    op.drop_constraint('ck_cloud_projects_bootstrap_shape', 'cloud_projects', type_='check')
    op.drop_constraint('ck_cloud_projects_bootstrap_state', 'cloud_projects', type_='check')
    op.drop_column('cloud_projects', 'bootstrap_completed_at')
    op.drop_column('cloud_projects', 'initial_max_server_sequence')
    op.drop_column('cloud_projects', 'initial_event_count')
    op.drop_column('cloud_projects', 'bootstrap_state')
    op.drop_column('cloud_projects', 'bootstrap_device_id')
    op.drop_column('cloud_projects', 'bootstrap_id')
