"""core/deps.py 全覆盖测试"""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials


class TestGetCurrentUser:
    """直接调用 get_current_user 测试所有分支"""

    @pytest.mark.asyncio
    async def test_invalid_token_returns_401(self, db_session):
        from app.core.deps import get_current_user
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="bad_token")
        with patch("app.core.deps.decode_access_token", return_value=None):
            with pytest.raises(HTTPException) as exc:
                await get_current_user(credentials=creds, db=db_session)
            assert exc.value.status_code == 401

    @pytest.mark.asyncio
    async def test_no_sub_in_token_returns_401(self, db_session):
        from app.core.deps import get_current_user
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="no_sub")
        with patch("app.core.deps.decode_access_token", return_value={"sub": None}):
            with pytest.raises(HTTPException) as exc:
                await get_current_user(credentials=creds, db=db_session)
            assert exc.value.status_code == 401

    @pytest.mark.asyncio
    async def test_non_int_sub_returns_401(self, db_session):
        from app.core.deps import get_current_user
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="text_sub")
        with patch("app.core.deps.decode_access_token", return_value={"sub": "not_a_number"}):
            with pytest.raises(HTTPException) as exc:
                await get_current_user(credentials=creds, db=db_session)
            assert exc.value.status_code == 401

    @pytest.mark.asyncio
    async def test_user_not_found_returns_401(self, db_session):
        from app.core.deps import get_current_user
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="not_found")
        with patch("app.core.deps.decode_access_token", return_value={"sub": "99999"}):
            with pytest.raises(HTTPException) as exc:
                await get_current_user(credentials=creds, db=db_session)
            assert exc.value.status_code == 401

    @pytest.mark.asyncio
    async def test_inactive_user_returns_403(self, db_session):
        from app.core.deps import get_current_user
        from app.auth.models import User

        inactive = User(id=50, username="inactive_user", hashed_password="h", is_active=False, role="user")
        db_session.add(inactive)
        await db_session.flush()

        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="inactive_token")
        with patch("app.core.deps.decode_access_token", return_value={"sub": "50"}):
            with pytest.raises(HTTPException) as exc:
                await get_current_user(credentials=creds, db=db_session)
            assert exc.value.status_code == 403

    @pytest.mark.asyncio
    async def test_success(self, db_session):
        from app.core.deps import get_current_user
        from app.auth.models import User

        active = User(id=51, username="active_user", hashed_password="h", is_active=True, role="user")
        db_session.add(active)
        await db_session.flush()

        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="good_token")
        with patch("app.core.deps.decode_access_token", return_value={"sub": "51"}):
            user = await get_current_user(credentials=creds, db=db_session)
            assert user.username == "active_user"


class TestGetCurrentAdminUser:
    @pytest.mark.asyncio
    async def test_non_admin_403(self):
        from app.core.deps import get_current_admin_user
        from app.auth.models import User
        regular = User(id=1, username="regular", hashed_password="h", is_active=True, role="user")
        with pytest.raises(HTTPException) as exc:
            await get_current_admin_user(current_user=regular)
        assert exc.value.status_code == 403

    @pytest.mark.asyncio
    async def test_admin_success(self):
        from app.core.deps import get_current_admin_user
        from app.auth.models import User
        admin = User(id=99, username="admin", hashed_password="h", is_active=True, role="admin")
        user = await get_current_admin_user(current_user=admin)
        assert user.role == "admin"
