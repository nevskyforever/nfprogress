"""Codec11 progress reader capabilities; no plaintext progress storage."""
from alembic import op
import sqlalchemy as sa

revision = 'c18_progress_readers'
down_revision = 'c18_document_readers'
branch_labels = None
depends_on = None


def upgrade():
    for name in ('progress_frame_version', 'progress_codec_version', 'progress_reader_version'):
        op.add_column('sync_devices', sa.Column(name, sa.Integer(), nullable=False, server_default='0'))
        op.create_check_constraint(f'ck_sync_devices_{name}', 'sync_devices', f'{name} IN (0,1)')
    op.add_column('sync_devices', sa.Column('progress_compression_zero', sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade():
    if op.get_bind().scalar(sa.text("SELECT EXISTS(SELECT 1 FROM sync_events WHERE entity_type='progress')")):
        raise RuntimeError('Cannot remove progress capabilities while progress history exists')
    op.drop_column('sync_devices', 'progress_compression_zero')
    for name in ('progress_frame_version', 'progress_codec_version', 'progress_reader_version'):
        op.drop_constraint(f'ck_sync_devices_{name}', 'sync_devices', type_='check')
        op.drop_column('sync_devices', name)
