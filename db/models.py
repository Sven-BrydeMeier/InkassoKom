"""
Database Models - InkassoKom Inkasso-Kommunikationsplattform
Minimal SQLite-compatible version
"""
from datetime import datetime, date
from sqlalchemy import (
    Column, String, Integer, Boolean, DateTime, Date, Text, Float, JSON, Index
)
from sqlalchemy.orm import declarative_base
import uuid

Base = declarative_base()


def generate_uuid():
    return str(uuid.uuid4())


# =============================================================================
# ORGANIZATION
# =============================================================================

class Organization(Base):
    __tablename__ = 'organizations'

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, nullable=False)
    street = Column(String(255))
    postal_code = Column(String(20))
    city = Column(String(100))
    country = Column(String(2), default='DE')
    phone = Column(String(50))
    email = Column(String(255))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# =============================================================================
# USER
# =============================================================================

class User(Base):
    __tablename__ = 'users'

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), nullable=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    title = Column(String(50))
    phone = Column(String(50))
    role = Column(String(50), nullable=False)
    settings = Column(JSON, default={})
    last_login = Column(DateTime)
    is_active = Column(Boolean, default=True)
    is_deleted = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @property
    def full_name(self):
        parts = [self.title, self.first_name, self.last_name]
        return " ".join(p for p in parts if p)


# =============================================================================
# CASE
# =============================================================================

class Case(Base):
    __tablename__ = 'cases'

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), nullable=False)
    internal_number = Column(String(50), nullable=False)
    external_number = Column(String(100))
    court_file_number = Column(String(100))
    subject = Column(String(500))
    description = Column(Text)

    # Parties
    creditor_user_id = Column(String(36), nullable=True)
    debtor_user_id = Column(String(36), nullable=True)
    creditor_name = Column(String(255))
    creditor_email = Column(String(255))
    debtor_name = Column(String(255))
    debtor_email = Column(String(255))

    # Status
    status = Column(String(50), default='offen')
    dunning_status = Column(String(50), default='nicht_beantragt')
    enforcement_status = Column(String(50), default='nicht_begonnen')

    # Dates
    mb_application_date = Column(Date)
    mb_delivery_date = Column(Date)
    vb_issue_date = Column(Date)

    # Assigned
    assigned_lawyer_id = Column(String(36), nullable=True)

    # Metadata
    tags = Column(JSON, default=[])
    is_deleted = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# =============================================================================
# CLAIM
# =============================================================================

class Claim(Base):
    __tablename__ = 'claims'

    id = Column(String(36), primary_key=True, default=generate_uuid)
    case_id = Column(String(36), nullable=False)
    description = Column(String(500), nullable=False)
    claim_type = Column(String(50))
    principal_amount = Column(Float, nullable=False)
    interest_rate = Column(Float)
    interest_start_date = Column(Date)
    due_date = Column(Date, nullable=False)
    invoice_number = Column(String(100))
    is_titled = Column(Boolean, default=False)
    title_date = Column(Date)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# =============================================================================
# LEDGER BOOKING
# =============================================================================

class LedgerBooking(Base):
    __tablename__ = 'ledger_bookings'

    id = Column(String(36), primary_key=True, default=generate_uuid)
    case_id = Column(String(36), nullable=False)
    claim_id = Column(String(36), nullable=True)
    booking_date = Column(Date, nullable=False)
    debit_credit = Column(String(1), nullable=False)  # S=Soll, H=Haben
    amount = Column(Float, nullable=False)
    category = Column(String(50), nullable=False)
    description = Column(String(500))
    reference = Column(String(100))
    source = Column(String(50))
    status = Column(String(50), default='verbucht')
    created_at = Column(DateTime, default=datetime.utcnow)


# =============================================================================
# DOCUMENT
# =============================================================================

class Document(Base):
    __tablename__ = 'documents'

    id = Column(String(36), primary_key=True, default=generate_uuid)
    case_id = Column(String(36), nullable=True)
    organization_id = Column(String(36), nullable=True)
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255))
    file_type = Column(String(50))
    file_size = Column(Integer)
    storage_path = Column(String(500), nullable=False)
    document_type = Column(String(50))
    title = Column(String(500))
    description = Column(Text)
    ocr_text = Column(Text)
    visible_to_creditor = Column(Boolean, default=True)
    visible_to_debtor = Column(Boolean, default=False)
    is_deleted = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


# =============================================================================
# TIMELINE EVENT
# =============================================================================

class TimelineEvent(Base):
    __tablename__ = 'timeline_events'

    id = Column(String(36), primary_key=True, default=generate_uuid)
    case_id = Column(String(36), nullable=False)
    event_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    event_type = Column(String(50), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    category = Column(String(50))
    severity = Column(String(20), default='info')
    actor_id = Column(String(36), nullable=True)
    actor_name = Column(String(255))
    actor_role = Column(String(50))
    visible_to_creditor = Column(Boolean, default=True)
    visible_to_debtor = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


# =============================================================================
# PAYMENT PLAN
# =============================================================================

class PaymentPlan(Base):
    __tablename__ = 'payment_plans'

    id = Column(String(36), primary_key=True, default=generate_uuid)
    case_id = Column(String(36), nullable=False)
    status = Column(String(50), default='angefragt')
    total_amount = Column(Float, nullable=False)
    installment_amount = Column(Float, nullable=False)
    number_of_installments = Column(Integer, nullable=False)
    first_installment_date = Column(Date, nullable=False)
    interval_days = Column(Integer, default=30)
    requested_at = Column(DateTime)
    approved_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)


# =============================================================================
# INBOX ITEM
# =============================================================================

class InboxItem(Base):
    __tablename__ = 'inbox_items'

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), nullable=False)
    document_id = Column(String(36), nullable=False)
    source = Column(String(50))
    received_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String(50), default='new')
    assigned_to_case_id = Column(String(36), nullable=True)
    assigned_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)


# =============================================================================
# NOTIFICATION
# =============================================================================

class Notification(Base):
    __tablename__ = 'notifications'

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), nullable=False)
    title = Column(String(255), nullable=False)
    message = Column(Text)
    notification_type = Column(String(50))
    category = Column(String(50))
    case_id = Column(String(36), nullable=True)
    is_read = Column(Boolean, default=False)
    read_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)


# =============================================================================
# LIMITATION EVENT
# =============================================================================

class LimitationEvent(Base):
    __tablename__ = 'limitation_events'

    id = Column(String(36), primary_key=True, default=generate_uuid)
    case_id = Column(String(36), nullable=False)
    claim_id = Column(String(36), nullable=True)
    event_type = Column(String(50), nullable=False)
    event_date = Column(Date, nullable=False)
    effect = Column(String(50))
    new_limitation_date = Column(Date)
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
