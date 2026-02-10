from pydantic import BaseModel, Field, computed_field
from typing import List, Optional

class HourlyPrice(BaseModel):
    """Single hourly price entry with validation"""
    timestamp_ms: int = Field(..., description="Unix timestamp in milliseconds")
    hour_label: str = Field(..., pattern=r"^\d{2}:\d{2}(?:[A|B])?$", description="Hour in HH:MM format")
    price_eur_mwh: Optional[float] = Field(None, ge=-1000, le=10000)
    price_ct_kwh: Optional[float] = Field(None, ge=-100, le=1000)
    is_missing: bool = False
    is_dst_transition: bool = False
    
    class Config:
        json_schema_extra = {
            "example": {
                "timestamp_ms": 1761433200000,
                "hour_label": "02:00A",
                "price_eur_mwh": 85.5,
                "price_ct_kwh": 8.55,
                "is_missing": False,
                "is_dst_transition": False
            }
        }

class DayPrices(BaseModel):
    date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    hours: List[HourlyPrice]

    @computed_field
    @property
    def total_hours(self) -> int:
        return len(self.hours)

    @computed_field
    @property
    def missing_hours(self) -> int:
        return sum(1 for h in self.hours if h.is_missing)

class PricesResponse(BaseModel):
    """Complete 3-day price response"""
    previous_day: DayPrices
    selected_day: DayPrices
    next_day: DayPrices
    metadata: dict = Field(default_factory=dict)