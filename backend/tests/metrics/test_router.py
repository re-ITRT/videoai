"""metrics/router.py 全覆盖测试"""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from app.auth.models import User


@pytest.fixture
def dummy_user():
    return User(id=1, username="cov_user", hashed_password="h", is_active=True, role="user")


class TestMetrics:
    @pytest.mark.asyncio
    async def test_overview_empty(self, db_session, dummy_user):
        from app.metrics.router import get_overview
        result = await get_overview(db=db_session, current_user=dummy_user)
        assert "total_views" in result
        assert result["total_views"] == 0

    @pytest.mark.asyncio
    async def test_trend_empty(self, db_session, dummy_user):
        from app.metrics.router import get_trend
        result = await get_trend(dimension="day", db=db_session, current_user=dummy_user)
        assert isinstance(result, list) or "data" in str(result)

    @pytest.mark.asyncio
    async def test_aggregate_empty(self, db_session, dummy_user):
        from app.metrics.router import get_aggregate
        result = await get_aggregate(by="platform", db=db_session, current_user=dummy_user)
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_funnel_empty(self, db_session, dummy_user):
        from app.metrics.router import get_funnel
        result = await get_funnel(db=db_session, current_user=dummy_user)
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_list_metrics_empty(self, db_session, dummy_user):
        from app.metrics.router import list_metrics
        result = await list_metrics(db=db_session, current_user=dummy_user)
        assert isinstance(result, list)
