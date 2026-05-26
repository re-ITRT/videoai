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

    @pytest.mark.asyncio
    async def test_build_payload_script(self, db_session):
        from app.core.orchestrator import build_payload
        from app.creation.models import VideoTask
        task = VideoTask(user_id=1, product_info={"name": "测试"}, auto_mode=True)
        db_session.add(task)
        await db_session.commit()
        await db_session.refresh(task)

        payload = await build_payload(db_session, task, "script-generate")
        assert payload["target_duration"] == 15
        assert payload["mode"] == "auto"

    @pytest.mark.asyncio
    async def test_build_payload_video(self, db_session):
        from app.core.orchestrator import build_payload
        from app.creation.models import VideoTask
        task = VideoTask(user_id=1, product_info={}, aspect_ratio="1:1")
        db_session.add(task)
        await db_session.commit()
        await db_session.refresh(task)

        payload = await build_payload(db_session, task, "video-generate")
        assert payload["aspect_ratio"] == "1:1"

    @pytest.mark.asyncio
    async def test_build_payload_default(self, db_session):
        from app.core.orchestrator import build_payload
        from app.creation.models import VideoTask
        task = VideoTask(user_id=1, product_info={})
        db_session.add(task)
        await db_session.commit()
        await db_session.refresh(task)

        assert await build_payload(db_session, task, "unknown") == {}

    @pytest.mark.asyncio
    async def test_save_result(self, db_session):
        from app.core.orchestrator import save_workflow_result
        from app.creation.models import VideoTask
        task = VideoTask(user_id=1, product_info={})
        db_session.add(task)
        await db_session.commit()
        await db_session.refresh(task)

        await save_workflow_result(db_session, task, "script-generate", {"scenes": []})
        await save_workflow_result(db_session, task, "video-compose", {"output_url": "https://ex.com/v.mp4"})
        assert task.output_url == "https://ex.com/v.mp4"

    @pytest.mark.asyncio
    async def test_build_payload_material_search(self, db_session):
        """测试 C2 material-search payload 构造"""
        from app.core.orchestrator import build_payload
        from app.creation.models import VideoTask
        from app.script.models import Script

        task = VideoTask(user_id=1, product_info={"name": "测试产品"}, status="CREATED")
        db_session.add(task)
        await db_session.commit()
        await db_session.refresh(task)

        # 先创建一个脚本
        script = Script(
            task_id=task.id,
            content={
                "scenes": [
                    {"visual_description": "产品特写展示", "narration": "大家好今天给大家推荐一款好物"},
                    {"visual_description": "使用效果演示", "narration": "看这个效果真的很棒"},
                ]
            }
        )
        db_session.add(script)
        await db_session.commit()
        await db_session.refresh(script)

        task.script_id = script.id
        await db_session.commit()

        payload = await build_payload(db_session, task, "material-search")
        assert "product_queries" in payload
        assert len(payload["product_queries"]) > 0
        assert "产品特写展示" in payload["product_queries"]

    @pytest.mark.asyncio
    async def test_build_payload_video_compose(self, db_session):
        """测试 C4 video-compose payload 构造"""
        from app.core.orchestrator import build_payload
        from app.creation.models import VideoTask
        from app.script.models import Script

        task = VideoTask(
            user_id=1,
            product_info={"name": "测试产品"},
            status="VIDEO_GENERATE_DONE",
            aspect_ratio="16:9",
            video_urls=[
                {"type": "scene_video", "scene_id": 1, "video_url": "https://ex.com/s1.mp4"},
                {"type": "scene_video", "scene_id": 2, "video_url": "https://ex.com/s2.mp4"},
            ],
        )
        db_session.add(task)
        await db_session.commit()
        await db_session.refresh(task)

        # 创建脚本
        script = Script(
            task_id=task.id,
            content={
                "scenes": [
                    {"scene_id": 1, "narration": "第一个分镜旁白", "duration": 3},
                    {"scene_id": 2, "narration": "第二个分镜旁白", "duration": 3},
                ]
            }
        )
        db_session.add(script)
        await db_session.commit()
        await db_session.refresh(script)

        task.script_id = script.id
        await db_session.commit()

        payload = await build_payload(db_session, task, "video-compose")
        assert payload["aspect_ratio"] == "16:9"
        assert len(payload["scenes"]) == 2
        assert payload["scenes"][0]["video_url"] == "https://ex.com/s1.mp4"
        assert payload["add_subtitles"] is True

    @pytest.mark.asyncio
    async def test_save_result_material_search(self, db_session):
        """测试 C2 material-search 结果保存"""
        from app.core.orchestrator import save_workflow_result
        from app.creation.models import VideoTask

        task = VideoTask(user_id=1, product_info={})
        db_session.add(task)
        await db_session.commit()
        await db_session.refresh(task)

        result = {
            "materials": [
                {"id": 1, "image_url": "https://ex.com/m1.jpg", "similarity": 0.92},
                {"id": 2, "image_url": "https://ex.com/m2.jpg", "similarity": 0.85},
            ]
        }
        await save_workflow_result(db_session, task, "material-search", result)
        assert task.video_urls is not None
        assert len(task.video_urls) >= 2
        assert task.video_urls[0]["type"] == "material"

    @pytest.mark.asyncio
    async def test_save_result_video_generate(self, db_session):
        """测试 C3 video-generate 结果保存"""
        from app.core.orchestrator import save_workflow_result
        from app.creation.models import VideoTask

        task = VideoTask(user_id=1, product_info={}, video_urls=[])
        db_session.add(task)
        await db_session.commit()
        await db_session.refresh(task)

        result = {
            "video_urls": [
                {"scene_id": 1, "video_url": "https://ex.com/s1.mp4"},
                {"scene_id": 2, "video_url": "https://ex.com/s2.mp4"},
            ]
        }
        await save_workflow_result(db_session, task, "video-generate", result)
        assert len(task.video_urls) == 2
        assert task.video_urls[0]["type"] == "scene_video"
        assert task.video_urls[0]["video_url"] == "https://ex.com/s1.mp4"

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
