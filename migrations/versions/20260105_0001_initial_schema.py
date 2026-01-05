"""Initial schema for InkassoKom

Revision ID: 0001
Revises:
Create Date: 2026-01-05

This migration creates the complete database schema for InkassoKom.
It follows the architecture defined in the ADR documents.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

# revision identifiers, used by Alembic.
revision: str = '0001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable required extensions
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto;")
    op.execute("CREATE EXTENSION IF NOT EXISTS vector;")  # For RAG embeddings later

    # ==========================================================================
    # ORGANIZATIONS
    # ==========================================================================
    op.create_table(
        'organizations',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('slug', sa.String(100), unique=True, nullable=False),
        sa.Column('street', sa.String(255)),
        sa.Column('postal_code', sa.String(20)),
        sa.Column('city', sa.String(100)),
        sa.Column('country', sa.String(2), server_default='DE'),
        sa.Column('phone', sa.String(50)),
        sa.Column('fax', sa.String(50)),
        sa.Column('email', sa.String(255)),
        sa.Column('website', sa.String(255)),
        sa.Column('bank_name', sa.String(255)),
        sa.Column('iban', sa.String(34)),
        sa.Column('bic', sa.String(11)),
        sa.Column('settings', JSONB, server_default='{}'),
        sa.Column('plan', sa.String(50), server_default='free'),
        sa.Column('is_active', sa.Boolean, server_default='true', nullable=False),
        sa.Column('is_deleted', sa.Boolean, server_default='false', nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
    )
    op.create_index('ix_organizations_slug', 'organizations', ['slug'])

    # ==========================================================================
    # USERS
    # ==========================================================================
    op.create_table(
        'users',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),  # Matches auth.users(id)
        sa.Column('email', sa.String(255), unique=True, nullable=False),
        sa.Column('first_name', sa.String(100), nullable=False),
        sa.Column('last_name', sa.String(100), nullable=False),
        sa.Column('title', sa.String(50)),
        sa.Column('phone', sa.String(50)),
        sa.Column('role_default', sa.String(50), server_default='staff'),
        sa.Column('settings', JSONB, server_default='{}'),
        sa.Column('notification_preferences', JSONB, server_default='{}'),
        sa.Column('is_active', sa.Boolean, server_default='true', nullable=False),
        sa.Column('is_deleted', sa.Boolean, server_default='false', nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
    )
    op.create_index('ix_users_email', 'users', ['email'])

    # ==========================================================================
    # MEMBERSHIPS (User <-> Organization)
    # ==========================================================================
    op.create_table(
        'memberships',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column('organization_id', UUID(as_uuid=True), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('role', sa.String(50), nullable=False, server_default='staff'),
        sa.Column('is_active', sa.Boolean, server_default='true', nullable=False),
        sa.Column('is_default', sa.Boolean, server_default='false', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
    )
    op.create_index('ix_memberships_org_user', 'memberships', ['organization_id', 'user_id'], unique=True)
    op.create_index('ix_memberships_user_active', 'memberships', ['user_id', 'is_active'])

    # ==========================================================================
    # PARTIES
    # ==========================================================================
    op.create_table(
        'parties',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column('organization_id', UUID(as_uuid=True), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('party_type', sa.String(50), nullable=False, server_default='natural_person'),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('name_addition', sa.String(255)),
        sa.Column('salutation', sa.String(20)),
        sa.Column('first_name', sa.String(100)),
        sa.Column('last_name', sa.String(100)),
        sa.Column('birth_date', sa.Date),
        sa.Column('legal_form', sa.String(50)),
        sa.Column('registration_number', sa.String(100)),
        sa.Column('registration_court', sa.String(100)),
        sa.Column('address', JSONB, server_default='{}'),
        sa.Column('email', sa.String(255)),
        sa.Column('phone', sa.String(50)),
        sa.Column('fax', sa.String(50)),
        sa.Column('identifiers', JSONB, server_default='{}'),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id')),
        sa.Column('is_deleted', sa.Boolean, server_default='false', nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
    )
    op.create_index('ix_parties_org', 'parties', ['organization_id'])

    # ==========================================================================
    # CASES
    # ==========================================================================
    op.create_table(
        'cases',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column('organization_id', UUID(as_uuid=True), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('case_no', sa.String(50), nullable=False),
        sa.Column('external_no', sa.String(100)),
        sa.Column('court_file_no', sa.String(100)),
        sa.Column('subject', sa.String(500)),
        sa.Column('description', sa.Text),
        sa.Column('status', sa.String(50), nullable=False, server_default='offen'),
        sa.Column('dunning_status', sa.String(50), server_default='nicht_beantragt'),
        sa.Column('enforcement_status', sa.String(50), server_default='nicht_begonnen'),
        sa.Column('opened_at', sa.Date),
        sa.Column('closed_at', sa.Date),
        sa.Column('mb_application_date', sa.Date),
        sa.Column('mb_delivery_date', sa.Date),
        sa.Column('vb_issue_date', sa.Date),
        sa.Column('assigned_lawyer_id', UUID(as_uuid=True), sa.ForeignKey('users.id')),
        sa.Column('tags', JSONB, server_default='[]'),
        sa.Column('metadata', JSONB, server_default='{}'),
        sa.Column('imported', sa.Boolean, server_default='false'),
        sa.Column('import_source', sa.String(100)),
        sa.Column('import_filename', sa.String(255)),
        sa.Column('is_deleted', sa.Boolean, server_default='false', nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
    )
    op.create_index('ix_cases_org_case_no', 'cases', ['organization_id', 'case_no'], unique=True)
    op.create_index('ix_cases_status', 'cases', ['status'])
    op.create_index('ix_cases_org', 'cases', ['organization_id'])

    # ==========================================================================
    # CASE_PARTIES
    # ==========================================================================
    op.create_table(
        'case_parties',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column('case_id', UUID(as_uuid=True), sa.ForeignKey('cases.id', ondelete='CASCADE'), nullable=False),
        sa.Column('party_id', UUID(as_uuid=True), sa.ForeignKey('parties.id', ondelete='CASCADE'), nullable=False),
        sa.Column('role', sa.String(50), nullable=False),
        sa.Column('reference', sa.String(100)),
        sa.Column('notes', sa.Text),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
    )
    op.create_index('ix_case_parties_case_party_role', 'case_parties', ['case_id', 'party_id', 'role'], unique=True)

    # ==========================================================================
    # CLAIMS
    # ==========================================================================
    op.create_table(
        'claims',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column('case_id', UUID(as_uuid=True), sa.ForeignKey('cases.id', ondelete='CASCADE'), nullable=False),
        sa.Column('description', sa.String(500), nullable=False),
        sa.Column('claim_type', sa.String(50)),
        sa.Column('principal', sa.Float, nullable=False),
        sa.Column('currency', sa.String(3), server_default='EUR'),
        sa.Column('interest_rate', sa.Float),
        sa.Column('interest_type', sa.String(50), server_default='verzugszinsen'),
        sa.Column('interest_start_date', sa.Date),
        sa.Column('interest_basis', sa.String(100)),
        sa.Column('due_date', sa.Date, nullable=False),
        sa.Column('invoice_number', sa.String(100)),
        sa.Column('invoice_date', sa.Date),
        sa.Column('is_titled', sa.Boolean, server_default='false'),
        sa.Column('title_date', sa.Date),
        sa.Column('title_reference', sa.String(100)),
        sa.Column('status', sa.String(50), server_default='offen'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
    )
    op.create_index('ix_claims_case', 'claims', ['case_id'])
    op.create_index('ix_claims_case_status', 'claims', ['case_id', 'status'])

    # ==========================================================================
    # LEDGER_BOOKINGS
    # ==========================================================================
    op.create_table(
        'ledger_bookings',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column('case_id', UUID(as_uuid=True), sa.ForeignKey('cases.id', ondelete='CASCADE'), nullable=False),
        sa.Column('claim_id', UUID(as_uuid=True), sa.ForeignKey('claims.id', ondelete='SET NULL')),
        sa.Column('booking_date', sa.Date, nullable=False),
        sa.Column('debit_credit', sa.String(1), nullable=False),
        sa.Column('amount', sa.Float, nullable=False),
        sa.Column('category', sa.String(50), nullable=False),
        sa.Column('description', sa.String(500)),
        sa.Column('reference', sa.String(100)),
        sa.Column('source', sa.String(50)),
        sa.Column('status', sa.String(50), server_default='verbucht'),
        sa.Column('metadata', JSONB, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
    )
    op.create_index('ix_ledger_bookings_case_date', 'ledger_bookings', ['case_id', 'booking_date'])
    op.create_index('ix_ledger_bookings_claim', 'ledger_bookings', ['claim_id'])

    # ==========================================================================
    # PAYMENTS
    # ==========================================================================
    op.create_table(
        'payments',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column('case_id', UUID(as_uuid=True), sa.ForeignKey('cases.id', ondelete='CASCADE'), nullable=False),
        sa.Column('debtor_party_id', UUID(as_uuid=True), sa.ForeignKey('parties.id')),
        sa.Column('received_at', sa.Date, nullable=False),
        sa.Column('amount', sa.Float, nullable=False),
        sa.Column('currency', sa.String(3), server_default='EUR'),
        sa.Column('channel', sa.String(50)),
        sa.Column('reference', sa.String(255)),
        sa.Column('status', sa.String(50), server_default='verbucht'),
        sa.Column('notes', sa.Text),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
    )
    op.create_index('ix_payments_case', 'payments', ['case_id'])

    # ==========================================================================
    # PAYMENT_ALLOCATIONS
    # ==========================================================================
    op.create_table(
        'payment_allocations',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column('payment_id', UUID(as_uuid=True), sa.ForeignKey('payments.id', ondelete='CASCADE'), nullable=False),
        sa.Column('ledger_booking_id', UUID(as_uuid=True), sa.ForeignKey('ledger_bookings.id', ondelete='CASCADE'), nullable=False),
        sa.Column('amount', sa.Float, nullable=False),
        sa.Column('allocation_order', sa.Integer, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
    )
    op.create_index('ix_payment_allocations_payment', 'payment_allocations', ['payment_id'])
    op.create_index('ix_payment_allocations_booking', 'payment_allocations', ['ledger_booking_id'])

    # ==========================================================================
    # DOCUMENTS
    # ==========================================================================
    op.create_table(
        'documents',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column('case_id', UUID(as_uuid=True), sa.ForeignKey('cases.id', ondelete='CASCADE')),
        sa.Column('organization_id', UUID(as_uuid=True), sa.ForeignKey('organizations.id', ondelete='CASCADE')),
        sa.Column('filename', sa.String(255), nullable=False),
        sa.Column('original_filename', sa.String(255)),
        sa.Column('mime_type', sa.String(100)),
        sa.Column('file_size', sa.Integer),
        sa.Column('file_hash', sa.String(64)),
        sa.Column('storage_bucket', sa.String(100), server_default='case-documents'),
        sa.Column('storage_path', sa.String(500), nullable=False),
        sa.Column('document_type', sa.String(50)),
        sa.Column('category', sa.String(50)),
        sa.Column('title', sa.String(500)),
        sa.Column('description', sa.Text),
        sa.Column('document_date', sa.Date),
        sa.Column('ocr_text', sa.Text),
        sa.Column('ocr_status', sa.String(50), server_default='pending'),
        sa.Column('ocr_language', sa.String(10), server_default='de'),
        sa.Column('visible_to_creditor', sa.Boolean, server_default='true'),
        sa.Column('visible_to_debtor', sa.Boolean, server_default='false'),
        sa.Column('page_count', sa.Integer, server_default='1'),
        sa.Column('source_page_start', sa.Integer),
        sa.Column('source_page_end', sa.Integer),
        sa.Column('metadata', JSONB, server_default='{}'),
        sa.Column('tags', JSONB, server_default='[]'),
        sa.Column('is_deleted', sa.Boolean, server_default='false', nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
    )
    op.create_index('ix_documents_case', 'documents', ['case_id'])
    op.create_index('ix_documents_case_type', 'documents', ['case_id', 'document_type'])
    op.create_index('ix_documents_hash', 'documents', ['file_hash'])
    op.create_index('ix_documents_org', 'documents', ['organization_id'])

    # ==========================================================================
    # TEMPLATES
    # ==========================================================================
    op.create_table(
        'templates',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column('organization_id', UUID(as_uuid=True), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('template_type', sa.String(50), nullable=False),
        sa.Column('storage_bucket', sa.String(100), server_default='templates'),
        sa.Column('storage_path', sa.String(500), nullable=False),
        sa.Column('placeholders', JSONB, server_default='[]'),
        sa.Column('version', sa.String(50), server_default='1.0'),
        sa.Column('is_active', sa.Boolean, server_default='true'),
        sa.Column('is_default', sa.Boolean, server_default='false'),
        sa.Column('metadata', JSONB, server_default='{}'),
        sa.Column('tags', JSONB, server_default='[]'),
        sa.Column('is_deleted', sa.Boolean, server_default='false', nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
    )
    op.create_index('ix_templates_org_type', 'templates', ['organization_id', 'template_type'])

    # ==========================================================================
    # LETTERHEADS
    # ==========================================================================
    op.create_table(
        'letterheads',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column('organization_id', UUID(as_uuid=True), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('docx_path', sa.String(500)),
        sa.Column('logo_path', sa.String(500)),
        sa.Column('defaults', JSONB, server_default='{}'),
        sa.Column('font_family', sa.String(100), server_default='Arial'),
        sa.Column('font_size', sa.Integer, server_default='11'),
        sa.Column('margin_top', sa.Integer, server_default='25'),
        sa.Column('margin_bottom', sa.Integer, server_default='20'),
        sa.Column('margin_left', sa.Integer, server_default='25'),
        sa.Column('margin_right', sa.Integer, server_default='20'),
        sa.Column('is_active', sa.Boolean, server_default='true'),
        sa.Column('is_default', sa.Boolean, server_default='false'),
        sa.Column('is_deleted', sa.Boolean, server_default='false', nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
    )
    op.create_index('ix_letterheads_org', 'letterheads', ['organization_id'])

    # ==========================================================================
    # COMMUNICATIONS
    # ==========================================================================
    op.create_table(
        'communications',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column('case_id', UUID(as_uuid=True), sa.ForeignKey('cases.id', ondelete='CASCADE'), nullable=False),
        sa.Column('channel', sa.String(50), nullable=False),
        sa.Column('subject', sa.String(500)),
        sa.Column('status', sa.String(50), server_default='active'),
        sa.Column('participants', JSONB, server_default='[]'),
        sa.Column('metadata', JSONB, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
    )
    op.create_index('ix_communications_case', 'communications', ['case_id'])

    # ==========================================================================
    # MESSAGES
    # ==========================================================================
    op.create_table(
        'messages',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column('thread_id', UUID(as_uuid=True), sa.ForeignKey('communications.id', ondelete='CASCADE'), nullable=False),
        sa.Column('direction', sa.String(10), nullable=False),
        sa.Column('from_party_id', UUID(as_uuid=True), sa.ForeignKey('parties.id')),
        sa.Column('from_user_id', UUID(as_uuid=True), sa.ForeignKey('users.id')),
        sa.Column('from_email', sa.String(255)),
        sa.Column('from_name', sa.String(255)),
        sa.Column('to_party_id', UUID(as_uuid=True), sa.ForeignKey('parties.id')),
        sa.Column('to_user_id', UUID(as_uuid=True), sa.ForeignKey('users.id')),
        sa.Column('to_email', sa.String(255)),
        sa.Column('to_name', sa.String(255)),
        sa.Column('subject', sa.String(500)),
        sa.Column('body_text', sa.Text),
        sa.Column('body_html', sa.Text),
        sa.Column('sent_at', sa.DateTime(timezone=True)),
        sa.Column('delivered_at', sa.DateTime(timezone=True)),
        sa.Column('read_at', sa.DateTime(timezone=True)),
        sa.Column('status', sa.String(50), server_default='draft'),
        sa.Column('is_ai_generated', sa.Boolean, server_default='false'),
        sa.Column('ai_draft_id', UUID(as_uuid=True)),
        sa.Column('attachments', JSONB, server_default='[]'),
        sa.Column('metadata', JSONB, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
    )
    op.create_index('ix_messages_thread_sent', 'messages', ['thread_id', 'sent_at'])
    op.create_index('ix_messages_status', 'messages', ['status'])

    # ==========================================================================
    # GENERATED_DOCUMENTS
    # ==========================================================================
    op.create_table(
        'generated_documents',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column('case_id', UUID(as_uuid=True), sa.ForeignKey('cases.id', ondelete='CASCADE'), nullable=False),
        sa.Column('template_id', UUID(as_uuid=True), sa.ForeignKey('templates.id')),
        sa.Column('letterhead_id', UUID(as_uuid=True), sa.ForeignKey('letterheads.id')),
        sa.Column('document_type', sa.String(50), nullable=False),
        sa.Column('title', sa.String(500)),
        sa.Column('storage_bucket', sa.String(100), server_default='generated-letters'),
        sa.Column('storage_path', sa.String(500), nullable=False),
        sa.Column('mime_type', sa.String(100), server_default='application/pdf'),
        sa.Column('file_size', sa.Integer),
        sa.Column('generated_by', UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('input_data', JSONB),
        sa.Column('template_version', sa.String(50)),
        sa.Column('message_id', UUID(as_uuid=True), sa.ForeignKey('messages.id')),
        sa.Column('status', sa.String(50), server_default='draft'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
    )
    op.create_index('ix_generated_documents_case', 'generated_documents', ['case_id'])

    # ==========================================================================
    # DEADLINES
    # ==========================================================================
    op.create_table(
        'deadlines',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column('case_id', UUID(as_uuid=True), sa.ForeignKey('cases.id', ondelete='CASCADE'), nullable=False),
        sa.Column('kind', sa.String(50), nullable=False, server_default='frist'),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('due_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('reminder_at', sa.DateTime(timezone=True)),
        sa.Column('completed_at', sa.DateTime(timezone=True)),
        sa.Column('status', sa.String(50), server_default='offen'),
        sa.Column('assigned_to', UUID(as_uuid=True), sa.ForeignKey('users.id')),
        sa.Column('notify_days_before', sa.Integer, server_default='3'),
        sa.Column('notification_sent', sa.Boolean, server_default='false'),
        sa.Column('legal_basis', sa.String(255)),
        sa.Column('is_court_deadline', sa.Boolean, server_default='false'),
        sa.Column('priority', sa.String(20), server_default='normal'),
        sa.Column('metadata', JSONB, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
    )
    op.create_index('ix_deadlines_case_due', 'deadlines', ['case_id', 'due_at'])
    op.create_index('ix_deadlines_status_due', 'deadlines', ['status', 'due_at'])

    # ==========================================================================
    # AUDIT_LOGS
    # ==========================================================================
    op.create_table(
        'audit_logs',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column('organization_id', UUID(as_uuid=True), sa.ForeignKey('organizations.id', ondelete='SET NULL')),
        sa.Column('actor_user_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL')),
        sa.Column('actor_email', sa.String(255)),
        sa.Column('actor_ip', sa.String(45)),
        sa.Column('actor_user_agent', sa.String(500)),
        sa.Column('action', sa.String(50), nullable=False),
        sa.Column('entity_type', sa.String(100), nullable=False),
        sa.Column('entity_id', UUID(as_uuid=True), nullable=False),
        sa.Column('entity_display', sa.String(255)),
        sa.Column('old_values', JSONB),
        sa.Column('new_values', JSONB),
        sa.Column('diff', JSONB),
        sa.Column('request_id', sa.String(36)),
        sa.Column('session_id', sa.String(36)),
        sa.Column('notes', sa.Text),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
    )
    op.create_index('ix_audit_logs_org_created', 'audit_logs', ['organization_id', 'created_at'])
    op.create_index('ix_audit_logs_actor_created', 'audit_logs', ['actor_user_id', 'created_at'])
    op.create_index('ix_audit_logs_entity', 'audit_logs', ['entity_type', 'entity_id'])
    op.create_index('ix_audit_logs_action', 'audit_logs', ['action'])

    # ==========================================================================
    # DOCUMENT_CHUNKS (for RAG)
    # ==========================================================================
    op.create_table(
        'document_chunks',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column('document_id', UUID(as_uuid=True), sa.ForeignKey('documents.id', ondelete='CASCADE'), nullable=False),
        sa.Column('case_id', UUID(as_uuid=True), sa.ForeignKey('cases.id', ondelete='CASCADE'), nullable=False),
        sa.Column('organization_id', UUID(as_uuid=True), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('chunk_index', sa.Integer, nullable=False),
        sa.Column('content', sa.Text, nullable=False),
        sa.Column('content_length', sa.Integer),
        sa.Column('page_number', sa.Integer),
        sa.Column('start_char', sa.Integer),
        sa.Column('end_char', sa.Integer),
        sa.Column('embedding_model', sa.String(100)),
        sa.Column('embedding_created_at', sa.DateTime(timezone=True)),
        sa.Column('metadata', JSONB, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
    )
    op.create_index('ix_document_chunks_document', 'document_chunks', ['document_id'])
    op.create_index('ix_document_chunks_case', 'document_chunks', ['case_id'])
    op.create_index('ix_document_chunks_org', 'document_chunks', ['organization_id'])
    op.create_index('ix_document_chunks_document_idx', 'document_chunks', ['document_id', 'chunk_index'])

    # Add embedding column with pgvector (commented out - enable when needed)
    # op.execute("ALTER TABLE document_chunks ADD COLUMN embedding vector(1536);")
    # op.execute("CREATE INDEX ix_document_chunks_embedding ON document_chunks USING ivfflat (embedding vector_cosine_ops);")


def downgrade() -> None:
    # Drop tables in reverse order of creation (respecting foreign keys)
    op.drop_table('document_chunks')
    op.drop_table('audit_logs')
    op.drop_table('deadlines')
    op.drop_table('generated_documents')
    op.drop_table('messages')
    op.drop_table('communications')
    op.drop_table('letterheads')
    op.drop_table('templates')
    op.drop_table('documents')
    op.drop_table('payment_allocations')
    op.drop_table('payments')
    op.drop_table('ledger_bookings')
    op.drop_table('claims')
    op.drop_table('case_parties')
    op.drop_table('cases')
    op.drop_table('parties')
    op.drop_table('memberships')
    op.drop_table('users')
    op.drop_table('organizations')
