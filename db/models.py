"""
Database Models - NotarFlow Inkasso-Kommunikationsplattform
SQLAlchemy ORM Models with full audit trail and versioning
"""
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List
from sqlalchemy import (
    Column, String, Integer, Boolean, DateTime, Date, Text,
    Numeric, ForeignKey, Enum, JSON, LargeBinary, Index,
    UniqueConstraint, CheckConstraint, event
)
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
import uuid
import hashlib

Base = declarative_base()


# =============================================================================
# MIXINS
# =============================================================================

class TimestampMixin:
    """Adds created_at and updated_at timestamps."""
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class AuditMixin:
    """Adds audit trail fields."""
    created_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)
    updated_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)


class SoftDeleteMixin:
    """Adds soft delete capability."""
    is_deleted = Column(Boolean, default=False, nullable=False)
    deleted_at = Column(DateTime, nullable=True)
    deleted_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)


# =============================================================================
# ORGANIZATION / TENANT
# =============================================================================

class Organization(Base, TimestampMixin):
    """Kanzlei / Mandant (Multi-Tenant Root)"""
    __tablename__ = 'organizations'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
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
    tax_id = Column(String(50))  # Steuernummer
    vat_id = Column(String(50))  # USt-IdNr

    # Settings
    settings = Column(JSONB, default={})

    # Letterhead & Signature
    letterhead_file_id = Column(UUID(as_uuid=True), ForeignKey('documents.id'), nullable=True)
    signature_file_id = Column(UUID(as_uuid=True), ForeignKey('documents.id'), nullable=True)

    # beA
    bea_safe_id = Column(String(100))  # beA SAFE-ID

    is_active = Column(Boolean, default=True)

    # Relationships
    users = relationship("User", back_populates="organization", foreign_keys="User.organization_id")
    cases = relationship("Case", back_populates="organization")


# =============================================================================
# USER / AUTH
# =============================================================================

class User(Base, TimestampMixin, SoftDeleteMixin):
    """User with role-based access."""
    __tablename__ = 'users'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey('organizations.id'), nullable=True)

    # Auth
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)

    # Profile
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    title = Column(String(50))  # Dr., RA, etc.
    phone = Column(String(50))

    # Role
    role = Column(String(50), nullable=False)  # admin, rechtsanwalt, glaeubigerin, schuldner

    # Settings
    settings = Column(JSONB, default={})
    notification_preferences = Column(JSONB, default={
        'email_reminders': True,
        'in_app_notifications': True
    })

    # Session
    last_login = Column(DateTime)
    is_active = Column(Boolean, default=True)
    email_verified = Column(Boolean, default=False)

    # 2FA (optional)
    totp_secret = Column(String(100))
    totp_enabled = Column(Boolean, default=False)

    # Relationships
    organization = relationship("Organization", back_populates="users", foreign_keys=[organization_id])

    # For external parties (Gläubigerin/Schuldner linked to cases)
    creditor_cases = relationship("Case", back_populates="creditor_user", foreign_keys="Case.creditor_user_id")
    debtor_cases = relationship("Case", back_populates="debtor_user", foreign_keys="Case.debtor_user_id")

    @property
    def full_name(self):
        parts = [self.title, self.first_name, self.last_name]
        return " ".join(p for p in parts if p)


class Session(Base, TimestampMixin):
    """User sessions for authentication."""
    __tablename__ = 'sessions'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    token_hash = Column(String(255), nullable=False, unique=True)
    expires_at = Column(DateTime, nullable=False)
    ip_address = Column(String(45))
    user_agent = Column(Text)
    is_valid = Column(Boolean, default=True)


# =============================================================================
# CASE / AKTE
# =============================================================================

class Case(Base, TimestampMixin, AuditMixin, SoftDeleteMixin):
    """Akte - Central case entity."""
    __tablename__ = 'cases'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey('organizations.id'), nullable=False)

    # Case numbers
    internal_number = Column(String(50), nullable=False)  # e.g., "1-26"
    external_number = Column(String(100))  # Kanzlei-Aktennummer
    court_file_number = Column(String(100))  # Gerichtsaktenzeichen

    # Short description
    subject = Column(String(500))
    description = Column(Text)

    # Parties (can be linked to users or stored as text)
    creditor_user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)
    debtor_user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)

    # Party details (if not linked to user)
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
    status = Column(String(50), default='offen')  # offen, mahnverfahren, vollstreckung, etc.

    # Dunning procedure
    dunning_status = Column(String(50), default='nicht_beantragt')
    mb_application_date = Column(Date)  # Datum Antragstellung MB
    mb_delivery_date = Column(Date)  # Datum Zustellung MB (wichtig für Hemmung)
    vb_application_date = Column(Date)
    vb_issue_date = Column(Date)  # Erlassdatum VB
    vb_finality_date = Column(Date)  # Rechtskraft/Bestandskraft
    objection_date = Column(Date)  # Widerspruchsdatum

    # Enforcement
    enforcement_status = Column(String(50), default='nicht_begonnen')

    # Payment plan
    payment_plan_status = Column(String(50))

    # Assigned lawyer
    assigned_lawyer_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)

    # Tags for filtering
    tags = Column(ARRAY(String), default=[])

    # Metadata
    metadata = Column(JSONB, default={})

    # Relationships
    organization = relationship("Organization", back_populates="cases")
    creditor_user = relationship("User", back_populates="creditor_cases", foreign_keys=[creditor_user_id])
    debtor_user = relationship("User", back_populates="debtor_cases", foreign_keys=[debtor_user_id])
    assigned_lawyer = relationship("User", foreign_keys=[assigned_lawyer_id])

    claims = relationship("Claim", back_populates="case", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="case")
    bookings = relationship("LedgerBooking", back_populates="case")
    messages = relationship("Message", back_populates="case")
    timeline_events = relationship("TimelineEvent", back_populates="case", order_by="TimelineEvent.event_date.desc()")
    payment_plans = relationship("PaymentPlan", back_populates="case")
    enforcement_measures = relationship("EnforcementMeasure", back_populates="case")

    __table_args__ = (
        Index('ix_cases_org_internal', 'organization_id', 'internal_number'),
        UniqueConstraint('organization_id', 'internal_number', name='uq_case_internal_number'),
    )


# =============================================================================
# CLAIM / FORDERUNG
# =============================================================================

class Claim(Base, TimestampMixin, AuditMixin):
    """Einzelne Forderung innerhalb einer Akte."""
    __tablename__ = 'claims'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id = Column(UUID(as_uuid=True), ForeignKey('cases.id'), nullable=False)

    # Description
    description = Column(String(500), nullable=False)
    claim_type = Column(String(50))  # Kaufpreis, Miete, Darlehen, Schadensersatz, etc.

    # Amounts
    principal_amount = Column(Numeric(12, 2), nullable=False)  # Hauptforderung
    interest_rate = Column(Numeric(5, 2))  # Zinssatz p.a.
    interest_start_date = Column(Date)  # Zinsbeginn
    additional_costs = Column(Numeric(12, 2), default=0)  # Nebenforderungen

    # Important dates
    due_date = Column(Date, nullable=False)  # Fälligkeitsdatum (wichtig für Verjährung!)
    invoice_date = Column(Date)
    invoice_number = Column(String(100))

    # Contract reference
    contract_number = Column(String(100))
    contract_date = Column(Date)

    # Status
    is_titled = Column(Boolean, default=False)  # Tituliert?
    title_date = Column(Date)
    title_type = Column(String(50))  # VB, Urteil, Vergleich

    # Metadata
    metadata = Column(JSONB, default={})

    # Relationships
    case = relationship("Case", back_populates="claims")
    documents = relationship("Document", back_populates="claim")


# =============================================================================
# LEDGER / FORDERUNGSKONTO
# =============================================================================

class LedgerBooking(Base, TimestampMixin, AuditMixin):
    """Buchung im Forderungskonto."""
    __tablename__ = 'ledger_bookings'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id = Column(UUID(as_uuid=True), ForeignKey('cases.id'), nullable=False)
    claim_id = Column(UUID(as_uuid=True), ForeignKey('claims.id'), nullable=True)

    # Booking details
    booking_date = Column(Date, nullable=False)
    value_date = Column(Date)  # Wertstellungsdatum

    # Debit/Credit
    debit_credit = Column(String(1), nullable=False)  # 'S' = Soll (increase), 'H' = Haben (decrease)
    amount = Column(Numeric(12, 2), nullable=False)

    # Category
    category = Column(String(50), nullable=False)  # hauptforderung, zinsen, ra_gebuehren, nebenkosten, etc.

    # Description
    description = Column(String(500))
    reference = Column(String(100))  # Zahlungsreferenz

    # Source
    source = Column(String(50))  # glaeubiger, rechtsanwalt, schuldner, system
    source_user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)

    # Status (for payment confirmations from creditor)
    status = Column(String(50), default='verbucht')  # gemeldet, akzeptiert, abgelehnt, verbucht

    # Approval (for reported payments)
    reported_at = Column(DateTime)
    accepted_at = Column(DateTime)
    accepted_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)
    rejection_reason = Column(Text)

    # Linked document (e.g., payment confirmation)
    document_id = Column(UUID(as_uuid=True), ForeignKey('documents.id'), nullable=True)

    # Metadata
    metadata = Column(JSONB, default={})

    # Relationships
    case = relationship("Case", back_populates="bookings")
    claim = relationship("Claim")
    source_user = relationship("User", foreign_keys=[source_user_id])
    approved_by_user = relationship("User", foreign_keys=[accepted_by])
    document = relationship("Document")

    __table_args__ = (
        Index('ix_ledger_case_date', 'case_id', 'booking_date'),
    )


# =============================================================================
# DOCUMENT
# =============================================================================

class Document(Base, TimestampMixin, AuditMixin, SoftDeleteMixin):
    """Document with versioning and OCR."""
    __tablename__ = 'documents'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id = Column(UUID(as_uuid=True), ForeignKey('cases.id'), nullable=True)
    claim_id = Column(UUID(as_uuid=True), ForeignKey('claims.id'), nullable=True)
    organization_id = Column(UUID(as_uuid=True), ForeignKey('organizations.id'), nullable=True)

    # File info
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255))
    file_type = Column(String(50))  # pdf, docx, xlsx, eml, msg, png, jpg
    mime_type = Column(String(100))
    file_size = Column(Integer)

    # Storage
    storage_path = Column(String(500), nullable=False)
    storage_type = Column(String(20), default='local')  # local, s3

    # Integrity
    file_hash = Column(String(64))  # SHA-256

    # Document type/category
    document_type = Column(String(50))  # rechnung, vertrag, mahnung, etc.
    category = Column(String(50))

    # Metadata
    title = Column(String(500))
    description = Column(Text)
    document_date = Column(Date)

    # OCR
    ocr_text = Column(Text)
    ocr_status = Column(String(20), default='pending')  # pending, processing, completed, failed
    ocr_completed_at = Column(DateTime)

    # AI extraction results
    extracted_data = Column(JSONB, default={})  # Beträge, Daten, IBANs, Parteien
    ai_classification = Column(JSONB, default={})

    # Source
    source = Column(String(50))  # upload, bea, email, generated
    source_reference = Column(String(255))  # beA message ID, email ID, etc.

    # Visibility
    visible_to_creditor = Column(Boolean, default=True)
    visible_to_debtor = Column(Boolean, default=False)

    # Version control
    version = Column(Integer, default=1)
    parent_document_id = Column(UUID(as_uuid=True), ForeignKey('documents.id'), nullable=True)
    is_latest = Column(Boolean, default=True)

    # Tags
    tags = Column(ARRAY(String), default=[])

    # Relationships
    case = relationship("Case", back_populates="documents")
    claim = relationship("Claim", back_populates="documents")
    organization = relationship("Organization", foreign_keys=[organization_id])
    parent_document = relationship("Document", remote_side=[id])

    __table_args__ = (
        Index('ix_documents_case', 'case_id'),
        Index('ix_documents_hash', 'file_hash'),
    )


# =============================================================================
# MESSAGE / COMMUNICATION
# =============================================================================

class Message(Base, TimestampMixin):
    """Message/Communication between parties."""
    __tablename__ = 'messages'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id = Column(UUID(as_uuid=True), ForeignKey('cases.id'), nullable=False)

    # Sender/Recipient
    sender_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    sender_role = Column(String(50))  # rechtsanwalt, glaeubigerin, schuldner

    # Recipients (can be multiple)
    recipient_ids = Column(ARRAY(UUID(as_uuid=True)), default=[])
    recipient_roles = Column(ARRAY(String), default=[])

    # Content
    subject = Column(String(500))
    body = Column(Text, nullable=False)
    body_html = Column(Text)

    # Type
    message_type = Column(String(50), default='internal')  # internal, email, bea, letter

    # Status
    status = Column(String(50), default='draft')  # draft, sent, delivered, read
    sent_at = Column(DateTime)
    delivered_at = Column(DateTime)
    read_at = Column(DateTime)

    # Attachments
    attachment_ids = Column(ARRAY(UUID(as_uuid=True)), default=[])

    # External references
    external_message_id = Column(String(255))  # beA message ID, email ID

    # Threading
    parent_message_id = Column(UUID(as_uuid=True), ForeignKey('messages.id'), nullable=True)
    thread_id = Column(UUID(as_uuid=True))

    # Relationships
    case = relationship("Case", back_populates="messages")
    sender = relationship("User", foreign_keys=[sender_id])
    parent_message = relationship("Message", remote_side=[id])


# =============================================================================
# TIMELINE EVENT
# =============================================================================

class TimelineEvent(Base, TimestampMixin):
    """Generic timeline event for case history."""
    __tablename__ = 'timeline_events'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id = Column(UUID(as_uuid=True), ForeignKey('cases.id'), nullable=False)

    # Event details
    event_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    event_type = Column(String(50), nullable=False)  # status_change, booking, document, message, deadline, etc.

    # Description
    title = Column(String(255), nullable=False)
    description = Column(Text)

    # Categorization
    category = Column(String(50))  # mahnverfahren, vollstreckung, zahlung, kommunikation
    severity = Column(String(20), default='info')  # info, warning, success, error

    # Actor
    actor_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)
    actor_role = Column(String(50))
    actor_name = Column(String(255))  # Store name for display even if user deleted

    # References
    reference_type = Column(String(50))  # document, booking, message, claim
    reference_id = Column(UUID(as_uuid=True))

    # Visibility
    visible_to_creditor = Column(Boolean, default=True)
    visible_to_debtor = Column(Boolean, default=False)

    # Metadata
    metadata = Column(JSONB, default={})

    # Relationships
    case = relationship("Case", back_populates="timeline_events")
    actor = relationship("User")

    __table_args__ = (
        Index('ix_timeline_case_date', 'case_id', 'event_date'),
    )


# =============================================================================
# PAYMENT PLAN / RATENZAHLUNG
# =============================================================================

class PaymentPlan(Base, TimestampMixin, AuditMixin):
    """Payment plan / Ratenzahlungsvereinbarung."""
    __tablename__ = 'payment_plans'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id = Column(UUID(as_uuid=True), ForeignKey('cases.id'), nullable=False)

    # Status
    status = Column(String(50), default='angefragt')  # angefragt, entwurf, geprueft, freigegeben, aktiv, etc.

    # Plan details
    total_amount = Column(Numeric(12, 2), nullable=False)
    installment_amount = Column(Numeric(12, 2), nullable=False)
    number_of_installments = Column(Integer, nullable=False)
    first_installment_date = Column(Date, nullable=False)
    interval_days = Column(Integer, default=30)  # Usually monthly (30 days)

    # Interest during payment plan
    interest_rate = Column(Numeric(5, 2), default=0)

    # Request details (from debtor)
    requested_at = Column(DateTime)
    requested_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)
    request_notes = Column(Text)

    # Lawyer review
    reviewed_at = Column(DateTime)
    reviewed_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)
    review_notes = Column(Text)

    # Creditor approval
    approved_at = Column(DateTime)
    approved_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)
    approval_notes = Column(Text)

    # Generated agreement document
    agreement_document_id = Column(UUID(as_uuid=True), ForeignKey('documents.id'), nullable=True)

    # Cancellation
    cancelled_at = Column(DateTime)
    cancelled_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)
    cancellation_reason = Column(Text)

    # Relationships
    case = relationship("Case", back_populates="payment_plans")
    installments = relationship("PaymentPlanInstallment", back_populates="payment_plan", cascade="all, delete-orphan")
    agreement_document = relationship("Document")


class PaymentPlanInstallment(Base, TimestampMixin):
    """Individual installment in a payment plan."""
    __tablename__ = 'payment_plan_installments'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    payment_plan_id = Column(UUID(as_uuid=True), ForeignKey('payment_plans.id'), nullable=False)

    # Installment details
    installment_number = Column(Integer, nullable=False)
    due_date = Column(Date, nullable=False)
    amount = Column(Numeric(12, 2), nullable=False)

    # Status
    status = Column(String(50), default='pending')  # pending, paid, overdue, cancelled

    # Payment
    paid_at = Column(DateTime)
    paid_amount = Column(Numeric(12, 2))
    booking_id = Column(UUID(as_uuid=True), ForeignKey('ledger_bookings.id'), nullable=True)

    # Reminders
    reminder_sent_at = Column(DateTime)
    overdue_reminder_sent_at = Column(DateTime)

    # Relationships
    payment_plan = relationship("PaymentPlan", back_populates="installments")
    booking = relationship("LedgerBooking")


# =============================================================================
# ENFORCEMENT / ZWANGSVOLLSTRECKUNG
# =============================================================================

class EnforcementMeasure(Base, TimestampMixin, AuditMixin):
    """Enforcement measure / Vollstreckungsmaßnahme."""
    __tablename__ = 'enforcement_measures'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id = Column(UUID(as_uuid=True), ForeignKey('cases.id'), nullable=False)

    # Type
    measure_type = Column(String(50), nullable=False)  # gv_auftrag, pfueb_bank, pfueb_arbeitgeber, hypothek, etc.

    # Status
    status = Column(String(50), default='vorgeschlagen')  # vorgeschlagen, ausgewaehlt, freigabe_ausstehend, genehmigt, abgelehnt, ausgefuehrt, ruecklaefer

    # Target (for PfüB, etc.)
    target_type = Column(String(50))  # bank, arbeitgeber, versicherung, grundbuchamt
    target_name = Column(String(255))
    target_address = Column(Text)
    target_iban = Column(String(34))

    # Court/Authority
    court_name = Column(String(255))
    court_address = Column(Text)
    court_file_number = Column(String(100))

    # Dates
    suggested_at = Column(DateTime)
    selected_at = Column(DateTime)
    approval_requested_at = Column(DateTime)
    approved_at = Column(DateTime)
    executed_at = Column(DateTime)
    completed_at = Column(DateTime)

    # Approval
    approved_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)
    approval_notes = Column(Text)
    rejection_notes = Column(Text)

    # Documents
    application_document_id = Column(UUID(as_uuid=True), ForeignKey('documents.id'), nullable=True)
    result_document_id = Column(UUID(as_uuid=True), ForeignKey('documents.id'), nullable=True)

    # Results
    result_amount = Column(Numeric(12, 2))  # Amount recovered
    result_notes = Column(Text)

    # AI recommendation
    ai_recommendation = Column(Text)
    ai_confidence = Column(Numeric(3, 2))  # 0.00 - 1.00

    # Metadata
    metadata = Column(JSONB, default={})

    # Relationships
    case = relationship("Case", back_populates="enforcement_measures")
    approved_by_user = relationship("User", foreign_keys=[approved_by])
    application_document = relationship("Document", foreign_keys=[application_document_id])
    result_document = relationship("Document", foreign_keys=[result_document_id])


class AssetFromVV(Base, TimestampMixin):
    """Asset extracted from Vermögensverzeichnis."""
    __tablename__ = 'assets_from_vv'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id = Column(UUID(as_uuid=True), ForeignKey('cases.id'), nullable=False)
    document_id = Column(UUID(as_uuid=True), ForeignKey('documents.id'), nullable=False)

    # Asset details
    asset_type = Column(String(50), nullable=False)  # konto, lebensversicherung, grundstueck, fahrzeug, rente, gehalt, sonstige

    # Details
    description = Column(Text)
    holder_name = Column(String(255))
    holder_address = Column(Text)

    # Values
    value_amount = Column(Numeric(12, 2))
    monthly_income = Column(Numeric(12, 2))  # For salary/pension

    # Bank accounts
    iban = Column(String(34))
    bic = Column(String(11))

    # Employment
    employer_name = Column(String(255))
    employer_address = Column(Text)

    # Property
    property_address = Column(Text)
    grundbuchamt = Column(String(255))
    grundbuchblatt = Column(String(100))

    # Status
    status = Column(String(50), default='extracted')  # extracted, verified, action_taken

    # Linked enforcement measure
    enforcement_measure_id = Column(UUID(as_uuid=True), ForeignKey('enforcement_measures.id'), nullable=True)

    # Relationships
    case = relationship("Case")
    document = relationship("Document")
    enforcement_measure = relationship("EnforcementMeasure")


# =============================================================================
# DUNNING PROCEDURE / MAHNVERFAHREN (EDA)
# =============================================================================

class DunningApplication(Base, TimestampMixin, AuditMixin):
    """Mahnverfahren application (MB/VB)."""
    __tablename__ = 'dunning_applications'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id = Column(UUID(as_uuid=True), ForeignKey('cases.id'), nullable=False)

    # Type
    application_type = Column(String(20), nullable=False)  # mb (Mahnbescheid), vb (Vollstreckungsbescheid)

    # Court
    court_code = Column(String(10))  # Kennziffer Mahngericht (z.B. Schleswig)
    court_name = Column(String(255), default='Amtsgericht Schleswig')

    # Status
    status = Column(String(50), default='entwurf')  # entwurf, generiert, versendet, zugestellt, widerspruch, erledigt

    # Dates
    created_at = Column(DateTime, default=datetime.utcnow)
    generated_at = Column(DateTime)
    sent_at = Column(DateTime)
    delivered_at = Column(DateTime)
    objection_at = Column(DateTime)

    # Application data (for EDA generation)
    applicant_data = Column(JSONB)  # Gläubiger-Daten
    defendant_data = Column(JSONB)  # Schuldner-Daten
    claim_data = Column(JSONB)  # Forderungs-Daten

    # EDA file
    eda_file_content = Column(Text)  # Generated EDA data
    eda_file_path = Column(String(500))
    eda_version = Column(String(10), default='4.0')  # EDA version

    # Generated documents
    eda_document_id = Column(UUID(as_uuid=True), ForeignKey('documents.id'), nullable=True)
    printout_document_id = Column(UUID(as_uuid=True), ForeignKey('documents.id'), nullable=True)

    # Court response
    court_file_number = Column(String(100))  # Gerichtsaktenzeichen
    response_data = Column(JSONB)  # Parsed court response

    # beA
    bea_message_id = Column(String(255))
    bea_sent_at = Column(DateTime)
    bea_delivery_confirmed = Column(Boolean, default=False)

    # Costs
    court_fees = Column(Numeric(12, 2))

    # Notes
    notes = Column(Text)

    # Relationships
    case = relationship("Case")
    eda_document = relationship("Document", foreign_keys=[eda_document_id])
    printout_document = relationship("Document", foreign_keys=[printout_document_id])


# =============================================================================
# INBOX / POSTEINGANG
# =============================================================================

class InboxItem(Base, TimestampMixin):
    """General inbox item for unassigned documents."""
    __tablename__ = 'inbox_items'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey('organizations.id'), nullable=False)

    # Document
    document_id = Column(UUID(as_uuid=True), ForeignKey('documents.id'), nullable=False)

    # Source
    source = Column(String(50))  # upload, bea, email
    source_reference = Column(String(255))
    received_at = Column(DateTime, default=datetime.utcnow)

    # Status
    status = Column(String(50), default='new')  # new, processing, assigned, archived

    # AI suggestions
    suggested_case_ids = Column(ARRAY(UUID(as_uuid=True)), default=[])  # Top 3 case suggestions
    suggested_action = Column(String(100))  # zahlung, einwand, adressaenderung, ratenwunsch, widerspruch
    ai_analysis = Column(JSONB)  # Full AI analysis results

    # Assignment
    assigned_to_case_id = Column(UUID(as_uuid=True), ForeignKey('cases.id'), nullable=True)
    assigned_at = Column(DateTime)
    assigned_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)

    # Notes
    notes = Column(Text)

    # Relationships
    organization = relationship("Organization")
    document = relationship("Document")
    assigned_case = relationship("Case")
    assigned_by_user = relationship("User")


# =============================================================================
# DEADLINE / FRISTEN
# =============================================================================

class Deadline(Base, TimestampMixin, AuditMixin):
    """Deadline/Frist tracking."""
    __tablename__ = 'deadlines'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id = Column(UUID(as_uuid=True), ForeignKey('cases.id'), nullable=False)

    # Deadline details
    deadline_type = Column(String(50), nullable=False)  # verjaehrung, widerspruch, einspruch, zahlung, sonstiges
    title = Column(String(255), nullable=False)
    description = Column(Text)

    # Dates
    due_date = Column(Date, nullable=False)
    reminder_date = Column(Date)  # When to send reminder

    # Status
    status = Column(String(50), default='active')  # active, completed, expired, cancelled

    # Priority
    priority = Column(String(20), default='normal')  # low, normal, high, critical

    # Completion
    completed_at = Column(DateTime)
    completed_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)
    completion_notes = Column(Text)

    # Reminder
    reminder_sent = Column(Boolean, default=False)
    reminder_sent_at = Column(DateTime)

    # Relationships
    case = relationship("Case")


# =============================================================================
# AUDIT LOG
# =============================================================================

class AuditLog(Base):
    """Comprehensive audit log for all actions."""
    __tablename__ = 'audit_logs'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Actor
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)
    user_email = Column(String(255))
    user_role = Column(String(50))

    # Organization
    organization_id = Column(UUID(as_uuid=True), ForeignKey('organizations.id'), nullable=True)

    # Action
    action = Column(String(100), nullable=False)  # create, update, delete, view, export, login, etc.
    resource_type = Column(String(50), nullable=False)  # case, document, booking, user, etc.
    resource_id = Column(UUID(as_uuid=True))

    # Details
    description = Column(Text)
    old_values = Column(JSONB)
    new_values = Column(JSONB)

    # Context
    ip_address = Column(String(45))
    user_agent = Column(Text)
    session_id = Column(UUID(as_uuid=True))

    # Reference
    case_id = Column(UUID(as_uuid=True), ForeignKey('cases.id'), nullable=True)

    __table_args__ = (
        Index('ix_audit_user_time', 'user_id', 'timestamp'),
        Index('ix_audit_org_time', 'organization_id', 'timestamp'),
        Index('ix_audit_resource', 'resource_type', 'resource_id'),
    )


# =============================================================================
# LIMITATION / VERJÄHRUNG
# =============================================================================

class LimitationEvent(Base, TimestampMixin):
    """Events affecting statute of limitations."""
    __tablename__ = 'limitation_events'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id = Column(UUID(as_uuid=True), ForeignKey('cases.id'), nullable=False)
    claim_id = Column(UUID(as_uuid=True), ForeignKey('claims.id'), nullable=True)

    # Event type
    event_type = Column(String(50), nullable=False)
    # Types: faelligkeit, mahnung, klage, mahnbescheid_antrag, mahnbescheid_zustellung,
    # vollstreckungsbescheid, titel, hemmung_start, hemmung_ende, neubeginn, override

    # Date
    event_date = Column(Date, nullable=False)

    # Effect
    effect = Column(String(50))  # hemmung, neubeginn, titel_30_jahre, custom

    # Calculated limitation date after this event
    new_limitation_date = Column(Date)

    # Manual override
    is_override = Column(Boolean, default=False)
    override_reason = Column(Text)

    # Reference
    reference_type = Column(String(50))
    reference_id = Column(UUID(as_uuid=True))

    # Notes
    notes = Column(Text)

    # Relationships
    case = relationship("Case")
    claim = relationship("Claim")


# =============================================================================
# NOTIFICATIONS
# =============================================================================

class Notification(Base, TimestampMixin):
    """In-app notifications."""
    __tablename__ = 'notifications'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)

    # Content
    title = Column(String(255), nullable=False)
    message = Column(Text)
    notification_type = Column(String(50))  # info, warning, success, error

    # Category
    category = Column(String(50))  # case, payment, deadline, message, system

    # Reference
    reference_type = Column(String(50))
    reference_id = Column(UUID(as_uuid=True))
    case_id = Column(UUID(as_uuid=True), ForeignKey('cases.id'), nullable=True)

    # Status
    is_read = Column(Boolean, default=False)
    read_at = Column(DateTime)

    # Delivery
    email_sent = Column(Boolean, default=False)
    email_sent_at = Column(DateTime)

    # Relationships
    user = relationship("User")
    case = relationship("Case")

    __table_args__ = (
        Index('ix_notifications_user_read', 'user_id', 'is_read'),
    )
