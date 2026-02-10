from datetime import datetime, timedelta
from typing import List, Dict, Tuple
import httpx
from apps.schemas import HourlyPrice
from config import settings
import logging

logger = logging.getLogger(__name__)

class PriceService:
    """Handles electricity price business logic"""
    
    def __init__(self, api_client: httpx.AsyncClient = None):
        self.api_client = api_client or httpx.AsyncClient(
            timeout=settings.API_TIMEOUT
        )
        self.vienna_tz = settings.VIENNA_TZ
    
    async def fetch_market_data(self, start_ts: int, end_ts: int) -> List[Dict]:
        """Fetch raw data from aWATTar API with retry logic"""
        try:
            response = await self.api_client.get(
                settings.API_URL,
                params={"start": start_ts, "end": end_ts}
            )
            response.raise_for_status()
            data = response.json()
            return data.get("data", [])
        except httpx.HTTPError as e:
            raise PriceServiceError(f"API fetch failed: {str(e)}") from e
    
    def create_hourly_grid(self, date: datetime, raw_data: List[Dict]) -> Tuple[List[HourlyPrice], bool]:
        target_date = date.date() if isinstance(date, datetime) else date
        
        day_start = datetime(target_date.year, target_date.month, target_date.day, 0, 0, tzinfo=self.vienna_tz)
        day_end = day_start + timedelta(days=1)

        price_map = {entry["start_timestamp"]: entry["marketprice"] for entry in raw_data}
        
        hourly_prices = []
        has_dst_transition = False
        seen_timestamps = set()
        
        current_time = day_start

        while current_time < day_end:
            timestamp_ms = int(current_time.timestamp() * 1000)
            next_time = current_time + timedelta(hours=1)
            next_timestamp_ms = int(next_time.timestamp() * 1000)

            # Handle SPRING-FORWARD (non-existent hour): skip if timestamps are equal
            if timestamp_ms == next_timestamp_ms:
                logger.debug(f"Skipping non-existent hour during spring forward: {current_time}")
                has_dst_transition = True
                # Don't add to seen_timestamps - we haven't processed this hour!
                # Just move to the next hour
                current_time = next_time
                continue
            
            # Skip if already processed
            if timestamp_ms in seen_timestamps:
                current_time = current_time + timedelta(hours=1)
                continue
            
            seen_timestamps.add(timestamp_ms)

            # Detect DST transition
            is_dst_transition = current_time.utcoffset() != next_time.utcoffset()
            if is_dst_transition:
                has_dst_transition = True

            price_eur_mwh = price_map.get(timestamp_ms)

            hourly_prices.append(HourlyPrice(
                timestamp_ms=timestamp_ms,
                hour_label=self._format_hour_label(current_time),
                price_eur_mwh=price_eur_mwh,
                price_ct_kwh=self._convert_to_ct_kwh(price_eur_mwh) if price_eur_mwh is not None else None,
                is_missing=(price_eur_mwh is None),
                is_dst_transition=is_dst_transition
            ))

            # CRITICAL: Handle fall-back duplicated hour
            # When falling back, the CURRENT hour has a fold=1 version that's different
            if is_dst_transition and current_time.utcoffset() > next_time.utcoffset():
                # This is a fall-back transition
                # Check if the current hour has a fold=1 version
                try:
                    current_fold1 = datetime(
                        current_time.year, current_time.month, current_time.day,
                        current_time.hour, current_time.minute, current_time.second,
                        tzinfo=self.vienna_tz, fold=1
                    )
                    current_fold1_ms = int(current_fold1.timestamp() * 1000)
                    
                    # If fold=1 creates a different timestamp, add it
                    if current_fold1_ms != timestamp_ms and current_fold1_ms not in seen_timestamps:
                        seen_timestamps.add(current_fold1_ms)
                        price_eur_mwh_fold1 = price_map.get(current_fold1_ms)
                        
                        hourly_prices.append(HourlyPrice(
                            timestamp_ms=current_fold1_ms,
                            hour_label=self._format_hour_label(current_fold1),
                            price_eur_mwh=price_eur_mwh_fold1,
                            price_ct_kwh=self._convert_to_ct_kwh(price_eur_mwh_fold1) if price_eur_mwh_fold1 is not None else None,
                            is_missing=(price_eur_mwh_fold1 is None),
                            is_dst_transition=False
                        ))
                        logger.debug(f"Added duplicate hour: {current_time.hour}:00 (fold=1)")
                except Exception as e:
                    logger.debug(f"No fold=1 for current hour: {e}")

            current_time = next_time

        logger.debug(f"Generated {len(hourly_prices)} hours for {target_date}, DST transition: {has_dst_transition}")
        return hourly_prices, has_dst_transition
    
    def _get_expected_hour_count(self, target_date) -> int:
        """
        Calculate expected number of hours for a given date.
        
        - Normal day: 24 hours
        - DST start (spring forward): 23 hours (March, last Sunday)
        - DST end (fall back): 25 hours (October, last Sunday)
        
        This method actually counts hours that exist, accounting for DST gaps/overlaps.
        """
        day_start = datetime(target_date.year, target_date.month, target_date.day, 0, 0, tzinfo=self.vienna_tz)
        next_day_date = target_date + timedelta(days=1)
        day_end = datetime(next_day_date.year, next_day_date.month, next_day_date.day, 0, 0, tzinfo=self.vienna_tz)
        
        # Count actual hours that exist (accounting for DST gaps and duplicates)
        current_time = day_start
        hour_count = 0
        seen_timestamps = set()
        
        while current_time < day_end:
            timestamp_ms = int(current_time.timestamp() * 1000)
            next_time = current_time + timedelta(hours=1)
            next_timestamp_ms = int(next_time.timestamp() * 1000)
            
            # Skip DST gaps (hours that don't exist - spring forward)
            if timestamp_ms == next_timestamp_ms:
                # Don't add to seen_timestamps - this hour doesn't exist!
                current_time = next_time
                continue
            
            # Skip if already counted
            if timestamp_ms in seen_timestamps:
                current_time = current_time + timedelta(hours=1)
                continue
            
            seen_timestamps.add(timestamp_ms)
            
            # Count this hour
            hour_count += 1
            
            # Check for fall-back: if UTC offset decreases, the CURRENT hour has a fold=1 version
            if current_time.utcoffset() != next_time.utcoffset() and current_time.utcoffset() > next_time.utcoffset():
                # The current hour occurs twice (fold=0 and fold=1)
                try:
                    current_fold1 = datetime(
                        current_time.year, current_time.month, current_time.day,
                        current_time.hour, current_time.minute, current_time.second,
                        tzinfo=self.vienna_tz, fold=1
                    )
                    current_fold1_ms = int(current_fold1.timestamp() * 1000)
                    
                    # Verify it's actually different (confirms ambiguous hour exists)
                    if current_fold1_ms != timestamp_ms and current_fold1_ms not in seen_timestamps:
                        seen_timestamps.add(current_fold1_ms)
                        hour_count += 1  # Count the duplicate hour
                except Exception:
                    pass
            
            current_time = next_time
        
        return hour_count
    
    def _format_hour_label(self, dt: datetime) -> str:
        """Format hour label, handling the 2A/2B notation for October DST transition"""
        base_label = dt.strftime("%H:%M")
        
        # In Europe, the 'fall back' happens in October at 3:00 -> 2:00
        # The hour 02:00-03:00 occurs twice
        # 'fold=0' is the first occurrence (CEST), 'fold=1' is the second (CET)
        if dt.month == 10 and dt.hour == 2:
            return f"{base_label}A" if dt.fold == 0 else f"{base_label}B"
        
        return base_label
    
    def _convert_to_ct_kwh(self, price_eur_mwh: float) -> float:
        """Convert EUR/MWh to ct/kWh"""
        return round(price_eur_mwh / settings.CONVERSION_FACTOR, 2)


class PriceServiceError(Exception):
    """Custom exception for price service errors"""
    pass