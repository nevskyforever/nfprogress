"""Add dormant C17 encrypted-sync transport-v2 server state.

Revision ID: c17_dormant_protocol_v2
Revises: c16_project_bootstrap
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c17_dormant_protocol_v2'
down_revision: Union[str, Sequence[str], None] = 'c16_project_bootstrap'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('sync_user_state', sa.Column(
        'writer_transport_version', sa.Integer(), nullable=False, server_default=sa.text('1'),
    ))
    op.add_column('sync_user_state', sa.Column(
        'cutover_epoch', sa.BigInteger(), nullable=False, server_default=sa.text('0'),
    ))
    op.create_check_constraint(
        'ck_sync_user_state_writer_transport_version', 'sync_user_state',
        'writer_transport_version IN (1, 2)',
    )
    op.create_check_constraint(
        'ck_sync_user_state_cutover_epoch_safe_integer', 'sync_user_state',
        'cutover_epoch >= 0 AND cutover_epoch <= 9007199254740991',
    )
    op.execute("""
        CREATE OR REPLACE FUNCTION enforce_sync_transport_cutover_epoch() RETURNS trigger AS $$
        BEGIN
            IF NEW.cutover_epoch < OLD.cutover_epoch THEN
                RAISE EXCEPTION 'sync transport cutover epoch cannot decrease';
            END IF;
            IF OLD.writer_transport_version = 2 AND NEW.writer_transport_version = 1 THEN
                RAISE EXCEPTION 'sync transport mode cannot downgrade to version 1';
            END IF;
            IF NEW.writer_transport_version <> OLD.writer_transport_version
               AND (NEW.writer_transport_version <> 2 OR NEW.cutover_epoch <= OLD.cutover_epoch) THEN
                RAISE EXCEPTION 'sync transport upgrade requires a new cutover epoch';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
    """)
    op.execute("""
        CREATE TRIGGER trg_sync_user_state_cutover_epoch
        BEFORE UPDATE ON sync_user_state
        FOR EACH ROW EXECUTE FUNCTION enforce_sync_transport_cutover_epoch()
    """)
    op.drop_constraint('ck_sync_events_operation', 'sync_events', type_='check')
    op.create_check_constraint(
        'ck_sync_events_operation', 'sync_events',
        "operation IN ('upsert', 'delete', 'event', 'resolution')",
    )


def downgrade() -> None:
    op.drop_constraint('ck_sync_events_operation', 'sync_events', type_='check')
    op.create_check_constraint(
        'ck_sync_events_operation', 'sync_events',
        "operation IN ('upsert', 'delete', 'event')",
    )
    op.execute('DROP TRIGGER IF EXISTS trg_sync_user_state_cutover_epoch ON sync_user_state')
    op.execute('DROP FUNCTION enforce_sync_transport_cutover_epoch()')
    op.drop_constraint('ck_sync_user_state_cutover_epoch_safe_integer', 'sync_user_state', type_='check')
    op.drop_constraint('ck_sync_user_state_writer_transport_version', 'sync_user_state', type_='check')
    op.drop_column('sync_user_state', 'cutover_epoch')
    op.drop_column('sync_user_state', 'writer_transport_version')
