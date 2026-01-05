"""
User Model

Users are managed by Supabase Auth (auth.users).
This model extends auth.users with application-specific data.
"""

from sqlalchemy import Column, String, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from src.models.base import Base, SoftDeleteMixin


class User(Base, SoftDeleteMixin):
    """
    Application user profile.

    The id references Supabase auth.users(id).
    Authentication is handled by Supabase Auth.
    """

    __tablename__ = "users"

    # Note: id is linked to auth.users(id) in Supabase
    # Do not generate UUIDs here - they come from Supabase Auth

    # Profile
    email = Column(String(255), unique=True, nullable=False, index=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    title = Column(String(50))  # e.g., "RA", "Dr."
    phone = Column(String(50))

    # Default Role (fallback when not in specific org context)
    role_default = Column(String(50), default="staff")

    # Settings
    settings = Column(JSONB, default={})
    notification_preferences = Column(JSONB, default={})

    # Status
    is_active = Column(Boolean, default=True, nullable=False)

    # Relationships
    memberships = relationship("Membership", back_populates="user", lazy="dynamic")
    audit_logs = relationship("AuditLog", back_populates="actor", lazy="dynamic")

    @property
    def full_name(self) -> str:
        """Get full name with optional title."""
        parts = [self.title, self.first_name, self.last_name]
        return " ".join(p for p in parts if p)

    @property
    def display_name(self) -> str:
        """Get display name (first + last)."""
        return f"{self.first_name} {self.last_name}"

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email='{self.email}')>"
