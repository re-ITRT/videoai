"""用户模块测试"""
import pytest


@pytest.mark.asyncio
async def test_get_user_requires_auth(client):
    """无 token 返回 403"""
    resp = await client.get("/api/v1/users/me")
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_update_user_requires_auth(client):
    resp = await client.put("/api/v1/users/me")
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_change_password_requires_auth(client):
    resp = await client.put("/api/v1/users/me/password")
    assert resp.status_code == 403


class TestUserSchemas:

    def test_update_request(self):
        from app.user.schemas import UserUpdateRequest
        req = UserUpdateRequest(nickname="新昵称", email="test@test.com")
        assert req.nickname == "新昵称"
        assert req.email == "test@test.com"

    def test_password_change_request(self):
        from app.user.schemas import PasswordChangeRequest
        req = PasswordChangeRequest(old_password="old", new_password="new123")
        assert req.old_password == "old"
        assert req.new_password == "new123"

    def test_user_list_response(self):
        from datetime import datetime
        from app.user.schemas import UserListResponse
        now = datetime.now()
        resp = UserListResponse(
            id=1, username="test", nickname="T", email="t@t.com",
            is_active=True, role="user", created_at=now
        )
        assert resp.username == "test"
        assert resp.role == "user"

    def test_user_detail_response(self):
        from datetime import datetime
        from app.user.schemas import UserDetailResponse
        now = datetime.now()
        resp = UserDetailResponse(
            id=1, username="test", is_active=True,
            role="admin", created_at=now, updated_at=now
        )
        assert resp.updated_at is not None
        assert resp.role == "admin"
