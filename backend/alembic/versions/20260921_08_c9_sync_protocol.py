"""Create C9 metadata-only sync transport tables.

Revision ID: c9_sync_protocol
Revises: c8_cloud_projects
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c9_sync_protocol'
down_revision: Union[str, Sequence[str], None] = 'c8_cloud_projects'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


UTC_NOW = sa.text("timezone('utc', now())")


def upgrade() -> None:
    op.create_table(
        'sync_user_state',
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('current_sequence', sa.BigInteger(), nullable=False, server_default=sa.text('0')),
        sa.CheckConstraint('current_sequence >= 0', name='ck_sync_user_state_sequence_nonnegative'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('user_id'),
    )
    op.create_table(
        'sync_devices',
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('device_id', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=UTC_NOW),
        sa.Column('last_seen_at', sa.DateTime(timezone=True), nullable=False, server_default=UTC_NOW),
        sa.Column('last_ack_sequence', sa.BigInteger(), nullable=False, server_default=sa.text('0')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('user_id', 'device_id'),
    )
    op.create_table(
        'sync_events',
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('event_id', sa.Uuid(), nullable=False),
        sa.Column('device_id', sa.Uuid(), nullable=False),
        sa.Column('project_id', sa.String(length=512), nullable=False),
        sa.Column('entity_id', sa.String(length=512), nullable=False),
        sa.Column('entity_type', sa.String(length=128), nullable=False),
        sa.Column('operation', sa.String(length=16), nullable=False),
        sa.Column('revision', sa.BigInteger(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('server_sequence', sa.BigInteger(), nullable=False),
        sa.Column('accepted_at', sa.DateTime(timezone=True), nullable=False, server_default=UTC_NOW),
        sa.CheckConstraint("operation IN ('upsert', 'delete', 'event')", name='ck_sync_events_operation'),
        sa.CheckConstraint('revision >= 1', name='ck_sync_events_revision_positive'),
        sa.CheckConstraint('server_sequence > 0', name='ck_sync_events_sequence_positive'),
        sa.CheckConstraint("(operation = 'delete' AND deleted_at IS NOT NULL) OR (operation != 'delete' AND deleted_at IS NULL)", name='ck_sync_events_tombstone'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('user_id', 'event_id'),
        sa.UniqueConstraint('user_id', 'server_sequence', name='uq_sync_events_user_sequence'),
    )
    op.create_index('ix_sync_events_user_sequence', 'sync_events', ['user_id', 'server_sequence'])


def downgrade() -> None:
    op.drop_index('ix_sync_events_user_sequence', table_name='sync_events')
    op.drop_table('sync_events')
    op.drop_table('sync_devices')
    op.drop_table('sync_user_state')
