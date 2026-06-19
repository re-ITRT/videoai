"""逐个啃 studio/router.py + metrics + user + core 剩余小行"""
import json, pytest
from unittest.mock import patch, AsyncMock, MagicMock, mock_open
from fastapi import HTTPException
from app.auth.models import User


@pytest.fixture
def dummy_user():
    return User(id=1, username="cov_user", hashed_password="h", is_active=True, role="user")


class TestStudioTinyLines:
    """覆盖 studio/router.py 的小单行"""

    def test_get_state_path_uses_session_dir(self):
        """line 48: get_state_path 正常路径"""
        from app.studio.router import get_state_path
        with patch("app.agent.models.ensure_session_dir",
                   return_value={"root": "/tmp/s/1"}):
            path = get_state_path(1)
            assert path is not None and "workflow_state.json" in path

    @pytest.mark.asyncio
    async def test_semantic_search_empty_body(self, db_session, dummy_user):
        """line 191: semantic-search 无 product_queries"""
        from app.studio.router import semantic_search
        async def fake_cwf(name, params):
            if name == "query-generate":
                return {}
            return {}
        with patch("app.workers.workflow.call_workflow", new=fake_cwf):
            result = await semantic_search({"product_info": {"title": "t"}}, db_session, dummy_user)
            assert result["total"] == 0

    @pytest.mark.asyncio
    async def test_generate_no_scene_mids_from_collection(self, db_session, dummy_user):
        """line 303,313: generate-video 从 state collection 取素材"""
        from app.studio.router import studio_generate_video
        from app.workflow.models import WorkflowConfig
        wfc = WorkflowConfig(
            user_id=str(dummy_user.id), workflow_name="video-generate",
            enabled=1, config=json.dumps({"api_key": "sk-test"}),
        )
        db_session.add(wfc)
        await db_session.flush()
        script = json.dumps({"script": {"scenes": [{"scene_id": 1, "duration": 5, "lines": []}], "title": "t", "style": "s"}})
        state_data = json.dumps({"selected_collection_id": 1, "collections": [{"id": 1, "material_ids": []}]})
        def mock_open_wrapper(*a, **kw):
            if "workflow_state.json" in str(a):
                return mock_open(read_data=state_data)(*a, **kw)
            return mock_open(read_data=script)(*a, **kw)
        with patch("app.studio.router.add_trace", new_callable=AsyncMock), \
             patch("os.path.exists", return_value=True), \
             patch("os.makedirs"), \
             patch("app.agent.models.ensure_session_dir", return_value={"root": "/tmp", "scripts": "/tmp/scripts"}), \
             patch("builtins.open", mock_open_wrapper), \
             patch("app.workflow.runners.video_generate.run_video_generate", new_callable=AsyncMock) as rvg:
            rvg.return_value = {"result": {"task_ids": [{"scene_id": 1}]}}
            result = await studio_generate_video({"session_id": 1}, db_session, dummy_user)
            assert result["submitted"] is True


class TestMetricsRemaining:
    """覆盖 metrics/router.py 剩余小行 (lines 78,92,94,130-133,146,148)"""

    @pytest.mark.asyncio


    @pytest.mark.asyncio
    async def test_aggregate_region(self, db_session, dummy_user):
        """line 130-131: get_aggregate by=region"""
        from app.metrics.router import get_aggregate
        result = await get_aggregate(
            by="region", start_date=None, end_date=None, limit=10,
            db=db_session, current_user=dummy_user,
        )
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_aggregate_template(self, db_session, dummy_user):
        """line 132-133: get_aggregate by=template"""
        from app.metrics.router import get_aggregate
        result = await get_aggregate(
            by="template", start_date=None, end_date=None, limit=10,
            db=db_session, current_user=dummy_user,
        )
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_trend_with_start_end(self, db_session, dummy_user):
        """line 92,94: get_trend with date filters"""
        from app.metrics.router import get_trend
        from datetime import date
        result = await get_trend(
            dimension="day", start_date=date(2024,1,1), end_date=date(2024,12,31),
            db=db_session, current_user=dummy_user,
        )
        assert isinstance(result, list)


class TestCoreSmall:
    """覆盖 core/database.py + core/ws_manager.py"""

    @pytest.mark.asyncio
    async def test_db_session_context(self):
        """core/database.py 导入"""
        from app.core.database import get_db, async_session
        assert get_db is not None

    def test_ws_manager(self):
        """core/ws_manager.py 基础"""
        from app.core.ws_manager import manager
        assert manager is not None


class TestUserTinyLines:
    """覆盖 user/router.py 剩余 (lines 47-51, 96-97, 119)"""

    @pytest.mark.asyncio
    async def test_get_users_list(self, db_session):
        from app.user.router import get_users_list
        admin = User(id=99, username="admin", hashed_password="h", is_active=True, role="admin")
        result = await get_users_list(skip=0, limit=100, db=db_session, admin=admin)
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_update_my_profile_value_error(self, db_session, dummy_user):
        """line 47-51: update_my_profile 抛出 ValueError"""
        from app.user.router import update_my_profile
        from app.user.schemas import UserUpdateRequest
        with patch("app.user.router.update_user_profile", new_callable=AsyncMock,
                   side_effect=ValueError("invalid")):
            with pytest.raises(HTTPException) as exc:
                await update_my_profile(
                    UserUpdateRequest(), current_user=dummy_user, db=db_session,
                )
            assert exc.value.status_code == 400
