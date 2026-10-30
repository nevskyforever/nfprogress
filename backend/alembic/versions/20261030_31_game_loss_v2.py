"""Gate standalone global streak losses on the compatible account Game reader."""
from alembic import op
import sqlalchemy as sa
revision = 'game_loss_v2'
down_revision = 'legal_acceptances'
branch_labels = None
depends_on = None


def upgrade():
    for field in ('codec_version', 'reader_version'):
        name = f'account_game_{field}'
        op.drop_constraint(f'ck_sync_devices_{name}', 'sync_devices', type_='check')
        op.create_check_constraint(f'ck_sync_devices_{name}', 'sync_devices', f'{name} IN (0,1,2)')


def downgrade():
    # Encrypted history cannot be inspected to prove the absence of v2 losses.
    if op.get_bind().scalar(sa.text("SELECT EXISTS(SELECT 1 FROM sync_events WHERE entity_type='account_game')")):
        raise RuntimeError('Cannot remove loss reader support while account Game history exists')
    op.execute('UPDATE sync_devices SET account_game_codec_version=0, account_game_reader_version=0 WHERE account_game_codec_version=2 OR account_game_reader_version=2')
    for field in ('codec_version', 'reader_version'):
        name = f'account_game_{field}'
        op.drop_constraint(f'ck_sync_devices_{name}', 'sync_devices', type_='check')
        op.create_check_constraint(f'ck_sync_devices_{name}', 'sync_devices', f'{name} IN (0,1)')
