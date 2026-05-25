"""用户管理端点测试 — 覆盖 admin 路径"""
import pytest


class TestAdminEndpoints:
    """管理员 API 测试"""

    @pytest.mark.asyncio
    async def test_admin_user_list_and_management(self, client, db_session):
        """注册普通用户 → 提升为 admin → 使用 admin API"""

        # 注册 admin 用户
        resp = await client.post("/api/v1/auth/register", json={
            "username": "admintest", "password": "Admin1234"
        })
        assert resp.status_code == 200
        admin_token = resp.json()["access_token"]

        # 通过 service 层直接提升为 admin
        from app.auth.service import get_user_by_username
        from sqlalchemy import update
        from app.auth.models import User

        admin_user = await get_user_by_username(db_session, "admintest")
        assert admin_user is not None

        # 直接修改 role
        from sqlalchemy import select
        stmt = select(User).where(User.id == admin_user.id)
        result = await db_session.execute(stmt)
        user = result.scalar_one()
        user.role = "admin"
        await db_session.commit()

        # 重新登录获取 admin token
        resp = await client.post("/api/v1/auth/login", json={
            "username": "admintest", "password": "Admin1234"
        })
        admin_token = resp.json()["access_token"]

        # 注册一个普通用户
        await client.post("/api/v1/auth/register", json={
            "username": "normaluser", "password": "Normal123"
        })

        # GET /users/ — 管理员获取用户列表
        resp = await client.get(
            "/api/v1/users/",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert resp.status_code == 200
        users = resp.json()
        assert isinstance(users, list)
        assert len(users) >= 2

        # 找到普通用户的 id
        normal_id = None
        for u in users:
            if u["username"] == "normaluser":
                normal_id = u["id"]
                break
        assert normal_id is not None

        # PATCH /users/{id} — 管理员修改用户
        resp = await client.patch(
            f"/api/v1/users/{normal_id}",
            json={"nickname": "AdminUpdated", "is_active": False},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert resp.status_code == 200
        assert resp.json()["nickname"] == "AdminUpdated"
        assert resp.json()["is_active"] is False

        # DELETE /users/{id} — 管理员删除用户
        resp = await client.delete(
            f"/api/v1/users/{normal_id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert resp.status_code == 204

    @pytest.mark.asyncio
    async def test_admin_get_users_non_admin(self, client, db_session):
        """非管理员获取用户列表 → 403"""
        resp = await client.post("/api/v1/auth/register", json={
            "username": "reguser", "password": "Reg12345"
        })
        token = resp.json()["access_token"]

        resp = await client.get(
            "/api/v1/users/",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_admin_patch_user_non_admin(self, client):
        """非管理员 PATCH 用户 → 403"""
        resp = await client.post("/api/v1/auth/register", json={
            "username": "patchuser1", "password": "Patch123"
        })
        token = resp.json()["access_token"]
        user_id = resp.json()["user"]["id"]

        resp = await client.patch(
            f"/api/v1/users/{user_id}",
            json={"nickname": "hacked"},
            headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_admin_delete_user_non_admin(self, client):
        """非管理员 DELETE 用户 → 403"""
        resp = await client.post("/api/v1/auth/register", json={
            "username": "deluser", "password": "Del12345"
        })
        token = resp.json()["access_token"]

        resp = await client.delete(
            "/api/v1/users/1",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 403
