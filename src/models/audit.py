"""
Audit Log Model

Tracks all changes to business data for compliance and debugging.
"""

from sqlalchemy import Column, String, Text, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from src.models.base import Base
import enum


class AuditAction(str, enum.Enum):
    """Type of audit action."""
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    SOFT_DELETE = "soft_delete"
    RESTORE = "restore"
    LOGIN = "login"
    LOGOUT = "logout"
    VIEW = "view"
    EXPORT = "export"
    IMPORT = "import"
    SEND = "send"
    APPROVE = "approve"
    REJECT = "reject"


class AuditLog(Base):
    """
    Audit log entry.

    Records all significant actions for compliance and debugging.
    Never delete audit logs - they are append-only.
    """

    __tablename__ = "audit_logs"

    # Organization Reference
    organization_id = Column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    # Actor
    actor_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    actor_email = Column(String(255))  # Denormalized for when user is deleted
    actor_ip = Column(String(45))  # IPv4 or IPv6
    actor_user_agent = Column(String(500))

    # Action
    action = Column(String(50), nullable=False)  # create, update, delete, etc.

    # Target Entity
    entity_type = Column(String(100), nullable=False)  # cases, claims, documents, etc.
    entity_id = Column(UUID(as_uuid=True), nullable=False)
    entity_display = Column(String(255))  # Human-readable identifier

    # Changes
    old_values = Column(JSONB)  # Previous state (for updates)
    new_values = Column(JSONB)  # New state (for creates/updates)
    diff = Column(JSONB)  # Computed diff (for updates)

    # Context
    request_id = Column(String(36))  # Correlation ID for request tracing
    session_id = Column(String(36))  # Session identifier
    notes = Column(Text)

    # Relationships
    actor = relationship("User", back_populates="audit_logs")

    # Indexes
    __table_args__ = (
        Index("ix_audit_logs_org_created", "organization_id", "created_at"),
        Index("ix_audit_logs_actor_created", "actor_user_id", "created_at"),
        Index("ix_audit_logs_entity", "entity_type", "entity_id"),
        Index("ix_audit_logs_action", "action"),
    )

    def __repr__(self) -> str:
        return f"<AuditLog(id={self.id}, action={self.action}, entity={self.entity_type})>"
