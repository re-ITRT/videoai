"""创作路由直接测试 — 绕开 ASGI 覆盖盲区"""
import pytest
from unittest.mock import patch, AsyncMock
from app.auth.models import User


@pytest.fixture
def dummy_user():
    return User(id=1, username="direct_creation", hashed_password="hash", is_active=True, role="user")


class TestCreationRouterDirect:

    @pytest.mark.asyncio
    async def test_create_task_direct(self, db_session, dummy_user):
        from app.creation.router import create_task
        from app.creation.schemas import TaskCreateRequest

        req = TaskCreateRequest(product_info={"name": "直测"})
        result = await create_task(request=req, db=db_session, current_user=dummy_user)
        assert result["status"] == "CREATED"
        assert result["aspect_ratio"] == "9:16"

    @pytest.mark.asyncio
    async def test_get_task_direct(self, db_session, dummy_user):
        from app.creation.router import create_task, get_task
        from app.creation.schemas import TaskCreateRequest

        created = await create_task(
            request=TaskCreateRequest(product_info={"name": "直测"}),
            db=db_session, current_user=dummy_user,
        )
        result = await get_task(task_id=created["id"], db=db_session, current_user=dummy_user)
        assert result["id"] == created["id"]

    @pytest.mark.asyncio
    async def test_get_task_404_direct(self, db_session, dummy_user):
        from app.creation.router import get_task
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            await get_task(task_id=99999, db=db_session, current_user=dummy_user)
        assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_list_tasks_direct(self, db_session, dummy_user):
        from app.creation.router import list_tasks
        result = await list_tasks(skip=0, limit=10, db=db_session, current_user=dummy_user)
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_get_task_logs_404_direct(self, db_session, dummy_user):
        from app.creation.router import get_task_logs
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            await get_task_logs(task_id=99999, db=db_session, current_user=dummy_user)
        assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_retry_task_direct(self, db_session, dummy_user):
        from app.creation.router import create_task, retry_task
        from app.creation.schemas import TaskCreateRequest

        created = await create_task(
            request=TaskCreateRequest(product_info={"name": "重试"}),
            db=db_session, current_user=dummy_user,
        )
        result = await retry_task(task_id=created["id"], db=db_session, current_user=dummy_user)
        assert result["retry_count"] == 1
        assert result["status"] == "RETRYING"

    @pytest.mark.asyncio
    async def test_retry_task_404_direct(self, db_session, dummy_user):
        from app.creation.router import retry_task
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            await retry_task(task_id=99999, db=db_session, current_user=dummy_user)
        assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_export_workflow_fails_direct(self, db_session, dummy_user):
        """export 时工作流失败 → 502"""
        from app.creation.router import create_task, export_video
        from app.creation.schemas import TaskCreateRequest
        from app.script.models import Script

        created = await create_task(
            request=TaskCreateRequest(product_info={"name": "wf_fail"}),
            db=db_session, current_user=dummy_user,
        )
        script = Script(task_id=created["id"], content={"scenes": [{"id": 1, "description": "t", "duration": 5}]}, strategy="s")
        db_session.add(script)
        await db_session.commit()

        # 需要设置 task.script_id
        from app.creation.models import VideoTask
        task = await db_session.get(VideoTask, created["id"])
        task.script_id = script.id
        await db_session.commit()

        with patch("app.creation.service.call_workflow", new_callable=AsyncMock) as m:
            m.side_effect = Exception("workflow error")
            from fastapi import HTTPException
            with pytest.raises(HTTPException) as exc:
                await export_video(
                    task_id=created["id"], aspect_ratio=None,
                    db=db_session, current_user=dummy_user,
                )
            assert exc.value.status_code == 502
        from app.creation.router import create_task, export_video
        from app.creation.schemas import TaskCreateRequest

        created = await create_task(
            request=TaskCreateRequest(product_info={"name": "导出测试"}),
            db=db_session, current_user=dummy_user,
        )
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            await export_video(
                task_id=created["id"], aspect_ratio="9:16",
                db=db_session, current_user=dummy_user,
            )
        assert exc.value.status_code == 400
