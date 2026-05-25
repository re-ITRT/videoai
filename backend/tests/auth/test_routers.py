"""认证模块测试"""
import pytest


class TestAuthSchemas:

    def test_username_validator(self):
        from app.auth.schemas import RegisterRequest
        req = RegisterRequest(username="hello_world", password="Pass1234")
        assert req.username == "hello_world"

    def test_username_invalid(self):
        from pydantic import ValidationError
        from app.auth.schemas import RegisterRequest
        with pytest.raises(ValidationError):
            RegisterRequest(username="bad@name", password="Pass1234")


class TestAuthFlow:
    """认证全流程 — 使用同一个 client 保证 DB 一致性"""

    @pytest.mark.asyncio
    async def test_full_auth_flow(self, client):
        """注册 → 登录 → 获取用户信息 → 刷新令牌"""
        login_data = {"username": "flowuser", "password": "Flow1234"}

        # 1. 注册
        resp = await client.post("/api/v1/auth/register", json={
            **login_data, "nickname": "Flow"
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["user"]["username"] == "flowuser"
        access_token = data["access_token"]
        refresh_token = data["refresh_token"]

        # 2. 重复注册 → 409
        resp = await client.post("/api/v1/auth/register", json={**login_data})
        assert resp.status_code == 409

        # 3. 用 token 获取用户信息
        resp = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        assert resp.status_code == 200
        assert resp.json()["username"] == "flowuser"

        # 4. 刷新令牌
        resp = await client.post("/api/v1/auth/refresh", json={
            "refresh_token": refresh_token
        })
        assert resp.status_code == 200
        assert "access_token" in resp.json()

    @pytest.mark.asyncio
    async def test_register_invalid_username(self, client):
        """特殊字符用户名应拒绝"""
        resp = await client.post("/api/v1/auth/register", json={
            "username": "bad@user", "password": "Pass1234"
        })
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, client):
        resp = await client.post("/api/v1/auth/login", json={
            "username": "nobody", "password": "wrongpw"
        })
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_me_requires_auth(self, client):
        """无 token 返回 403"""
        resp = await client.get("/api/v1/auth/me")
        assert resp.status_code == 403
