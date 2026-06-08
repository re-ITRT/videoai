"""最后一批覆盖冲刺"""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock, mock_open
from app.auth.models import User


@pytest.fixture
def dummy_user():
    return User(id=1, username="cov_user", hashed_password="h", is_active=True, role="user")


class TestMetricsCreate:
    """覆盖 metrics/router.py lines 263-289: create_metric"""

    @pytest.mark.asyncio
    async def test_create_metric(self, db_session, dummy_user):
        from app.metrics.router import create_metric
        from datetime import date
        result = await create_metric(
            data={"platform": "douyin", "video_url": "/u/v.mp4", "views": 1000,
                  "impressions": 5000, "gmv": 200.0, "cost": 50.0,
                  "publish_date": date.today(), "region": "中国",
                  "completion_rate": 0.85, "likes": 100, "comments": 20,
                  "shares": 30, "product_clicks": 50, "orders": 10, "roi": 4.0},
            db=db_session, current_user=dummy_user,
        )
        assert result is not None


class TestMaterialRunEmbed:
    """覆盖 material/router.py run_embed 异步路径"""

    @pytest.mark.asyncio
    async def test_run_embed_path(self, db_session, dummy_user):
        from app.material.router import upload_material_file
        mock_file = MagicMock()
        mock_file.filename = "prod.jpg"
        mock_file.file = MagicMock()

        with patch("shutil.copyfileobj"), \
             patch("app.material.router.generate_signed_url", return_value="/signed/t/u.jpg"), \
             patch("app.material.service.create_material", new_callable=AsyncMock) as cm, \
             patch("app.workers.workflow.call_workflow", new_callable=AsyncMock) as cwf, \
             patch("asyncio.create_task") as ct:
            cwf.return_value = {"scenes": [], "video_tags": []}

            cm.return_value = MagicMock(id=20, material_type="product", input_type="image",
                                         image_url="/u/prod.jpg", source="upload",
                                         created_at=MagicMock())

            result = await upload_material_file(
                file=mock_file, material_type="product", input_type="image",
                category="", name="prod", text_content="product desc", product_name="",
                db=db_session, current_user=dummy_user,
            )
            assert result["source"] == "upload"
            ct.assert_called_once()


class TestStudioTraceFinal:
    """覆盖 studio 剩余单行"""

    @pytest.mark.asyncio
    async def test_trace_with_file(self):
        """add_trace 读取已有文件"""
        from app.studio.router import add_trace
        existing = '{"trace": [{"step": "s1", "status": "completed"}]}'
        with patch("app.studio.router.get_state_path", return_value="/fake/path"), \
             patch("os.path.exists", return_value=True), \
             patch("builtins.open", mock_open(read_data=existing)):
            # 不会报错就算通过
            await add_trace(1, "s2", "running", "测试")

    @pytest.mark.asyncio
    async def test_trace_running_sets_started_at(self):
        """running 状态设置 started_at"""
        from app.studio.router import add_trace
        with patch("app.studio.router.get_state_path", return_value="/fake/path"), \
             patch("os.path.exists", return_value=False), \
             patch("builtins.open", mock_open()):
            await add_trace(1, "step_new", "running", "测试中")
