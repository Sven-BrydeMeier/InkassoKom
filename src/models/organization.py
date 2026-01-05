"""
Organization and Membership Models

Implements multi-tenancy as defined in ADR-001.
"""

from sqlalchemy import Column, String, Boolean, ForeignKey, Enum, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from src.models.base import Base, SoftDeleteMixin
import enum


class MembershipRole(str, enum.Enum):
    """Roles within an organization."""
    ADMIN = "admin"
    LAWYER = "lawyer"
    STAFF = "staff"
    EXTERNAL_CREDITOR = "external_creditor"
    EXTERNAL_DEBTOR = "external_debtor"


class Organization(Base, SoftDeleteMixin):
    """
    Organization / Kanzlei / Workspace.

    The top-level tenant for multi-tenancy.
    All business data is scoped to an organization.
    """

    __tablename__ = "organizations"

    # Basic Info
    name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, nullable=False, index=True)

    # Address
    street = Column(String(255))
    postal_code = Column(String(20))
    city = Column(String(100))
    country = Column(String(2), default="DE")

    # Contact
    phone = Column(String(50))
    fax = Column(String(50))
    email = Column(String(255))
    website = Column(String(255))

    # Bank Details
    bank_name = Column(String(255))
    iban = Column(String(34))
    bic = Column(String(11))

    # Settings
    settings = Column(JSONB, default={})
    plan = Column(String(50), default="free")  # free, pro, enterprise

    # Status
    is_active = Column(Boolean, default=True, nullable=False)

    # Relationships
    memberships = relationship("Membership", back_populates="organization", lazy="dynamic")
    cases = relationship("Case", back_populates="organization", lazy="dynamic")
    templates = relationship("Template", back_populates="organization", lazy="dynamic")
    letterheads = relationship("Letterhead", back_populates="organization", lazy="dynamic")

    def __repr__(self) -> str:
        return f"<Organization(id={self.id}, name='{self.name}')>"


class Membership(Base):
    """
    User-Organization association (many-to-many).

    Defines which users belong to which organizations and with what role.
    This is the anchor for RLS policies.
    """

    __tablename__ = "memberships"

    # Foreign Keys
    organization_id = Column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False
    )
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )

    # Role
    role = Column(
        String(50),
        nullable=False,
        default=MembershipRole.STAFF.value
    )

    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    is_default = Column(Boolean, default=False, nullable=False)  # Default org for user

    # Relationships
    organization = relationship("Organization", back_populates="memberships")
    user = relationship("User", back_populates="memberships")

    # Indexes
    __table_args__ = (
        Index("ix_memberships_org_user", "organization_id", "user_id", unique=True),
        Index("ix_memberships_user_active", "user_id", "is_active"),
    )

    def __repr__(self) -> str:
        return f"<Membership(org={self.organization_id}, user={self.user_id}, role={self.role})>"
