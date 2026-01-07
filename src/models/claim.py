"""
Claim, LedgerBooking, Payment, and PaymentAllocation Models

Financial data models for tracking claims, bookings, and payments.
"""

from sqlalchemy import Column, String, Text, Float, Integer, Date, Boolean, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from src.models.base import Base
import enum


class ClaimStatus(str, enum.Enum):
    """Status of a claim."""
    OFFEN = "offen"
    TEILBEGLICHEN = "teilbeglichen"
    BEGLICHEN = "beglichen"
    UNEINBRINGLICH = "uneinbringlich"
    STRITTIG = "strittig"


class BookingCategory(str, enum.Enum):
    """Category of a ledger booking."""
    HAUPTFORDERUNG = "hauptforderung"
    ZINSEN = "zinsen"
    RA_GEBUEHREN = "ra_gebuehren"
    NEBENKOSTEN = "nebenkosten"
    GERICHTSKOSTEN = "gerichtskosten"
    VOLLSTRECKUNGSKOSTEN = "vollstreckungskosten"
    MAHNKOSTEN = "mahnkosten"
    INKASSOKOSTEN = "inkassokosten"
    AUSLAGEN = "auslagen"
    SONSTIGES = "sonstiges"


class Claim(Base):
    """
    Claim / Forderung.

    Represents a single claim within a case.
    A case can have multiple claims (e.g., principal, legal fees, court costs).
    """

    __tablename__ = "claims"

    # Case Reference
    case_id = Column(
        UUID(as_uuid=True),
        ForeignKey("cases.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Claim Details
    description = Column(String(500), nullable=False)
    claim_type = Column(String(50))  # kaufpreis, miete, darlehen, etc.

    # Amounts
    principal = Column(Float, nullable=False)  # Hauptforderung
    currency = Column(String(3), default="EUR")

    # Interest
    interest_rate = Column(Float)  # e.g., 5.0 for 5%
    interest_type = Column(String(50), default="verzugszinsen")  # verzugszinsen, basiszins_plus
    interest_start_date = Column(Date)
    interest_basis = Column(String(100))  # Legal basis for interest

    # Due Date
    due_date = Column(Date, nullable=False)

    # Invoice Reference
    invoice_number = Column(String(100))
    invoice_date = Column(Date)

    # Title (if judgment obtained)
    is_titled = Column(Boolean, default=False)
    title_date = Column(Date)
    title_reference = Column(String(100))

    # Status
    status = Column(String(50), default=ClaimStatus.OFFEN.value)

    # Relationships
    case = relationship("Case", back_populates="claims")
    ledger_bookings = relationship("LedgerBooking", back_populates="claim", lazy="dynamic")

    # Indexes
    __table_args__ = (
        Index("ix_claims_case_status", "case_id", "status"),
    )

    def __repr__(self) -> str:
        return f"<Claim(id={self.id}, principal={self.principal})>"


class LedgerBooking(Base):
    """
    Ledger Booking / Kontobuchung.

    Tracks all financial movements in a case's Forderungskonto.
    """

    __tablename__ = "ledger_bookings"

    # Case Reference
    case_id = Column(
        UUID(as_uuid=True),
        ForeignKey("cases.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Optional Claim Reference
    claim_id = Column(
        UUID(as_uuid=True),
        ForeignKey("claims.id", ondelete="SET NULL"),
        nullable=True
    )

    # Booking Details
    booking_date = Column(Date, nullable=False)
    debit_credit = Column(String(1), nullable=False)  # 'S' = Soll (debit), 'H' = Haben (credit)
    amount = Column(Float, nullable=False)
    category = Column(String(50), nullable=False)  # See BookingCategory
    description = Column(String(500))
    reference = Column(String(100))  # External reference

    # Source
    source = Column(String(50))  # system, import, manual, schuldner, etc.
    status = Column(String(50), default="verbucht")

    # Metadata
    extra_data = Column(JSONB, default={})

    # Relationships
    case = relationship("Case", back_populates="ledger_bookings")
    claim = relationship("Claim", back_populates="ledger_bookings")
    payment_allocations = relationship("PaymentAllocation", back_populates="booking", lazy="dynamic")

    # Indexes
    __table_args__ = (
        Index("ix_ledger_bookings_case_date", "case_id", "booking_date"),
        Index("ix_ledger_bookings_claim", "claim_id"),
    )

    def __repr__(self) -> str:
        return f"<LedgerBooking(id={self.id}, type={self.debit_credit}, amount={self.amount})>"


class Payment(Base):
    """
    Payment / Zahlung.

    Tracks incoming payments from debtors.
    """

    __tablename__ = "payments"

    # Case Reference
    case_id = Column(
        UUID(as_uuid=True),
        ForeignKey("cases.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Debtor Reference (optional, for multi-debtor cases)
    debtor_party_id = Column(
        UUID(as_uuid=True),
        ForeignKey("parties.id"),
        nullable=True
    )

    # Payment Details
    received_at = Column(Date, nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(String(3), default="EUR")

    # Channel
    channel = Column(String(50))  # bank_transfer, cash, check, etc.
    reference = Column(String(255))  # Bank reference, etc.

    # Status
    status = Column(String(50), default="verbucht")  # verbucht, storniert

    # Notes
    notes = Column(Text)

    # Relationships
    allocations = relationship("PaymentAllocation", back_populates="payment", lazy="dynamic")

    def __repr__(self) -> str:
        return f"<Payment(id={self.id}, amount={self.amount})>"


class PaymentAllocation(Base):
    """
    Payment Allocation / Zahlungszuordnung.

    Maps payments to specific ledger bookings.
    Implements § 367 BGB logic (payment allocation rules).
    """

    __tablename__ = "payment_allocations"

    # Payment Reference
    payment_id = Column(
        UUID(as_uuid=True),
        ForeignKey("payments.id", ondelete="CASCADE"),
        nullable=False
    )

    # Booking Reference
    ledger_booking_id = Column(
        UUID(as_uuid=True),
        ForeignKey("ledger_bookings.id", ondelete="CASCADE"),
        nullable=False
    )

    # Allocated Amount
    amount = Column(Float, nullable=False)

    # Allocation Order (for § 367 BGB)
    allocation_order = Column(Integer, default=0)

    # Relationships
    payment = relationship("Payment", back_populates="allocations")
    booking = relationship("LedgerBooking", back_populates="payment_allocations")

    # Indexes
    __table_args__ = (
        Index("ix_payment_allocations_payment", "payment_id"),
        Index("ix_payment_allocations_booking", "ledger_booking_id"),
    )

    def __repr__(self) -> str:
        return f"<PaymentAllocation(payment={self.payment_id}, booking={self.ledger_booking_id})>"
