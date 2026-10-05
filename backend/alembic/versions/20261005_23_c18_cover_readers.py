"""Explicit metadata-v2/cover reader capability; no blob or plaintext schema."""
from alembic import op
import sqlalchemy as sa
revision = 'c18_cover_readers'
down_revision = 'c18_game_readers'
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('sync_devices', sa.Column('metadata_cover_reader_version', sa.Integer(), nullable=False, server_default='0'))
    op.create_check_constraint('ck_sync_devices_metadata_cover_reader_version', 'sync_devices', 'metadata_cover_reader_version IN (0,2)')

def downgrade():
    if op.get_bind().scalar(sa.text("SELECT EXISTS(SELECT 1 FROM sync_devices WHERE metadata_cover_reader_version=2)")):
        raise RuntimeError('Cannot discard declared cover reader capability; encrypted metadata may require it')
    op.drop_constraint('ck_sync_devices_metadata_cover_reader_version', 'sync_devices', type_='check')
    op.drop_column('sync_devices', 'metadata_cover_reader_version')
