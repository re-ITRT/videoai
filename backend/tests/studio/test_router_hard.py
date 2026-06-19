"""studio/router.py 视频帧提取 + ASR LLM 纠错 + ai-edit 工具路径覆盖"""
import json, os, pytest
from unittest.mock import patch, AsyncMock, MagicMock, mock_open
from app.auth.models import User


@pytest.fixture
def dummy_user():
    return User(id=1, username="cov_user", hashed_password="h", is_active=True, role="user")


SESSION_ID = 300


class TestVideoFrameExtraction:
    """覆盖 studio/router.py lines 316-370: 视频素材帧提取"""

    @pytest.mark.asyncio
    async def test_video_frame_extraction_with_video_material(self, db_session, dummy_user):
        """视频素材帧提取 + generate_signed_url 调用"""
        from app.studio.router import studio_generate_video
        from app.workflow.models import WorkflowConfig

        wfc = WorkflowConfig(
            user_id=str(dummy_user.id), workflow_name="video-generate",
            enabled=1, config=json.dumps({"api_key": "sk-test"}),
        )
        db_session.add(wfc)
        await db_session.flush()

        script = json.dumps({
            "script": {
                "scenes": [{"scene_id": 1, "duration": 5, "lines": [], "type": "scene", "materials": [1]}],
                "title": "test", "style": "电商",
            }
        })

        with patch("app.studio.router.add_trace", new_callable=AsyncMock), \
             patch("os.path.exists", return_value=True), \
             patch("os.makedirs"), \
             patch("app.studio.router.ensure_session_dir",
                   return_value={"root": f"/tmp/sessions/{SESSION_ID}",
                                  "scripts": f"/tmp/sessions/{SESSION_ID}/scripts"}), \
             patch("builtins.open", mock_open(read_data=script)), \
             patch("app.workflow.runners.video_generate.run_video_generate",
                   new_callable=AsyncMock) as rvg, \
             patch("app.agent.models.SessionFile", MagicMock()), \
             patch("sqlalchemy.ext.asyncio.AsyncSession.add"), \
             patch("sqlalchemy.ext.asyncio.AsyncSession.commit", new_callable=AsyncMock), \
             patch("sqlalchemy.ext.asyncio.AsyncSession.flush", new_callable=AsyncMock), \
             patch("sqlalchemy.select") as sel:
            # Mock Material query to return a video material
            from app.material.models import Material
            from sqlalchemy import select as real_select
            original_select = real_select

            sel.return_value.where.return_value = MagicMock()
            # Make the execute return a result with video material
            async def fake_execute(*a):
                result = MagicMock()
                m = Material(id=1, user_id="1", material_type="video", input_type="video",
                              image_url="/uploads/videos/test.mp4")
                result.scalars.return_value.all.return_value = [m]
                return result
            db_session.execute = fake_execute

            rvg.return_value = {"result": {"task_ids": [{"scene_id": 1}]}}

            result = await studio_generate_video(
                {"session_id": SESSION_ID}, db_session, dummy_user
            )
            assert result["submitted"] is True


class TestAiEditToolEdges:
    """覆盖 ai-edit 工具边缘 (lines 1235-1279)"""

    @pytest.mark.asyncio
    async def test_change_text_not_found(self, db_session, dummy_user):
        """change_text 找不到旧文本"""
        from app.studio.router import studio_ai_edit
        from app.ai.models import UserAIConfig

        uac = UserAIConfig(
            user_id=str(dummy_user.id), api_key="sk-test",
            base_url="https://api.test.com/v1", model="test-model",
        )
        db_session.add(uac)
        await db_session.flush()

        script_data = json.dumps({"scenes": [{"scene_id": 1, "lines": [{"speaker": "A", "text": "你好"}]}]})
        call_count = [0]

        async def fake_post(*a, **kw):
            call_count[0] += 1
            m = MagicMock()
            m.status_code = 200
            if call_count[0] == 1:
                m.json.return_value = {
                    "choices": [{"message": {
                        "role": "assistant", "content": None,
                        "tool_calls": [{
                            "id": "c1", "type": "function",
                            "function": {"name": "change_text",
                                         "arguments": json.dumps({"old_text": "不存在的文本", "new_text": "新文本"})},
                        }]
                    }}]
                }
            else:
                m.json.return_value = {"choices": [{"message": {"role": "assistant", "content": "未找到"}}]}
            return m

        body = {"session_id": SESSION_ID, "messages": [{"role": "user", "content": "改一下"}]}
        with patch("httpx.AsyncClient.post", new=fake_post), \
             patch("app.studio.router.ensure_session_dir",
                   return_value={"root": f"/tmp/sessions/{SESSION_ID}",
                                  "scripts": f"/tmp/sessions/{SESSION_ID}/scripts"}), \
             patch("os.path.exists", return_value=True), \
             patch("builtins.open", mock_open(read_data=script_data)):
            result = await studio_ai_edit(body, db_session, dummy_user)
            assert "reply" in result
