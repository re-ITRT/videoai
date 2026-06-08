"""auth/router.py 全覆盖测试"""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi import HTTPException
from app.auth.models import User
from app.auth.schemas import RegisterRequest, LoginRequest, TokenRefreshRequest


@pytest.fixture
def dummy_user():
    return User(id=1, username="test_user", hashed_password="h", is_active=True, role="user")


@pytest.fixture
def admin_user():
    return User(id=99, username="admin", hashed_password="h", is_active=True, role="admin")


class TestRegister:
    @pytest.mark.asyncio
    async def test_existing_user_409(self, db_session):
        """已存在用户名 -> 409"""
        from app.auth.router import register
        with patch("app.auth.service.get_user_by_username", new_callable=AsyncMock) as gub:
            gub.return_value = MagicMock()
            with pytest.raises(HTTPException) as exc:
                await register(
                    request=RegisterRequest(username="exists", password="Pw12345"),
                    db=db_session,
                )
            assert exc.value.status_code == 409

    @pytest.mark.asyncio
    async def test_integrity_error_409(self, db_session):
        """create_user 抛 IntegrityError -> 409"""
        from app.auth.router import register
        from sqlalchemy.exc import IntegrityError
        with patch("app.auth.service.get_user_by_username", new_callable=AsyncMock, return_value=None), \
             patch("app.auth.service.create_user", new_callable=AsyncMock,
                   side_effect=IntegrityError("mock", {}, "")):
            with pytest.raises(HTTPException) as exc:
                await register(
                    request=RegisterRequest(username="dup", password="Pw12345"),
                    db=db_session,
                )
            assert exc.value.status_code == 409


class TestRefresh:
    @pytest.mark.asyncio
    async def test_user_not_found_401(self, db_session):
        from app.auth.router import refresh
        with patch("app.auth.router.decode_refresh_token", return_value={"sub": "99999"}), \
             patch("app.auth.router.select"):
            with pytest.raises(HTTPException) as exc:
                await refresh(
                    request=TokenRefreshRequest(refresh_token="fake"),
                    db=db_session,
                )
            assert exc.value.status_code == 401


class TestLogout:
    @pytest.mark.asyncio
    async def test_success(self):
        from app.auth.router import logout
        redis_mock = AsyncMock()
        result = await logout(
            current_user=MagicMock(id=1),
            redis_client=redis_mock,
        )
        assert "message" in str(result)
        redis_mock.set.assert_called_once()
