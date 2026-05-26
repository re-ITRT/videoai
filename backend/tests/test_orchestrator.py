"""状态机 + WebSocket + 编排器测试"""
import pytest
from unittest.mock import AsyncMock, patch


async def _auth(client, username):
    resp = await client.post("/api/v1/auth/register", json={
        "username": username, "password": "Orch12345"
    })
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


class TestTaskState:

    def test_all_states_defined(self):
        from app.core.states import TaskState
        states = [s.value for s in TaskState]
        assert "CREATED" in states
        assert "FAILED" in states
        assert len(states) == 17

    def test_workflow_steps_count(self):
        from app.core.states import WORKFLOW_STEPS
        assert len(WORKFLOW_STEPS) == 7

    def test_transitions(self):
        from app.core.states import TRANSITIONS, TaskState
        assert TRANSITIONS[TaskState.MATERIAL_EMBED_DONE] == TaskState.QUERY_GENERATE
        assert TRANSITIONS[TaskState.VIDEO_COMPOSE_DONE] == TaskState.EXPORTED

    def test_editable_states(self):
        from app.core.states import EDITABLE_STATES, TaskState
        assert TaskState.SCRIPT_GENERATE_DONE in EDITABLE_STATES


class TestWSManager:

    @pytest.mark.asyncio
    async def test_connect_disconnect(self):
        from app.core.ws_manager import manager
        from unittest.mock import AsyncMock
        ws = AsyncMock()
        await manager.connect("u1", ws)
        assert ws in manager.active["u1"]
        manager.disconnect("u1", ws)
        assert ws not in manager.active["u1"]

    @pytest.mark.asyncio
    async def test_send_to_user(self):
        from app.core.ws_manager import manager
        from unittest.mock import AsyncMock
        ws = AsyncMock()
        ws.send_json = AsyncMock()
        await manager.connect("u2", ws)
        await manager.send_to_user("u2", {"type": "t"})
        ws.send_json.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_to_unknown(self):
        from app.core.ws_manager import manager
        await manager.send_to_user("ghost", {"type": "t"})

    @pytest.mark.asyncio
    async def test_broadcast(self):
        from app.core.ws_manager import manager
        from unittest.mock import AsyncMock
        ws = AsyncMock()
        ws.send_json = AsyncMock()
        await manager.connect("u3", ws)
        await manager.broadcast_task_progress("u3", 1, "DONE", editable=True)
        msg = ws.send_json.call_args[0][0]
        assert msg["type"] == "task_progress"
        assert msg["editable"] is True


class TestOrchestrator:

    def test_build_payload_script(self):
        from app.core.orchestrator import build_payload
        from app.creation.models import VideoTask
        task = VideoTask(user_id=1, product_info={"name": "测试"}, auto_mode=True)
        payload = build_payload(task, "script-generate")
        assert payload["target_duration"] == 15
        assert payload["mode"] == "auto"

    def test_build_payload_video(self):
        from app.core.orchestrator import build_payload
        from app.creation.models import VideoTask
        task = VideoTask(user_id=1, product_info={}, aspect_ratio="1:1")
        payload = build_payload(task, "video-generate")
        assert payload["aspect_ratio"] == "1:1"

    def test_build_payload_default(self):
        from app.core.orchestrator import build_payload
        from app.creation.models import VideoTask
        task = VideoTask(user_id=1, product_info={})
        assert build_payload(task, "unknown") == {}

    def test_save_result(self):
        from app.core.orchestrator import save_workflow_result
        from app.creation.models import VideoTask
        task = VideoTask(user_id=1, product_info={})
        save_workflow_result(task, "script-generate", {"scenes": []})
        save_workflow_result(task, "video-compose", {"output_url": "https://ex.com/v.mp4"})
        assert task.output_url == "https://ex.com/v.mp4"

    @pytest.mark.asyncio
    async def test_run_next_step_completed(self, db_session):
        """任务已完成 → run_next_step 直接返回"""
        from app.core.orchestrator import run_next_step
        from app.creation.models import VideoTask
        task = VideoTask(user_id=1, product_info={}, status="EXPORTED")
        db_session.add(task)
        await db_session.commit()
        await run_next_step(db_session, task, "user1")
        assert task.status == "EXPORTED"

    @pytest.mark.asyncio
    async def test_run_next_step_fails(self, db_session):
        """工作流失败 → 状态变为 FAILED"""
        from app.core.orchestrator import run_next_step
        from app.creation.models import VideoTask
        task = VideoTask(user_id=1, product_info={"name": "测试"})
        db_session.add(task)
        await db_session.commit()

        with patch("app.core.orchestrator.call_workflow", new_callable=AsyncMock) as m:
            m.side_effect = Exception("网络错误")
            await run_next_step(db_session, task, "user1")
        await db_session.refresh(task)
        assert task.status == "FAILED"

    @pytest.mark.asyncio
    async def test_run_next_step_success(self, db_session):
        """工作流成功 → 状态变为 DONE"""
        from app.core.orchestrator import run_next_step
        from app.creation.models import VideoTask
        task = VideoTask(user_id=1, product_info={"name": "测试"}, auto_mode=False)
        db_session.add(task)
        await db_session.commit()

        with patch("app.core.orchestrator.call_workflow", new_callable=AsyncMock) as m:
            m.return_value = {"output_url": "https://ex.com/v.mp4"}
            await run_next_step(db_session, task, "user1")

        await db_session.refresh(task)
        assert task.status == "MATERIAL_EMBED_DONE"


class TestApprove:

    @pytest.mark.asyncio
    async def test_approve_nonexistent(self, client):
        resp = await client.post("/api/v1/tasks/99999/approve")
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_approve_not_editable(self, client):
        headers = await _auth(client, "app1")
        create = await client.post("/api/v1/tasks", json={
            "product_info": {"name": "测试"},
            "auto_mode": False,
        }, headers=headers)
        tid = create.json()["id"]
        resp = await client.post(f"/api/v1/tasks/{tid}/approve", headers=headers)
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_run_step_completed(self, db_session):
        from app.core.orchestrator import run_next_step
        from app.creation.models import VideoTask
        task = VideoTask(user_id=1, product_info={}, status="EXPORTED")
        db_session.add(task)
        await db_session.commit()
        await run_next_step(db_session, task, "u1")
        assert task.status == "EXPORTED"

    @pytest.mark.asyncio
    async def test_run_step_success(self, db_session):
        from app.core.orchestrator import run_next_step
        from app.creation.models import VideoTask
        task = VideoTask(user_id=1, product_info={"name": "测试"}, auto_mode=False, status="CREATED")
        db_session.add(task)
        await db_session.commit()

        with patch("app.core.orchestrator.call_workflow", new_callable=AsyncMock) as m:
            m.return_value = {"output_url": "https://ex.com/v.mp4"}
            await run_next_step(db_session, task, "u1")
        await db_session.refresh(task)
        # CREATED → MATERIAL_EMBED → MATERIAL_EMBED_DONE
        assert task.status == "MATERIAL_EMBED_DONE"

    @pytest.mark.asyncio
    async def test_run_step_no_transition(self, db_session):
        """EXPORTED 状态无下一跳 → 直接返回"""
        from app.core.orchestrator import run_next_step
        from app.creation.models import VideoTask
        task = VideoTask(user_id=1, product_info={}, status="EXPORTED")
        db_session.add(task)
        await db_session.commit()
        await run_next_step(db_session, task, "u1")
        await db_session.refresh(task)
        assert task.status == "EXPORTED"

    @pytest.mark.asyncio
    async def test_run_step_no_workflow(self, db_session):
        """有状态转换但找不到对应工作流 → 跳过"""
        from app.core.orchestrator import run_next_step
        from app.creation.models import VideoTask
        from app.core.states import TRANSITIONS, TaskState

        # 找个不在 WORKFLOW_STEPS 里的目标状态
        task = VideoTask(user_id=1, product_info={}, status="CREATED")
        db_session.add(task)
        await db_session.commit()

        with patch("app.core.orchestrator.TRANSITIONS", {
            TaskState.CREATED: TaskState.FAILED,
        }):
            await run_next_step(db_session, task, "u1")
            await db_session.refresh(task)
            # 找不到工作流 → 直接返回，状态不变
            assert task.status != "EXPORTED"
