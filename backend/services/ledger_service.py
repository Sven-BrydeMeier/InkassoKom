"""
Ledger Service - Forderungskonto Management
Handles all booking operations with proper payment allocation
"""
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from uuid import UUID
from decimal import Decimal

from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from db.models import (
    Case, Claim, LedgerBooking, User, TimelineEvent, AuditLog
)
from config.settings import BookingCategory, PaymentStatus


class LedgerService:
    """
    Service for managing the Forderungskonto (ledger).

    Payment allocation order (as per German debt collection law):
    1. Zinsen (Interest)
    2. RA-Gebühren (Lawyer fees)
    3. Nebenkosten (Additional costs)
    4. Gerichtskosten (Court costs)
    5. Vollstreckungskosten (Enforcement costs)
    6. Hauptforderung (Principal)
    """

    ALLOCATION_ORDER = [
        BookingCategory.ZINSEN,
        BookingCategory.RA_GEBUEHREN,
        BookingCategory.NEBENKOSTEN,
        BookingCategory.GERICHTSKOSTEN,
        BookingCategory.VOLLSTRECKUNGSKOSTEN,
        BookingCategory.HAUPTFORDERUNG,
    ]

    def __init__(self, db: Session):
        self.db = db

    # =========================================================================
    # BOOKING CRUD
    # =========================================================================

    def create_booking(
        self,
        case_id: UUID,
        booking_date: date,
        debit_credit: str,
        amount: Decimal,
        category: str,
        description: str,
        source: str,
        created_by: UUID,
        claim_id: Optional[UUID] = None,
        value_date: Optional[date] = None,
        reference: Optional[str] = None,
        status: str = PaymentStatus.VERBUCHT,
        document_id: Optional[UUID] = None
    ) -> LedgerBooking:
        """Create a new ledger booking."""
        if debit_credit not in ['S', 'H']:
            raise ValueError("debit_credit must be 'S' (Soll) or 'H' (Haben)")

        if amount <= 0:
            raise ValueError("Amount must be positive")

        booking = LedgerBooking(
            case_id=case_id,
            claim_id=claim_id,
            booking_date=booking_date,
            value_date=value_date or booking_date,
            debit_credit=debit_credit,
            amount=amount,
            category=category,
            description=description,
            reference=reference,
            source=source,
            source_user_id=created_by,
            status=status,
            document_id=document_id,
            created_by=created_by
        )

        self.db.add(booking)
        self.db.commit()
        self.db.refresh(booking)

        # Create timeline event for significant bookings
        if status == PaymentStatus.VERBUCHT:
            self._create_booking_timeline_event(booking, created_by)

        self._log_audit(
            action="create",
            resource_type="booking",
            resource_id=booking.id,
            user_id=created_by,
            case_id=case_id,
            description=f"Booking created: {debit_credit} {amount}€ - {category}"
        )

        return booking

    def report_payment(
        self,
        case_id: UUID,
        payment_date: date,
        amount: Decimal,
        reference: str,
        reported_by: UUID,
        description: Optional[str] = None
    ) -> LedgerBooking:
        """
        Report a payment (from creditor).
        Status: 'gemeldet' - needs approval from lawyer.
        """
        booking = LedgerBooking(
            case_id=case_id,
            booking_date=payment_date,
            value_date=payment_date,
            debit_credit='H',  # Haben = payment/credit
            amount=amount,
            category=BookingCategory.HAUPTFORDERUNG,  # Will be allocated on approval
            description=description or f"Zahlungseingang gemeldet: {reference}",
            reference=reference,
            source='glaeubiger',
            source_user_id=reported_by,
            status=PaymentStatus.GEMELDET,
            reported_at=datetime.utcnow(),
            created_by=reported_by
        )

        self.db.add(booking)
        self.db.commit()
        self.db.refresh(booking)

        # Create timeline event
        self._create_timeline_event(
            case_id=case_id,
            event_type="payment_reported",
            title="Zahlungseingang gemeldet",
            description=f"Gläubigerin hat Zahlungseingang über {amount}€ gemeldet (Referenz: {reference})",
            category="zahlung",
            actor_id=reported_by,
            reference_type="booking",
            reference_id=booking.id,
            visible_to_creditor=True,
            visible_to_debtor=False,
            severity="info"
        )

        return booking

    def approve_payment(
        self,
        booking_id: UUID,
        approved_by: UUID,
        allocate: bool = True
    ) -> LedgerBooking:
        """
        Approve a reported payment and optionally allocate it.
        Changes status from 'gemeldet' to 'akzeptiert' then 'verbucht'.
        """
        booking = self.db.query(LedgerBooking).filter(
            LedgerBooking.id == booking_id
        ).first()

        if not booking:
            raise ValueError("Booking not found")

        if booking.status != PaymentStatus.GEMELDET:
            raise ValueError("Booking is not in 'gemeldet' status")

        booking.status = PaymentStatus.AKZEPTIERT
        booking.accepted_at = datetime.utcnow()
        booking.accepted_by = approved_by

        self.db.commit()

        if allocate:
            # Allocate the payment according to the allocation order
            self._allocate_payment(booking, approved_by)

        booking.status = PaymentStatus.VERBUCHT
        self.db.commit()
        self.db.refresh(booking)

        # Create timeline event
        self._create_timeline_event(
            case_id=booking.case_id,
            event_type="payment_approved",
            title="Zahlungseingang bestätigt",
            description=f"Zahlungseingang über {booking.amount}€ wurde bestätigt und verbucht",
            category="zahlung",
            actor_id=approved_by,
            reference_type="booking",
            reference_id=booking.id,
            visible_to_creditor=True,
            visible_to_debtor=True,
            severity="success"
        )

        self._log_audit(
            action="approve",
            resource_type="booking",
            resource_id=booking.id,
            user_id=approved_by,
            case_id=booking.case_id,
            description=f"Payment approved: {booking.amount}€"
        )

        return booking

    def reject_payment(
        self,
        booking_id: UUID,
        rejected_by: UUID,
        reason: str
    ) -> LedgerBooking:
        """Reject a reported payment."""
        booking = self.db.query(LedgerBooking).filter(
            LedgerBooking.id == booking_id
        ).first()

        if not booking:
            raise ValueError("Booking not found")

        if booking.status != PaymentStatus.GEMELDET:
            raise ValueError("Booking is not in 'gemeldet' status")

        booking.status = PaymentStatus.ABGELEHNT
        booking.rejection_reason = reason
        booking.updated_by = rejected_by

        self.db.commit()
        self.db.refresh(booking)

        # Create timeline event
        self._create_timeline_event(
            case_id=booking.case_id,
            event_type="payment_rejected",
            title="Zahlungseingang abgelehnt",
            description=f"Zahlungseingang über {booking.amount}€ wurde abgelehnt: {reason}",
            category="zahlung",
            actor_id=rejected_by,
            reference_type="booking",
            reference_id=booking.id,
            visible_to_creditor=True,
            visible_to_debtor=False,
            severity="warning"
        )

        return booking

    def _allocate_payment(self, booking: LedgerBooking, allocated_by: UUID):
        """
        Allocate a payment according to German debt collection allocation rules.
        Order: Zinsen -> RA-Gebühren -> Nebenkosten -> Gerichtskosten ->
               Vollstreckungskosten -> Hauptforderung
        """
        remaining_amount = booking.amount
        allocations = []

        for category in self.ALLOCATION_ORDER:
            if remaining_amount <= 0:
                break

            # Get open amount for this category
            open_amount = self._get_open_amount_for_category(booking.case_id, category)

            if open_amount > 0:
                allocation = min(remaining_amount, open_amount)
                allocations.append((category, allocation))
                remaining_amount -= allocation

        # Update the booking with allocation details
        booking.metadata = {
            "allocations": [
                {"category": cat, "amount": float(amt)}
                for cat, amt in allocations
            ],
            "allocated_by": str(allocated_by),
            "allocated_at": datetime.utcnow().isoformat()
        }

        self.db.commit()

    def _get_open_amount_for_category(self, case_id: UUID, category: str) -> Decimal:
        """Get the open (unpaid) amount for a specific category."""
        result = self.db.query(
            func.coalesce(func.sum(
                func.case(
                    (LedgerBooking.debit_credit == 'S', LedgerBooking.amount),
                    else_=-LedgerBooking.amount
                )
            ), 0)
        ).filter(
            LedgerBooking.case_id == case_id,
            LedgerBooking.category == category,
            LedgerBooking.status == PaymentStatus.VERBUCHT
        ).scalar()

        return Decimal(str(result)) if result else Decimal('0')

    # =========================================================================
    # BALANCE CALCULATIONS
    # =========================================================================

    def get_case_balance(self, case_id: UUID) -> Dict[str, Any]:
        """
        Get the current balance breakdown for a case.
        Returns amounts by category and total.
        """
        bookings = self.db.query(LedgerBooking).filter(
            LedgerBooking.case_id == case_id,
            LedgerBooking.status == PaymentStatus.VERBUCHT
        ).all()

        balance_by_category = {}
        total_soll = Decimal('0')
        total_haben = Decimal('0')

        for booking in bookings:
            category = booking.category
            if category not in balance_by_category:
                balance_by_category[category] = Decimal('0')

            if booking.debit_credit == 'S':
                balance_by_category[category] += booking.amount
                total_soll += booking.amount
            else:
                balance_by_category[category] -= booking.amount
                total_haben += booking.amount

        # Ensure non-negative balances
        for cat in balance_by_category:
            if balance_by_category[cat] < 0:
                balance_by_category[cat] = Decimal('0')

        total_open = total_soll - total_haben
        if total_open < 0:
            total_open = Decimal('0')

        return {
            "by_category": {k: float(v) for k, v in balance_by_category.items()},
            "total_principal": float(balance_by_category.get(BookingCategory.HAUPTFORDERUNG, Decimal('0'))),
            "total_interest": float(balance_by_category.get(BookingCategory.ZINSEN, Decimal('0'))),
            "total_lawyer_fees": float(balance_by_category.get(BookingCategory.RA_GEBUEHREN, Decimal('0'))),
            "total_costs": float(
                balance_by_category.get(BookingCategory.NEBENKOSTEN, Decimal('0')) +
                balance_by_category.get(BookingCategory.GERICHTSKOSTEN, Decimal('0')) +
                balance_by_category.get(BookingCategory.VOLLSTRECKUNGSKOSTEN, Decimal('0'))
            ),
            "total_soll": float(total_soll),
            "total_haben": float(total_haben),
            "total_open": float(total_open),
            "is_paid": total_open <= 0
        }

    def get_bookings_for_case(
        self,
        case_id: UUID,
        status: Optional[str] = None,
        category: Optional[str] = None
    ) -> List[LedgerBooking]:
        """Get all bookings for a case with optional filters."""
        query = self.db.query(LedgerBooking).filter(
            LedgerBooking.case_id == case_id
        )

        if status:
            query = query.filter(LedgerBooking.status == status)

        if category:
            query = query.filter(LedgerBooking.category == category)

        return query.order_by(LedgerBooking.booking_date.desc()).all()

    def get_pending_payments(self, organization_id: UUID) -> List[LedgerBooking]:
        """Get all pending (reported) payments for an organization."""
        return self.db.query(LedgerBooking).join(Case).filter(
            Case.organization_id == organization_id,
            LedgerBooking.status == PaymentStatus.GEMELDET
        ).order_by(LedgerBooking.reported_at.desc()).all()

    # =========================================================================
    # INTEREST CALCULATION
    # =========================================================================

    def calculate_interest(
        self,
        case_id: UUID,
        as_of_date: date,
        create_booking: bool = False,
        created_by: Optional[UUID] = None
    ) -> Dict[str, Any]:
        """
        Calculate interest for all claims in a case up to a specific date.
        Uses the interest rate from each claim.
        """
        from db.models import Claim

        claims = self.db.query(Claim).filter(Claim.case_id == case_id).all()
        total_interest = Decimal('0')
        interest_details = []

        for claim in claims:
            if not claim.interest_rate or not claim.interest_start_date:
                continue

            # Get principal balance for this claim
            principal_balance = claim.principal_amount

            # Calculate days
            if claim.interest_start_date > as_of_date:
                continue

            days = (as_of_date - claim.interest_start_date).days

            # Simple interest calculation: P * r * t / 365
            daily_rate = claim.interest_rate / Decimal('100') / Decimal('365')
            interest = principal_balance * daily_rate * Decimal(days)

            total_interest += interest
            interest_details.append({
                "claim_id": str(claim.id),
                "claim_description": claim.description,
                "principal": float(claim.principal_amount),
                "rate": float(claim.interest_rate),
                "start_date": claim.interest_start_date.isoformat(),
                "days": days,
                "interest": float(interest)
            })

        result = {
            "as_of_date": as_of_date.isoformat(),
            "total_interest": float(total_interest),
            "details": interest_details
        }

        if create_booking and total_interest > 0 and created_by:
            # Check if interest booking already exists for this date
            existing = self.db.query(LedgerBooking).filter(
                LedgerBooking.case_id == case_id,
                LedgerBooking.category == BookingCategory.ZINSEN,
                LedgerBooking.booking_date == as_of_date,
                LedgerBooking.status == PaymentStatus.VERBUCHT
            ).first()

            if not existing:
                self.create_booking(
                    case_id=case_id,
                    booking_date=as_of_date,
                    debit_credit='S',
                    amount=total_interest,
                    category=BookingCategory.ZINSEN,
                    description=f"Zinsen berechnet bis {as_of_date}",
                    source='system',
                    created_by=created_by
                )

        return result

    # =========================================================================
    # TIMELINE AND AUDIT
    # =========================================================================

    def _create_booking_timeline_event(self, booking: LedgerBooking, actor_id: UUID):
        """Create a timeline event for a booking."""
        if booking.debit_credit == 'H':
            title = "Zahlung verbucht"
            description = f"Zahlung über {booking.amount}€ verbucht"
            severity = "success"
        else:
            title = "Forderung gebucht"
            description = f"{booking.category}: {booking.amount}€"
            severity = "info"

        self._create_timeline_event(
            case_id=booking.case_id,
            event_type="booking",
            title=title,
            description=description,
            category="zahlung",
            actor_id=actor_id,
            reference_type="booking",
            reference_id=booking.id,
            visible_to_creditor=True,
            visible_to_debtor=booking.debit_credit == 'H',  # Only show payments to debtor
            severity=severity
        )

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
            severity=severity,
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
        case_id: Optional[UUID] = None,
        description: Optional[str] = None,
        old_values: Optional[Dict] = None,
        new_values: Optional[Dict] = None
    ):
        """Log an audit entry."""
        user = None
        organization_id = None

        if user_id:
            user = self.db.query(User).filter(User.id == user_id).first()

        if case_id:
            case = self.db.query(Case).filter(Case.id == case_id).first()
            if case:
                organization_id = case.organization_id

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
