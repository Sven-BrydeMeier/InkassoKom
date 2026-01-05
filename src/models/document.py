"""
Document, DocumentChunk, and GeneratedDocument Models

Document storage and RAG preparation models.
"""

from sqlalchemy import Column, String, Text, Integer, Date, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from src.models.base import Base, SoftDeleteMixin


class Document(Base, SoftDeleteMixin):
    """
    Document metadata.

    The actual file is stored in Supabase Storage.
    This table stores metadata and references.
    """

    __tablename__ = "documents"

    # Case Reference (optional - some docs are org-level)
    case_id = Column(
        UUID(as_uuid=True),
        ForeignKey("cases.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )

    # Organization Reference
    organization_id = Column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )

    # File Info
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255))
    mime_type = Column(String(100))
    file_size = Column(Integer)  # bytes
    file_hash = Column(String(64), index=True)  # SHA-256 for dedup

    # Storage
    storage_bucket = Column(String(100), default="case-documents")
    storage_path = Column(String(500), nullable=False)

    # Classification
    document_type = Column(String(50))  # rechnung, vertrag, mahnung, etc.
    category = Column(String(50))  # aussergerichtlich, gerichtlich, intern, etc.
    title = Column(String(500))
    description = Column(Text)

    # Document Date
    document_date = Column(Date)

    # OCR
    ocr_text = Column(Text)
    ocr_status = Column(String(50), default="pending")  # pending, completed, failed, skipped
    ocr_language = Column(String(10), default="de")

    # Visibility
    visible_to_creditor = Column(Boolean, default=True)
    visible_to_debtor = Column(Boolean, default=False)

    # Page Info (for multi-page PDFs)
    page_count = Column(Integer, default=1)
    source_page_start = Column(Integer)  # If extracted from larger PDF
    source_page_end = Column(Integer)

    # Metadata
    metadata = Column(JSONB, default={})
    tags = Column(JSONB, default=[])

    # Relationships
    case = relationship("Case", back_populates="documents")
    chunks = relationship("DocumentChunk", back_populates="document", lazy="dynamic")

    # Indexes
    __table_args__ = (
        Index("ix_documents_case_type", "case_id", "document_type"),
        Index("ix_documents_hash", "file_hash"),
    )

    def __repr__(self) -> str:
        return f"<Document(id={self.id}, filename='{self.filename}')>"


# Import Boolean
from sqlalchemy import Boolean


class DocumentChunk(Base):
    """
    Document chunk for RAG.

    Stores text chunks with embeddings for semantic search.
    """

    __tablename__ = "document_chunks"

    # Document Reference
    document_id = Column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Case Reference (denormalized for faster queries)
    case_id = Column(
        UUID(as_uuid=True),
        ForeignKey("cases.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Organization Reference (denormalized for RLS)
    organization_id = Column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Chunk Info
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    content_length = Column(Integer)

    # Position in Document
    page_number = Column(Integer)
    start_char = Column(Integer)
    end_char = Column(Integer)

    # Embedding
    # Note: For pgvector, add: embedding = Column(Vector(1536))
    # This requires the pgvector extension
    embedding_model = Column(String(100))  # e.g., "text-embedding-3-small"
    embedding_created_at = Column(DateTime(timezone=True))

    # Metadata
    metadata = Column(JSONB, default={})

    # Relationships
    document = relationship("Document", back_populates="chunks")

    # Indexes
    __table_args__ = (
        Index("ix_document_chunks_document_idx", "document_id", "chunk_index"),
    )

    def __repr__(self) -> str:
        return f"<DocumentChunk(doc={self.document_id}, idx={self.chunk_index})>"


# Import DateTime
from sqlalchemy import DateTime


class GeneratedDocument(Base):
    """
    Generated document (letters, court filings, etc.).

    Tracks documents generated from templates.
    """

    __tablename__ = "generated_documents"

    # Case Reference
    case_id = Column(
        UUID(as_uuid=True),
        ForeignKey("cases.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Template Used
    template_id = Column(
        UUID(as_uuid=True),
        ForeignKey("templates.id"),
        nullable=True
    )

    # Letterhead Used
    letterhead_id = Column(
        UUID(as_uuid=True),
        ForeignKey("letterheads.id"),
        nullable=True
    )

    # Document Info
    document_type = Column(String(50), nullable=False)  # mahnung, klage, etc.
    title = Column(String(500))

    # Storage
    storage_bucket = Column(String(100), default="generated-letters")
    storage_path = Column(String(500), nullable=False)
    mime_type = Column(String(100), default="application/pdf")
    file_size = Column(Integer)

    # Generation Details
    generated_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False
    )
    input_data = Column(JSONB)  # Data used for generation
    template_version = Column(String(50))

    # Linked Message (if sent)
    message_id = Column(
        UUID(as_uuid=True),
        ForeignKey("messages.id"),
        nullable=True
    )

    # Status
    status = Column(String(50), default="draft")  # draft, final, sent, archived

    # Relationships
    case = relationship("Case", back_populates="generated_documents")

    def __repr__(self) -> str:
        return f"<GeneratedDocument(id={self.id}, type='{self.document_type}')>"
