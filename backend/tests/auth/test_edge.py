"""认证模块扩展测试 — 覆盖边缘路径"""
import pytest


class TestAuthEdgeCases:
    """覆盖 auth/router.py 未触及的分支"""

    @pytest.mark.asyncio
    async def test_logout_no_token(self, client):
        """无 token 注销 → 403"""
        resp = await client.post("/api/v1/auth/logout")
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_refresh_invalid_token(self, client):
        """无效刷新令牌 → 401（jose decode 失败）"""
        resp = await client.post("/api/v1/auth/refresh", json={
            "refresh_token": "totally_invalid_token"
        })
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_refresh_token_no_sub(self, client):
        """刷新令牌 payload 缺少 sub → 401"""
        from app.core.security import create_refresh_token
        token = create_refresh_token(data={"something": "else"})
        resp = await client.post("/api/v1/auth/refresh", json={
            "refresh_token": token
        })
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_refresh_nonexistent_user(self, client):
        """刷新令牌指向不存在的用户 → 401"""
        from app.core.security import create_refresh_token
        token = create_refresh_token(data={"sub": "99999", "type": "refresh"})
        resp = await client.post("/api/v1/auth/refresh", json={
            "refresh_token": token
        })
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_refresh_wrong_type(self, client):
        """access_token 当 refresh_token 用 → 401（type 校验失败）"""
        from app.core.security import create_access_token
        token = create_access_token(data={"sub": "1"})
        resp = await client.post("/api/v1/auth/refresh", json={
            "refresh_token": token
        })
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_auth_me_without_token(self, client):
        """/auth/me 无 token → 403"""
        resp = await client.get("/api/v1/auth/me")
        assert resp.status_code == 403
