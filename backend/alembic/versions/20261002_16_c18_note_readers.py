"""Explicit codec8 reader evidence; mode3 alone is insufficient."""
from alembic import op
import sqlalchemy as sa

revision = 'c18_note_readers'
down_revision = 'c18_account_scope'
branch_labels = None
depends_on = None


def upgrade():
    for name in ('note_frame_version', 'note_codec_version', 'note_ordinary_reader_version', 'note_resolution_reader_version'):
        op.add_column('sync_devices', sa.Column(name, sa.Integer(), nullable=False, server_default='0'))
        versions = '(0,2)' if name == 'note_resolution_reader_version' else '(0,1)'
        op.create_check_constraint(f'ck_sync_devices_{name}', 'sync_devices', f'{name} IN {versions}')
    op.add_column('sync_devices', sa.Column('note_compression_zero', sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade():
    # Do not remove the gate while framed history can remain in the sequence.
    connection = op.get_bind()
    if connection.scalar(sa.text("SELECT EXISTS(SELECT 1 FROM sync_events WHERE entity_type='note' AND operation='event')")):
        raise RuntimeError('Cannot remove reader capabilities while framed Note history exists')
    op.drop_column('sync_devices', 'note_compression_zero')
    for name in ('note_frame_version', 'note_codec_version', 'note_ordinary_reader_version', 'note_resolution_reader_version'):
        op.drop_constraint(f'ck_sync_devices_{name}', 'sync_devices', type_='check')
        op.drop_column('sync_devices', name)
