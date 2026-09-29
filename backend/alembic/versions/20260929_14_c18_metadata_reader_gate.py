"""Record explicit per-device mode-3 reader readiness before account cutover.

Revision ID: c18_metadata_reader_gate
Revises: c18_metadata_dormant_mode
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'c18_metadata_reader_gate'
down_revision: Union[str, Sequence[str], None] = 'c18_metadata_dormant_mode'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('sync_devices', sa.Column('reader_transport_version', sa.Integer(),
                                           nullable=False, server_default='2'))
    op.create_check_constraint('ck_sync_devices_reader_transport_version', 'sync_devices',
                               'reader_transport_version IN (2, 3)')


def downgrade() -> None:
    op.drop_constraint('ck_sync_devices_reader_transport_version', 'sync_devices', type_='check')
    op.drop_column('sync_devices', 'reader_transport_version')
