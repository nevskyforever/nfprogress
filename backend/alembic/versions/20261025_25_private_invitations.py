"""Add single-use private invitations without changing public registration."""

from alembic import op
import sqlalchemy as sa


revision = 'private_invitations'
down_revision = 'c18_compression_readers'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'admin_invitations',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('user_id', sa.Uuid(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('created_by_id', sa.Uuid(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('token_hash', sa.String(length=64), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("timezone('utc', now())")),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('used_at', sa.DateTime(timezone=True)),
        sa.Column('revoked_at', sa.DateTime(timezone=True)),
    )
    op.create_index('ix_admin_invitations_user_id', 'admin_invitations', ['user_id'])


def downgrade():
    # Retain issued/used/revoked security evidence on any populated deployment.
    if op.get_bind().scalar(sa.text('SELECT EXISTS(SELECT 1 FROM admin_invitations)')):
        raise RuntimeError('Private invitation history cannot be discarded automatically.')
    op.drop_index('ix_admin_invitations_user_id', table_name='admin_invitations')
    op.drop_table('admin_invitations')
