"""metrics/router.py 基础覆盖测试"""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from datetime import date
from app.auth.models import User


@pytest.fixture
def dummy_user():
    return User(id=1, username="cov_user", hashed_password="h", is_active=True, role="user")


class TestMetricsOverview:
    @pytest.mark.asyncio
    async def test_overview_defaults(self, db_session, dummy_user):
        from app.metrics.router import get_overview
        result = await get_overview(
            start_date=None, end_date=None, platform=None,
            db=db_session, current_user=dummy_user,
        )
        assert "total_views" in result
        assert result["total_views"] == 0
        assert result["overall_roi"] == 0

    @pytest.mark.asyncio
    async def test_overview_with_filters(self, db_session, dummy_user):
        from app.metrics.router import get_overview
        result = await get_overview(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
            platform="douyin",
            db=db_session, current_user=dummy_user,
        )
        assert "total_views" in result

    @pytest.mark.asyncio
    async def test_trend(self, db_session, dummy_user):
        from app.metrics.router import get_trend
        result = await get_trend(
            dimension="day",
            start_date=None, end_date=None,
            db=db_session, current_user=dummy_user,
        )
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_aggregate(self, db_session, dummy_user):
        from app.metrics.router import get_aggregate
        result = await get_aggregate(
            by="platform",
            start_date=None, end_date=None, limit=10,
            db=db_session, current_user=dummy_user,
        )
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_funnel(self, db_session, dummy_user):
        from app.metrics.router import get_funnel
        result = await get_funnel(
            task_id=None, start_date=None, end_date=None,
            db=db_session, current_user=dummy_user,
        )
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_list_metrics(self, db_session, dummy_user):
        from app.metrics.router import list_metrics
        result = await list_metrics(
            skip=0, limit=20,
            platform=None, start_date=None, end_date=None,
            db=db_session, current_user=dummy_user,
        )
        assert isinstance(result, list)
