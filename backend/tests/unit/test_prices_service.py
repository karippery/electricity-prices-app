import pytest
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from apps.services.prices import PriceService
from apps.schemas import HourlyPrice

VIENNA_TZ = ZoneInfo("Europe/Vienna")

class TestCreateHourlyGrid:
    """Test DST handling - key differentiator for German roles"""
    
    @pytest.mark.parametrize("test_date_str,expected_hours", [
        ("2025-01-15", 24),   # Normal winter day (CET)
        ("2025-06-15", 24),   # Normal summer day (CEST)
        ("2025-03-30", 23),   # Spring forward: 30 Mar 02:00 → 03:00 (skip 02:00–03:00)
        ("2025-10-26", 25),   # Fall back: 26 Oct 02:00–03:00 occurs twice
    ])
    def test_hour_count_for_date(self, test_date_str, expected_hours):
        """Verify correct number of hours generated for given date, accounting for DST"""
        service = PriceService()
        target_date = datetime.strptime(test_date_str, "%Y-%m-%d").date()
        
        # Generate valid hourly timestamps for the entire day (accounting for gaps/duplicates)
        day_start = datetime(target_date.year, target_date.month, target_date.day, tzinfo=VIENNA_TZ)
        raw_data = []
        current = day_start
        
        # Safely iterate through all local hours that actually exist
        for _ in range(26):  # max 26 iterations to avoid infinite loop
            if current.date() != target_date:
                break
            # Use timestamp to uniquely identify each real hour
            raw_data.append({
                "start_timestamp": int(current.timestamp() * 1000),
                "marketprice": 50.0 + (current.hour % 5)
            })
            # Advance by 1 hour in local time (respects DST)
            current += timedelta(hours=1)
        
        hours, has_dst = service.create_hourly_grid(day_start, raw_data)
        assert len(hours) == expected_hours
        assert has_dst == (expected_hours != 24)
    
    def test_fall_back_hour_labeling(self):
        """Verify correct labeling of ambiguous 02:00 hour during fall-back (2025)"""
        service = PriceService()
        target_date = datetime(2025, 10, 26, tzinfo=VIENNA_TZ)
        
        # Dynamically compute the two 02:00 timestamps in 2025
        # First occurrence: still in CEST (UTC+2)
        dt_first = datetime(2025, 10, 26, 2, 0, tzinfo=VIENNA_TZ, fold=0)
        # Second occurrence: after fallback to CET (UTC+1)
        dt_second = datetime(2025, 10, 26, 2, 0, tzinfo=VIENNA_TZ, fold=1)
        
        raw_data = [
            {"start_timestamp": int(dt_first.timestamp() * 1000), "marketprice": 45.0},
            {"start_timestamp": int(dt_second.timestamp() * 1000), "marketprice": 42.0},
        ]
        
        hours, _ = service.create_hourly_grid(target_date, raw_data)
        
        # FIXED: Use timestamp_ms to reconstruct datetime and check hour
        hour_labels = []
        for h in hours:
            # Convert timestamp_ms back to datetime to check the hour
            dt = datetime.fromtimestamp(h.timestamp_ms / 1000, tz=VIENNA_TZ)
            if dt.hour == 2:
                hour_labels.append(h.hour_label)
        
        assert "02:00A" in hour_labels
        assert "02:00B" in hour_labels
        assert len([h for h in hours if h.is_dst_transition]) == 1

class TestGetExpectedHourCount:
    """Direct test of hour calculation logic"""
    
    @pytest.mark.parametrize("date_str,expected", [
        ("2025-03-29", 24),   # Day before spring forward
        ("2025-03-30", 23),   # Spring forward day (23 hours)
        ("2025-03-31", 24),   # Day after
        ("2025-10-25", 24),   # Day before fall back
        ("2025-10-26", 25),   # Fall back day (25 hours)
        ("2025-10-27", 24),   # Day after
    ])
    def test_dst_transitions(self, date_str, expected):
        service = PriceService()
        test_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        assert service._get_expected_hour_count(test_date) == expected