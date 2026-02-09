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
        current_time = day_start
        has_dst_transition = False

        while current_time < day_end:
            timestamp_ms = int(current_time.timestamp() * 1000)
            
            # Compute next hour
            next_time = current_time + timedelta(hours=1)
            next_timestamp_ms = int(next_time.timestamp() * 1000)

            # Handle SPRING-FORWARD (non-existent hour): skip if timestamps are equal
            if timestamp_ms == next_timestamp_ms:
                logger.debug(f"Skipping non-existent hour during DST spring forward: {current_time}")
                has_dst_transition = True
                current_time = next_time
                continue

            # Detect DST transition: compare UTC offsets between current and next hour
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
        
        # Count actual hours that exist (accounting for DST gaps)
        current_time = day_start
        hour_count = 0
        
        while current_time < day_end:
            timestamp_ms = int(current_time.timestamp() * 1000)
            next_time = current_time + timedelta(hours=1)
            next_timestamp_ms = int(next_time.timestamp() * 1000)
            
            # Skip DST gaps (hours that don't exist)
            if timestamp_ms != next_timestamp_ms:
                hour_count += 1
            
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