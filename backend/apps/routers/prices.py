from fastapi import APIRouter, HTTPException, Query, Path
from datetime import datetime, timedelta
from typing import Dict
from apps.schemas import PricesResponse, DayPrices
from apps.services.prices import PriceService, PriceServiceError
from config import settings
import io
import csv
from fastapi.responses import StreamingResponse
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/prices", tags=["prices"])

@router.get("/{date}", response_model=PricesResponse)
async def get_prices(
    date: str = Path(
        ...,
        description="Date in YYYY-MM-DD format",
        pattern=r"^\d{4}-\d{2}-\d{2}$"
    ),
    include_metadata: bool = Query(False, description="Include additional metadata")
):
    """
    Retrieve electricity prices for selected date and surrounding days.
    
    Handles:
    - DST transitions (23h/25h days)
    - Missing data points
    - Timezone conversions (UTC → Europe/Vienna)
    - Unit conversions (EUR/MWh → ct/kWh)
    """
    service = PriceService()
    
    try:
        # Validate and parse date
        selected_date = _validate_date(date)
        
        # Calculate date range
        date_range = _calculate_date_range(selected_date)
        
        # Fetch data from API
        raw_data = await service.fetch_market_data(
            date_range["start_ts"],
            date_range["end_ts"]
        )
        
        logger.info(f"Fetched {len(raw_data)} data points for date range")
        
        # Process data for each day
        result = await _process_three_days(
            service, 
            date_range["dates"], 
            raw_data,
            include_metadata
        )
        
        # Validate hour counts
        _validate_hour_counts(result, date_range["dates"])
        
        return result
        
    except PriceServiceError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error processing prices: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


def _validate_date(date_str: str) -> datetime.date:
    """Validate date format and range"""
    try:
        parsed_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        
        # Validate date range (e.g., not too far in future/past)
        today = datetime.now(settings.VIENNA_TZ).date()
        max_future = today + timedelta(days=365)
        min_past = today - timedelta(days=365)
        
        if parsed_date > max_future:
            raise ValueError("Date cannot be more than 1 year in the future")
        if parsed_date < min_past:
            raise ValueError("Date cannot be more than 1 year in the past")
        
        return parsed_date
    except ValueError as e:
        raise ValueError(f"Invalid date format or range: {str(e)}")


def _calculate_date_range(selected_date: datetime.date) -> Dict:
    """Calculate timestamp range for API query"""
    previous_date = selected_date - timedelta(days=1)
    next_date = selected_date + timedelta(days=1)
    
    vienna_tz = settings.VIENNA_TZ
    
    # Create timezone-aware boundaries
    start_dt = datetime.combine(previous_date, datetime.min.time()).replace(tzinfo=vienna_tz)
    end_dt = datetime.combine(next_date + timedelta(days=1), datetime.min.time()).replace(tzinfo=vienna_tz)
    
    return {
        "dates": {
            "previous": previous_date,
            "selected": selected_date,
            "next": next_date
        },
        "start_ts": int(start_dt.timestamp() * 1000),
        "end_ts": int(end_dt.timestamp() * 1000)
    }


async def _process_three_days(
    service: PriceService,
    dates: Dict[str, datetime.date],
    raw_data: list,
    include_metadata: bool
) -> PricesResponse:
    """Process data for all three days"""
    
    # Separate data by day
    day_data = {"previous": [], "selected": [], "next": []}
    
    for entry in raw_data:
        entry_dt = datetime.fromtimestamp(
            entry["start_timestamp"] / 1000,
            tz=settings.VIENNA_TZ
        )
        entry_date = entry_dt.date()
        
        if entry_date == dates["previous"]:
            day_data["previous"].append(entry)
        elif entry_date == dates["selected"]:
            day_data["selected"].append(entry)
        elif entry_date == dates["next"]:
            day_data["next"].append(entry)
    
    # Debug: Log data points per day
    logger.debug(f"Data points - Previous: {len(day_data['previous'])}, "
                f"Selected: {len(day_data['selected'])}, "
                f"Next: {len(day_data['next'])}")
    
    # Create hourly grids
    days_result = {}
    for day_key, day_date in dates.items():
        day_start = datetime.combine(day_date, datetime.min.time()).replace(
            tzinfo=settings.VIENNA_TZ
        )
        
        hours, has_dst = service.create_hourly_grid(
            day_start,
            day_data[day_key]
        )
        
        # Debug: Print hours being processed
        logger.debug(f"{day_key.upper()} ({day_date}): {len(hours)} hours generated, DST: {has_dst}")
        logger.debug(f"  First hour: {hours[0].hour_label if hours else 'N/A'}")
        logger.debug(f"  Last hour: {hours[-1].hour_label if hours else 'N/A'}")
        
        days_result[day_key] = DayPrices(
            date=day_date.isoformat(),
            hours=hours
        )
    
    # Build response
    response = PricesResponse(
        previous_day=days_result["previous"],
        selected_day=days_result["selected"],
        next_day=days_result["next"]
    )
    
    if include_metadata:
        response.metadata = {
            "timezone": str(settings.VIENNA_TZ),
            "conversion_factor": settings.CONVERSION_FACTOR,
            "data_points_received": len(raw_data),
            "processing_timestamp": datetime.now(settings.VIENNA_TZ).isoformat(),
            "hour_counts": {
                "previous": len(days_result["previous"].hours),
                "selected": len(days_result["selected"].hours),
                "next": len(days_result["next"].hours)
            }
        }
    
    return response


def _validate_hour_counts(response: PricesResponse, dates: Dict[str, datetime.date]):
    """Validate that each day has the correct number of hours"""
    service = PriceService()
    
    validations = [
        ("previous_day", dates["previous"], response.previous_day),
        ("selected_day", dates["selected"], response.selected_day),
        ("next_day", dates["next"], response.next_day)
    ]
    
    for day_name, day_date, day_prices in validations:
        expected_hours = service._get_expected_hour_count(day_date)
        actual_hours = len(day_prices.hours)
        
        if actual_hours != expected_hours:
            error_msg = (
                f"Hour count mismatch for {day_name} ({day_date}): "
                f"expected {expected_hours} hours, got {actual_hours} hours"
            )
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        logger.info(f"{day_name} ({day_date}): ✓ {actual_hours} hours (correct)")

@router.get("/{date}/export-csv")
async def export_prices_csv(
    date: str = Path(
        ...,
        description="Date in YYYY-MM-DD format",
        pattern=r"^\d{4}-\d{2}-\d{2}$"
    )
):
    """
    Export electricity prices for three days (previous, selected, next) as CSV.
    Matches the data structure of the main GET endpoint.
    """
    selected_date = _validate_date(date)
    date_range = _calculate_date_range(selected_date)
    
    service = PriceService()
    raw_data = await service.fetch_market_data(
        date_range["start_ts"],
        date_range["end_ts"]
    )
    
    result = await _process_three_days(
        service, 
        date_range["dates"], 
        raw_data,
        include_metadata=False
    )
    
    # Create CSV
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow([
        "date", 
        "hour", 
        "price_eur_mwh", 
        "price_ct_kwh",
        "is_missing",
        "is_dst_transition"
    ])
    
    # Helper to write day data
    def write_day_data(day_prices: DayPrices):
        for hour in day_prices.hours:
            writer.writerow([
                day_prices.date,  # ISO format date string (e.g., "2025-10-25")
                hour.hour_label,
                hour.price_eur_mwh if hour.price_eur_mwh is not None else "",
                hour.price_ct_kwh if hour.price_ct_kwh is not None else "",
                hour.is_missing,
                hour.is_dst_transition
            ])
    
    # Write all three days in order: previous → selected → next
    write_day_data(result.previous_day)
    write_day_data(result.selected_day)
    write_day_data(result.next_day)
    
    output.seek(0)
    
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=electricity_prices_{date}_three_days.csv"
        }
    )