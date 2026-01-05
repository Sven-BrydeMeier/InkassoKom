"""
Case, Party, and CaseParty Models

The Case is the central business object in InkassoKom.
Parties represent involved entities (creditors, debtors, etc.).
"""

from sqlalchemy import Column, String, Text, Boolean, Date, ForeignKey, Enum, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from src.models.base import Base, SoftDeleteMixin
import enum


class CaseStatus(str, enum.Enum):
    """Status of a case."""
    OFFEN = "offen"
    MAHNVERFAHREN = "mahnverfahren"
    VOLLSTRECKUNG = "vollstreckung"
    RATENZAHLUNG = "ratenzahlung"
    ABGESCHLOSSEN = "abgeschlossen"
    UNEINBRINGLICH = "uneinbringlich"


class DunningStatus(str, enum.Enum):
    """Status of the dunning procedure."""
    NICHT_BEANTRAGT = "nicht_beantragt"
    MB_BEANTRAGT = "mb_beantragt"
    MB_ZUGESTELLT = "mb_zugestellt"
    WIDERSPRUCH = "widerspruch"
    VB_BEANTRAGT = "vb_beantragt"
    VB_ERLASSEN = "vb_erlassen"
    TITEL_RECHTSKRAEFTIG = "titel_rechtskraeftig"


class EnforcementStatus(str, enum.Enum):
    """Status of enforcement."""
    NICHT_BEGONNEN = "nicht_begonnen"
    GV_AUFTRAG = "gv_auftrag"
    VV_ERHALTEN = "vv_erhalten"
    PFUEB_BEANTRAGT = "pfueb_beantragt"
    PFUEB_ERLASSEN = "pfueb_erlassen"
    PFUEB_ZUGESTELLT = "pfueb_zugestellt"
    TEILZAHLUNG = "teilzahlung"
    VOLLSTAENDIG = "vollstaendig"


class PartyType(str, enum.Enum):
    """Type of party."""
    NATURAL_PERSON = "natural_person"
    LEGAL_ENTITY = "legal_entity"


class PartyRole(str, enum.Enum):
    """Role of a party in a case."""
    CREDITOR = "creditor"
    DEBTOR = "debtor"
    DEBTOR_EMPLOYER = "debtor_employer"
    DEBTOR_BANK = "debtor_bank"
    THIRD_PARTY = "third_party"


class Case(Base, SoftDeleteMixin):
    """
    Legal case / Akte.

    The central business object containing all related data.
    """

    __tablename__ = "cases"

    # Organization (multi-tenancy)
    organization_id = Column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Case Numbers
    case_no = Column(String(50), nullable=False)  # Internal: "1/25"
    external_no = Column(String(100))  # Client reference
    court_file_no = Column(String(100))  # Court file number

    # Description
    subject = Column(String(500))
    description = Column(Text)

    # Status
    status = Column(String(50), nullable=False, default=CaseStatus.OFFEN.value)
    dunning_status = Column(String(50), default=DunningStatus.NICHT_BEANTRAGT.value)
    enforcement_status = Column(String(50), default=EnforcementStatus.NICHT_BEGONNEN.value)

    # Important Dates
    opened_at = Column(Date)
    closed_at = Column(Date)
    mb_application_date = Column(Date)  # Mahnbescheid
    mb_delivery_date = Column(Date)
    vb_issue_date = Column(Date)  # Vollstreckungsbescheid

    # Assignment
    assigned_lawyer_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    # Metadata
    tags = Column(JSONB, default=[])
    metadata = Column(JSONB, default={})

    # Import tracking
    imported = Column(Boolean, default=False)
    import_source = Column(String(100))  # e.g., "ra-micro"
    import_filename = Column(String(255))

    # Relationships
    organization = relationship("Organization", back_populates="cases")
    case_parties = relationship("CaseParty", back_populates="case", lazy="dynamic")
    claims = relationship("Claim", back_populates="case", lazy="dynamic")
    ledger_bookings = relationship("LedgerBooking", back_populates="case", lazy="dynamic")
    documents = relationship("Document", back_populates="case", lazy="dynamic")
    communications = relationship("Communication", back_populates="case", lazy="dynamic")
    deadlines = relationship("Deadline", back_populates="case", lazy="dynamic")
    generated_documents = relationship("GeneratedDocument", back_populates="case", lazy="dynamic")

    # Indexes
    __table_args__ = (
        Index("ix_cases_org_case_no", "organization_id", "case_no", unique=True),
        Index("ix_cases_status", "status"),
    )

    def __repr__(self) -> str:
        return f"<Case(id={self.id}, case_no='{self.case_no}')>"


class Party(Base, SoftDeleteMixin):
    """
    Party / Beteiligte.

    Represents creditors, debtors, and other involved parties.
    Can be shared across multiple cases.
    """

    __tablename__ = "parties"

    # Organization (for party master data)
    organization_id = Column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Type
    party_type = Column(String(50), nullable=False, default=PartyType.NATURAL_PERSON.value)

    # Identity
    name = Column(String(255), nullable=False)  # Full name / Company name
    name_addition = Column(String(255))  # c/o, z.Hd., etc.

    # Natural Person
    salutation = Column(String(20))  # Herr, Frau
    first_name = Column(String(100))
    last_name = Column(String(100))
    birth_date = Column(Date)

    # Legal Entity
    legal_form = Column(String(50))  # GmbH, AG, etc.
    registration_number = Column(String(100))  # HRB, etc.
    registration_court = Column(String(100))

    # Address
    address = Column(JSONB, default={})  # {street, postal_code, city, country}

    # Contact
    email = Column(String(255))
    phone = Column(String(50))
    fax = Column(String(50))

    # Identifiers
    identifiers = Column(JSONB, default={})  # {tax_id, vat_id, iban, etc.}

    # Linked User (if party is also a platform user)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    # Relationships
    case_parties = relationship("CaseParty", back_populates="party", lazy="dynamic")

    def __repr__(self) -> str:
        return f"<Party(id={self.id}, name='{self.name}')>"


class CaseParty(Base):
    """
    Case-Party association (many-to-many).

    Defines which parties are involved in which cases and in what role.
    """

    __tablename__ = "case_parties"

    # Foreign Keys
    case_id = Column(
        UUID(as_uuid=True),
        ForeignKey("cases.id", ondelete="CASCADE"),
        nullable=False
    )
    party_id = Column(
        UUID(as_uuid=True),
        ForeignKey("parties.id", ondelete="CASCADE"),
        nullable=False
    )

    # Role in this case
    role = Column(String(50), nullable=False)  # creditor, debtor, etc.

    # Additional info for this case
    reference = Column(String(100))  # Party's own reference number
    notes = Column(Text)

    # Relationships
    case = relationship("Case", back_populates="case_parties")
    party = relationship("Party", back_populates="case_parties")

    # Indexes
    __table_args__ = (
        Index("ix_case_parties_case_party", "case_id", "party_id", "role", unique=True),
    )

    def __repr__(self) -> str:
        return f"<CaseParty(case={self.case_id}, party={self.party_id}, role={self.role})>"
