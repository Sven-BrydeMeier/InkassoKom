"""
Database Models - NotarFlow Inkasso-Kommunikationsplattform
SQLAlchemy ORM Models - SQLite compatible
"""
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List
from sqlalchemy import (
    Column, String, Integer, Boolean, DateTime, Date, Text,
    Float, ForeignKey, JSON, Index, UniqueConstraint, event
)
from sqlalchemy.orm import relationship, declarative_base
import uuid

Base = declarative_base()


def generate_uuid():
    """Generate UUID as string for SQLite compatibility."""
    return str(uuid.uuid4())


# =============================================================================
# MIXINS
# =============================================================================

class TimestampMixin:
    """Adds created_at and updated_at timestamps."""
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


# =============================================================================
# ORGANIZATION / TENANT
# =============================================================================

class Organization(Base, TimestampMixin):
    """Kanzlei / Mandant (Multi-Tenant Root)"""
    __tablename__ = 'organizations'

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, nullable=False)

    # Contact
    street = Column(String(255))
    postal_code = Column(String(20))
    city = Column(String(100))
    country = Column(String(2), default='DE')
    phone = Column(String(50))
    email = Column(String(255))
    website = Column(String(255))

    # Legal
    tax_id = Column(String(50))
    vat_id = Column(String(50))

    # Settings
    settings = Column(JSON, default={})

    is_active = Column(Boolean, default=True)

    # Relationships
    users = relationship("User", back_populates="organization")
    cases = relationship("Case", back_populates="organization")


# =============================================================================
# USER / AUTH
# =============================================================================

class User(Base, TimestampMixin):
    """User with role-based access."""
    __tablename__ = 'users'

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey('organizations.id'), nullable=True)

    # Auth
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)

    # Profile
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    title = Column(String(50))
    phone = Column(String(50))

    # Role
    role = Column(String(50), nullable=False)  # admin, rechtsanwalt, glaeubigerin, schuldner

    # Settings
    settings = Column(JSON, default={})

    # Session
    last_login = Column(DateTime)
    is_active = Column(Boolean, default=True)
    is_deleted = Column(Boolean, default=False)

    # Relationships
    organization = relationship("Organization", back_populates="users")

    @property
    def full_name(self):
        parts = [self.title, self.first_name, self.last_name]
        return " ".join(p for p in parts if p)


# =============================================================================
# CASE / AKTE
# =============================================================================

class Case(Base, TimestampMixin):
    """Akte - Central case entity."""
    __tablename__ = 'cases'

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey('organizations.id'), nullable=False)

    # Case numbers
    internal_number = Column(String(50), nullable=False)
    external_number = Column(String(100))
    court_file_number = Column(String(100))

    # Short description
    subject = Column(String(500))
    description = Column(Text)

    # Parties
    creditor_user_id = Column(String(36), ForeignKey('users.id'), nullable=True)
    debtor_user_id = Column(String(36), ForeignKey('users.id'), nullable=True)

    # Party details
    creditor_name = Column(String(255))
    creditor_street = Column(String(255))
    creditor_postal_code = Column(String(20))
    creditor_city = Column(String(100))
    creditor_country = Column(String(2), default='DE')
    creditor_email = Column(String(255))
    creditor_phone = Column(String(50))

    debtor_name = Column(String(255))
    debtor_street = Column(String(255))
    debtor_postal_code = Column(String(20))
    debtor_city = Column(String(100))
    debtor_country = Column(String(2), default='DE')
    debtor_email = Column(String(255))
    debtor_phone = Column(String(50))
    debtor_birth_date = Column(Date)

    # Status
    status = Column(String(50), default='offen')
    dunning_status = Column(String(50), default='nicht_beantragt')
    enforcement_status = Column(String(50), default='nicht_begonnen')
    payment_plan_status = Column(String(50))

    # Dunning dates
    mb_application_date = Column(Date)
    mb_delivery_date = Column(Date)
    vb_application_date = Column(Date)
    vb_issue_date = Column(Date)
    vb_finality_date = Column(Date)
    objection_date = Column(Date)

    # Assigned lawyer
    assigned_lawyer_id = Column(String(36), ForeignKey('users.id'), nullable=True)

    # Tags (JSON array)
    tags = Column(JSON, default=[])

    # Metadata
    metadata = Column(JSON, default={})

    # Soft delete
    is_deleted = Column(Boolean, default=False)
    deleted_at = Column(DateTime)

    # Relationships
    organization = relationship("Organization", back_populates="cases")
    claims = relationship("Claim", back_populates="case", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="case")
    bookings = relationship("LedgerBooking", back_populates="case")
    timeline_events = relationship("TimelineEvent", back_populates="case")
    payment_plans = relationship("PaymentPlan", back_populates="case")

    __table_args__ = (
        Index('ix_cases_org_internal', 'organization_id', 'internal_number'),
    )


# =============================================================================
# CLAIM / FORDERUNG
# =============================================================================

class Claim(Base, TimestampMixin):
    """Einzelne Forderung innerhalb einer Akte."""
    __tablename__ = 'claims'

    id = Column(String(36), primary_key=True, default=generate_uuid)
    case_id = Column(String(36), ForeignKey('cases.id'), nullable=False)

    # Description
    description = Column(String(500), nullable=False)
    claim_type = Column(String(50))

    # Amounts
    principal_amount = Column(Float, nullable=False)
    interest_rate = Column(Float)
    interest_start_date = Column(Date)
    additional_costs = Column(Float, default=0)

    # Important dates
    due_date = Column(Date, nullable=False)
    invoice_date = Column(Date)
    invoice_number = Column(String(100))

    # Contract reference
    contract_number = Column(String(100))
    contract_date = Column(Date)

    # Status
    is_titled = Column(Boolean, default=False)
    title_date = Column(Date)
    title_type = Column(String(50))

    # Metadata
    metadata = Column(JSON, default={})

    # Relationships
    case = relationship("Case", back_populates="claims")


# =============================================================================
# LEDGER / FORDERUNGSKONTO
# =============================================================================

class LedgerBooking(Base, TimestampMixin):
    """Buchung im Forderungskonto."""
    __tablename__ = 'ledger_bookings'

    id = Column(String(36), primary_key=True, default=generate_uuid)
    case_id = Column(String(36), ForeignKey('cases.id'), nullable=False)
    claim_id = Column(String(36), ForeignKey('claims.id'), nullable=True)

    # Booking details
    booking_date = Column(Date, nullable=False)
    value_date = Column(Date)

    # Debit/Credit
    debit_credit = Column(String(1), nullable=False)  # 'S' = Soll, 'H' = Haben
    amount = Column(Float, nullable=False)

    # Category
    category = Column(String(50), nullable=False)

    # Description
    description = Column(String(500))
    reference = Column(String(100))

    # Source
    source = Column(String(50))
    source_user_id = Column(String(36), ForeignKey('users.id'), nullable=True)

    # Status
    status = Column(String(50), default='verbucht')

    # Metadata
    metadata = Column(JSON, default={})

    # Relationships
    case = relationship("Case", back_populates="bookings")

    __table_args__ = (
        Index('ix_ledger_case_date', 'case_id', 'booking_date'),
    )


# =============================================================================
# DOCUMENT
# =============================================================================

class Document(Base, TimestampMixin):
    """Document with versioning."""
    __tablename__ = 'documents'

    id = Column(String(36), primary_key=True, default=generate_uuid)
    case_id = Column(String(36), ForeignKey('cases.id'), nullable=True)
    organization_id = Column(String(36), ForeignKey('organizations.id'), nullable=True)

    # File info
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255))
    file_type = Column(String(50))
    mime_type = Column(String(100))
    file_size = Column(Integer)

    # Storage
    storage_path = Column(String(500), nullable=False)
    storage_type = Column(String(20), default='local')

    # Integrity
    file_hash = Column(String(64))

    # Document type/category
    document_type = Column(String(50))
    category = Column(String(50))

    # Metadata
    title = Column(String(500))
    description = Column(Text)
    document_date = Column(Date)

    # OCR
    ocr_text = Column(Text)
    ocr_status = Column(String(20), default='pending')

    # AI extraction
    extracted_data = Column(JSON, default={})

    # Source
    source = Column(String(50))

    # Visibility
    visible_to_creditor = Column(Boolean, default=True)
    visible_to_debtor = Column(Boolean, default=False)

    # Version control
    version = Column(Integer, default=1)
    is_latest = Column(Boolean, default=True)

    # Soft delete
    is_deleted = Column(Boolean, default=False)

    # Relationships
    case = relationship("Case", back_populates="documents")

    __table_args__ = (
        Index('ix_documents_case', 'case_id'),
    )


# =============================================================================
# TIMELINE EVENT
# =============================================================================

class TimelineEvent(Base, TimestampMixin):
    """Timeline event for case history."""
    __tablename__ = 'timeline_events'

    id = Column(String(36), primary_key=True, default=generate_uuid)
    case_id = Column(String(36), ForeignKey('cases.id'), nullable=False)

    # Event details
    event_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    event_type = Column(String(50), nullable=False)

    # Description
    title = Column(String(255), nullable=False)
    description = Column(Text)

    # Categorization
    category = Column(String(50))
    severity = Column(String(20), default='info')

    # Actor
    actor_id = Column(String(36), ForeignKey('users.id'), nullable=True)
    actor_role = Column(String(50))
    actor_name = Column(String(255))

    # References
    reference_type = Column(String(50))
    reference_id = Column(String(36))

    # Visibility
    visible_to_creditor = Column(Boolean, default=True)
    visible_to_debtor = Column(Boolean, default=False)

    # Metadata
    metadata = Column(JSON, default={})

    # Relationships
    case = relationship("Case", back_populates="timeline_events")

    __table_args__ = (
        Index('ix_timeline_case_date', 'case_id', 'event_date'),
    )


# =============================================================================
# PAYMENT PLAN / RATENZAHLUNG
# =============================================================================

class PaymentPlan(Base, TimestampMixin):
    """Payment plan / Ratenzahlungsvereinbarung."""
    __tablename__ = 'payment_plans'

    id = Column(String(36), primary_key=True, default=generate_uuid)
    case_id = Column(String(36), ForeignKey('cases.id'), nullable=False)

    # Status
    status = Column(String(50), default='angefragt')

    # Plan details
    total_amount = Column(Float, nullable=False)
    installment_amount = Column(Float, nullable=False)
    number_of_installments = Column(Integer, nullable=False)
    first_installment_date = Column(Date, nullable=False)
    interval_days = Column(Integer, default=30)

    # Interest
    interest_rate = Column(Float, default=0)

    # Request details
    requested_at = Column(DateTime)
    request_notes = Column(Text)

    # Approval
    approved_at = Column(DateTime)
    approval_notes = Column(Text)

    # Relationships
    case = relationship("Case", back_populates="payment_plans")
    installments = relationship("PaymentPlanInstallment", back_populates="payment_plan", cascade="all, delete-orphan")


# =============================================================================
# INBOX / POSTEINGANG
# =============================================================================

class InboxItem(Base, TimestampMixin):
    """Inbox item for unassigned documents."""
    __tablename__ = 'inbox_items'

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey('organizations.id'), nullable=False)
    document_id = Column(String(36), ForeignKey('documents.id'), nullable=False)

    # Source
    source = Column(String(50))
    received_at = Column(DateTime, default=datetime.utcnow)

    # Status
    status = Column(String(50), default='new')

    # AI suggestions
    ai_analysis = Column(JSON, default={})

    # Assignment
    assigned_to_case_id = Column(String(36), ForeignKey('cases.id'), nullable=True)
    assigned_at = Column(DateTime)

    # Notes
    notes = Column(Text)


# =============================================================================
# NOTIFICATION
# =============================================================================

class Notification(Base, TimestampMixin):
    """In-app notifications."""
    __tablename__ = 'notifications'

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey('users.id'), nullable=False)

    # Content
    title = Column(String(255), nullable=False)
    message = Column(Text)
    notification_type = Column(String(50))

    # Category
    category = Column(String(50))

    # Reference
    reference_type = Column(String(50))
    reference_id = Column(String(36))
    case_id = Column(String(36), ForeignKey('cases.id'), nullable=True)

    # Status
    is_read = Column(Boolean, default=False)
    read_at = Column(DateTime)

    __table_args__ = (
        Index('ix_notifications_user_read', 'user_id', 'is_read'),
    )


# =============================================================================
# LIMITATION / VERJÄHRUNG
# =============================================================================

class LimitationEvent(Base, TimestampMixin):
    """Events affecting statute of limitations."""
    __tablename__ = 'limitation_events'

    id = Column(String(36), primary_key=True, default=generate_uuid)
    case_id = Column(String(36), ForeignKey('cases.id'), nullable=False)
    claim_id = Column(String(36), ForeignKey('claims.id'), nullable=True)

    # Event type
    event_type = Column(String(50), nullable=False)
    event_date = Column(Date, nullable=False)

    # Effect
    effect = Column(String(50))
    new_limitation_date = Column(Date)

    # Manual override
    is_override = Column(Boolean, default=False)
    override_reason = Column(Text)

    # Notes
    notes = Column(Text)


# =============================================================================
# DEADLINE / FRISTEN
# =============================================================================

class Deadline(Base, TimestampMixin):
    """Deadline/Frist tracking."""
    __tablename__ = 'deadlines'

    id = Column(String(36), primary_key=True, default=generate_uuid)
    case_id = Column(String(36), ForeignKey('cases.id'), nullable=False)

    # Deadline details
    deadline_type = Column(String(50), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text)

    # Dates
    due_date = Column(Date, nullable=False)
    reminder_date = Column(Date)

    # Status
    status = Column(String(50), default='active')
    priority = Column(String(20), default='normal')

    # Completion
    completed_at = Column(DateTime)

    # Reminder
    reminder_sent = Column(Boolean, default=False)
    reminder_sent_at = Column(DateTime)


# =============================================================================
# PAYMENT PLAN INSTALLMENT
# =============================================================================

class PaymentPlanInstallment(Base, TimestampMixin):
    """Individual installment in a payment plan."""
    __tablename__ = 'payment_plan_installments'

    id = Column(String(36), primary_key=True, default=generate_uuid)
    payment_plan_id = Column(String(36), ForeignKey('payment_plans.id'), nullable=False)

    # Installment details
    installment_number = Column(Integer, nullable=False)
    due_date = Column(Date, nullable=False)
    amount = Column(Float, nullable=False)

    # Status
    status = Column(String(50), default='pending')

    # Payment
    paid_at = Column(DateTime)
    paid_amount = Column(Float)

    # Reminders
    reminder_sent_at = Column(DateTime)
    overdue_reminder_sent_at = Column(DateTime)

    # Relationships
    payment_plan = relationship("PaymentPlan", back_populates="installments")


# =============================================================================
# AUDIT LOG (simplified)
# =============================================================================

class AuditLog(Base):
    """Audit log for actions."""
    __tablename__ = 'audit_logs'

    id = Column(String(36), primary_key=True, default=generate_uuid)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Actor
    user_id = Column(String(36), ForeignKey('users.id'), nullable=True)
    user_email = Column(String(255))
    user_role = Column(String(50))

    # Organization
    organization_id = Column(String(36), ForeignKey('organizations.id'), nullable=True)

    # Action
    action = Column(String(100), nullable=False)
    resource_type = Column(String(50), nullable=False)
    resource_id = Column(String(36))

    # Details
    description = Column(Text)
    old_values = Column(JSON)
    new_values = Column(JSON)

    # Reference
    case_id = Column(String(36), ForeignKey('cases.id'), nullable=True)
