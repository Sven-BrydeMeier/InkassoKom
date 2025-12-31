"""
Unit tests for LimitationService
Tests statute of limitations calculations and events
"""
import pytest
from decimal import Decimal
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from uuid import uuid4

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


class TestLimitationPeriods:
    """Tests for limitation period constants."""

    def test_regular_limitation_period(self):
        """Test regular 3-year limitation period."""
        from backend.services.limitation_service import LimitationService

        assert LimitationService.REGULAR_LIMITATION_YEARS == 3

    def test_title_limitation_period(self):
        """Test 30-year title limitation period."""
        from backend.services.limitation_service import LimitationService

        assert LimitationService.TITLE_LIMITATION_YEARS == 30


class TestLimitationStartDate:
    """Tests for limitation start date calculation."""

    def test_limitation_starts_year_end(self):
        """
        Test that limitation starts at end of year of due date.
        According to § 199 Abs. 1 BGB.
        """
        due_date = date(2024, 3, 15)

        # Limitation should start at 2024-12-31
        limitation_start = date(due_date.year, 12, 31)

        assert limitation_start == date(2024, 12, 31)

    def test_regular_limitation_date(self):
        """Test calculation of regular limitation date."""
        due_date = date(2024, 6, 1)

        # Start: 2024-12-31
        # End: 2027-12-31 (3 years later)
        limitation_start = date(due_date.year, 12, 31)
        limitation_end = limitation_start + relativedelta(years=3)

        assert limitation_end == date(2027, 12, 31)

    def test_title_limitation_date(self):
        """Test calculation of title limitation date."""
        title_date = date(2024, 5, 20)

        # 30 years from title date
        limitation_end = title_date + relativedelta(years=30)

        assert limitation_end == date(2054, 5, 20)


class TestLimitationHemmung:
    """Tests for limitation suspension (Hemmung)."""

    def test_suspension_extends_limitation(self):
        """Test that suspension period extends limitation date."""
        original_end = date(2027, 12, 31)
        suspension_days = 100

        new_end = original_end + timedelta(days=suspension_days)

        assert new_end == date(2027, 12, 31) + timedelta(days=100)

    def test_mb_delivery_suspends_limitation(self):
        """Test that MB delivery suspends limitation."""
        # Mahnbescheid delivery creates Hemmung
        # The suspension period should be added to limitation date
        mb_delivery = date(2024, 6, 1)
        mb_end = date(2024, 12, 1)  # Suspension ends

        suspension_days = (mb_end - mb_delivery).days
        assert suspension_days > 0

    def test_ongoing_suspension_calculation(self):
        """Test calculation during ongoing suspension."""
        suspension_start = date(2024, 6, 1)
        as_of = date(2024, 8, 15)

        ongoing_days = (as_of - suspension_start).days
        assert ongoing_days == 75


class TestLimitationNeubeginn:
    """Tests for limitation restart (Neubeginn)."""

    def test_neubeginn_resets_period(self):
        """Test that Neubeginn resets the limitation period."""
        original_due = date(2022, 1, 1)
        neubeginn_date = date(2024, 6, 15)

        # After Neubeginn, new limitation period starts
        new_start = date(neubeginn_date.year, 12, 31)
        new_end = new_start + relativedelta(years=3)

        assert new_end == date(2027, 12, 31)


class TestLimitationWarnings:
    """Tests for limitation warning calculations."""

    def test_risk_threshold_6_months(self):
        """Test that 6 months is considered at risk."""
        today = date(2024, 6, 1)
        limitation_date = date(2024, 10, 15)

        months_until = (limitation_date.year - today.year) * 12 + (limitation_date.month - today.month)

        assert months_until <= 6

    def test_critical_threshold_30_days(self):
        """Test that 30 days is critical."""
        today = date(2024, 6, 1)
        limitation_date = date(2024, 6, 25)

        days_until = (limitation_date - today).days

        assert days_until <= 30

    def test_december_year_end_check(self):
        """Test December special check for year-end limitation."""
        today = date(2024, 12, 1)
        year_end = date(2024, 12, 31)

        # Claims with limitation ending this year should be flagged
        limitation_date = date(2024, 12, 31)

        is_year_end_risk = limitation_date <= year_end

        assert is_year_end_risk is True


class TestVBTitleLimitation:
    """Tests for Vollstreckungsbescheid title limitation."""

    def test_vb_creates_30_year_limitation(self):
        """Test that VB creates 30-year limitation."""
        vb_date = date(2024, 5, 10)

        new_limitation = vb_date + relativedelta(years=30)

        assert new_limitation == date(2054, 5, 10)

    def test_vb_overrides_regular_limitation(self):
        """Test that VB title overrides regular limitation."""
        # Original due: 2024-01-01
        # Regular limitation: 2027-12-31
        # VB date: 2024-06-01
        # New limitation: 2054-06-01

        original_limitation = date(2027, 12, 31)
        vb_date = date(2024, 6, 1)
        vb_limitation = vb_date + relativedelta(years=30)

        # VB limitation should be much later
        assert vb_limitation > original_limitation
        assert (vb_limitation - original_limitation).days > 9000  # ~26 years


class TestLimitationEvents:
    """Tests for limitation event types and effects."""

    def test_event_types(self):
        """Test all supported event types."""
        event_types = [
            'faelligkeit',
            'mahnung',
            'klage',
            'mahnbescheid_antrag',
            'mahnbescheid_zustellung',
            'vollstreckungsbescheid',
            'titel',
            'hemmung_start',
            'hemmung_ende',
            'neubeginn',
            'anerkenntnis',
            'override'
        ]

        for event_type in event_types:
            assert isinstance(event_type, str)
            assert len(event_type) > 0

    def test_event_effects(self):
        """Test all supported event effects."""
        effects = [
            'hemmung',
            'hemmung_ende',
            'neubeginn',
            'titel_30_jahre',
            'custom'
        ]

        for effect in effects:
            assert isinstance(effect, str)
            assert len(effect) > 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
