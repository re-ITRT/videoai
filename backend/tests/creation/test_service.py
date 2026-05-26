"""创作模块服务层测试 — C10 多画幅导出"""
import pytest
from unittest.mock import patch, AsyncMock
from app.creation import service as svc
from app.script.models import Script


class TestCreationService:
    """C10 多画幅导出服务层"""

    @pytest.mark.asyncio
    async def test_create_task_with_defaults(self, db_session):
        task = await svc.create_task(
            db_session, user_id=1, product_info={"name": "默认测试"}
        )
        assert task.aspect_ratio == "9:16"
        assert task.auto_mode is True
        assert task.status == "CREATED"
        assert task.style is None

    @pytest.mark.asyncio
    async def test_list_tasks_by_user(self, db_session):
        # 使用大数值 user_id 避免与其他测试冲突
        uid = 87654
        await svc.create_task(db_session, user_id=uid, product_info={"name": "A"})
        await svc.create_task(db_session, user_id=uid + 1, product_info={"name": "B"})
        tasks = await svc.list_tasks(db_session, user_id=uid)
        assert len(tasks) == 1

    @pytest.mark.asyncio
    async def test_export_without_script_raises(self, db_session):
        """无剧本时导出应报错"""
        task = await svc.create_task(db_session, user_id=1, product_info={"name": "测试"})
        with pytest.raises(ValueError, match="无可导出"):
            await svc.export_video(db_session, task.id)

    @pytest.mark.asyncio
    async def test_export_happy_path(self, db_session):
        """完整导出流程"""
        task = await svc.create_task(
            db_session, user_id=1,
            product_info={"name": "测试"},
            aspect_ratio="16:9",
        )

        # 创建剧本
        script = Script(
            task_id=task.id,
            content={
                "scenes": [
                    {"id": 1, "description": "开场", "narration": "大家好", "duration": 5},
                ]
            },
            strategy="promotional",
        )
        db_session.add(script)
        await db_session.commit()
        task.script_id = script.id
        await db_session.commit()

        mock_result = {"output_url": "https://example.com/output.mp4"}

        with patch("app.creation.service.call_workflow", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = mock_result

            result = await svc.export_video(db_session, task.id, aspect_ratio="1:1")

            assert result["output_url"] == "https://example.com/output.mp4"
            assert result["aspect_ratio"] == "1:1"
            assert result["status"] == "EXPORTED"

            # 验证工作流被调用
            mock_call.assert_called_once()
            payload = mock_call.call_args[0][1]
            assert payload["aspect_ratio"] == "1:1"
            assert len(payload["scenes"]) == 1
            assert payload["scenes"][0]["scene_id"] == "1"

    @pytest.mark.asyncio
    async def test_export_uses_task_aspect_ratio(self, db_session):
        """不传 aspect_ratio 时使用任务原有的"""
        task = await svc.create_task(
            db_session, user_id=1,
            product_info={"name": "测试"},
            aspect_ratio="4:3",
        )
        script = Script(
            task_id=task.id,
            content={"scenes": [{"id": 1, "description": "开场", "duration": 5}]},
            strategy="promotional",
        )
        db_session.add(script)
        await db_session.commit()
        task.script_id = script.id
        await db_session.commit()

        with patch("app.creation.service.call_workflow", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = {"output_url": "https://example.com/out.mp4"}
            result = await svc.export_video(db_session, task.id)

            assert result["aspect_ratio"] == "4:3"
            payload = mock_call.call_args[0][1]
            assert payload["aspect_ratio"] == "4:3"

    @pytest.mark.asyncio
    async def test_export_workflow_fails(self, db_session):
        """工作流调用失败应抛出 RuntimeError"""
        task = await svc.create_task(db_session, user_id=1, product_info={"name": "测试"})
        script = Script(
            task_id=task.id,
            content={"scenes": [{"id": 1, "description": "开场", "duration": 5}]},
            strategy="promotional",
        )
        db_session.add(script)
        await db_session.commit()
        task.script_id = script.id
        await db_session.commit()

        with patch("app.creation.service.call_workflow", new_callable=AsyncMock) as mock_call:
            mock_call.side_effect = Exception("工作流超时")
            with pytest.raises(RuntimeError, match="视频合成工作流调用失败"):
                await svc.export_video(db_session, task.id)

    @pytest.mark.asyncio
    async def test_get_task_logs_empty(self, db_session):
        logs = await svc.get_task_logs(db_session, 99999)
        assert logs == []

    @pytest.mark.asyncio
    async def test_get_nonexistent_task(self, db_session):
        task = await svc.get_task(db_session, 99999)
        assert task is None

    @pytest.mark.asyncio
    async def test_update_task_status(self, db_session):
        task = await svc.create_task(db_session, user_id=1, product_info={"name": "测试"})
        updated = await svc.update_task_status(db_session, task.id, "COMPLETED")
        assert updated is not None
        assert updated.status == "COMPLETED"

    @pytest.mark.asyncio
    async def test_update_nonexistent_status(self, db_session):
        result = await svc.update_task_status(db_session, 99999, "DONE")
        assert result is None
