"""
Case Management Service
Handles all case-related operations
"""
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from uuid import UUID
from decimal import Decimal

from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, func

from db.models import (
    Case, Claim, User, Organization, TimelineEvent,
    LedgerBooking, Document, AuditLog
)
from config.settings import CaseStatus, DunningStatus, EnforcementStatus


class CaseService:
    """Service for case management operations."""

    def __init__(self, db: Session):
        self.db = db

    # =========================================================================
    # CASE CRUD
    # =========================================================================

    def create_case(
        self,
        organization_id: UUID,
        creditor_name: str,
        debtor_name: str,
        created_by: UUID,
        **kwargs
    ) -> Case:
        """Create a new case with auto-generated internal number."""
        # Generate internal number (e.g., 1-26 for first case in 2026)
        year_suffix = str(datetime.now().year)[-2:]

        # Get the next sequence number for this organization
        last_case = self.db.query(Case).filter(
            Case.organization_id == organization_id,
            Case.internal_number.like(f"%-{year_suffix}")
        ).order_by(Case.created_at.desc()).first()

        if last_case:
            try:
                last_num = int(last_case.internal_number.split('-')[0])
                next_num = last_num + 1
            except (ValueError, IndexError):
                next_num = 1
        else:
            next_num = 1

        internal_number = f"{next_num}-{year_suffix}"

        case = Case(
            organization_id=organization_id,
            internal_number=internal_number,
            creditor_name=creditor_name,
            debtor_name=debtor_name,
            status=CaseStatus.OFFEN,
            dunning_status=DunningStatus.NICHT_BEANTRAGT,
            enforcement_status=EnforcementStatus.NICHT_BEGONNEN,
            created_by=created_by,
            **kwargs
        )

        self.db.add(case)
        self.db.commit()
        self.db.refresh(case)

        # Create timeline event
        self._create_timeline_event(
            case_id=case.id,
            event_type="case_created",
            title="Akte angelegt",
            description=f"Akte {internal_number} wurde angelegt",
            category="system",
            actor_id=created_by,
            visible_to_creditor=True,
            visible_to_debtor=False
        )

        self._log_audit(
            action="create",
            resource_type="case",
            resource_id=case.id,
            user_id=created_by,
            organization_id=organization_id,
            case_id=case.id,
            description=f"Case created: {internal_number}"
        )

        return case

    def get_case(self, case_id: UUID) -> Optional[Case]:
        """Get a case by ID."""
        return self.db.query(Case).filter(
            Case.id == case_id,
            Case.is_deleted == False
        ).first()

    def get_case_by_internal_number(
        self,
        organization_id: UUID,
        internal_number: str
    ) -> Optional[Case]:
        """Get a case by internal number within an organization."""
        return self.db.query(Case).filter(
            Case.organization_id == organization_id,
            Case.internal_number == internal_number,
            Case.is_deleted == False
        ).first()

    def get_cases_for_organization(
        self,
        organization_id: UUID,
        status: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Case]:
        """Get all cases for an organization with optional filters."""
        query = self.db.query(Case).filter(
            Case.organization_id == organization_id,
            Case.is_deleted == False
        )

        if status:
            query = query.filter(Case.status == status)

        if search:
            search_term = f"%{search}%"
            query = query.filter(
                or_(
                    Case.internal_number.ilike(search_term),
                    Case.external_number.ilike(search_term),
                    Case.creditor_name.ilike(search_term),
                    Case.debtor_name.ilike(search_term),
                    Case.subject.ilike(search_term)
                )
            )

        # Sort by internal number (parse the number part)
        query = query.order_by(Case.created_at.desc())

        return query.offset(offset).limit(limit).all()

    def get_cases_for_creditor(self, creditor_user_id: UUID) -> List[Case]:
        """Get all cases where user is the creditor."""
        return self.db.query(Case).filter(
            Case.creditor_user_id == creditor_user_id,
            Case.is_deleted == False
        ).order_by(Case.created_at.desc()).all()

    def get_cases_for_debtor(self, debtor_user_id: UUID) -> List[Case]:
        """Get all cases where user is the debtor."""
        return self.db.query(Case).filter(
            Case.debtor_user_id == debtor_user_id,
            Case.is_deleted == False
        ).order_by(Case.created_at.desc()).all()

    def update_case(
        self,
        case_id: UUID,
        updated_by: UUID,
        **kwargs
    ) -> Optional[Case]:
        """Update a case."""
        case = self.get_case(case_id)
        if not case:
            return None

        old_values = {}
        new_values = {}

        for key, value in kwargs.items():
            if hasattr(case, key) and key not in ['id', 'created_at', 'organization_id']:
                old_val = getattr(case, key)
                if old_val != value:
                    old_values[key] = str(old_val) if old_val else None
                    setattr(case, key, value)
                    new_values[key] = str(value) if value else None

        if new_values:
            case.updated_by = updated_by
            self.db.commit()
            self.db.refresh(case)

            # Log status changes as timeline events
            if 'status' in new_values:
                self._create_timeline_event(
                    case_id=case.id,
                    event_type="status_change",
                    title="Status geändert",
                    description=f"Status geändert von {old_values.get('status')} zu {new_values.get('status')}",
                    category="system",
                    actor_id=updated_by,
                    visible_to_creditor=True,
                    visible_to_debtor=True
                )

            self._log_audit(
                action="update",
                resource_type="case",
                resource_id=case.id,
                user_id=updated_by,
                organization_id=case.organization_id,
                case_id=case.id,
                description=f"Case updated: {case.internal_number}",
                old_values=old_values,
                new_values=new_values
            )

        return case

    def delete_case(self, case_id: UUID, deleted_by: UUID) -> bool:
        """Soft delete a case."""
        case = self.get_case(case_id)
        if not case:
            return False

        case.is_deleted = True
        case.deleted_at = datetime.utcnow()
        case.deleted_by = deleted_by
        self.db.commit()

        self._log_audit(
            action="delete",
            resource_type="case",
            resource_id=case.id,
            user_id=deleted_by,
            organization_id=case.organization_id,
            case_id=case.id,
            description=f"Case deleted: {case.internal_number}"
        )

        return True

    # =========================================================================
    # CLAIM MANAGEMENT
    # =========================================================================

    def add_claim(
        self,
        case_id: UUID,
        description: str,
        principal_amount: Decimal,
        due_date: date,
        created_by: UUID,
        **kwargs
    ) -> Claim:
        """Add a claim to a case."""
        case = self.get_case(case_id)
        if not case:
            raise ValueError("Case not found")

        claim = Claim(
            case_id=case_id,
            description=description,
            principal_amount=principal_amount,
            due_date=due_date,
            created_by=created_by,
            **kwargs
        )

        self.db.add(claim)
        self.db.commit()
        self.db.refresh(claim)

        # Create initial booking for the principal amount
        from .ledger_service import LedgerService
        ledger = LedgerService(self.db)
        ledger.create_booking(
            case_id=case_id,
            claim_id=claim.id,
            booking_date=due_date,
            debit_credit='S',
            amount=principal_amount,
            category='hauptforderung',
            description=f"Hauptforderung: {description}",
            source='system',
            created_by=created_by
        )

        self._create_timeline_event(
            case_id=case_id,
            event_type="claim_added",
            title="Forderung hinzugefügt",
            description=f"Forderung über {principal_amount}€ hinzugefügt: {description}",
            category="forderung",
            actor_id=created_by,
            reference_type="claim",
            reference_id=claim.id,
            visible_to_creditor=True,
            visible_to_debtor=True
        )

        return claim

    def get_claims_for_case(self, case_id: UUID) -> List[Claim]:
        """Get all claims for a case."""
        return self.db.query(Claim).filter(
            Claim.case_id == case_id
        ).order_by(Claim.due_date).all()

    def update_claim(
        self,
        claim_id: UUID,
        updated_by: UUID,
        **kwargs
    ) -> Optional[Claim]:
        """Update a claim."""
        claim = self.db.query(Claim).filter(Claim.id == claim_id).first()
        if not claim:
            return None

        old_values = {}
        new_values = {}

        for key, value in kwargs.items():
            if hasattr(claim, key) and key not in ['id', 'case_id', 'created_at']:
                old_val = getattr(claim, key)
                if old_val != value:
                    old_values[key] = str(old_val) if old_val else None
                    setattr(claim, key, value)
                    new_values[key] = str(value) if value else None

        if new_values:
            claim.updated_by = updated_by
            self.db.commit()
            self.db.refresh(claim)

            self._log_audit(
                action="update",
                resource_type="claim",
                resource_id=claim.id,
                user_id=updated_by,
                case_id=claim.case_id,
                description=f"Claim updated",
                old_values=old_values,
                new_values=new_values
            )

        return claim

    # =========================================================================
    # CASE SUMMARY / STATISTICS
    # =========================================================================

    def get_case_summary(self, case_id: UUID) -> Dict[str, Any]:
        """Get a summary of a case including total amounts."""
        case = self.get_case(case_id)
        if not case:
            return {}

        # Calculate total from ledger
        from .ledger_service import LedgerService
        ledger = LedgerService(self.db)
        balance = ledger.get_case_balance(case_id)

        # Get claims
        claims = self.get_claims_for_case(case_id)

        # Get documents count
        doc_count = self.db.query(Document).filter(
            Document.case_id == case_id,
            Document.is_deleted == False
        ).count()

        return {
            "case_id": str(case.id),
            "internal_number": case.internal_number,
            "external_number": case.external_number,
            "status": case.status,
            "dunning_status": case.dunning_status,
            "enforcement_status": case.enforcement_status,
            "creditor_name": case.creditor_name,
            "debtor_name": case.debtor_name,
            "claims_count": len(claims),
            "documents_count": doc_count,
            "balance": balance,
            "created_at": case.created_at.isoformat() if case.created_at else None
        }

    def get_organization_statistics(self, organization_id: UUID) -> Dict[str, Any]:
        """Get statistics for all cases in an organization."""
        cases = self.db.query(Case).filter(
            Case.organization_id == organization_id,
            Case.is_deleted == False
        ).all()

        status_counts = {}
        total_principal = Decimal('0')
        total_open = Decimal('0')

        for case in cases:
            status = case.status or 'unknown'
            status_counts[status] = status_counts.get(status, 0) + 1

            # Get balance
            from .ledger_service import LedgerService
            ledger = LedgerService(self.db)
            balance = ledger.get_case_balance(case.id)
            total_principal += balance.get('total_principal', Decimal('0'))
            total_open += balance.get('total_open', Decimal('0'))

        return {
            "total_cases": len(cases),
            "status_counts": status_counts,
            "total_principal": float(total_principal),
            "total_open": float(total_open)
        }

    # =========================================================================
    # TIMELINE EVENTS
    # =========================================================================

    def _create_timeline_event(
        self,
        case_id: UUID,
        event_type: str,
        title: str,
        actor_id: Optional[UUID] = None,
        description: Optional[str] = None,
        category: Optional[str] = None,
        severity: str = "info",
        reference_type: Optional[str] = None,
        reference_id: Optional[UUID] = None,
        visible_to_creditor: bool = True,
        visible_to_debtor: bool = False,
        metadata: Optional[Dict] = None
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
            severity=severity,
            actor_id=actor_id,
            actor_name=actor_name,
            actor_role=actor_role,
            reference_type=reference_type,
            reference_id=reference_id,
            visible_to_creditor=visible_to_creditor,
            visible_to_debtor=visible_to_debtor,
            metadata=metadata or {}
        )

        self.db.add(event)
        self.db.commit()
        self.db.refresh(event)

        return event

    def get_timeline_events(
        self,
        case_id: UUID,
        user_role: str,
        limit: int = 50
    ) -> List[TimelineEvent]:
        """Get timeline events for a case based on user role visibility."""
        query = self.db.query(TimelineEvent).filter(
            TimelineEvent.case_id == case_id
        )

        # Filter based on visibility
        if user_role == 'glaeubigerin':
            query = query.filter(TimelineEvent.visible_to_creditor == True)
        elif user_role == 'schuldner':
            query = query.filter(TimelineEvent.visible_to_debtor == True)
        # RA/Admin can see all

        return query.order_by(TimelineEvent.event_date.desc()).limit(limit).all()

    # =========================================================================
    # SEARCH
    # =========================================================================

    def search_cases(
        self,
        organization_id: UUID,
        search_term: str,
        include_ocr: bool = True
    ) -> List[Case]:
        """
        Search cases by various criteria including OCR text.
        """
        search_pattern = f"%{search_term}%"

        # Base query
        query = self.db.query(Case).filter(
            Case.organization_id == organization_id,
            Case.is_deleted == False
        )

        # Search in case fields
        case_conditions = [
            Case.internal_number.ilike(search_pattern),
            Case.external_number.ilike(search_pattern),
            Case.court_file_number.ilike(search_pattern),
            Case.creditor_name.ilike(search_pattern),
            Case.debtor_name.ilike(search_pattern),
            Case.subject.ilike(search_pattern),
            Case.description.ilike(search_pattern),
        ]

        if include_ocr:
            # Get case IDs from document OCR text matches
            doc_case_ids = self.db.query(Document.case_id).filter(
                Document.case_id.isnot(None),
                Document.is_deleted == False,
                Document.ocr_text.ilike(search_pattern)
            ).distinct().subquery()

            case_conditions.append(Case.id.in_(doc_case_ids))

        return query.filter(or_(*case_conditions)).all()

    # =========================================================================
    # AUDIT LOGGING
    # =========================================================================

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
