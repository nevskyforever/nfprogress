"""Create C13 client-encrypted cloud storage tables.

Revision ID: c13_encrypted_cloud_schema
Revises: c9_sync_protocol
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c13_encrypted_cloud_schema'
down_revision: Union[str, Sequence[str], None] = 'c9_sync_protocol'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

UTC_NOW = sa.text("timezone('utc', now())")


def upgrade() -> None:
    op.create_table(
        'user_crypto',
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('password_crypto_version', sa.Integer(), nullable=False),
        sa.Column('password_wrapping_version', sa.Integer(), nullable=False),
        sa.Column('kdf_version', sa.Integer(), nullable=False),
        sa.Column('kdf_algorithm', sa.String(length=32), nullable=False),
        sa.Column('kdf_salt', sa.LargeBinary(), nullable=False),
        sa.Column('kdf_opslimit', sa.BigInteger(), nullable=False),
        sa.Column('kdf_memlimit', sa.BigInteger(), nullable=False),
        sa.Column('password_nonce', sa.LargeBinary(), nullable=False),
        sa.Column('password_wrapped_amk', sa.LargeBinary(), nullable=False),
        sa.Column('recovery_crypto_version', sa.Integer()),
        sa.Column('recovery_wrapping_version', sa.Integer()),
        sa.Column('recovery_nonce', sa.LargeBinary()),
        sa.Column('recovery_wrapped_amk', sa.LargeBinary()),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=UTC_NOW),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=UTC_NOW),
        sa.CheckConstraint('password_crypto_version >= 1', name='ck_user_crypto_password_crypto_version_positive'),
        sa.CheckConstraint('password_wrapping_version >= 1', name='ck_user_crypto_password_wrapping_version_positive'),
        sa.CheckConstraint('kdf_version >= 1', name='ck_user_crypto_kdf_version_positive'),
        sa.CheckConstraint('kdf_opslimit >= 1', name='ck_user_crypto_kdf_opslimit_positive'),
        sa.CheckConstraint('kdf_memlimit >= 1', name='ck_user_crypto_kdf_memlimit_positive'),
        sa.CheckConstraint('octet_length(kdf_salt) = 16', name='ck_user_crypto_kdf_salt_length'),
        sa.CheckConstraint('octet_length(password_nonce) = 24', name='ck_user_crypto_password_nonce_length'),
        sa.CheckConstraint('octet_length(password_wrapped_amk) = 48', name='ck_user_crypto_password_wrapped_amk_length'),
        sa.CheckConstraint("(recovery_crypto_version IS NULL AND recovery_wrapping_version IS NULL AND recovery_nonce IS NULL AND recovery_wrapped_amk IS NULL) OR (recovery_crypto_version IS NOT NULL AND recovery_wrapping_version IS NOT NULL AND recovery_nonce IS NOT NULL AND recovery_wrapped_amk IS NOT NULL)", name='ck_user_crypto_recovery_all_or_none'),
        sa.CheckConstraint('recovery_crypto_version IS NULL OR recovery_crypto_version >= 1', name='ck_user_crypto_recovery_crypto_version_positive'),
        sa.CheckConstraint('recovery_wrapping_version IS NULL OR recovery_wrapping_version >= 1', name='ck_user_crypto_recovery_wrapping_version_positive'),
        sa.CheckConstraint('recovery_nonce IS NULL OR octet_length(recovery_nonce) = 24', name='ck_user_crypto_recovery_nonce_length'),
        sa.CheckConstraint('recovery_wrapped_amk IS NULL OR octet_length(recovery_wrapped_amk) = 48', name='ck_user_crypto_recovery_wrapped_amk_length'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('user_id'),
    )
    op.create_table(
        'encrypted_objects',
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('event_id', sa.Uuid(), nullable=False),
        sa.Column('crypto_version', sa.Integer(), nullable=False),
        sa.Column('aad_version', sa.Integer(), nullable=False),
        sa.Column('nonce', sa.LargeBinary(), nullable=False),
        sa.Column('ciphertext', sa.LargeBinary(), nullable=False),
        sa.Column('stored_at', sa.DateTime(timezone=True), nullable=False, server_default=UTC_NOW),
        sa.CheckConstraint('crypto_version >= 1', name='ck_encrypted_objects_crypto_version_positive'),
        sa.CheckConstraint('aad_version >= 1', name='ck_encrypted_objects_aad_version_positive'),
        sa.CheckConstraint('octet_length(nonce) = 24', name='ck_encrypted_objects_nonce_length'),
        sa.CheckConstraint('octet_length(ciphertext) >= 16', name='ck_encrypted_objects_ciphertext_min_length'),
        sa.ForeignKeyConstraint(['user_id', 'event_id'], ['sync_events.user_id', 'sync_events.event_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('user_id', 'event_id'),
    )


def downgrade() -> None:
    op.drop_table('encrypted_objects')
    op.drop_table('user_crypto')
