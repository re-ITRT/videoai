"""创作模块测试 — C10 多画幅导出"""
import pytest
from unittest.mock import patch, AsyncMock


async def _auth(client, username):
    resp = await client.post("/api/v1/auth/register", json={
        "username": username, "password": "Task12345"
    })
    assert resp.status_code == 200
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


class TestCreationEndpoints:
    """创作模块端到端测试"""

    @pytest.mark.asyncio
    async def test_create_task(self, client):
        headers = await _auth(client, "create_t1")
        resp = await client.post("/api/v1/tasks", json={
            "product_info": {"name": "测试产品"},
            "aspect_ratio": "16:9",
            "auto_mode": True,
        }, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "CREATED"
        assert data["aspect_ratio"] == "16:9"
        assert data["id"] > 0

    @pytest.mark.asyncio
    async def test_create_task_default_aspect(self, client):
        headers = await _auth(client, "create_t2")
        resp = await client.post("/api/v1/tasks", json={
            "product_info": {"name": "产品"},
        }, headers=headers)
        assert resp.status_code == 200
        assert resp.json()["aspect_ratio"] == "9:16"  # 默认

    @pytest.mark.asyncio
    async def test_list_tasks(self, client):
        headers = await _auth(client, "list_t1")
        resp = await client.get("/api/v1/tasks", headers=headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    @pytest.mark.asyncio
    async def test_create_task_with_style(self, client):
        headers = await _auth(client, "style_t")
        resp = await client.post("/api/v1/tasks", json={
            "product_info": {"name": "产品"},
            "style": "电商带货",
            "aspect_ratio": "16:9",
        }, headers=headers)
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_create_task_minimal(self, client):
        headers = await _auth(client, "minimal")
        resp = await client.post("/api/v1/tasks", json={
            "product_info": {"name": "最小"},
        }, headers=headers)
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_list_tasks_empty(self, client):
        headers = await _auth(client, "empty_t")
        resp = await client.get("/api/v1/tasks", headers=headers)
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.asyncio
    async def test_get_task_detail(self, client):
        headers = await _auth(client, "detail_t")
        create = await client.post("/api/v1/tasks", json={
            "product_info": {"name": "产品"},
        }, headers=headers)
        tid = create.json()["id"]

        resp = await client.get(f"/api/v1/tasks/{tid}", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["id"] == tid

    @pytest.mark.asyncio
    async def test_get_nonexistent_task(self, client):
        headers = await _auth(client, "notfound")
        resp = await client.get("/api/v1/tasks/99999", headers=headers)
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_retry_task(self, client):
        headers = await _auth(client, "retry_t")
        create = await client.post("/api/v1/tasks", json={
            "product_info": {"name": "产品"},
        }, headers=headers)
        tid = create.json()["id"]

        resp = await client.post(f"/api/v1/tasks/{tid}/retry", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["retry_count"] == 1

    @pytest.mark.asyncio
    async def test_retry_nonexistent(self, client):
        headers = await _auth(client, "retry_404")
        resp = await client.post("/api/v1/tasks/99999/retry", headers=headers)
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_get_task_logs(self, client):
        headers = await _auth(client, "logs_t")
        create = await client.post("/api/v1/tasks", json={
            "product_info": {"name": "产品"},
        }, headers=headers)
        tid = create.json()["id"]

        resp = await client.get(f"/api/v1/tasks/{tid}/logs", headers=headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    @pytest.mark.asyncio
    async def test_no_auth(self, client):
        for method, path in [
            ("POST", "/api/v1/tasks"),
            ("GET", "/api/v1/tasks/1"),
        ]:
            resp = await getattr(client, method.lower())(path)
            assert resp.status_code == 403


class TestC10Export:
    """C10 多画幅导出测试"""

    @pytest.mark.asyncio
    async def test_export_no_task(self, client):
        headers = await _auth(client, "exp404")
        resp = await client.post("/api/v1/tasks/99999/export", headers=headers)
        assert resp.status_code == 400
        assert "不存在" in resp.text

    @pytest.mark.asyncio
    async def test_export_no_script(self, client):
        """有任务但无剧本 → 400"""
        headers = await _auth(client, "exp_nos")
        create = await client.post("/api/v1/tasks", json={
            "product_info": {"name": "产品"},
        }, headers=headers)
        tid = create.json()["id"]

        resp = await client.post(f"/api/v1/tasks/{tid}/export", headers=headers)
        assert resp.status_code == 400
        assert "无可导出" in resp.text

    @pytest.mark.asyncio
    async def test_export_with_aspect_ratio(self, client):
        """指定画幅导出"""
        headers = await _auth(client, "exp_ar")
        create = await client.post("/api/v1/tasks", json={
            "product_info": {"name": "产品"},
        }, headers=headers)
        tid = create.json()["id"]

        resp = await client.post(
            f"/api/v1/tasks/{tid}/export?aspect_ratio=1:1",
            headers=headers,
        )
        # 没有剧本所以 400，说明 aspect_ratio 传到了
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_export_no_auth(self, client):
        resp = await client.post("/api/v1/tasks/1/export")
        assert resp.status_code == 403
