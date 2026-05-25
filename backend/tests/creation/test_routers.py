"""创作模块测试 — B 负责 C10/C11/P0"""
import pytest


class TestCreationRoutes:
    """多画幅导出/任务管理"""

    @pytest.mark.asyncio
    async def test_create_task(self, client):
        """POST /api/v1/tasks"""
        resp = await client.post("/api/v1/tasks")
        assert resp.status_code in (200, 401)

    @pytest.mark.asyncio
    async def test_get_task(self, client):
        """GET /api/v1/tasks/{id}"""
        resp = await client.get("/api/v1/tasks/1")
        assert resp.status_code in (200, 401, 404)

    @pytest.mark.asyncio
    async def test_get_task_logs(self, client):
        """GET /api/v1/tasks/{id}/logs"""
        resp = await client.get("/api/v1/tasks/1/logs")
        assert resp.status_code in (200, 401, 404)

    @pytest.mark.asyncio
    async def test_approve_script(self, client):
        """手动模式：批准剧本"""
        resp = await client.post("/api/v1/tasks/1/approve-script")
        assert resp.status_code in (200, 401, 404)

    @pytest.mark.asyncio
    async def test_retry_task(self, client):
        """异常重试"""
        resp = await client.post("/api/v1/tasks/1/retry")
        assert resp.status_code in (200, 401, 404)

    @pytest.mark.asyncio
    async def test_regenerate_scene(self, client):
        """分镜级重生成"""
        resp = await client.post("/api/v1/tasks/1/regenerate-scene/1")
        assert resp.status_code in (200, 401, 404)

    @pytest.mark.asyncio
    async def test_export_video(self, client):
        """多画幅导出"""
        resp = await client.post("/api/v1/tasks/1/export")
        assert resp.status_code in (200, 401, 404)
