"""
Case Service - Business logic for case management
"""
from typing import List, Optional, Dict, Any
from datetime import date, datetime
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, func

from src.models.case import Case, Party, CaseParty
from src.models.claim import Claim, LedgerBooking
from src.database.connection import get_db_session
from src.database.cache import get_cache, cached


class CaseService:
    """Service for case-related operations."""

    @staticmethod
    def create_case(
        organization_id: str,
        case_number: str,
        creditor_name: str,
        debtor_name: str,
        principal_amount: float,
        **kwargs
    ) -> Case:
        """Create a new case with parties."""
        with get_db_session() as session:
            # Create case
            case = Case(
                organization_id=organization_id,
                case_number=case_number,
                status='offen',
                dunning_status='nicht_beantragt',
                enforcement_status='nicht_begonnen',
                **kwargs
            )
            session.add(case)
            session.flush()  # Get case ID

            # Create creditor party
            creditor = Party(
                organization_id=organization_id,
                party_type='creditor',
                name=creditor_name,
                address=kwargs.get('creditor_address', '')
            )
            session.add(creditor)
            session.flush()

            # Link creditor to case
            case_creditor = CaseParty(
                case_id=case.id,
                party_id=creditor.id,
                role='creditor'
            )
            session.add(case_creditor)

            # Create debtor party
            debtor = Party(
                organization_id=organization_id,
                party_type='debtor',
                name=debtor_name,
                address=kwargs.get('debtor_address', '')
            )
            session.add(debtor)
            session.flush()

            # Link debtor to case
            case_debtor = CaseParty(
                case_id=case.id,
                party_id=debtor.id,
                role='debtor'
            )
            session.add(case_debtor)

            # Create main claim
            claim = Claim(
                case_id=case.id,
                claim_type='hauptforderung',
                principal_amount=principal_amount,
                interest_rate=kwargs.get('interest_rate', 5.0),
                due_date=kwargs.get('due_date', date.today()),
                description=kwargs.get('subject', 'Hauptforderung')
            )
            session.add(claim)

            # Invalidate cache
            get_cache().clear_namespace("cases")

            return case

    @staticmethod
    def get_case(case_id: str) -> Optional[Dict[str, Any]]:
        """Get case by ID with caching."""
        cache = get_cache()

        # Try cache first
        cached = cache.get_cached_case(case_id)
        if cached:
            return cached

        with get_db_session() as session:
            case = session.query(Case).filter(Case.id == case_id).first()
            if not case:
                return None

            case_dict = CaseService._case_to_dict(case, session)

            # Cache result
            cache.cache_case(case_id, case_dict)
            return case_dict

    @staticmethod
    def get_all_cases(
        organization_id: Optional[str] = None,
        status: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get all cases with optional filtering."""
        with get_db_session() as session:
            query = session.query(Case)

            if organization_id:
                query = query.filter(Case.organization_id == organization_id)

            if status:
                query = query.filter(Case.status == status)

            if search:
                search_term = f"%{search}%"
                query = query.filter(
                    or_(
                        Case.case_number.ilike(search_term),
                        Case.subject.ilike(search_term)
                    )
                )

            query = query.order_by(Case.created_at.desc())
            query = query.limit(limit).offset(offset)

            cases = query.all()
            return [CaseService._case_to_dict(c, session) for c in cases]

    @staticmethod
    def update_case(case_id: str, **updates) -> Optional[Dict[str, Any]]:
        """Update case fields."""
        with get_db_session() as session:
            case = session.query(Case).filter(Case.id == case_id).first()
            if not case:
                return None

            for key, value in updates.items():
                if hasattr(case, key):
                    setattr(case, key, value)

            # Invalidate cache
            get_cache().invalidate_case(case_id)

            return CaseService._case_to_dict(case, session)

    @staticmethod
    def update_status(case_id: str, status: str) -> bool:
        """Update case status."""
        with get_db_session() as session:
            case = session.query(Case).filter(Case.id == case_id).first()
            if not case:
                return False

            case.status = status
            get_cache().invalidate_case(case_id)
            return True

    @staticmethod
    def get_case_statistics(organization_id: Optional[str] = None) -> Dict[str, Any]:
        """Get case statistics."""
        with get_db_session() as session:
            query = session.query(Case)

            if organization_id:
                query = query.filter(Case.organization_id == organization_id)

            total = query.count()

            status_counts = {}
            for status in ['offen', 'mahnverfahren', 'vollstreckung', 'ratenzahlung', 'abgeschlossen']:
                status_counts[status] = query.filter(Case.status == status).count()

            # Calculate totals (would need to join with claims in real implementation)
            return {
                'total_cases': total,
                'by_status': status_counts,
                'total_principal': 0,  # Would need claim aggregation
                'total_collected': 0
            }

    @staticmethod
    def add_booking(
        case_id: str,
        booking_date: date,
        booking_type: str,  # 'S' for Soll, 'H' for Haben
        amount: float,
        category: str,
        description: str
    ) -> bool:
        """Add a booking to the case ledger."""
        with get_db_session() as session:
            # Get the main claim for this case
            claim = session.query(Claim).filter(
                Claim.case_id == case_id,
                Claim.claim_type == 'hauptforderung'
            ).first()

            if not claim:
                return False

            booking = LedgerBooking(
                claim_id=claim.id,
                booking_date=booking_date,
                booking_type=booking_type,
                amount=amount,
                category=category,
                description=description
            )
            session.add(booking)

            # Update claim balance
            if booking_type == 'S':
                claim.current_balance += amount
            else:
                claim.current_balance -= amount

            get_cache().invalidate_case(case_id)
            return True

    @staticmethod
    def get_bookings(case_id: str) -> List[Dict[str, Any]]:
        """Get all bookings for a case."""
        with get_db_session() as session:
            bookings = session.query(LedgerBooking).join(Claim).filter(
                Claim.case_id == case_id
            ).order_by(LedgerBooking.booking_date).all()

            return [
                {
                    'id': str(b.id),
                    'date': b.booking_date,
                    'type': b.booking_type,
                    'amount': float(b.amount),
                    'category': b.category,
                    'description': b.description
                }
                for b in bookings
            ]

    @staticmethod
    def _case_to_dict(case: Case, session: Session) -> Dict[str, Any]:
        """Convert case model to dictionary."""
        # Get parties
        creditor = None
        debtor = None

        case_parties = session.query(CaseParty).filter(CaseParty.case_id == case.id).all()
        for cp in case_parties:
            party = session.query(Party).filter(Party.id == cp.party_id).first()
            if party:
                if cp.role == 'creditor':
                    creditor = party
                elif cp.role == 'debtor':
                    debtor = party

        # Get main claim
        claim = session.query(Claim).filter(
            Claim.case_id == case.id,
            Claim.claim_type == 'hauptforderung'
        ).first()

        return {
            'id': str(case.id),
            'nr': case.case_number,
            'creditor': creditor.name if creditor else 'Unbekannt',
            'creditor_address': creditor.address if creditor else '',
            'debtor': debtor.name if debtor else 'Unbekannt',
            'debtor_address': debtor.address if debtor else '',
            'subject': case.subject or '',
            'status': case.status,
            'dunning': case.dunning_status,
            'enforcement': case.enforcement_status,
            'principal': float(claim.principal_amount) if claim else 0,
            'interest': float(claim.interest_rate) if claim else 5.0,
            'due_date': claim.due_date if claim else date.today(),
            'created': case.created_at,
            'imported': case.source == 'import'
        }


# Convenience functions for use without instantiation
def get_all_cases(**kwargs) -> List[Dict[str, Any]]:
    """Get all cases."""
    return CaseService.get_all_cases(**kwargs)


def get_case(case_id: str) -> Optional[Dict[str, Any]]:
    """Get single case."""
    return CaseService.get_case(case_id)


def create_case(**kwargs) -> Case:
    """Create new case."""
    return CaseService.create_case(**kwargs)
