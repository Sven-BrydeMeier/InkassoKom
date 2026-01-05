"""
Template and Letterhead Models

Document templates and letterheads for generating letters.
"""

from sqlalchemy import Column, String, Text, Boolean, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from src.models.base import Base, SoftDeleteMixin


class Template(Base, SoftDeleteMixin):
    """
    Document template.

    DOCX templates with placeholders for generating letters.
    """

    __tablename__ = "templates"

    # Organization Reference
    organization_id = Column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Template Info
    name = Column(String(255), nullable=False)
    description = Column(Text)
    template_type = Column(String(50), nullable=False)  # mahnung, klage, zahlungsaufforderung, etc.

    # Storage
    storage_bucket = Column(String(100), default="templates")
    storage_path = Column(String(500), nullable=False)

    # Placeholders
    # Format: [{"key": "AKTENZEICHEN", "description": "Aktenzeichen", "required": true}]
    placeholders = Column(JSONB, default=[])

    # Version
    version = Column(String(50), default="1.0")
    is_active = Column(Boolean, default=True)
    is_default = Column(Boolean, default=False)  # Default for this type

    # Metadata
    metadata = Column(JSONB, default={})
    tags = Column(JSONB, default=[])

    # Relationships
    organization = relationship("Organization", back_populates="templates")

    # Indexes
    __table_args__ = (
        Index("ix_templates_org_type", "organization_id", "template_type"),
    )

    def __repr__(self) -> str:
        return f"<Template(id={self.id}, name='{self.name}')>"


class Letterhead(Base, SoftDeleteMixin):
    """
    Letterhead / Briefkopf.

    Organization-specific letterheads with logo and styling.
    """

    __tablename__ = "letterheads"

    # Organization Reference
    organization_id = Column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Letterhead Info
    name = Column(String(255), nullable=False)
    description = Column(Text)

    # Storage Paths
    docx_path = Column(String(500))  # Word template with header/footer
    logo_path = Column(String(500))  # Logo image

    # Default Values
    defaults = Column(JSONB, default={})  # Default placeholder values

    # Styling
    font_family = Column(String(100), default="Arial")
    font_size = Column(Integer, default=11)
    margin_top = Column(Integer, default=25)  # mm
    margin_bottom = Column(Integer, default=20)
    margin_left = Column(Integer, default=25)
    margin_right = Column(Integer, default=20)

    # Status
    is_active = Column(Boolean, default=True)
    is_default = Column(Boolean, default=False)

    # Relationships
    organization = relationship("Organization", back_populates="letterheads")

    def __repr__(self) -> str:
        return f"<Letterhead(id={self.id}, name='{self.name}')>"


# Import Integer
from sqlalchemy import Integer
