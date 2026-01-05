"""
Document Service - Business logic for document management
"""
from typing import List, Optional, Dict, Any
from datetime import date, datetime
from sqlalchemy.orm import Session

from src.models.document import Document
from src.database.connection import get_db_session
from src.database.cache import get_cache


class DocumentService:
    """Service for document-related operations."""

    @staticmethod
    def create_document(
        case_id: str,
        name: str,
        document_type: str,
        category: str = 'aussergerichtlich',
        **kwargs
    ) -> Document:
        """Create a new document."""
        with get_db_session() as session:
            document = Document(
                case_id=case_id,
                name=name,
                document_type=document_type,
                category=category,
                file_path=kwargs.get('file_path'),
                file_size=kwargs.get('file_size', 0),
                mime_type=kwargs.get('mime_type', 'application/pdf'),
                page_start=kwargs.get('page_start'),
                page_end=kwargs.get('page_end'),
                storage_url=kwargs.get('storage_url'),
                metadata=kwargs.get('metadata', {})
            )
            session.add(document)
            session.flush()

            # Invalidate cache
            get_cache().delete("documents", case_id)

            return document

    @staticmethod
    def get_document(document_id: str) -> Optional[Dict[str, Any]]:
        """Get document by ID."""
        with get_db_session() as session:
            doc = session.query(Document).filter(Document.id == document_id).first()
            if not doc:
                return None
            return DocumentService._doc_to_dict(doc)

    @staticmethod
    def get_documents_for_case(case_id: str) -> List[Dict[str, Any]]:
        """Get all documents for a case with caching."""
        cache = get_cache()

        # Try cache first
        cached = cache.get_cached_documents(case_id)
        if cached:
            return cached

        with get_db_session() as session:
            documents = session.query(Document).filter(
                Document.case_id == case_id
            ).order_by(Document.created_at).all()

            result = [DocumentService._doc_to_dict(d) for d in documents]

            # Cache result
            cache.cache_documents(case_id, result)
            return result

    @staticmethod
    def get_documents_by_category(case_id: str, category: str) -> List[Dict[str, Any]]:
        """Get documents for a case filtered by category."""
        with get_db_session() as session:
            documents = session.query(Document).filter(
                Document.case_id == case_id,
                Document.category == category
            ).order_by(Document.created_at).all()

            return [DocumentService._doc_to_dict(d) for d in documents]

    @staticmethod
    def update_document(document_id: str, **updates) -> Optional[Dict[str, Any]]:
        """Update document fields."""
        with get_db_session() as session:
            doc = session.query(Document).filter(Document.id == document_id).first()
            if not doc:
                return None

            for key, value in updates.items():
                if hasattr(doc, key):
                    setattr(doc, key, value)

            # Invalidate cache
            get_cache().delete("documents", str(doc.case_id))

            return DocumentService._doc_to_dict(doc)

    @staticmethod
    def delete_document(document_id: str) -> bool:
        """Delete a document."""
        with get_db_session() as session:
            doc = session.query(Document).filter(Document.id == document_id).first()
            if not doc:
                return False

            case_id = str(doc.case_id)
            session.delete(doc)

            # Invalidate cache
            get_cache().delete("documents", case_id)
            return True

    @staticmethod
    def bulk_create_documents(case_id: str, documents: List[Dict[str, Any]]) -> List[Document]:
        """Create multiple documents at once."""
        with get_db_session() as session:
            created = []
            for doc_data in documents:
                document = Document(
                    case_id=case_id,
                    name=doc_data.get('name', 'Dokument'),
                    document_type=doc_data.get('type', 'sonstiges'),
                    category=doc_data.get('category', 'aussergerichtlich'),
                    file_path=doc_data.get('file_path'),
                    file_size=doc_data.get('size', 0),
                    mime_type=doc_data.get('mime_type', 'application/pdf'),
                    page_start=doc_data.get('page'),
                    page_end=doc_data.get('end_page'),
                    metadata=doc_data.get('metadata', {})
                )
                session.add(document)
                created.append(document)

            session.flush()

            # Invalidate cache
            get_cache().delete("documents", case_id)

            return created

    @staticmethod
    def count_documents(case_id: str) -> int:
        """Count documents for a case."""
        with get_db_session() as session:
            return session.query(Document).filter(Document.case_id == case_id).count()

    @staticmethod
    def _doc_to_dict(doc: Document) -> Dict[str, Any]:
        """Convert document model to dictionary."""
        return {
            'id': str(doc.id),
            'case_id': str(doc.case_id),
            'name': doc.name,
            'type': doc.document_type,
            'category': doc.category,
            'date': doc.created_at.strftime('%d.%m.%Y') if doc.created_at else '',
            'page': doc.page_start,
            'end_page': doc.page_end,
            'size': f"{doc.file_size // 1024} KB" if doc.file_size else "0 KB",
            'file_path': doc.file_path,
            'storage_url': doc.storage_url,
            'created': doc.created_at
        }


# Convenience functions
def get_documents_for_case(case_id: str) -> List[Dict[str, Any]]:
    """Get documents for a case."""
    return DocumentService.get_documents_for_case(case_id)


def create_document(**kwargs) -> Document:
    """Create a document."""
    return DocumentService.create_document(**kwargs)
