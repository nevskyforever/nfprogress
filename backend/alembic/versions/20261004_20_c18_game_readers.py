"""Independent project/account Game reader capabilities; no Game plaintext."""
from alembic import op
import sqlalchemy as sa

revision = 'c18_game_readers'
down_revision = 'c18_progress_readers'
branch_labels = None
depends_on = None


def upgrade():
    op.drop_constraint('ck_sync_events_scope', 'sync_events', type_='check')
    op.create_check_constraint('ck_sync_events_scope', 'sync_events', "(project_id IS NULL AND entity_type IN ('folder','folder_order','folder_membership','project_order','account_game')) OR (project_id IS NOT NULL AND entity_type NOT IN ('folder','folder_order','folder_membership','project_order','account_game'))")
    for domain in ('project', 'account'):
        for suffix in ('frame_version', 'codec_version', 'reader_version'):
            name = f'{domain}_game_{suffix}'
            op.add_column('sync_devices', sa.Column(name, sa.Integer(), nullable=False, server_default='0'))
            op.create_check_constraint(f'ck_sync_devices_{name}', 'sync_devices', f'{name} IN (0,1)')
        op.add_column('sync_devices', sa.Column(f'{domain}_game_compression_zero', sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade():
    if op.get_bind().scalar(sa.text("SELECT EXISTS(SELECT 1 FROM sync_events WHERE entity_type IN ('project_game','account_game'))")):
        raise RuntimeError('Cannot remove Game capabilities while Game history exists')
    op.drop_constraint('ck_sync_events_scope', 'sync_events', type_='check')
    op.create_check_constraint('ck_sync_events_scope', 'sync_events', "(project_id IS NULL AND entity_type IN ('folder','folder_order','folder_membership','project_order')) OR (project_id IS NOT NULL AND entity_type NOT IN ('folder','folder_order','folder_membership','project_order'))")
    for domain in ('account', 'project'):
        op.drop_column('sync_devices', f'{domain}_game_compression_zero')
        for suffix in ('reader_version', 'codec_version', 'frame_version'):
            name = f'{domain}_game_{suffix}'
            op.drop_constraint(f'ck_sync_devices_{name}', 'sync_devices', type_='check')
            op.drop_column('sync_devices', name)
