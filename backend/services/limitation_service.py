"""
Limitation Service - Verjährungsmodul
Event-based statute of limitations calculation for German debt collection
"""
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any
from uuid import UUID
from decimal import Decimal
from dateutil.relativedelta import relativedelta

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from db.models import (
    Case, Claim, LimitationEvent, TimelineEvent, User, AuditLog, Notification
)
from config.settings import DunningStatus


class LimitationService:
    """
    Service for managing statute of limitations (Verjährung).

    German limitation rules:
    - Regular claims (§ 195 BGB): 3 years, starting end of year when claim arose
    - Titled claims (Vollstreckungsbescheid/Urteil): 30 years from title date
    - Limitation suspended (gehemmt) during pending dunning/court proceedings
    - Limitation restarted (Neubeginn) on debtor acknowledgment

    Events that affect limitation:
    - Fälligkeit: Start of regular limitation period
    - Mahnbescheid-Antrag: Suspension if delivered within 1 month (§ 204 Abs. 1 Nr. 3 BGB)
    - Mahnbescheid-Zustellung: Confirms suspension
    - Vollstreckungsbescheid: Creates 30-year title limitation
    - Vollstreckungshandlung: Can restart limitation
    - Anerkenntnis: Restarts limitation (Neubeginn)
    """

    # Regular limitation period in years
    REGULAR_LIMITATION_YEARS = 3

    # Title limitation period in years
    TITLE_LIMITATION_YEARS = 30

    def __init__(self, db: Session):
        self.db = db

    # =========================================================================
    # LIMITATION CALCULATION
    # =========================================================================

    def calculate_limitation_date(
        self,
        case_id: UUID,
        claim_id: Optional[UUID] = None,
        as_of_date: Optional[date] = None
    ) -> Dict[str, Any]:
        """
        Calculate the current limitation date for a claim or case.
        Returns detailed breakdown of events affecting limitation.
        """
        as_of = as_of_date or date.today()

        if claim_id:
            claim = self.db.query(Claim).filter(Claim.id == claim_id).first()
            if not claim:
                return {"error": "Claim not found"}
            claims = [claim]
        else:
            claims = self.db.query(Claim).filter(Claim.case_id == case_id).all()

        results = []

        for claim in claims:
            result = self._calculate_claim_limitation(claim, case_id, as_of)
            results.append(result)

        # Find the earliest limitation date across all claims
        earliest_date = None
        for r in results:
            if r.get("limitation_date"):
                ld = r["limitation_date"]
                if earliest_date is None or ld < earliest_date:
                    earliest_date = ld

        return {
            "case_id": str(case_id),
            "as_of_date": as_of.isoformat(),
            "claims": results,
            "earliest_limitation": earliest_date.isoformat() if earliest_date else None,
            "is_at_risk": self._is_at_risk(earliest_date, as_of) if earliest_date else False,
            "days_until_limitation": (earliest_date - as_of).days if earliest_date else None
        }

    def _calculate_claim_limitation(
        self,
        claim: Claim,
        case_id: UUID,
        as_of: date
    ) -> Dict[str, Any]:
        """Calculate limitation for a single claim."""
        # Get all limitation events for this claim/case
        events = self.db.query(LimitationEvent).filter(
            LimitationEvent.case_id == case_id,
            or_(
                LimitationEvent.claim_id == claim.id,
                LimitationEvent.claim_id.is_(None)
            )
        ).order_by(LimitationEvent.event_date).all()

        # Start with the due date
        due_date = claim.due_date
        if not due_date:
            return {
                "claim_id": str(claim.id),
                "description": claim.description,
                "error": "No due date set"
            }

        # Calculate regular limitation (3 years from end of year of due date)
        # § 199 Abs. 1 BGB: Frist beginnt mit Schluss des Jahres
        limitation_start = date(due_date.year, 12, 31)
        current_limitation = limitation_start + relativedelta(years=self.REGULAR_LIMITATION_YEARS)

        # Track suspension periods
        suspension_start = None
        total_suspension_days = 0
        event_log = []
        is_titled = claim.is_titled

        for event in events:
            event_log.append({
                "date": event.event_date.isoformat(),
                "type": event.event_type,
                "effect": event.effect,
                "notes": event.notes
            })

            if event.effect == 'hemmung':
                # Suspension starts
                suspension_start = event.event_date

            elif event.effect == 'hemmung_ende':
                # Suspension ends
                if suspension_start:
                    suspension_days = (event.event_date - suspension_start).days
                    total_suspension_days += suspension_days
                    suspension_start = None

            elif event.effect == 'neubeginn':
                # Limitation restarts completely
                restart_date = event.event_date
                limitation_start = date(restart_date.year, 12, 31)
                current_limitation = limitation_start + relativedelta(
                    years=self.REGULAR_LIMITATION_YEARS
                )
                total_suspension_days = 0  # Reset suspension

            elif event.effect == 'titel_30_jahre':
                # Title creates 30-year limitation
                is_titled = True
                title_date = event.event_date
                current_limitation = title_date + relativedelta(years=self.TITLE_LIMITATION_YEARS)
                total_suspension_days = 0  # Suspension doesn't apply to titled claims

            elif event.is_override:
                # Manual override
                if event.new_limitation_date:
                    current_limitation = event.new_limitation_date

        # Add suspension days to limitation date (suspension extends limitation)
        if total_suspension_days > 0 and not is_titled:
            current_limitation += timedelta(days=total_suspension_days)

        # If currently suspended, add days until today
        if suspension_start:
            ongoing_suspension = (as_of - suspension_start).days
            current_limitation += timedelta(days=ongoing_suspension)

        return {
            "claim_id": str(claim.id),
            "description": claim.description,
            "principal_amount": float(claim.principal_amount),
            "due_date": due_date.isoformat(),
            "limitation_date": current_limitation.isoformat(),
            "is_titled": is_titled,
            "is_suspended": suspension_start is not None,
            "suspension_days": total_suspension_days,
            "events": event_log,
            "is_at_risk": self._is_at_risk(current_limitation, as_of),
            "is_expired": current_limitation < as_of
        }

    def _is_at_risk(self, limitation_date: date, as_of: date) -> bool:
        """Check if limitation is approaching (within 6 months)."""
        risk_threshold = as_of + relativedelta(months=6)
        return limitation_date <= risk_threshold

    # =========================================================================
    # LIMITATION EVENTS
    # =========================================================================

    def add_limitation_event(
        self,
        case_id: UUID,
        event_type: str,
        event_date: date,
        effect: str,
        created_by: UUID,
        claim_id: Optional[UUID] = None,
        notes: Optional[str] = None,
        reference_type: Optional[str] = None,
        reference_id: Optional[UUID] = None
    ) -> LimitationEvent:
        """
        Add a limitation event.

        Event types:
        - faelligkeit: Original due date
        - mahnung: Demand letter
        - klage: Court action
        - mahnbescheid_antrag: Dunning order application
        - mahnbescheid_zustellung: Dunning order delivery
        - vollstreckungsbescheid: Enforcement order
        - titel: Other title (judgment, settlement)
        - hemmung_start: Start of suspension
        - hemmung_ende: End of suspension
        - neubeginn: Restart of limitation
        - anerkenntnis: Debtor acknowledgment
        - override: Manual override

        Effects:
        - hemmung: Suspension of limitation
        - hemmung_ende: End of suspension
        - neubeginn: Restart limitation period
        - titel_30_jahre: Create 30-year title limitation
        - custom: Manual adjustment
        """
        # Calculate new limitation date after this event
        existing = self.calculate_limitation_date(case_id, claim_id, event_date)

        event = LimitationEvent(
            case_id=case_id,
            claim_id=claim_id,
            event_type=event_type,
            event_date=event_date,
            effect=effect,
            notes=notes,
            reference_type=reference_type,
            reference_id=reference_id
        )

        self.db.add(event)
        self.db.commit()
        self.db.refresh(event)

        # Recalculate and store new limitation date
        new_calculation = self.calculate_limitation_date(case_id, claim_id)

        # Update claim if titled
        if effect == 'titel_30_jahre' and claim_id:
            claim = self.db.query(Claim).filter(Claim.id == claim_id).first()
            if claim:
                claim.is_titled = True
                claim.title_date = event_date
                self.db.commit()

        # Create timeline event
        self._create_timeline_event(
            case_id=case_id,
            event_type="limitation_event",
            title="Verjährungsereignis",
            description=f"{event_type}: {notes}" if notes else event_type,
            category="verjaehrung",
            actor_id=created_by,
            reference_type="limitation_event",
            reference_id=event.id,
            visible_to_creditor=True,
            visible_to_debtor=False
        )

        self._log_audit(
            action="create",
            resource_type="limitation_event",
            resource_id=event.id,
            user_id=created_by,
            case_id=case_id,
            description=f"Limitation event: {event_type} - {effect}"
        )

        return event

    def add_override(
        self,
        case_id: UUID,
        new_limitation_date: date,
        reason: str,
        created_by: UUID,
        claim_id: Optional[UUID] = None
    ) -> LimitationEvent:
        """Add a manual override for limitation date."""
        event = LimitationEvent(
            case_id=case_id,
            claim_id=claim_id,
            event_type="override",
            event_date=date.today(),
            effect="custom",
            new_limitation_date=new_limitation_date,
            is_override=True,
            override_reason=reason
        )

        self.db.add(event)
        self.db.commit()
        self.db.refresh(event)

        self._log_audit(
            action="override",
            resource_type="limitation_event",
            resource_id=event.id,
            user_id=created_by,
            case_id=case_id,
            description=f"Limitation override: new date {new_limitation_date}, reason: {reason}"
        )

        return event

    # =========================================================================
    # DUNNING PROCEDURE INTEGRATION
    # =========================================================================

    def record_dunning_application(
        self,
        case_id: UUID,
        application_date: date,
        created_by: UUID,
        claim_id: Optional[UUID] = None
    ):
        """Record MB application - starts potential suspension."""
        # MB application creates suspension if delivered within 1 month
        return self.add_limitation_event(
            case_id=case_id,
            claim_id=claim_id,
            event_type="mahnbescheid_antrag",
            event_date=application_date,
            effect="hemmung",  # Provisional suspension
            created_by=created_by,
            notes="Mahnbescheid-Antrag eingereicht"
        )

    def record_dunning_delivery(
        self,
        case_id: UUID,
        delivery_date: date,
        created_by: UUID,
        claim_id: Optional[UUID] = None
    ):
        """Record MB delivery - confirms suspension."""
        return self.add_limitation_event(
            case_id=case_id,
            claim_id=claim_id,
            event_type="mahnbescheid_zustellung",
            event_date=delivery_date,
            effect="hemmung",
            created_by=created_by,
            notes="Mahnbescheid zugestellt - Verjährung gehemmt"
        )

    def record_enforcement_order(
        self,
        case_id: UUID,
        order_date: date,
        created_by: UUID,
        claim_id: Optional[UUID] = None
    ):
        """Record VB - creates 30-year title limitation."""
        return self.add_limitation_event(
            case_id=case_id,
            claim_id=claim_id,
            event_type="vollstreckungsbescheid",
            event_date=order_date,
            effect="titel_30_jahre",
            created_by=created_by,
            notes="Vollstreckungsbescheid erlassen - 30-jährige Titelverjährung"
        )

    # =========================================================================
    # AUTOMATIC CHECKS
    # =========================================================================

    def check_all_cases_limitation(
        self,
        organization_id: UUID,
        warning_months: int = 6
    ) -> List[Dict[str, Any]]:
        """
        Check all cases for approaching limitation.
        Used for daily/monthly batch checks.
        """
        cases = self.db.query(Case).filter(
            Case.organization_id == organization_id,
            Case.is_deleted == False,
            Case.status.notin_(['abgeschlossen', 'uneinbringlich'])
        ).all()

        warnings = []
        today = date.today()
        warning_date = today + relativedelta(months=warning_months)

        for case in cases:
            result = self.calculate_limitation_date(case.id, as_of_date=today)

            if result.get("earliest_limitation"):
                earliest = date.fromisoformat(result["earliest_limitation"])

                if earliest <= warning_date:
                    days_left = (earliest - today).days
                    severity = "critical" if days_left <= 30 else "warning"

                    warning = {
                        "case_id": str(case.id),
                        "internal_number": case.internal_number,
                        "creditor_name": case.creditor_name,
                        "debtor_name": case.debtor_name,
                        "limitation_date": earliest.isoformat(),
                        "days_remaining": days_left,
                        "severity": severity,
                        "is_titled": any(
                            c.get("is_titled") for c in result.get("claims", [])
                        )
                    }
                    warnings.append(warning)

        # Sort by days remaining (most urgent first)
        warnings.sort(key=lambda x: x["days_remaining"])

        return warnings

    def run_december_check(self, organization_id: UUID) -> List[Dict[str, Any]]:
        """
        Special December check for year-end limitation.
        Regular limitation periods end at year's end.
        """
        today = date.today()
        year_end = date(today.year, 12, 31)

        # Check all cases for limitation ending this year
        cases = self.db.query(Case).filter(
            Case.organization_id == organization_id,
            Case.is_deleted == False,
            Case.status.notin_(['abgeschlossen', 'uneinbringlich'])
        ).all()

        critical_cases = []

        for case in cases:
            result = self.calculate_limitation_date(case.id, as_of_date=today)

            for claim_result in result.get("claims", []):
                if claim_result.get("limitation_date"):
                    lim_date = date.fromisoformat(claim_result["limitation_date"])

                    if lim_date <= year_end:
                        critical_cases.append({
                            "case_id": str(case.id),
                            "internal_number": case.internal_number,
                            "creditor_name": case.creditor_name,
                            "debtor_name": case.debtor_name,
                            "claim_id": claim_result.get("claim_id"),
                            "claim_description": claim_result.get("description"),
                            "limitation_date": claim_result["limitation_date"],
                            "is_titled": claim_result.get("is_titled", False),
                            "action_required": "DRINGEND: Verjährung droht zum Jahresende!"
                        })

        return critical_cases

    def create_limitation_notifications(
        self,
        organization_id: UUID,
        lawyer_user_id: UUID
    ) -> int:
        """Create notifications for approaching limitations."""
        warnings = self.check_all_cases_limitation(organization_id)
        notifications_created = 0

        for warning in warnings:
            # Check if notification already exists for today
            existing = self.db.query(Notification).filter(
                Notification.user_id == lawyer_user_id,
                Notification.category == 'deadline',
                Notification.reference_type == 'limitation',
                Notification.case_id == UUID(warning["case_id"]),
                Notification.created_at >= datetime.combine(date.today(), datetime.min.time())
            ).first()

            if not existing:
                severity = "error" if warning["severity"] == "critical" else "warning"

                notification = Notification(
                    user_id=lawyer_user_id,
                    title=f"Verjährungswarnung: {warning['internal_number']}",
                    message=f"Akte {warning['internal_number']} ({warning['debtor_name']}): "
                            f"Verjährung in {warning['days_remaining']} Tagen "
                            f"({warning['limitation_date']})",
                    notification_type=severity,
                    category='deadline',
                    reference_type='limitation',
                    case_id=UUID(warning["case_id"])
                )

                self.db.add(notification)
                notifications_created += 1

        self.db.commit()
        return notifications_created

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
        case_id: Optional[UUID] = None,
        description: Optional[str] = None
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
            case_id=case_id
        )

        self.db.add(log)
