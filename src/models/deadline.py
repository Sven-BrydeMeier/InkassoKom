"""
Deadline Model

Tracks deadlines and reminders for cases.
"""

from sqlalchemy import Column, String, Text, Boolean, Date, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy import DateTime

from src.models.base import Base
import enum


class DeadlineKind(str, enum.Enum):
    """Type of deadline."""
    FRIST = "frist"  # Legal deadline
    TERMIN = "termin"  # Appointment
    WIEDERVORLAGE = "wiedervorlage"  # Follow-up reminder
    VERJAEHRUNG = "verjaehrung"  # Statute of limitations
    ZAHLUNG = "zahlung"  # Payment due
    SONSTIGES = "sonstiges"


class DeadlineStatus(str, enum.Enum):
    """Status of deadline."""
    OFFEN = "offen"
    ERLEDIGT = "erledigt"
    VERSTRICHEN = "verstrichen"
    STORNIERT = "storniert"


class Deadline(Base):
    """
    Deadline / Frist / Termin.

    Tracks important dates and reminders for cases.
    """

    __tablename__ = "deadlines"

    # Case Reference
    case_id = Column(
        UUID(as_uuid=True),
        ForeignKey("cases.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Deadline Info
    kind = Column(String(50), nullable=False, default=DeadlineKind.FRIST.value)
    title = Column(String(255), nullable=False)
    description = Column(Text)

    # Dates
    due_at = Column(DateTime(timezone=True), nullable=False)
    reminder_at = Column(DateTime(timezone=True))  # When to send reminder
    completed_at = Column(DateTime(timezone=True))

    # Status
    status = Column(String(50), default=DeadlineStatus.OFFEN.value)

    # Assignment
    assigned_to = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    # Notification
    notify_days_before = Column(Integer, default=3)
    notification_sent = Column(Boolean, default=False)

    # Legal Reference
    legal_basis = Column(String(255))  # e.g., "§ 167 ZPO"
    is_court_deadline = Column(Boolean, default=False)

    # Priority
    priority = Column(String(20), default="normal")  # low, normal, high, critical

    # Metadata
    metadata = Column(JSONB, default={})

    # Relationships
    case = relationship("Case", back_populates="deadlines")

    # Indexes
    __table_args__ = (
        Index("ix_deadlines_case_due", "case_id", "due_at"),
        Index("ix_deadlines_status_due", "status", "due_at"),
    )

    def __repr__(self) -> str:
        return f"<Deadline(id={self.id}, title='{self.title}')>"


# Import Integer
from sqlalchemy import Integer
