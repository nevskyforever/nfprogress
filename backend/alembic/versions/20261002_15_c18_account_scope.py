"""C18 account descriptors share the immutable authenticated sequence."""
from alembic import op
import sqlalchemy as sa
revision = 'c18_account_scope'
down_revision = 'c18_metadata_reader_gate'
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column('sync_events', 'project_id', existing_type=sa.String(512), nullable=True)
    op.create_check_constraint('ck_sync_events_scope', 'sync_events', "(project_id IS NULL AND entity_type IN ('folder','folder_order','folder_membership','project_order')) OR (project_id IS NOT NULL AND entity_type NOT IN ('folder','folder_order','folder_membership','project_order'))")


def downgrade():
    # Fail closed if account history exists; never discard immutable ciphertext.
    op.alter_column('sync_events', 'project_id', existing_type=sa.String(512), nullable=False)
    op.drop_constraint('ck_sync_events_scope', 'sync_events', type_='check')
