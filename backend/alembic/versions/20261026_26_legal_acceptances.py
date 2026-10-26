"""Add append-only versioned legal-document acceptance evidence."""

from alembic import op
import sqlalchemy as sa


revision = 'legal_acceptances'
down_revision = 'private_invitations'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'user_document_acceptances',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('user_id', sa.Uuid(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('document_type', sa.String(length=32), nullable=False),
        sa.Column('document_id', sa.String(length=128), nullable=False),
        sa.Column('revision', sa.String(length=64), nullable=False),
        sa.Column('content_checksum', sa.String(length=64), nullable=False),
        sa.Column('language', sa.String(length=16), nullable=False),
        sa.Column('acceptance_method', sa.String(length=32), nullable=False),
        sa.Column('accepted_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("timezone('utc', now())")),
        sa.CheckConstraint(
            "document_type IN ('user_agreement', 'privacy_policy', 'personal_data_consent', 'beta_terms')",
            name='ck_user_document_acceptances_type',
        ),
        sa.CheckConstraint(
            "acceptance_method IN ('invitation', 'authenticated_confirmation')",
            name='ck_user_document_acceptances_method',
        ),
        sa.CheckConstraint("content_checksum ~ '^[0-9a-f]{64}$'", name='ck_user_document_acceptances_checksum'),
        sa.CheckConstraint("char_length(document_id) >= 1", name='ck_user_document_acceptances_document_id'),
        sa.CheckConstraint("char_length(revision) >= 1", name='ck_user_document_acceptances_revision'),
        sa.UniqueConstraint(
            'user_id', 'document_id', 'revision', 'content_checksum', 'language',
            name='uq_user_document_acceptance_exact',
        ),
    )
    op.create_index(
        'ix_user_document_acceptances_user_id', 'user_document_acceptances', ['user_id'],
    )
    op.execute("""
        CREATE OR REPLACE FUNCTION reject_legal_acceptance_mutation() RETURNS trigger AS $$
        BEGIN
            IF TG_OP = 'UPDATE' OR EXISTS (
                SELECT 1 FROM users WHERE id = OLD.user_id
            ) THEN
                RAISE EXCEPTION 'legal acceptance history is append-only';
            END IF;
            RETURN OLD;
        END;
        $$ LANGUAGE plpgsql
    """)
    op.execute("""
        CREATE TRIGGER user_document_acceptances_append_only
        BEFORE UPDATE OR DELETE ON user_document_acceptances
        FOR EACH ROW EXECUTE FUNCTION reject_legal_acceptance_mutation()
    """)


def downgrade():
    # Alembic downgrade is an explicit destructive administrative operation;
    # application-level UPDATE/DELETE remains forbidden by the trigger.
    op.execute('DROP TRIGGER user_document_acceptances_append_only ON user_document_acceptances')
    op.execute('DROP FUNCTION reject_legal_acceptance_mutation()')
    op.drop_index('ix_user_document_acceptances_user_id', table_name='user_document_acceptances')
    op.drop_table('user_document_acceptances')
