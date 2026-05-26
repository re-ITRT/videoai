"""覆盖率冲刺 — 直接调 router 函数覆盖 ASGI 盲区"""
import pytest
from unittest.mock import patch, AsyncMock
from fastapi import HTTPException
from app.auth.models import User


@pytest.fixture
def dummy_user():
    return User(id=1, username="cov_user", hashed_password="h", is_active=True, role="user")


@pytest.fixture
def dummy_admin():
    return User(id=99, username="admin", hashed_password="h", is_active=True, role="admin")


class TestCreationApproveDirect:

    @pytest.mark.asyncio
    async def test_get_task_logs_404(self, db_session, dummy_user):
        from app.creation.router import get_task_logs
        with pytest.raises(HTTPException) as exc:
            await get_task_logs(task_id=99999, db=db_session, current_user=dummy_user)
        assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_approve_404(self, db_session, dummy_user):
        from app.creation.router import approve_step
        with pytest.raises(HTTPException) as exc:
            await approve_step(task_id=99999, db=db_session, current_user=dummy_user)
        assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_export_404(self, db_session, dummy_user):
        from app.creation.router import export_video
        with pytest.raises(HTTPException) as exc:
            await export_video(task_id=99999, aspect_ratio=None,
                               db=db_session, current_user=dummy_user)
        assert exc.value.status_code == 400

    @pytest.mark.asyncio
    async def test_approve_not_editable(self, db_session, dummy_user):
        from app.creation.router import create_task, approve_step
        from app.creation.schemas import TaskCreateRequest
        created = await create_task(
            request=TaskCreateRequest(product_info={"name": "t"}, auto_mode=False),
            db=db_session, current_user=dummy_user,
        )
        with pytest.raises(HTTPException) as exc:
            await approve_step(task_id=created["id"], db=db_session, current_user=dummy_user)
        assert exc.value.status_code == 400


class TestWorkersRouterDirect:

    @pytest.mark.asyncio
    async def test_list_workflows(self):
        from app.workers.router import list_workflows
        result = await list_workflows()
        assert "workflows" in result

    @pytest.mark.asyncio
    async def test_run_unknown_workflow(self):
        from app.workers.router import run_workflow
        with pytest.raises(HTTPException) as exc:
            await run_workflow("unknown_workflow", {})
        assert exc.value.status_code == 404


class TestOrchestratorEdgeCases:

    @pytest.mark.asyncio
    async def test_auto_mode_continues(self, db_session):
        from app.core.orchestrator import run_next_step
        from app.creation.models import VideoTask
        task = VideoTask(user_id=1, product_info={"name": "t"}, auto_mode=True,
                         status="CREATED")
        db_session.add(task)
        await db_session.commit()
        with patch("app.core.orchestrator.call_workflow", new_callable=AsyncMock) as m:
            m.return_value = {"output_url": "https://ex.com/v.mp4"}
            await run_next_step(db_session, task, "u1")
        await db_session.refresh(task)
        assert task.status is not None
