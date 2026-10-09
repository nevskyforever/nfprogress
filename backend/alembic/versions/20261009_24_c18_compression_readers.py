"""Explicit ID1 readers and conservative retained-history read barrier."""
from alembic import op
import sqlalchemy as sa
revision = 'c18_compression_readers'
down_revision = 'c18_cover_readers'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('sync_devices', sa.Column('compression_id1', sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column('sync_user_state', sa.Column('compression_id1_required', sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade():
    # Never erase the read barrier while immutable ID1 history may exist.
    if op.get_bind().scalar(sa.text('SELECT EXISTS(SELECT 1 FROM sync_user_state WHERE compression_id1_required)')):
        raise RuntimeError('Cannot discard compression read barrier; retained ciphertext may require ID1')
    op.drop_column('sync_user_state', 'compression_id1_required')
    op.drop_column('sync_devices', 'compression_id1')
