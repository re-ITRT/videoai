"""直接覆盖服务层和派发器 — 解决 ASGI 覆盖率追踪盲区"""
import pytest


class TestAuthRouterDirect:
    """直接调用 router 函数（绕过 httpx ASGI）"""

    @pytest.mark.asyncio
    async def test_register_happy_path(self, db_session):
        """直接调用 register handler"""
        from app.auth.router import register
        from app.auth.schemas import RegisterRequest

        req = RegisterRequest(username="direct_reg", password="Direct1234")
        resp = await register(request=req, db=db_session)
        assert resp.access_token is not None
        assert resp.user.username == "direct_reg"

    @pytest.mark.asyncio
    async def test_login_happy_path(self, db_session):
        from app.auth.router import register, login
        from app.auth.schemas import RegisterRequest, LoginRequest

        await register(request=RegisterRequest(username="direct_login", password="Direct1234"), db=db_session)
        resp = await login(request=LoginRequest(username="direct_login", password="Direct1234"), db=db_session)
        assert resp.access_token is not None
        assert resp.refresh_token is not None
        assert resp.user.username == "direct_login"

    @pytest.mark.asyncio
    async def test_refresh_happy_path(self, db_session):
        from app.auth.router import register, refresh
        from app.auth.schemas import RegisterRequest, TokenRefreshRequest

        reg_resp = await register(
            request=RegisterRequest(username="direct_refresh", password="Direct1234"),
            db=db_session
        )
        resp = await refresh(
            request=TokenRefreshRequest(refresh_token=reg_resp.refresh_token),
            db=db_session
        )
        assert resp.access_token is not None

    @pytest.mark.asyncio
    async def test_login_inactive_user(self, db_session):
        """直接测试登录禁用用户"""
        from app.auth.router import register, login
        from app.auth.schemas import RegisterRequest, LoginRequest
        from fastapi import HTTPException
        from app.auth.service import get_user_by_username

        await register(
            request=RegisterRequest(username="inactive_direct", password="Inact1234"),
            db=db_session
        )

        # 直接标记为 inactive
        user = await get_user_by_username(db_session, "inactive_direct")
        user.is_active = False
        await db_session.commit()

        with pytest.raises(HTTPException) as exc:
            await login(
                request=LoginRequest(username="inactive_direct", password="Inact1234"),
                db=db_session
            )
        assert exc.value.status_code == 403


class TestCoreDepsDirect:
    """直接测试 deps 函数"""

    @pytest.mark.asyncio
    async def test_get_current_user_invalid_token(self, db_session):
        from fastapi import HTTPException
        from app.core.deps import get_current_user

        # 模拟一个无效的 Bearer token
        from fastapi.security import HTTPAuthorizationCredentials
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="invalid_token")

        with pytest.raises(HTTPException) as exc:
            await get_current_user(credentials=creds, db=db_session)
        assert exc.value.status_code == 401


class TestUserRouterDirect:
    """直接调用 user router"""

    @pytest.mark.asyncio
    async def test_get_my_info(self, db_session):
        from app.auth.router import register
        from app.auth.schemas import RegisterRequest
        from app.user.router import get_my_info

        reg_resp = await register(
            request=RegisterRequest(username="direct_me", password="Me12345"),
            db=db_session
        )
        resp = await get_my_info(current_user=reg_resp.user)
        assert resp.username == "direct_me"

    @pytest.mark.asyncio
    async def test_admin_delete_not_found(self, db_session):
        from fastapi import HTTPException
        from app.user.router import admin_delete_user_by_id
        from app.auth.models import User

        admin = User(id=999, username="admin", hashed_password="hash", role="admin")
        admin.is_active = True

        with pytest.raises(HTTPException) as exc:
            await admin_delete_user_by_id(user_id=99999, db=db_session, admin=admin)
        assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_admin_update_not_found(self, db_session):
        from fastapi import HTTPException
        from app.user.router import admin_update_user_by_id
        from app.user.schemas import UserAdminUpdateRequest
        from app.auth.models import User

        admin = User(id=999, username="admin", hashed_password="hash", role="admin")
        admin.is_active = True

        with pytest.raises(HTTPException) as exc:
            await admin_update_user_by_id(
                user_id=99999,
                request=UserAdminUpdateRequest(nickname="test"),
                db=db_session,
                admin=admin
            )
        assert exc.value.status_code == 404
