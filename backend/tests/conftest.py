import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
import freezegun
from datetime import datetime
from zoneinfo import ZoneInfo

# Add backend to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from main import app
from apps.services.prices import PriceService

# Fix event loop policy for Windows
@pytest.fixture(scope="session", autouse=True)
def configure_event_loop():
    if sys.platform == "win32":
        import asyncio
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def mock_price_service():
    with patch("apps.routers.prices.PriceService") as mock:
        service_mock = AsyncMock(spec=PriceService)
        mock.return_value = service_mock
        yield service_mock

# ✅ CORRECTED FIXTURES — using real timezone-aware datetimes
@pytest.fixture
def freeze_october_2025_dst():
    """Freeze during fall-back DST transition in Vienna (2025-10-26)"""
    vienna_tz = ZoneInfo("Europe/Vienna")
    frozen_dt = datetime(2025, 10, 26, 12, 0, 0, tzinfo=vienna_tz)
    with freezegun.freeze_time(frozen_dt):
        yield

@pytest.fixture
def freeze_march_2025_dst():
    """Freeze during spring-forward DST transition in Vienna (2025-03-30)"""
    vienna_tz = ZoneInfo("Europe/Vienna")
    frozen_dt = datetime(2025, 3, 30, 12, 0, 0, tzinfo=vienna_tz)
    with freezegun.freeze_time(frozen_dt):
        yield