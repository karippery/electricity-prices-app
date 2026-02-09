from dataclasses import dataclass, field
from zoneinfo import ZoneInfo
from typing import List

@dataclass(frozen=True)
class Settings:
    """Application configuration"""
    API_URL: str = "https://api.awattar.at/v1/marketdata"
    VIENNA_TZ: ZoneInfo = ZoneInfo("Europe/Vienna")
    CONVERSION_FACTOR: float = 10.0  # EUR/MWh to ct/kWh
    MAX_HOURS_PER_DAY: int = 26
    API_TIMEOUT: float = 30.0
    CORS_ORIGINS: List[str] = field(default_factory=lambda: ["http://localhost:3000", "http://localhost:5173"])

settings = Settings()