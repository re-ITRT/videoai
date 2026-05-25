"""用户模块测试 — 覆盖 /me 相关端点"""
import pytest


class TestUserEndpoints:

    @pytest.mark.asyncio
    async def test_full_user_flow(self, client):
        """注册 → 查看/修改个人资料 → 改密码"""
        # 使用唯一用户名避免冲突
        username, password = f"flowuser_{id(self)}", "Flow1234"

        # 注册
        resp = await client.post("/api/v1/auth/register", json={
            "username": username, "password": password, "nickname": "测试用户"
        })
        assert resp.status_code == 200
        token = resp.json()["access_token"]

        # GET /me
        resp = await client.get(
            "/api/v1/users/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 200
        assert resp.json()["username"] == username

        # PUT /me 更新昵称
        resp = await client.put(
            "/api/v1/users/me",
            json={"nickname": "新昵称", "email": "new@test.com"},
            headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 200
        assert resp.json()["nickname"] == "新昵称"

        # PUT /me/password 改密码
        resp = await client.put(
            "/api/v1/users/me/password",
            json={"old_password": password, "new_password": "NewPass888"},
            headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_user_endpoints_no_auth(self, client):
        """无 token 访问用户端点 → 403"""
        resp = await client.get("/api/v1/users/me")
        assert resp.status_code == 403
        resp = await client.put("/api/v1/users/me")
        assert resp.status_code == 403
        resp = await client.put("/api/v1/users/me/password")
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_change_password_wrong_old(self, client):
        """旧密码错误 → 400"""
        resp = await client.post("/api/v1/auth/register", json={
            "username": f"pwuser_{id(self)}", "password": "OldPass123"
        })
        token = resp.json()["access_token"]
        resp = await client.put(
            "/api/v1/users/me/password",
            json={"old_password": "wrongold", "new_password": "NewPass123"},
            headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 400
