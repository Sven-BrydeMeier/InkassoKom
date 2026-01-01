"""
Seed Data Script for InkassoKom
Creates demo organizations, users, cases, and sample data
"""
from datetime import date, datetime, timedelta
from passlib.hash import bcrypt
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db import get_db_session, init_db
from db.models import Organization, User, Case, Claim, LedgerBooking, TimelineEvent


def create_seed_data():
    """Create all seed data."""
    print("Initializing database...")
    init_db()

    with get_db_session() as db:
        # Check if data exists
        if db.query(User).first():
            print("Demo data already exists.")
            return

        print("Creating organization...")
        org = Organization(
            name="Kanzlei Müller & Partner",
            slug="kanzlei-mueller",
            street="Musterstraße 123",
            postal_code="10115",
            city="Berlin",
            email="info@kanzlei-mueller.de",
            phone="+49 30 123456"
        )
        db.add(org)
        db.flush()

        print("Creating users...")
        password_hash = bcrypt.hash("demo123")

        lawyer = User(
            organization_id=org.id,
            email="ra@kanzlei-mueller.de",
            password_hash=password_hash,
            first_name="Thomas",
            last_name="Müller",
            title="RA",
            role="rechtsanwalt"
        )
        db.add(lawyer)

        creditor = User(
            organization_id=org.id,
            email="erika@mustermann-gmbh.de",
            password_hash=password_hash,
            first_name="Erika",
            last_name="Mustermann",
            role="glaeubigerin"
        )
        db.add(creditor)

        debtor = User(
            organization_id=org.id,
            email="max@example.de",
            password_hash=password_hash,
            first_name="Max",
            last_name="Schmidt",
            role="schuldner"
        )
        db.add(debtor)
        db.flush()

        print("Creating cases...")
        case1 = Case(
            organization_id=org.id,
            internal_number="1-25",
            creditor_user_id=creditor.id,
            creditor_name="Mustermann GmbH",
            creditor_email="erika@mustermann-gmbh.de",
            debtor_user_id=debtor.id,
            debtor_name="Max Schmidt",
            debtor_email="max@example.de",
            subject="Offene Rechnung 2024-001",
            status="offen",
            assigned_lawyer_id=lawyer.id
        )
        db.add(case1)

        case2 = Case(
            organization_id=org.id,
            internal_number="2-25",
            creditor_user_id=creditor.id,
            creditor_name="Mustermann GmbH",
            debtor_name="Hans Meier",
            subject="Kaufpreisforderung",
            status="mahnverfahren",
            dunning_status="mb_zugestellt",
            assigned_lawyer_id=lawyer.id
        )
        db.add(case2)
        db.flush()

        print("Creating claims and bookings...")
        claim1 = Claim(
            case_id=case1.id,
            description="Rechnung 2024-001",
            claim_type="kaufpreis",
            principal_amount=5000.00,
            interest_rate=5.0,
            due_date=date.today() - timedelta(days=60),
            invoice_number="2024-001"
        )
        db.add(claim1)
        db.flush()

        # Hauptforderung (Soll)
        db.add(LedgerBooking(
            case_id=case1.id,
            claim_id=claim1.id,
            booking_date=date.today() - timedelta(days=60),
            debit_credit='S',
            amount=5000.00,
            category='hauptforderung',
            description="Hauptforderung Rechnung 2024-001",
            source='system'
        ))

        # Zinsen (Soll)
        db.add(LedgerBooking(
            case_id=case1.id,
            booking_date=date.today(),
            debit_credit='S',
            amount=125.00,
            category='zinsen',
            description="Verzugszinsen",
            source='system'
        ))

        # Teilzahlung (Haben)
        db.add(LedgerBooking(
            case_id=case1.id,
            booking_date=date.today() - timedelta(days=30),
            debit_credit='H',
            amount=1000.00,
            category='zahlung',
            description="Teilzahlung Schuldner",
            source='schuldner'
        ))

        print("Creating timeline events...")
        db.add(TimelineEvent(
            case_id=case1.id,
            event_type="case_created",
            title="Akte angelegt",
            description=f"Akte 1-25 wurde angelegt",
            category="system",
            actor_id=lawyer.id,
            actor_name="RA Thomas Müller",
            actor_role="rechtsanwalt"
        ))

        db.commit()
        print("\n✅ Seed data created successfully!")
        print("\n" + "=" * 50)
        print("DEMO LOGIN CREDENTIALS")
        print("=" * 50)
        print("\n📋 Rechtsanwalt: ra@kanzlei-mueller.de / demo123")
        print("💼 Gläubigerin: erika@mustermann-gmbh.de / demo123")
        print("👤 Schuldner: max@example.de / demo123")
        print("=" * 50)


if __name__ == "__main__":
    create_seed_data()
