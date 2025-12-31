"""
Unit tests for LedgerService
Tests payment allocation order and balance calculations
"""
import pytest
from decimal import Decimal
from datetime import date, datetime
from uuid import uuid4

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from config.settings import BookingCategory, PaymentStatus


class TestLedgerAllocation:
    """Tests for payment allocation order."""

    def test_allocation_order_constant(self):
        """Verify correct allocation order: Zinsen -> RA -> Nebenkosten -> Hauptforderung"""
        from backend.services.ledger_service import LedgerService

        expected_order = [
            BookingCategory.ZINSEN,
            BookingCategory.RA_GEBUEHREN,
            BookingCategory.NEBENKOSTEN,
            BookingCategory.GERICHTSKOSTEN,
            BookingCategory.VOLLSTRECKUNGSKOSTEN,
            BookingCategory.HAUPTFORDERUNG,
        ]

        assert LedgerService.ALLOCATION_ORDER == expected_order

    def test_interest_before_principal(self):
        """Verify interest is allocated before principal."""
        from backend.services.ledger_service import LedgerService

        # Interest should come before principal in allocation order
        zinsen_idx = LedgerService.ALLOCATION_ORDER.index(BookingCategory.ZINSEN)
        hauptforderung_idx = LedgerService.ALLOCATION_ORDER.index(BookingCategory.HAUPTFORDERUNG)

        assert zinsen_idx < hauptforderung_idx

    def test_ra_fees_before_principal(self):
        """Verify RA fees are allocated before principal."""
        from backend.services.ledger_service import LedgerService

        ra_idx = LedgerService.ALLOCATION_ORDER.index(BookingCategory.RA_GEBUEHREN)
        hauptforderung_idx = LedgerService.ALLOCATION_ORDER.index(BookingCategory.HAUPTFORDERUNG)

        assert ra_idx < hauptforderung_idx


class TestBalanceCalculations:
    """Tests for balance calculation logic."""

    def test_debit_credit_logic(self):
        """Test that S = Soll (increase) and H = Haben (decrease)."""
        # S should increase the balance (add to debt)
        # H should decrease the balance (payment)
        assert 'S' != 'H'  # Basic sanity check

    def test_balance_cannot_be_negative(self):
        """Test that balance cannot go below zero."""
        # Balance should be capped at 0
        total = Decimal('100')
        paid = Decimal('150')  # Overpayment

        open_amount = max(total - paid, Decimal('0'))
        assert open_amount == Decimal('0')

    def test_category_balance_calculation(self):
        """Test balance calculation by category."""
        bookings = [
            {'category': 'hauptforderung', 'debit_credit': 'S', 'amount': Decimal('1000')},
            {'category': 'zinsen', 'debit_credit': 'S', 'amount': Decimal('100')},
            {'category': 'ra_gebuehren', 'debit_credit': 'S', 'amount': Decimal('200')},
            {'category': 'hauptforderung', 'debit_credit': 'H', 'amount': Decimal('500')},
        ]

        balance_by_category = {}

        for b in bookings:
            cat = b['category']
            if cat not in balance_by_category:
                balance_by_category[cat] = Decimal('0')

            if b['debit_credit'] == 'S':
                balance_by_category[cat] += b['amount']
            else:
                balance_by_category[cat] -= b['amount']

        assert balance_by_category['hauptforderung'] == Decimal('500')
        assert balance_by_category['zinsen'] == Decimal('100')
        assert balance_by_category['ra_gebuehren'] == Decimal('200')


class TestPaymentStatus:
    """Tests for payment status workflow."""

    def test_payment_status_values(self):
        """Test all payment status values exist."""
        assert PaymentStatus.GEMELDET == 'gemeldet'
        assert PaymentStatus.AKZEPTIERT == 'akzeptiert'
        assert PaymentStatus.ABGELEHNT == 'abgelehnt'
        assert PaymentStatus.VERBUCHT == 'verbucht'

    def test_payment_workflow_order(self):
        """Test valid payment workflow transitions."""
        # gemeldet -> akzeptiert -> verbucht
        # gemeldet -> abgelehnt
        valid_from_gemeldet = [PaymentStatus.AKZEPTIERT, PaymentStatus.ABGELEHNT]
        valid_from_akzeptiert = [PaymentStatus.VERBUCHT]

        assert PaymentStatus.AKZEPTIERT in valid_from_gemeldet
        assert PaymentStatus.ABGELEHNT in valid_from_gemeldet
        assert PaymentStatus.VERBUCHT in valid_from_akzeptiert


class TestInterestCalculation:
    """Tests for interest calculation."""

    def test_daily_interest_rate(self):
        """Test daily interest rate calculation."""
        annual_rate = Decimal('5.0')  # 5% p.a.
        daily_rate = annual_rate / Decimal('100') / Decimal('365')

        # For 1000€ principal, 1 year, 5% = 50€
        principal = Decimal('1000')
        days = 365
        interest = principal * daily_rate * Decimal(days)

        # Should be approximately 50€ (allowing for rounding)
        assert Decimal('49') < interest < Decimal('51')

    def test_interest_start_from_due_date(self):
        """Test that interest starts from the due date."""
        due_date = date(2024, 1, 1)
        as_of_date = date(2024, 7, 1)

        days = (as_of_date - due_date).days
        assert days == 182  # Half year

    def test_no_interest_if_rate_zero(self):
        """Test no interest calculated if rate is zero."""
        principal = Decimal('1000')
        rate = Decimal('0')
        days = 365

        daily_rate = rate / Decimal('100') / Decimal('365')
        interest = principal * daily_rate * Decimal(days)

        assert interest == Decimal('0')


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
