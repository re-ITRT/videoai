"""核心与服务层集成测试 — 覆盖 deps / database / service 剩余分支"""
import pytest


class TestCoreDatabase:
    """app.core.database"""

    def test_get_db_generator(self):
        import inspect
        from app.core.database import get_db
        assert inspect.isasyncgenfunction(get_db)

    def test_base_imports(self):
        from app.core.database import Base, engine, async_session
        assert Base is not None


class TestCoreDeps:
    """app.core.deps"""

    def test_get_current_admin_user_non_admin(self):
        import pytest
        from fastapi import HTTPException
        from app.core.deps import get_current_admin_user
        from app.auth.models import User

        user = User(id=1, username="user", hashed_password="hash", role="user")

        with pytest.raises(HTTPException) as exc:
            import asyncio
            asyncio.run(get_current_admin_user(current_user=user))
        assert exc.value.status_code == 403

    def test_security_scheme(self):
        from app.core.deps import security
        assert security is not None


class TestAuthService:
    """app.auth.service"""

    @pytest.mark.asyncio
    async def test_get_user_by_username_not_found(self, db_session):
        from app.auth.service import get_user_by_username
        user = await get_user_by_username(db_session, "nonexistent")
        assert user is None

    @pytest.mark.asyncio
    async def test_get_user_by_id_not_found(self, db_session):
        from app.auth.service import get_user_by_id
        user = await get_user_by_id(db_session, 99999)
        assert user is None


class TestUserService:
    """app.user.service — 使用真实 test DB"""

    @pytest.mark.asyncio
    async def test_get_user_by_id_not_found(self, db_session):
        from app.user.service import get_user_by_id
        user = await get_user_by_id(db_session, 99999)
        assert user is None

    @pytest.mark.asyncio
    async def test_get_all_users(self, db_session):
        from app.user.service import get_all_users
        users = await get_all_users(db_session)
        assert isinstance(users, list)

    @pytest.mark.asyncio
    async def test_get_all_users_pagination(self, db_session):
        from app.user.service import get_all_users
        users = await get_all_users(db_session, skip=0, limit=10)
        assert isinstance(users, list)

    @pytest.mark.asyncio
    async def test_update_user_profile_not_found(self, db_session):
        from app.user.service import update_user_profile
        from app.user.schemas import UserUpdateRequest
        req = UserUpdateRequest(nickname="test")
        with pytest.raises(ValueError, match="User not found"):
            await update_user_profile(db_session, 99999, req)

    @pytest.mark.asyncio
    async def test_change_password_not_found(self, db_session):
        from app.user.service import change_user_password
        with pytest.raises(ValueError, match="User not found"):
            await change_user_password(db_session, 99999, "old", "new")

    @pytest.mark.asyncio
    async def test_admin_update_user_not_found(self, db_session):
        from app.user.service import admin_update_user
        from app.user.schemas import UserAdminUpdateRequest
        req = UserAdminUpdateRequest(nickname="test")
        with pytest.raises(ValueError, match="User not found"):
            await admin_update_user(db_session, 99999, req)

    @pytest.mark.asyncio
    async def test_delete_user_not_found(self, db_session):
        from app.user.service import delete_user
        with pytest.raises(ValueError, match="User not found"):
            await delete_user(db_session, 99999)

    @pytest.mark.asyncio
    async def test_user_crud_lifecycle(self, db_session):
        """创建用户 → 查询 → 更新 → 删密码 → 删除"""
        from app.auth.service import create_user, get_user_by_username
        from app.user.service import update_user_profile, change_user_password, \
            admin_update_user, delete_user, get_all_users
        from app.user.schemas import UserUpdateRequest, UserAdminUpdateRequest

        # 创建
        user = await create_user(db_session, "crudtest", "Pass1234", "CRUD")
        assert user.username == "crudtest"
        assert user.id is not None

        # 查询
        found = await get_user_by_username(db_session, "crudtest")
        assert found is not None

        # 更新
        updated = await update_user_profile(
            db_session, user.id,
            UserUpdateRequest(nickname="Updated", email="u@test.com")
        )
        assert updated.nickname == "Updated"

        # 改密码
        pw_changed = await change_user_password(db_session, user.id, "Pass1234", "NewPass999")
        assert pw_changed is not None

        # 管理员更新
        admin_updated = await admin_update_user(
            db_session, user.id,
            UserAdminUpdateRequest(nickname="Admined", is_active=False)
        )
        assert admin_updated.nickname == "Admined"
        assert admin_updated.is_active is False

        # 获取全部用户
        all_users = await get_all_users(db_session)
        assert len(all_users) >= 1

        # 删除
        await delete_user(db_session, user.id)
        gone = await get_user_by_username(db_session, "crudtest")
        assert gone is None
