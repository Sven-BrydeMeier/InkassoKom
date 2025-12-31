"""
Document Service - Document Management with OCR and AI extraction
"""
from datetime import datetime, date
from typing import Optional, List, Dict, Any, BinaryIO
from uuid import UUID, uuid4
import hashlib
import os
import mimetypes

from sqlalchemy.orm import Session
from sqlalchemy import or_

from db.models import (
    Document, Case, User, TimelineEvent, AuditLog, InboxItem
)
from config.settings import settings, DocumentType


class DocumentService:
    """Service for document management, OCR, and AI extraction."""

    ALLOWED_EXTENSIONS = {
        'pdf', 'docx', 'doc', 'xlsx', 'xls',
        'eml', 'msg', 'txt', 'png', 'jpg', 'jpeg'
    }

    MIME_TYPES = {
        'pdf': 'application/pdf',
        'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'doc': 'application/msword',
        'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'xls': 'application/vnd.ms-excel',
        'eml': 'message/rfc822',
        'msg': 'application/vnd.ms-outlook',
        'txt': 'text/plain',
        'png': 'image/png',
        'jpg': 'image/jpeg',
        'jpeg': 'image/jpeg'
    }

    def __init__(self, db: Session):
        self.db = db

    # =========================================================================
    # DOCUMENT UPLOAD
    # =========================================================================

    def upload_document(
        self,
        file_content: bytes,
        filename: str,
        uploaded_by: UUID,
        organization_id: Optional[UUID] = None,
        case_id: Optional[UUID] = None,
        claim_id: Optional[UUID] = None,
        document_type: Optional[str] = None,
        title: Optional[str] = None,
        description: Optional[str] = None,
        document_date: Optional[date] = None,
        visible_to_creditor: bool = True,
        visible_to_debtor: bool = False,
        source: str = 'upload',
        source_reference: Optional[str] = None,
        run_ocr: bool = True
    ) -> Document:
        """
        Upload a new document with optional OCR processing.
        """
        # Validate file extension
        ext = self._get_extension(filename)
        if ext not in self.ALLOWED_EXTENSIONS:
            raise ValueError(f"File extension .{ext} not allowed")

        # Check file size
        if len(file_content) > settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
            raise ValueError(f"File size exceeds {settings.MAX_UPLOAD_SIZE_MB}MB limit")

        # Calculate hash for integrity
        file_hash = hashlib.sha256(file_content).hexdigest()

        # Check for duplicate
        existing = self.db.query(Document).filter(
            Document.file_hash == file_hash,
            Document.is_deleted == False
        ).first()

        if existing:
            # Return existing document if it's a duplicate
            return existing

        # Generate storage path
        storage_path = self._generate_storage_path(organization_id, case_id, filename)

        # Save file
        self._save_file(file_content, storage_path)

        # Create document record
        document = Document(
            organization_id=organization_id,
            case_id=case_id,
            claim_id=claim_id,
            filename=os.path.basename(storage_path),
            original_filename=filename,
            file_type=ext,
            mime_type=self.MIME_TYPES.get(ext, 'application/octet-stream'),
            file_size=len(file_content),
            storage_path=storage_path,
            storage_type=settings.STORAGE_TYPE,
            file_hash=file_hash,
            document_type=document_type,
            title=title or filename,
            description=description,
            document_date=document_date,
            source=source,
            source_reference=source_reference,
            visible_to_creditor=visible_to_creditor,
            visible_to_debtor=visible_to_debtor,
            ocr_status='pending' if run_ocr and ext == 'pdf' else 'not_applicable',
            created_by=uploaded_by
        )

        self.db.add(document)
        self.db.commit()
        self.db.refresh(document)

        # Create timeline event if linked to case
        if case_id:
            self._create_timeline_event(
                case_id=case_id,
                event_type="document_uploaded",
                title="Dokument hochgeladen",
                description=f"Dokument '{filename}' hochgeladen",
                category="dokument",
                actor_id=uploaded_by,
                reference_type="document",
                reference_id=document.id,
                visible_to_creditor=visible_to_creditor,
                visible_to_debtor=visible_to_debtor
            )

        self._log_audit(
            action="upload",
            resource_type="document",
            resource_id=document.id,
            user_id=uploaded_by,
            organization_id=organization_id,
            case_id=case_id,
            description=f"Document uploaded: {filename}"
        )

        # Queue OCR if applicable
        if run_ocr and ext == 'pdf' and settings.OCR_ENABLED:
            self._queue_ocr(document.id)

        return document

    def upload_to_inbox(
        self,
        file_content: bytes,
        filename: str,
        organization_id: UUID,
        uploaded_by: UUID,
        source: str = 'upload',
        source_reference: Optional[str] = None
    ) -> InboxItem:
        """
        Upload a document to the general inbox for later assignment.
        """
        # Upload document without case association
        document = self.upload_document(
            file_content=file_content,
            filename=filename,
            uploaded_by=uploaded_by,
            organization_id=organization_id,
            source=source,
            source_reference=source_reference
        )

        # Create inbox item
        inbox_item = InboxItem(
            organization_id=organization_id,
            document_id=document.id,
            source=source,
            source_reference=source_reference,
            status='new'
        )

        self.db.add(inbox_item)
        self.db.commit()
        self.db.refresh(inbox_item)

        return inbox_item

    # =========================================================================
    # DOCUMENT RETRIEVAL
    # =========================================================================

    def get_document(self, document_id: UUID) -> Optional[Document]:
        """Get a document by ID."""
        return self.db.query(Document).filter(
            Document.id == document_id,
            Document.is_deleted == False
        ).first()

    def get_document_content(self, document_id: UUID) -> Optional[bytes]:
        """Get the content of a document."""
        document = self.get_document(document_id)
        if not document:
            return None

        return self._read_file(document.storage_path)

    def get_documents_for_case(
        self,
        case_id: UUID,
        user_role: Optional[str] = None,
        document_type: Optional[str] = None
    ) -> List[Document]:
        """Get all documents for a case with optional filters."""
        query = self.db.query(Document).filter(
            Document.case_id == case_id,
            Document.is_deleted == False,
            Document.is_latest == True
        )

        # Filter based on visibility for external users
        if user_role == 'glaeubigerin':
            query = query.filter(Document.visible_to_creditor == True)
        elif user_role == 'schuldner':
            query = query.filter(Document.visible_to_debtor == True)

        if document_type:
            query = query.filter(Document.document_type == document_type)

        return query.order_by(Document.created_at.desc()).all()

    def get_inbox_items(
        self,
        organization_id: UUID,
        status: Optional[str] = None
    ) -> List[InboxItem]:
        """Get inbox items for an organization."""
        query = self.db.query(InboxItem).filter(
            InboxItem.organization_id == organization_id
        )

        if status:
            query = query.filter(InboxItem.status == status)

        return query.order_by(InboxItem.received_at.desc()).all()

    # =========================================================================
    # DOCUMENT ASSIGNMENT
    # =========================================================================

    def assign_inbox_item_to_case(
        self,
        inbox_item_id: UUID,
        case_id: UUID,
        assigned_by: UUID,
        document_type: Optional[str] = None,
        visible_to_creditor: bool = True,
        visible_to_debtor: bool = False
    ) -> Document:
        """Assign an inbox item to a case."""
        inbox_item = self.db.query(InboxItem).filter(
            InboxItem.id == inbox_item_id
        ).first()

        if not inbox_item:
            raise ValueError("Inbox item not found")

        document = self.get_document(inbox_item.document_id)
        if not document:
            raise ValueError("Document not found")

        # Update document
        document.case_id = case_id
        document.document_type = document_type
        document.visible_to_creditor = visible_to_creditor
        document.visible_to_debtor = visible_to_debtor
        document.updated_by = assigned_by

        # Update inbox item
        inbox_item.status = 'assigned'
        inbox_item.assigned_to_case_id = case_id
        inbox_item.assigned_at = datetime.utcnow()
        inbox_item.assigned_by = assigned_by

        self.db.commit()
        self.db.refresh(document)

        # Create timeline event
        self._create_timeline_event(
            case_id=case_id,
            event_type="document_assigned",
            title="Dokument zugeordnet",
            description=f"Dokument '{document.original_filename}' aus Posteingang zugeordnet",
            category="dokument",
            actor_id=assigned_by,
            reference_type="document",
            reference_id=document.id,
            visible_to_creditor=visible_to_creditor,
            visible_to_debtor=visible_to_debtor
        )

        return document

    # =========================================================================
    # DOCUMENT UPDATE
    # =========================================================================

    def update_document(
        self,
        document_id: UUID,
        updated_by: UUID,
        **kwargs
    ) -> Optional[Document]:
        """Update document metadata."""
        document = self.get_document(document_id)
        if not document:
            return None

        old_values = {}
        new_values = {}

        allowed_fields = [
            'title', 'description', 'document_date', 'document_type',
            'category', 'visible_to_creditor', 'visible_to_debtor', 'tags'
        ]

        for key, value in kwargs.items():
            if key in allowed_fields and hasattr(document, key):
                old_val = getattr(document, key)
                if old_val != value:
                    old_values[key] = str(old_val) if old_val else None
                    setattr(document, key, value)
                    new_values[key] = str(value) if value else None

        if new_values:
            document.updated_by = updated_by
            self.db.commit()
            self.db.refresh(document)

            self._log_audit(
                action="update",
                resource_type="document",
                resource_id=document.id,
                user_id=updated_by,
                case_id=document.case_id,
                description=f"Document updated: {document.original_filename}",
                old_values=old_values,
                new_values=new_values
            )

        return document

    def delete_document(self, document_id: UUID, deleted_by: UUID) -> bool:
        """Soft delete a document."""
        document = self.get_document(document_id)
        if not document:
            return False

        document.is_deleted = True
        document.deleted_at = datetime.utcnow()
        document.deleted_by = deleted_by
        self.db.commit()

        self._log_audit(
            action="delete",
            resource_type="document",
            resource_id=document.id,
            user_id=deleted_by,
            case_id=document.case_id,
            description=f"Document deleted: {document.original_filename}"
        )

        return True

    # =========================================================================
    # OCR PROCESSING
    # =========================================================================

    def _queue_ocr(self, document_id: UUID):
        """Queue document for OCR processing."""
        # In a full implementation, this would queue a Celery task
        # For now, we'll just mark it as queued
        document = self.get_document(document_id)
        if document:
            document.ocr_status = 'queued'
            self.db.commit()

    def process_ocr(self, document_id: UUID) -> Optional[str]:
        """
        Process OCR for a document.
        Returns the extracted text.
        """
        document = self.get_document(document_id)
        if not document:
            return None

        if document.file_type != 'pdf':
            return None

        try:
            document.ocr_status = 'processing'
            self.db.commit()

            # Get document content
            content = self.get_document_content(document_id)
            if not content:
                document.ocr_status = 'failed'
                self.db.commit()
                return None

            # Perform OCR
            ocr_text = self._perform_ocr(content)

            # Update document
            document.ocr_text = ocr_text
            document.ocr_status = 'completed'
            document.ocr_completed_at = datetime.utcnow()
            self.db.commit()

            return ocr_text

        except Exception as e:
            document.ocr_status = 'failed'
            self.db.commit()
            raise

    def _perform_ocr(self, pdf_content: bytes) -> str:
        """
        Perform OCR on PDF content.
        Uses pdf2image and pytesseract.
        """
        try:
            from pdf2image import convert_from_bytes
            import pytesseract

            # Convert PDF to images
            images = convert_from_bytes(pdf_content)

            # OCR each page
            text_parts = []
            for i, image in enumerate(images):
                page_text = pytesseract.image_to_string(image, lang='deu')
                text_parts.append(f"--- Seite {i+1} ---\n{page_text}")

            return "\n\n".join(text_parts)

        except ImportError:
            # OCR dependencies not installed
            return ""
        except Exception as e:
            raise

    # =========================================================================
    # SEARCH
    # =========================================================================

    def search_documents(
        self,
        organization_id: UUID,
        search_term: str,
        case_id: Optional[UUID] = None
    ) -> List[Document]:
        """Search documents by filename, title, or OCR text."""
        search_pattern = f"%{search_term}%"

        query = self.db.query(Document).filter(
            Document.organization_id == organization_id,
            Document.is_deleted == False,
            or_(
                Document.filename.ilike(search_pattern),
                Document.original_filename.ilike(search_pattern),
                Document.title.ilike(search_pattern),
                Document.description.ilike(search_pattern),
                Document.ocr_text.ilike(search_pattern)
            )
        )

        if case_id:
            query = query.filter(Document.case_id == case_id)

        return query.order_by(Document.created_at.desc()).all()

    # =========================================================================
    # FILE STORAGE
    # =========================================================================

    def _get_extension(self, filename: str) -> str:
        """Get file extension from filename."""
        return filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''

    def _generate_storage_path(
        self,
        organization_id: Optional[UUID],
        case_id: Optional[UUID],
        filename: str
    ) -> str:
        """Generate a unique storage path for a file."""
        ext = self._get_extension(filename)
        unique_name = f"{uuid4().hex}.{ext}"

        if organization_id:
            org_part = str(organization_id)[:8]
        else:
            org_part = "general"

        if case_id:
            case_part = str(case_id)[:8]
            path = os.path.join(settings.STORAGE_PATH, org_part, case_part, unique_name)
        else:
            path = os.path.join(settings.STORAGE_PATH, org_part, "inbox", unique_name)

        return path

    def _save_file(self, content: bytes, path: str):
        """Save file content to storage."""
        if settings.STORAGE_TYPE == 'local':
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, 'wb') as f:
                f.write(content)
        elif settings.STORAGE_TYPE == 's3':
            self._save_to_s3(content, path)

    def _read_file(self, path: str) -> Optional[bytes]:
        """Read file content from storage."""
        if settings.STORAGE_TYPE == 'local':
            try:
                with open(path, 'rb') as f:
                    return f.read()
            except FileNotFoundError:
                return None
        elif settings.STORAGE_TYPE == 's3':
            return self._read_from_s3(path)
        return None

    def _save_to_s3(self, content: bytes, path: str):
        """Save file to S3."""
        import boto3

        s3 = boto3.client(
            's3',
            endpoint_url=settings.S3_ENDPOINT,
            aws_access_key_id=settings.S3_ACCESS_KEY,
            aws_secret_access_key=settings.S3_SECRET_KEY,
            region_name=settings.S3_REGION
        )

        s3.put_object(
            Bucket=settings.S3_BUCKET,
            Key=path,
            Body=content
        )

    def _read_from_s3(self, path: str) -> Optional[bytes]:
        """Read file from S3."""
        import boto3

        try:
            s3 = boto3.client(
                's3',
                endpoint_url=settings.S3_ENDPOINT,
                aws_access_key_id=settings.S3_ACCESS_KEY,
                aws_secret_access_key=settings.S3_SECRET_KEY,
                region_name=settings.S3_REGION
            )

            response = s3.get_object(Bucket=settings.S3_BUCKET, Key=path)
            return response['Body'].read()
        except Exception:
            return None

    # =========================================================================
    # TIMELINE AND AUDIT
    # =========================================================================

    def _create_timeline_event(
        self,
        case_id: UUID,
        event_type: str,
        title: str,
        actor_id: Optional[UUID] = None,
        description: Optional[str] = None,
        category: Optional[str] = None,
        reference_type: Optional[str] = None,
        reference_id: Optional[UUID] = None,
        visible_to_creditor: bool = True,
        visible_to_debtor: bool = False
    ) -> TimelineEvent:
        """Create a timeline event."""
        actor_name = None
        actor_role = None

        if actor_id:
            actor = self.db.query(User).filter(User.id == actor_id).first()
            if actor:
                actor_name = actor.full_name
                actor_role = actor.role

        event = TimelineEvent(
            case_id=case_id,
            event_type=event_type,
            title=title,
            description=description,
            category=category,
            actor_id=actor_id,
            actor_name=actor_name,
            actor_role=actor_role,
            reference_type=reference_type,
            reference_id=reference_id,
            visible_to_creditor=visible_to_creditor,
            visible_to_debtor=visible_to_debtor
        )

        self.db.add(event)
        self.db.commit()

        return event

    def _log_audit(
        self,
        action: str,
        resource_type: str,
        resource_id: Optional[UUID] = None,
        user_id: Optional[UUID] = None,
        organization_id: Optional[UUID] = None,
        case_id: Optional[UUID] = None,
        description: Optional[str] = None,
        old_values: Optional[Dict] = None,
        new_values: Optional[Dict] = None
    ):
        """Log an audit entry."""
        user = None
        if user_id:
            user = self.db.query(User).filter(User.id == user_id).first()

        log = AuditLog(
            user_id=user_id,
            user_email=user.email if user else None,
            user_role=user.role if user else None,
            organization_id=organization_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            description=description,
            old_values=old_values,
            new_values=new_values,
            case_id=case_id
        )

        self.db.add(log)
