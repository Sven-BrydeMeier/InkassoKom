"""
Notification Service - Email and In-App Notifications
Handles reminders, alerts, and communication
"""
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from db.models import (
    Notification, User, Case, PaymentPlan, PaymentPlanInstallment,
    Deadline, TimelineEvent
)
from config.settings import settings


class NotificationService:
    """
    Service for managing notifications and sending emails.

    Notification types:
    - Payment reminders (1 day before due)
    - Overdue payment alerts
    - Approval requests
    - Deadline warnings
    - Limitation warnings
    - Case status updates
    """

    def __init__(self, db: Session):
        self.db = db

    # =========================================================================
    # IN-APP NOTIFICATIONS
    # =========================================================================

    def create_notification(
        self,
        user_id: UUID,
        title: str,
        message: str,
        notification_type: str = "info",
        category: str = "system",
        case_id: Optional[UUID] = None,
        reference_type: Optional[str] = None,
        reference_id: Optional[UUID] = None,
        send_email: bool = False
    ) -> Notification:
        """Create a new notification."""
        notification = Notification(
            user_id=user_id,
            title=title,
            message=message,
            notification_type=notification_type,
            category=category,
            case_id=case_id,
            reference_type=reference_type,
            reference_id=reference_id
        )

        self.db.add(notification)
        self.db.commit()
        self.db.refresh(notification)

        if send_email:
            self._queue_email_notification(notification)

        return notification

    def get_unread_notifications(
        self,
        user_id: UUID,
        limit: int = 50
    ) -> List[Notification]:
        """Get unread notifications for a user."""
        return self.db.query(Notification).filter(
            Notification.user_id == user_id,
            Notification.is_read == False
        ).order_by(Notification.created_at.desc()).limit(limit).all()

    def get_notifications(
        self,
        user_id: UUID,
        include_read: bool = True,
        category: Optional[str] = None,
        limit: int = 100
    ) -> List[Notification]:
        """Get notifications for a user."""
        query = self.db.query(Notification).filter(
            Notification.user_id == user_id
        )

        if not include_read:
            query = query.filter(Notification.is_read == False)

        if category:
            query = query.filter(Notification.category == category)

        return query.order_by(Notification.created_at.desc()).limit(limit).all()

    def mark_as_read(self, notification_id: UUID) -> bool:
        """Mark a notification as read."""
        notification = self.db.query(Notification).filter(
            Notification.id == notification_id
        ).first()

        if notification:
            notification.is_read = True
            notification.read_at = datetime.utcnow()
            self.db.commit()
            return True

        return False

    def mark_all_as_read(self, user_id: UUID) -> int:
        """Mark all notifications as read for a user."""
        updated = self.db.query(Notification).filter(
            Notification.user_id == user_id,
            Notification.is_read == False
        ).update({
            Notification.is_read: True,
            Notification.read_at: datetime.utcnow()
        })

        self.db.commit()
        return updated

    def get_notification_count(self, user_id: UUID) -> Dict[str, int]:
        """Get notification counts for a user."""
        total = self.db.query(Notification).filter(
            Notification.user_id == user_id
        ).count()

        unread = self.db.query(Notification).filter(
            Notification.user_id == user_id,
            Notification.is_read == False
        ).count()

        return {
            "total": total,
            "unread": unread
        }

    # =========================================================================
    # PAYMENT PLAN REMINDERS
    # =========================================================================

    def send_payment_reminders(self) -> int:
        """
        Send payment reminders for installments due tomorrow.
        Called by scheduled job (daily).
        """
        tomorrow = date.today() + timedelta(days=1)

        # Get installments due tomorrow that haven't been reminded
        installments = self.db.query(PaymentPlanInstallment).join(PaymentPlan).join(Case).filter(
            PaymentPlanInstallment.due_date == tomorrow,
            PaymentPlanInstallment.status == 'pending',
            PaymentPlanInstallment.reminder_sent_at.is_(None),
            PaymentPlan.status == 'aktiv'
        ).all()

        sent_count = 0

        for installment in installments:
            payment_plan = installment.payment_plan
            case = payment_plan.case

            if case.debtor_user_id:
                debtor = self.db.query(User).filter(User.id == case.debtor_user_id).first()

                if debtor:
                    # Create in-app notification
                    self.create_notification(
                        user_id=debtor.id,
                        title="Zahlungserinnerung",
                        message=f"Rate {installment.installment_number} über {installment.amount}€ "
                                f"ist morgen ({installment.due_date.strftime('%d.%m.%Y')}) fällig.",
                        notification_type="warning",
                        category="payment",
                        case_id=case.id,
                        reference_type="installment",
                        reference_id=installment.id,
                        send_email=debtor.notification_preferences.get('email_reminders', True)
                    )

                    installment.reminder_sent_at = datetime.utcnow()
                    sent_count += 1

        self.db.commit()
        return sent_count

    def send_overdue_reminders(self) -> int:
        """
        Send reminders for overdue installments.
        Called by scheduled job (daily).
        """
        today = date.today()

        # Get overdue installments
        installments = self.db.query(PaymentPlanInstallment).join(PaymentPlan).join(Case).filter(
            PaymentPlanInstallment.due_date < today,
            PaymentPlanInstallment.status == 'pending',
            PaymentPlanInstallment.overdue_reminder_sent_at.is_(None),
            PaymentPlan.status == 'aktiv'
        ).all()

        sent_count = 0

        for installment in installments:
            payment_plan = installment.payment_plan
            case = payment_plan.case
            days_overdue = (today - installment.due_date).days

            # Update status to overdue
            installment.status = 'overdue'

            # Notify debtor
            if case.debtor_user_id:
                debtor = self.db.query(User).filter(User.id == case.debtor_user_id).first()
                if debtor:
                    self.create_notification(
                        user_id=debtor.id,
                        title="Überfällige Zahlung",
                        message=f"Rate {installment.installment_number} über {installment.amount}€ "
                                f"ist seit {days_overdue} Tag(en) überfällig!",
                        notification_type="error",
                        category="payment",
                        case_id=case.id,
                        reference_type="installment",
                        reference_id=installment.id,
                        send_email=True
                    )

            # Notify lawyer
            if case.assigned_lawyer_id:
                self.create_notification(
                    user_id=case.assigned_lawyer_id,
                    title=f"Überfällige Rate: {case.internal_number}",
                    message=f"Rate {installment.installment_number} über {installment.amount}€ "
                            f"ist seit {days_overdue} Tag(en) überfällig. Schuldner: {case.debtor_name}",
                    notification_type="error",
                    category="payment",
                    case_id=case.id,
                    reference_type="installment",
                    reference_id=installment.id
                )

            # Check if payment plan should be marked as delayed
            if days_overdue >= 14:
                payment_plan.status = 'verzoegert'

            installment.overdue_reminder_sent_at = datetime.utcnow()
            sent_count += 1

        self.db.commit()
        return sent_count

    # =========================================================================
    # DEADLINE REMINDERS
    # =========================================================================

    def send_deadline_reminders(self) -> int:
        """Send reminders for upcoming deadlines."""
        tomorrow = date.today() + timedelta(days=1)
        next_week = date.today() + timedelta(days=7)

        # Get deadlines due within next week
        deadlines = self.db.query(Deadline).join(Case).filter(
            Deadline.due_date <= next_week,
            Deadline.due_date >= date.today(),
            Deadline.status == 'active',
            Deadline.reminder_sent == False
        ).all()

        sent_count = 0

        for deadline in deadlines:
            case = self.db.query(Case).filter(Case.id == deadline.case_id).first()
            if not case:
                continue

            days_until = (deadline.due_date - date.today()).days
            urgency = "error" if days_until <= 1 else "warning"

            # Notify assigned lawyer
            if case.assigned_lawyer_id:
                self.create_notification(
                    user_id=case.assigned_lawyer_id,
                    title=f"Frist: {deadline.title}",
                    message=f"Akte {case.internal_number}: {deadline.description or deadline.title} "
                            f"- fällig in {days_until} Tag(en) ({deadline.due_date.strftime('%d.%m.%Y')})",
                    notification_type=urgency,
                    category="deadline",
                    case_id=case.id,
                    reference_type="deadline",
                    reference_id=deadline.id
                )
                sent_count += 1

            deadline.reminder_sent = True
            deadline.reminder_sent_at = datetime.utcnow()

        self.db.commit()
        return sent_count

    # =========================================================================
    # EMAIL NOTIFICATIONS
    # =========================================================================

    def _queue_email_notification(self, notification: Notification):
        """Queue an email notification for sending."""
        # In production, this would queue a Celery task
        # For now, we'll try to send directly
        try:
            self._send_email_notification(notification)
            notification.email_sent = True
            notification.email_sent_at = datetime.utcnow()
            self.db.commit()
        except Exception as e:
            # Log error but don't fail
            pass

    def _send_email_notification(self, notification: Notification):
        """Send an email notification."""
        user = self.db.query(User).filter(User.id == notification.user_id).first()
        if not user or not user.email:
            return

        # Build email content
        subject = f"[NotarFlow] {notification.title}"
        body = self._build_email_body(notification, user)

        # Send email
        self._send_email(
            to_email=user.email,
            subject=subject,
            body=body
        )

    def _build_email_body(self, notification: Notification, user: User) -> str:
        """Build email body from notification."""
        case_info = ""
        if notification.case_id:
            case = self.db.query(Case).filter(Case.id == notification.case_id).first()
            if case:
                case_info = f"\n\nAkte: {case.internal_number}"

        return f"""Sehr geehrte/r {user.first_name} {user.last_name},

{notification.message}
{case_info}

---
Diese E-Mail wurde automatisch von NotarFlow generiert.
Bitte antworten Sie nicht auf diese E-Mail.
"""

    def _send_email(self, to_email: str, subject: str, body: str):
        """Send an email using configured SMTP settings."""
        if not settings.SMTP_HOST:
            return

        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart

        msg = MIMEMultipart()
        msg['From'] = settings.SMTP_FROM_EMAIL
        msg['To'] = to_email
        msg['Subject'] = subject

        msg.attach(MIMEText(body, 'plain', 'utf-8'))

        try:
            if settings.SMTP_TLS:
                server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT)
                server.starttls()
            else:
                server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT)

            if settings.SMTP_USER and settings.SMTP_PASSWORD:
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)

            server.sendmail(
                settings.SMTP_FROM_EMAIL,
                to_email,
                msg.as_string()
            )
            server.quit()

        except Exception as e:
            raise

    # =========================================================================
    # BULK NOTIFICATIONS
    # =========================================================================

    def notify_case_update(
        self,
        case_id: UUID,
        title: str,
        message: str,
        notification_type: str = "info",
        exclude_user_id: Optional[UUID] = None,
        visible_to_creditor: bool = True,
        visible_to_debtor: bool = False
    ):
        """Send notifications to all relevant parties for a case update."""
        case = self.db.query(Case).filter(Case.id == case_id).first()
        if not case:
            return

        recipients = []

        # Add assigned lawyer
        if case.assigned_lawyer_id and case.assigned_lawyer_id != exclude_user_id:
            recipients.append(case.assigned_lawyer_id)

        # Add creditor if visible
        if visible_to_creditor and case.creditor_user_id and case.creditor_user_id != exclude_user_id:
            recipients.append(case.creditor_user_id)

        # Add debtor if visible
        if visible_to_debtor and case.debtor_user_id and case.debtor_user_id != exclude_user_id:
            recipients.append(case.debtor_user_id)

        for user_id in recipients:
            self.create_notification(
                user_id=user_id,
                title=f"{case.internal_number}: {title}",
                message=message,
                notification_type=notification_type,
                category="case",
                case_id=case_id
            )

    def notify_approval_request(
        self,
        case_id: UUID,
        approver_user_id: UUID,
        title: str,
        message: str,
        reference_type: str,
        reference_id: UUID
    ):
        """Send approval request notification."""
        self.create_notification(
            user_id=approver_user_id,
            title=title,
            message=message,
            notification_type="warning",
            category="approval",
            case_id=case_id,
            reference_type=reference_type,
            reference_id=reference_id,
            send_email=True
        )

    # =========================================================================
    # ACTIVITY FEED
    # =========================================================================

    def get_activity_feed(
        self,
        user_id: UUID,
        organization_id: Optional[UUID] = None,
        case_id: Optional[UUID] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get activity feed for dashboard.
        Combines timeline events and notifications.
        """
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return []

        items = []

        # Get timeline events
        event_query = self.db.query(TimelineEvent)

        if case_id:
            event_query = event_query.filter(TimelineEvent.case_id == case_id)
        elif organization_id:
            event_query = event_query.join(Case).filter(
                Case.organization_id == organization_id
            )

        # Filter based on role visibility
        if user.role == 'glaeubigerin':
            event_query = event_query.filter(TimelineEvent.visible_to_creditor == True)
        elif user.role == 'schuldner':
            event_query = event_query.filter(TimelineEvent.visible_to_debtor == True)

        events = event_query.order_by(TimelineEvent.event_date.desc()).limit(limit).all()

        for event in events:
            case = self.db.query(Case).filter(Case.id == event.case_id).first()
            items.append({
                "type": "timeline_event",
                "id": str(event.id),
                "timestamp": event.event_date.isoformat(),
                "title": event.title,
                "description": event.description,
                "category": event.category,
                "severity": event.severity,
                "case_id": str(event.case_id) if event.case_id else None,
                "case_number": case.internal_number if case else None,
                "actor_name": event.actor_name,
                "reference_type": event.reference_type,
                "reference_id": str(event.reference_id) if event.reference_id else None
            })

        # Sort by timestamp
        items.sort(key=lambda x: x["timestamp"], reverse=True)

        return items[:limit]
