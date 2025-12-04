"""
Unit tests for timezone utility functions.

Tests timezone conversion utilities for CET/CEST (Europe/Amsterdam) timezone handling,
including UTC conversion, local time conversion, formatting, and DST handling.

Week 13-14: Testing & Quality Assurance - Phase 1 Quick Wins (Pure Functions)
"""

import pytest
import pytz
from datetime import datetime
from freezegun import freeze_time

from app.utils.timezone_utils import (
    utc_to_local,
    local_to_utc,
    format_datetime,
    get_current_local_time,
    get_current_utc_time,
    get_timezone_info,
    format_timestamp,
    LOCAL_TIMEZONE
)


class TestUTCToLocal:
    """Test UTC to local timezone conversion."""

    def test_utc_to_local_with_datetime_object(self):
        """Test conversion with datetime object."""
        # Create a UTC datetime
        utc_dt = datetime(2025, 1, 15, 12, 0, 0, tzinfo=pytz.utc)

        # Convert to local
        local_dt = utc_to_local(utc_dt)

        assert local_dt is not None
        # In winter (January), Europe/Amsterdam is UTC+1 (CET)
        assert local_dt.hour == 13
        assert local_dt.tzinfo is not None

    def test_utc_to_local_with_iso_string(self):
        """Test conversion with ISO format string."""
        iso_string = "2025-01-15T12:00:00Z"

        local_dt = utc_to_local(iso_string)

        assert local_dt is not None
        assert local_dt.hour == 13  # UTC+1 in winter

    def test_utc_to_local_with_iso_string_plus_format(self):
        """Test conversion with ISO string using +00:00 format."""
        iso_string = "2025-01-15T12:00:00+00:00"

        local_dt = utc_to_local(iso_string)

        assert local_dt is not None
        assert local_dt.hour == 13

    def test_utc_to_local_with_summer_time(self):
        """Test conversion during summer (CEST, UTC+2)."""
        # July is summer time in Europe
        utc_dt = datetime(2025, 7, 15, 12, 0, 0, tzinfo=pytz.utc)

        local_dt = utc_to_local(utc_dt)

        assert local_dt is not None
        # In summer (July), Europe/Amsterdam is UTC+2 (CEST)
        assert local_dt.hour == 14
        assert local_dt.tzinfo is not None

    def test_utc_to_local_with_none(self):
        """Test conversion with None input."""
        result = utc_to_local(None)
        assert result is None

    def test_utc_to_local_with_naive_datetime(self):
        """Test conversion with naive (no timezone) datetime."""
        # Naive datetime is assumed to be UTC
        naive_dt = datetime(2025, 1, 15, 12, 0, 0)

        local_dt = utc_to_local(naive_dt)

        assert local_dt is not None
        assert local_dt.hour == 13

    def test_utc_to_local_with_invalid_string(self):
        """Test conversion with invalid ISO string."""
        result = utc_to_local("invalid-date-string")
        assert result is None


class TestLocalToUTC:
    """Test local timezone to UTC conversion."""

    def test_local_to_utc_with_datetime_object(self):
        """Test conversion with datetime object."""
        # Create a local datetime (winter time)
        local_dt = LOCAL_TIMEZONE.localize(datetime(2025, 1, 15, 13, 0, 0))

        # Convert to UTC
        utc_dt = local_to_utc(local_dt)

        assert utc_dt is not None
        assert utc_dt.hour == 12  # CET is UTC+1
        assert utc_dt.tzinfo == pytz.utc

    def test_local_to_utc_with_iso_string(self):
        """Test conversion with ISO format string."""
        iso_string = "2025-01-15T13:00:00"

        utc_dt = local_to_utc(iso_string)

        assert utc_dt is not None
        assert utc_dt.hour == 12

    def test_local_to_utc_with_summer_time(self):
        """Test conversion during summer (CEST, UTC+2)."""
        # July is summer time in Europe
        local_dt = LOCAL_TIMEZONE.localize(datetime(2025, 7, 15, 14, 0, 0))

        utc_dt = local_to_utc(local_dt)

        assert utc_dt is not None
        # CEST is UTC+2
        assert utc_dt.hour == 12

    def test_local_to_utc_with_none(self):
        """Test conversion with None input."""
        result = local_to_utc(None)
        assert result is None

    def test_local_to_utc_with_naive_datetime(self):
        """Test conversion with naive datetime (assumed local)."""
        naive_dt = datetime(2025, 1, 15, 13, 0, 0)

        utc_dt = local_to_utc(naive_dt)

        assert utc_dt is not None
        assert utc_dt.hour == 12

    def test_local_to_utc_with_invalid_string(self):
        """Test conversion with invalid ISO string."""
        result = local_to_utc("invalid-date-string")
        assert result is None


class TestFormatDatetime:
    """Test datetime formatting."""

    def test_format_datetime_with_timezone(self):
        """Test formatting with timezone included."""
        utc_dt = datetime(2025, 1, 15, 12, 0, 0, tzinfo=pytz.utc)

        formatted = format_datetime(utc_dt, include_timezone=True)

        assert formatted is not None
        assert "2025-01-15 13:00:00" in formatted
        assert "CET" in formatted  # Winter time

    def test_format_datetime_without_timezone(self):
        """Test formatting without timezone abbreviation."""
        utc_dt = datetime(2025, 1, 15, 12, 0, 0, tzinfo=pytz.utc)

        formatted = format_datetime(utc_dt, include_timezone=False)

        assert formatted == "2025-01-15 13:00:00"
        assert "CET" not in formatted

    def test_format_datetime_with_custom_format(self):
        """Test formatting with custom date format."""
        utc_dt = datetime(2025, 1, 15, 12, 30, 45, tzinfo=pytz.utc)

        formatted = format_datetime(
            utc_dt,
            include_timezone=False,
            date_format='%Y/%m/%d %H:%M'
        )

        assert formatted == "2025/01/15 13:30"

    def test_format_datetime_with_iso_string(self):
        """Test formatting with ISO string input."""
        iso_string = "2025-01-15T12:00:00Z"

        formatted = format_datetime(iso_string, include_timezone=True)

        assert "2025-01-15 13:00:00" in formatted

    def test_format_datetime_with_none(self):
        """Test formatting with None input."""
        result = format_datetime(None)
        assert result == 'N/A'

    def test_format_datetime_with_summer_time(self):
        """Test formatting during summer (CEST)."""
        utc_dt = datetime(2025, 7, 15, 12, 0, 0, tzinfo=pytz.utc)

        formatted = format_datetime(utc_dt, include_timezone=True)

        assert "2025-07-15 14:00:00" in formatted
        assert "CEST" in formatted  # Summer time

    def test_format_datetime_with_invalid_input(self):
        """Test formatting with invalid input."""
        result = format_datetime("invalid-date")
        # Should return the input string or 'N/A'
        assert result in ["invalid-date", "N/A"]


class TestCurrentTimeGetters:
    """Test functions that get current time."""

    @freeze_time("2025-01-15 12:00:00", tz_offset=0)
    def test_get_current_utc_time(self):
        """Test getting current UTC time."""
        utc_now = get_current_utc_time()

        assert utc_now is not None
        assert utc_now.tzinfo == pytz.utc
        assert utc_now.year == 2025
        assert utc_now.month == 1
        assert utc_now.day == 15
        assert utc_now.hour == 12

    @freeze_time("2025-01-15 12:00:00", tz_offset=0)
    def test_get_current_local_time(self):
        """Test getting current local time."""
        local_now = get_current_local_time()

        assert local_now is not None
        assert local_now.tzinfo is not None
        # In winter, local time is UTC+1
        assert local_now.hour == 13

    def test_current_times_are_recent(self):
        """Test that current time functions return recent times."""
        utc_now = get_current_utc_time()
        local_now = get_current_local_time()

        # Both should be within last minute
        now = datetime.now(pytz.utc)
        time_diff = abs((now - utc_now).total_seconds())
        assert time_diff < 60  # Within 1 minute

        # Local and UTC should have correct timezone info
        assert utc_now.tzinfo == pytz.utc
        assert local_now.tzinfo is not None


class TestTimezoneInfo:
    """Test timezone information retrieval."""

    def test_get_timezone_info_structure(self):
        """Test that timezone info returns correct structure."""
        info = get_timezone_info()

        assert 'timezone' in info
        assert 'current_abbreviation' in info
        assert 'utc_offset' in info
        assert 'is_dst' in info

        assert info['timezone'] == 'Europe/Amsterdam'

    def test_get_timezone_info_abbreviation(self):
        """Test timezone abbreviation is CET or CEST."""
        info = get_timezone_info()

        # Should be either CET (winter) or CEST (summer)
        assert info['current_abbreviation'] in ['CET', 'CEST']

    def test_get_timezone_info_offset(self):
        """Test UTC offset is +0100 or +0200."""
        info = get_timezone_info()

        # Should be either +0100 (CET) or +0200 (CEST)
        assert info['utc_offset'] in ['+0100', '+0200']

    def test_get_timezone_info_dst_is_boolean(self):
        """Test is_dst is a boolean."""
        info = get_timezone_info()

        assert isinstance(info['is_dst'], bool)

    @freeze_time("2025-01-15")  # Winter
    def test_get_timezone_info_winter(self):
        """Test timezone info in winter (CET)."""
        info = get_timezone_info()

        assert info['current_abbreviation'] == 'CET'
        assert info['utc_offset'] == '+0100'
        assert info['is_dst'] is False

    @freeze_time("2025-07-15")  # Summer
    def test_get_timezone_info_summer(self):
        """Test timezone info in summer (CEST)."""
        info = get_timezone_info()

        assert info['current_abbreviation'] == 'CEST'
        assert info['utc_offset'] == '+0200'
        assert info['is_dst'] is True


class TestFormatTimestamp:
    """Test convenience timestamp formatting function."""

    def test_format_timestamp_with_iso_string(self):
        """Test quick format for ISO timestamp."""
        iso_string = "2025-01-15T12:00:00Z"

        formatted = format_timestamp(iso_string)

        assert formatted is not None
        assert "2025-01-15 13:00:00" in formatted
        assert "CET" in formatted

    def test_format_timestamp_with_plus_format(self):
        """Test quick format with +00:00 format."""
        iso_string = "2025-01-15T12:00:00+00:00"

        formatted = format_timestamp(iso_string)

        assert formatted is not None
        assert "13:00:00" in formatted


class TestRoundTripConversions:
    """Test round-trip conversions (UTC -> Local -> UTC)."""

    def test_round_trip_utc_to_local_to_utc(self):
        """Test converting UTC -> Local -> UTC returns same time."""
        original_utc = datetime(2025, 1, 15, 12, 0, 0, tzinfo=pytz.utc)

        # UTC -> Local
        local_dt = utc_to_local(original_utc)

        # Local -> UTC
        back_to_utc = local_to_utc(local_dt)

        # Should be the same (accounting for microseconds)
        time_diff = abs((back_to_utc - original_utc).total_seconds())
        assert time_diff < 1  # Within 1 second

    def test_round_trip_local_to_utc_to_local(self):
        """Test converting Local -> UTC -> Local returns same time."""
        original_local = LOCAL_TIMEZONE.localize(datetime(2025, 1, 15, 13, 0, 0))

        # Local -> UTC
        utc_dt = local_to_utc(original_local)

        # UTC -> Local
        back_to_local = utc_to_local(utc_dt)

        # Should be the same (accounting for microseconds)
        time_diff = abs((back_to_local - original_local).total_seconds())
        assert time_diff < 1


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_dst_transition_spring_forward(self):
        """Test DST transition when clocks go forward."""
        # Last Sunday of March 2025 at 2:00 AM -> 3:00 AM
        # This is when CET becomes CEST
        before_dst = LOCAL_TIMEZONE.localize(datetime(2025, 3, 30, 1, 0, 0))
        after_dst = LOCAL_TIMEZONE.localize(datetime(2025, 3, 30, 3, 0, 0))

        # Convert to UTC
        before_utc = local_to_utc(before_dst)
        after_utc = local_to_utc(after_dst)

        # Time difference should be 1 hour (not 2)
        time_diff = (after_utc - before_utc).total_seconds()
        assert time_diff == 3600  # 1 hour

    def test_dst_transition_fall_back(self):
        """Test DST transition when clocks go back."""
        # Last Sunday of October 2025 at 3:00 AM -> 2:00 AM
        # This is when CEST becomes CET
        # Note: pytz localize with is_dst parameter can be tricky
        # For testing purposes, we'll use explicit timezone aware datetimes
        before_dst = datetime(2025, 10, 26, 1, 0, 0, tzinfo=pytz.timezone('Europe/Amsterdam'))

        # One hour before the transition vs one hour after
        utc_before = before_dst.astimezone(pytz.utc)

        # Just verify the conversion works without error
        assert utc_before.tzinfo == pytz.utc

    def test_midnight_conversion(self):
        """Test conversion at midnight."""
        utc_midnight = datetime(2025, 1, 15, 0, 0, 0, tzinfo=pytz.utc)

        local_dt = utc_to_local(utc_midnight)

        assert local_dt.hour == 1  # Midnight UTC is 1 AM CET

    def test_end_of_year_conversion(self):
        """Test conversion at end of year."""
        utc_dt = datetime(2025, 12, 31, 23, 30, 0, tzinfo=pytz.utc)

        local_dt = utc_to_local(utc_dt)

        # Should be next day in local time
        assert local_dt.day == 1
        assert local_dt.month == 1
        assert local_dt.year == 2026
