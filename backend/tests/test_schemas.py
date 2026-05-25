"""Schema 层测试 — 覆盖所有 Pydantic 模型"""
from datetime import datetime
import pytest


class TestAuthSchemas:
    """app.auth.schemas"""

    def test_register_request(self):
        from app.auth.schemas import RegisterRequest
        r = RegisterRequest(username="hello", password="Pass1234")
        assert r.username == "hello"

    def test_login_request(self):
        from app.auth.schemas import LoginRequest
        r = LoginRequest(username="user", password="pw")
        assert r.username == "user"

    def test_token_refresh_request(self):
        from app.auth.schemas import TokenRefreshRequest
        r = TokenRefreshRequest(refresh_token="abc")
        assert r.refresh_token == "abc"

    def test_user_response(self):
        from app.auth.schemas import UserResponse
        r = UserResponse(id=1, username="u", created_at=datetime.now())
        assert r.username == "u"

    def test_token_response(self):
        from app.auth.schemas import TokenResponse, UserResponse
        user = UserResponse(id=1, username="u", created_at=datetime.now())
        r = TokenResponse(access_token="a", refresh_token="b", user=user)
        assert r.token_type == "bearer"

    def test_refresh_token_response(self):
        from app.auth.schemas import RefreshTokenResponse
        r = RefreshTokenResponse(access_token="new_token")
        assert r.token_type == "bearer"

    def test_logout_response(self):
        from app.auth.schemas import LogoutResponse
        r = LogoutResponse()
        assert r.message == "Logged out successfully"

    def test_error_response(self):
        from app.auth.schemas import ErrorResponse
        r = ErrorResponse(code=409, message="冲突")
        assert r.code == 409


class TestMaterialSchemas:
    """app.material.schemas"""

    def test_upload_request(self):
        from app.material.schemas import MaterialUploadRequest
        r = MaterialUploadRequest(material_type="product", input_type="image")
        assert r.input_type == "image"

    def test_search_request(self):
        from app.material.schemas import MaterialSearchRequest
        r = MaterialSearchRequest(query="watch")
        assert r.query == "watch"
        assert r.threshold == 0.6
        assert r.search_level == "material"

    def test_search_result(self):
        from app.material.schemas import MaterialSearchResult
        r = MaterialSearchResult(id=42, similarity=0.85, tags=["test"])
        assert r.similarity == 0.85
        assert r.tags == ["test"]


class TestCreationSchemas:
    """app.creation.schemas"""

    def test_task_create_request(self):
        from app.creation.schemas import TaskCreateRequest
        r = TaskCreateRequest(product_info={"name": "test"})
        assert r.auto_mode is True
        assert r.aspect_ratio == "9:16"

    def test_task_create_request_custom_ratio(self):
        from app.creation.schemas import TaskCreateRequest
        r = TaskCreateRequest(product_info={"name": "t"}, aspect_ratio="1:1")
        assert r.aspect_ratio == "1:1"

    def test_task_approve_script_request(self):
        from app.creation.schemas import TaskApproveScriptRequest
        r = TaskApproveScriptRequest(script_id=1)
        assert r.script_id == 1

    def test_task_retry_request(self):
        from app.creation.schemas import TaskRetryRequest
        r = TaskRetryRequest(step="script")
        assert r.step == "script"

    def test_task_retry_request_empty(self):
        from app.creation.schemas import TaskRetryRequest
        r = TaskRetryRequest()
        assert r.step is None


class TestScriptSchemas:
    """app.script.schemas"""

    def test_script_generate_request_defaults(self):
        from app.script.schemas import ScriptGenerateRequest
        r = ScriptGenerateRequest(product_info={"name": "t"})
        assert r.target_duration == 15
        assert r.mode == "auto"
        assert r.num_variants == 1

    def test_script_generate_request_imitation(self):
        from app.script.schemas import ScriptGenerateRequest
        r = ScriptGenerateRequest(
            product_info={"name": "t"},
            mode="imitation",
            reference_video_id=42
        )
        assert r.mode == "imitation"
        assert r.reference_video_id == 42

    def test_script_generate_request_template(self):
        from app.script.schemas import ScriptGenerateRequest
        r = ScriptGenerateRequest(
            product_info={"name": "t"},
            mode="template",
            template_id=5
        )
        assert r.mode == "template"
        assert r.template_id == 5
