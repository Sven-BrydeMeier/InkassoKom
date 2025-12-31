"""
Seed Data Script for NotarFlow
Creates demo organizations, users, cases, and sample data
"""
from datetime import date, datetime, timedelta
from decimal import Decimal
from uuid import uuid4
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from db import SessionLocal, init_db
from db.models import (
    Organization, User, Case, Claim, LedgerBooking,
    Document, TimelineEvent, PaymentPlan, PaymentPlanInstallment
)
from backend.services.auth_service import AuthService
from config.settings import UserRole, CaseStatus, DunningStatus, BookingCategory


def create_seed_data():
    """Create all seed data."""
    print("Initializing database...")
    init_db()

    db = SessionLocal()

    try:
        print("Creating organization...")
        org = create_organization(db)

        print("Creating users...")
        users = create_users(db, org.id)

        print("Creating cases...")
        cases = create_cases(db, org.id, users)

        print("Creating sample bookings...")
        create_bookings(db, cases, users)

        print("Creating timeline events...")
        create_timeline_events(db, cases, users)

        print("Creating payment plan...")
        create_payment_plan(db, cases[0], users)

        db.commit()
        print("\n✅ Seed data created successfully!")

        print_login_info(users)

    except Exception as e:
        db.rollback()
        print(f"\n❌ Error creating seed data: {e}")
        raise
    finally:
        db.close()


def create_organization(db: Session) -> Organization:
    """Create demo organization."""
    org = Organization(
        name="Musterkanzlei RA Schmidt",
        slug="musterkanzlei-schmidt",
        street="Musterstraße 123",
        postal_code="24118",
        city="Kiel",
        country="DE",
        phone="+49 431 123456",
        email="kanzlei@ra-schmidt.de",
        website="https://www.ra-schmidt.de",
        tax_id="12/345/67890",
        is_active=True
    )

    db.add(org)
    db.flush()

    return org


def create_users(db: Session, org_id) -> dict:
    """Create demo users for all roles."""
    auth = AuthService(db)

    users = {}

    # Lawyer (Admin)
    lawyer = User(
        organization_id=org_id,
        email="ra.schmidt@kanzlei.de",
        password_hash=auth.hash_password("Demo123!"),
        first_name="Thomas",
        last_name="Schmidt",
        title="RA",
        role=UserRole.RECHTSANWALT,
        is_active=True,
        email_verified=True
    )
    db.add(lawyer)
    db.flush()
    users['lawyer'] = lawyer

    # Creditor
    creditor = User(
        organization_id=org_id,
        email="glaeubiger@firma.de",
        password_hash=auth.hash_password("Demo123!"),
        first_name="Maria",
        last_name="Müller",
        role=UserRole.GLAEUBIGERIN,
        is_active=True,
        email_verified=True
    )
    db.add(creditor)
    db.flush()
    users['creditor'] = creditor

    # Debtor
    debtor = User(
        organization_id=org_id,
        email="schuldner@beispiel.de",
        password_hash=auth.hash_password("Demo123!"),
        first_name="Hans",
        last_name="Meier",
        role=UserRole.SCHULDNER,
        is_active=True,
        email_verified=True
    )
    db.add(debtor)
    db.flush()
    users['debtor'] = debtor

    return users


def create_cases(db: Session, org_id, users: dict) -> list:
    """Create demo cases."""
    cases = []

    # Case 1: Active case with MB
    case1 = Case(
        organization_id=org_id,
        internal_number="1-24",
        external_number="2024/001",
        subject="Kaufpreisforderung Warenlieferung",
        description="Offene Rechnung für Warenlieferung vom 15.01.2024",
        creditor_user_id=users['creditor'].id,
        debtor_user_id=users['debtor'].id,
        creditor_name="Müller GmbH",
        creditor_street="Industriestr. 42",
        creditor_postal_code="24103",
        creditor_city="Kiel",
        creditor_email="buchhaltung@mueller-gmbh.de",
        debtor_name="Hans Meier",
        debtor_street="Waldweg 7",
        debtor_postal_code="24105",
        debtor_city="Kiel",
        debtor_email="hans.meier@example.de",
        debtor_birth_date=date(1975, 5, 15),
        status=CaseStatus.MAHNVERFAHREN,
        dunning_status=DunningStatus.MB_ZUGESTELLT,
        mb_application_date=date(2024, 3, 1),
        mb_delivery_date=date(2024, 3, 15),
        court_file_number="24 B 123/24",
        assigned_lawyer_id=users['lawyer'].id,
        created_by=users['lawyer'].id
    )
    db.add(case1)
    db.flush()
    cases.append(case1)

    # Add claim for case 1
    claim1 = Claim(
        case_id=case1.id,
        description="Warenlieferung Rechnung Nr. 2024-0042",
        claim_type="Kaufpreis",
        principal_amount=Decimal("2500.00"),
        interest_rate=Decimal("5.0"),
        interest_start_date=date(2024, 2, 1),
        due_date=date(2024, 1, 31),
        invoice_date=date(2024, 1, 15),
        invoice_number="2024-0042",
        created_by=users['lawyer'].id
    )
    db.add(claim1)

    # Case 2: New case
    case2 = Case(
        organization_id=org_id,
        internal_number="2-24",
        subject="Mietrückstand",
        description="Offene Mieten für Mai-Juli 2024",
        creditor_user_id=users['creditor'].id,
        creditor_name="Hausverwaltung Müller",
        creditor_street="Hauptstraße 1",
        creditor_postal_code="24103",
        creditor_city="Kiel",
        debtor_name="Peter Schulz",
        debtor_street="Nebenstraße 5",
        debtor_postal_code="24107",
        debtor_city="Kiel",
        status=CaseStatus.OFFEN,
        dunning_status=DunningStatus.NICHT_BEANTRAGT,
        assigned_lawyer_id=users['lawyer'].id,
        created_by=users['lawyer'].id
    )
    db.add(case2)
    db.flush()
    cases.append(case2)

    # Add claim for case 2
    claim2 = Claim(
        case_id=case2.id,
        description="Miete Mai 2024",
        claim_type="Miete",
        principal_amount=Decimal("850.00"),
        interest_rate=Decimal("5.0"),
        interest_start_date=date(2024, 5, 4),
        due_date=date(2024, 5, 3),
        created_by=users['lawyer'].id
    )
    db.add(claim2)

    claim3 = Claim(
        case_id=case2.id,
        description="Miete Juni 2024",
        claim_type="Miete",
        principal_amount=Decimal("850.00"),
        interest_rate=Decimal("5.0"),
        interest_start_date=date(2024, 6, 4),
        due_date=date(2024, 6, 3),
        created_by=users['lawyer'].id
    )
    db.add(claim3)

    # Case 3: Case with payment plan
    case3 = Case(
        organization_id=org_id,
        internal_number="3-24",
        subject="Darlehensrückzahlung",
        creditor_user_id=users['creditor'].id,
        debtor_user_id=users['debtor'].id,
        creditor_name="Müller GmbH",
        debtor_name="Anna Weber",
        debtor_street="Gartenweg 12",
        debtor_postal_code="24109",
        debtor_city="Kiel",
        status=CaseStatus.RATENZAHLUNG,
        payment_plan_status="aktiv",
        assigned_lawyer_id=users['lawyer'].id,
        created_by=users['lawyer'].id
    )
    db.add(case3)
    db.flush()
    cases.append(case3)

    claim4 = Claim(
        case_id=case3.id,
        description="Darlehensrückzahlung",
        claim_type="Darlehen",
        principal_amount=Decimal("5000.00"),
        due_date=date(2024, 1, 1),
        created_by=users['lawyer'].id
    )
    db.add(claim4)

    db.flush()
    return cases


def create_bookings(db: Session, cases: list, users: dict):
    """Create sample ledger bookings."""
    case = cases[0]

    # Initial principal
    booking1 = LedgerBooking(
        case_id=case.id,
        booking_date=date(2024, 1, 31),
        debit_credit='S',
        amount=Decimal("2500.00"),
        category=BookingCategory.HAUPTFORDERUNG,
        description="Hauptforderung Rechnung 2024-0042",
        source='system',
        source_user_id=users['lawyer'].id,
        status='verbucht',
        created_by=users['lawyer'].id
    )
    db.add(booking1)

    # Interest
    booking2 = LedgerBooking(
        case_id=case.id,
        booking_date=date(2024, 6, 1),
        debit_credit='S',
        amount=Decimal("52.08"),
        category=BookingCategory.ZINSEN,
        description="Zinsen 5% p.a. (01.02.2024 - 01.06.2024)",
        source='system',
        status='verbucht',
        created_by=users['lawyer'].id
    )
    db.add(booking2)

    # RA fees
    booking3 = LedgerBooking(
        case_id=case.id,
        booking_date=date(2024, 2, 15),
        debit_credit='S',
        amount=Decimal("261.80"),
        category=BookingCategory.RA_GEBUEHREN,
        description="1,3 Geschäftsgebühr Nr. 2300 VV RVG",
        source='rechtsanwalt',
        status='verbucht',
        created_by=users['lawyer'].id
    )
    db.add(booking3)

    # Partial payment
    booking4 = LedgerBooking(
        case_id=case.id,
        booking_date=date(2024, 4, 15),
        debit_credit='H',
        amount=Decimal("500.00"),
        category=BookingCategory.HAUPTFORDERUNG,
        description="Teilzahlung Schuldner",
        reference="ÜBERWEISUNG 2024-04-15",
        source='glaeubiger',
        status='verbucht',
        created_by=users['creditor'].id
    )
    db.add(booking4)

    # Reported payment (pending)
    booking5 = LedgerBooking(
        case_id=case.id,
        booking_date=date(2024, 6, 1),
        debit_credit='H',
        amount=Decimal("300.00"),
        category=BookingCategory.HAUPTFORDERUNG,
        description="Weiterer Zahlungseingang",
        reference="ÜBERWEISUNG 2024-06-01",
        source='glaeubiger',
        status='gemeldet',
        reported_at=datetime.now(),
        created_by=users['creditor'].id
    )
    db.add(booking5)


def create_timeline_events(db: Session, cases: list, users: dict):
    """Create sample timeline events."""
    case = cases[0]

    events = [
        TimelineEvent(
            case_id=case.id,
            event_type="case_created",
            title="Akte angelegt",
            description=f"Akte {case.internal_number} wurde angelegt",
            category="system",
            severity="info",
            actor_id=users['lawyer'].id,
            actor_name="RA Thomas Schmidt",
            actor_role="rechtsanwalt",
            visible_to_creditor=True,
            visible_to_debtor=False,
            event_date=datetime(2024, 2, 1, 9, 0)
        ),
        TimelineEvent(
            case_id=case.id,
            event_type="claim_added",
            title="Forderung hinzugefügt",
            description="Hauptforderung über 2.500,00€",
            category="forderung",
            severity="info",
            actor_id=users['lawyer'].id,
            actor_name="RA Thomas Schmidt",
            visible_to_creditor=True,
            visible_to_debtor=True,
            event_date=datetime(2024, 2, 1, 9, 5)
        ),
        TimelineEvent(
            case_id=case.id,
            event_type="mb_sent",
            title="Mahnbescheid beantragt",
            description="Mahnbescheid beim AG Schleswig beantragt",
            category="mahnverfahren",
            severity="info",
            actor_id=users['lawyer'].id,
            actor_name="RA Thomas Schmidt",
            visible_to_creditor=True,
            visible_to_debtor=True,
            event_date=datetime(2024, 3, 1, 10, 30)
        ),
        TimelineEvent(
            case_id=case.id,
            event_type="mb_delivered",
            title="Mahnbescheid zugestellt",
            description="Zustellung am 15.03.2024 bestätigt",
            category="mahnverfahren",
            severity="success",
            actor_id=users['lawyer'].id,
            actor_name="RA Thomas Schmidt",
            visible_to_creditor=True,
            visible_to_debtor=True,
            event_date=datetime(2024, 3, 20, 14, 0)
        ),
        TimelineEvent(
            case_id=case.id,
            event_type="payment_received",
            title="Zahlung eingegangen",
            description="Teilzahlung über 500,00€ verbucht",
            category="zahlung",
            severity="success",
            actor_id=users['creditor'].id,
            actor_name="Maria Müller",
            visible_to_creditor=True,
            visible_to_debtor=True,
            event_date=datetime(2024, 4, 15, 16, 0)
        ),
    ]

    for event in events:
        db.add(event)


def create_payment_plan(db: Session, case, users: dict):
    """Create a sample payment plan."""
    case3 = case  # Use case 3 which has payment plan status

    plan = PaymentPlan(
        case_id=case3.id,
        status='aktiv',
        total_amount=Decimal("5000.00"),
        installment_amount=Decimal("250.00"),
        number_of_installments=20,
        first_installment_date=date(2024, 3, 1),
        interval_days=30,
        requested_at=datetime(2024, 2, 15),
        reviewed_at=datetime(2024, 2, 20),
        approved_at=datetime(2024, 2, 25),
        created_by=users['lawyer'].id
    )
    db.add(plan)
    db.flush()

    # Create installments
    for i in range(1, 21):
        due_date = date(2024, 3, 1) + timedelta(days=30 * (i - 1))

        # First 3 are paid
        status = 'paid' if i <= 3 else 'pending'
        paid_at = datetime(2024, 3, 1) + timedelta(days=30 * (i - 1)) if i <= 3 else None

        inst = PaymentPlanInstallment(
            payment_plan_id=plan.id,
            installment_number=i,
            due_date=due_date,
            amount=Decimal("250.00"),
            status=status,
            paid_at=paid_at
        )
        db.add(inst)


def print_login_info(users: dict):
    """Print login information for demo users."""
    print("\n" + "=" * 60)
    print("DEMO LOGIN CREDENTIALS")
    print("=" * 60)
    print("\n📋 Rechtsanwalt (Lawyer):")
    print(f"   Email: ra.schmidt@kanzlei.de")
    print(f"   Password: Demo123!")
    print("\n💼 Gläubigerin (Creditor):")
    print(f"   Email: glaeubiger@firma.de")
    print(f"   Password: Demo123!")
    print("\n👤 Schuldner (Debtor):")
    print(f"   Email: schuldner@beispiel.de")
    print(f"   Password: Demo123!")
    print("\n" + "=" * 60)


if __name__ == "__main__":
    create_seed_data()
