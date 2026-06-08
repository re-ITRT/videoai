"""剩余小模块全覆盖"""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi import HTTPException
from app.auth.models import User


@pytest.fixture
def dummy_user():
    return User(id=1, username="cov_user", hashed_password="h", is_active=True, role="user")


class TestUserEdge:
    @pytest.mark.asyncio
    async def test_get_my_info(self, db_session, dummy_user):
        from app.user.router import get_my_info
        from datetime import datetime
        dummy_user.created_at = datetime.utcnow()
        r = await get_my_info(current_user=dummy_user)
        assert r.username == "cov_user"

    @pytest.mark.asyncio
    async def test_admin_delete_not_found(self, db_session):
        from app.user.router import admin_delete_user_by_id
        admin = User(id=99, username="admin", hashed_password="h", is_active=True, role="admin")
        with pytest.raises(HTTPException) as exc:
            await admin_delete_user_by_id(99999, db=db_session, admin=admin)
        assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_admin_update_not_found(self, db_session):
        from app.user.router import admin_update_user_by_id
        from app.user.schemas import UserAdminUpdateRequest
        admin = User(id=99, username="admin", hashed_password="h", is_active=True, role="admin")
        with pytest.raises(HTTPException) as exc:
            await admin_update_user_by_id(99999, UserAdminUpdateRequest(), db=db_session, admin=admin)
        assert exc.value.status_code == 404


class TestWorkersEdge:
    @pytest.mark.asyncio
    async def test_list_workflows(self):
        from app.workers.router import list_workflows
        result = await list_workflows()
        assert "workflows" in result

    @pytest.mark.asyncio
    async def test_run_unknown_workflow_404(self):
        from app.workers.router import run_workflow
        with pytest.raises(HTTPException) as exc:
            await run_workflow("nonexistent", {})
        assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_tasks_module_import(self):
        from app.workers import tasks
        assert hasattr(tasks, '__file__')

    @pytest.mark.asyncio
    async def test_workers_init_import(self):
        from app.workers import __init__ as wi
        assert wi is not None


class TestScriptServiceEdge:
    @pytest.mark.asyncio
    async def test_generate_script(self):
        from app.script.service import generate_script
        from app.script.schemas import ScriptGenerateRequest
        from unittest.mock import patch
        req = ScriptGenerateRequest(product_info={"name": "test"})
        with patch("app.script.service.call_workflow", new_callable=AsyncMock) as cwf:
            cwf.return_value = {"script": "test"}
            result = await generate_script(req)
            assert result.metadata["workflow_result"]["script"] == "test"
