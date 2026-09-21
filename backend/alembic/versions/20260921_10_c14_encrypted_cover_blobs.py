"""Create C14 metadata for encrypted external cover blobs.

Revision ID: c14_encrypted_cover_blobs
Revises: c13_encrypted_cloud_schema
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c14_encrypted_cover_blobs'
down_revision: Union[str, Sequence[str], None] = 'c13_encrypted_cloud_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

UTC_NOW = sa.text("timezone('utc', now())")


def upgrade() -> None:
    op.create_table(
        'encrypted_blobs',
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('blob_id', sa.Uuid(), nullable=False),
        sa.Column('project_id', sa.String(length=512), nullable=False),
        sa.Column('kind', sa.String(length=32), nullable=False),
        sa.Column('crypto_version', sa.Integer(), nullable=False),
        sa.Column('aad_version', sa.Integer(), nullable=False),
        sa.Column('nonce', sa.LargeBinary(), nullable=False),
        sa.Column('ciphertext_size', sa.Integer(), nullable=False),
        sa.Column('ciphertext_sha256', sa.LargeBinary(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=UTC_NOW),
        sa.CheckConstraint("kind = 'project_cover'", name='ck_encrypted_blobs_kind'),
        sa.CheckConstraint('crypto_version >= 1', name='ck_encrypted_blobs_crypto_version_positive'),
        sa.CheckConstraint('aad_version >= 1', name='ck_encrypted_blobs_aad_version_positive'),
        sa.CheckConstraint('octet_length(nonce) = 24', name='ck_encrypted_blobs_nonce_length'),
        sa.CheckConstraint('ciphertext_size >= 16', name='ck_encrypted_blobs_ciphertext_size_min'),
        sa.CheckConstraint('ciphertext_size <= 2097168', name='ck_encrypted_blobs_ciphertext_size_max'),
        sa.CheckConstraint('octet_length(ciphertext_sha256) = 32', name='ck_encrypted_blobs_ciphertext_sha256_length'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('user_id', 'blob_id'),
    )


def downgrade() -> None:
    op.drop_table('encrypted_blobs')
