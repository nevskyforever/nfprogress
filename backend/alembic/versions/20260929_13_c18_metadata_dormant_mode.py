"""Permit dormant transport mode 3 for C18 metadata; no activation path.

Revision ID: c18_metadata_dormant_mode
Revises: c17_dormant_protocol_v2
"""
from typing import Sequence, Union
from alembic import op

revision: str = 'c18_metadata_dormant_mode'
down_revision: Union[str, Sequence[str], None] = 'c17_dormant_protocol_v2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint('ck_sync_user_state_writer_transport_version', 'sync_user_state', type_='check')
    op.create_check_constraint(
        'ck_sync_user_state_writer_transport_version', 'sync_user_state',
        'writer_transport_version IN (1, 2, 3)',
    )
    op.execute("""
        CREATE OR REPLACE FUNCTION enforce_sync_transport_cutover_epoch() RETURNS trigger AS $$
        BEGIN
            IF NEW.cutover_epoch < OLD.cutover_epoch THEN
                RAISE EXCEPTION 'sync transport cutover epoch cannot decrease';
            END IF;
            IF NEW.writer_transport_version < OLD.writer_transport_version THEN
                RAISE EXCEPTION 'sync transport mode cannot downgrade';
            END IF;
            IF NEW.writer_transport_version <> OLD.writer_transport_version
               AND (NEW.writer_transport_version <> OLD.writer_transport_version + 1
                    OR NEW.cutover_epoch <= OLD.cutover_epoch) THEN
                RAISE EXCEPTION 'sync transport upgrade requires a new cutover epoch';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
    """)


def downgrade() -> None:
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
    op.drop_constraint('ck_sync_user_state_writer_transport_version', 'sync_user_state', type_='check')
    op.create_check_constraint(
        'ck_sync_user_state_writer_transport_version', 'sync_user_state',
        'writer_transport_version IN (1, 2)',
    )
