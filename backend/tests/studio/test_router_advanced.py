"""studio/router.py 进阶端点测试 — generate-script/compose/ai-edit/video-url"""
import json, os
import pytest
from unittest.mock import patch, AsyncMock, MagicMock, mock_open
from fastapi import HTTPException
from app.auth.models import User
from app.agent.models import SessionFile


@pytest.fixture
def dummy_user():
    return User(id=1, username="cov_user", hashed_password="h", is_active=True, role="user")


SESSION_ID = 99
FAKE_ROOT = f"/fake/sessions/{SESSION_ID}"


# ── GET /video-url/{clip_id} ──────────────────────────────

class TestVideoUrl:
    @pytest.mark.asyncio
    async def test_clip_not_found_404(self, db_session, dummy_user):
        from app.studio.router import get_signed_video_url
        with pytest.raises(HTTPException) as exc:
            await get_signed_video_url(99999, db_session, dummy_user)
        assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_clip_no_file_url_404(self, db_session, dummy_user):
        sf = SessionFile(session_id=1, file_type="video_clip", file_url=None)
        db_session.add(sf)
        await db_session.flush()
        from app.studio.router import get_signed_video_url
        with pytest.raises(HTTPException) as exc:
            await get_signed_video_url(sf.id, db_session, dummy_user)
        assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_clip_with_http_url_extracts_path(self, db_session, dummy_user):
        sf = SessionFile(
            session_id=1, file_type="video_clip",
            file_url="http://cdn.com/uploads/clips/v.mp4",
        )
        db_session.add(sf)
        await db_session.flush()
        from app.studio.router import get_signed_video_url
        with patch("app.core.signer.generate_signed_url") as m:
            m.return_value = "/signed/token/uploads/clips/v.mp4"
            result = await get_signed_video_url(sf.id, db_session, dummy_user)
            assert "url" in result

    @pytest.mark.asyncio
    async def test_clip_http_no_uploads_raises_400(self, db_session, dummy_user):
        sf = SessionFile(
            session_id=1, file_type="video_clip",
            file_url="http://cdn.com/something/mp4",
        )
        db_session.add(sf)
        await db_session.flush()
        from app.studio.router import get_signed_video_url
        with pytest.raises(HTTPException) as exc:
            await get_signed_video_url(sf.id, db_session, dummy_user)
        assert exc.value.status_code == 400

    @pytest.mark.asyncio
    async def test_clip_with_relative_path(self, db_session, dummy_user):
        sf = SessionFile(
            session_id=1, file_type="video_clip",
            file_url="/uploads/clips/v.mp4",
        )
        db_session.add(sf)
        await db_session.flush()
        from app.studio.router import get_signed_video_url
        with patch("app.core.signer.generate_signed_url") as m:
            m.return_value = "/signed/token/u/v.mp4"
            result = await get_signed_video_url(sf.id, db_session, dummy_user)
            assert "url" in result
            m.assert_called_once()


# ── POST /generate-script ─────────────────────────────────

class TestGenerateScript:
    @pytest.mark.asyncio
    async def test_save_only_with_script(self, db_session, dummy_user):
        from app.studio.router import studio_generate_script
        body = {"save_only": True, "script": {"scenes": [{"scene_id": 1}]}, "session_id": SESSION_ID}
        with patch("app.studio.router._save_script") as save_mock:
            result = await studio_generate_script(body, db_session, dummy_user)
            assert result["saved"] is True
            save_mock.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_with_local_config(self, db_session, dummy_user):
        """有本地 WorkflowConfig 且启用的路径"""
        from app.studio.router import studio_generate_script
        from app.workflow.models import WorkflowConfig
        wfc = WorkflowConfig(
            user_id=str(dummy_user.id), workflow_name="script-generate",
            enabled=1, config=json.dumps({"api_key": "sk-test", "base_url": "https://test.com/v1", "model": "test-model"}),
        )
        db_session.add(wfc)
        await db_session.flush()
        body = {
            "product_content": "测试产品",
            "template": "default",
            "session_id": SESSION_ID,
            "materials": [{"id": 1}],
            "script": None,
        }
        with patch("app.workflow.runners.script_generate.run_script_generate", new_callable=AsyncMock) as rsg, \
             patch("app.studio.router._inject_materials") as inj, \
             patch("app.studio.router._save_script") as sv:
            rsg.return_value = {"script": {"scenes": [{"scene_id": 1}]}}
            inj.return_value = {"ok": True}
            result = await studio_generate_script(body, db_session, dummy_user)
            assert result["ok"] is True
            rsg.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_disabled_config_falls_to_coze(self, db_session, dummy_user):
        """WorkflowConfig 存在但 disabled，走 Coze fallback"""
        from app.studio.router import studio_generate_script
        from app.workflow.models import WorkflowConfig
        wfc = WorkflowConfig(
            user_id=str(dummy_user.id), workflow_name="script-generate",
            enabled=0, config=json.dumps({"api_key": "sk-test"}),
        )
        db_session.add(wfc)
        await db_session.flush()
        body = {
            "product_content": "测试",
            "session_id": SESSION_ID,
            "materials": [],
        }
        with patch("app.workers.workflow.call_workflow", new_callable=AsyncMock) as cwf, \
             patch("app.studio.router._inject_materials") as inj, \
             patch("app.studio.router._save_script"):
            cwf.return_value = {"script": {"scenes": []}}
            inj.return_value = {"ok": True}
            result = await studio_generate_script(body, db_session, dummy_user)
            assert result["ok"] is True
            cwf.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_config_missing_key_falls_to_coze(self, db_session, dummy_user):
        """WorkflowConfig 有但缺 api_key，走 Coze"""
        from app.studio.router import studio_generate_script
        from app.workflow.models import WorkflowConfig
        wfc = WorkflowConfig(
            user_id=str(dummy_user.id), workflow_name="script-generate",
            enabled=1, config=json.dumps({"model": "test"}),  # no api_key
        )
        db_session.add(wfc)
        await db_session.flush()
        body = {"product_content": "测试", "session_id": SESSION_ID}
        with patch("app.workers.workflow.call_workflow", new_callable=AsyncMock) as cwf, \
             patch("app.studio.router._inject_materials") as inj, \
             patch("app.studio.router._save_script"):
            cwf.return_value = {"script": {"scenes": []}}
            inj.return_value = {"ok": True}
            result = await studio_generate_script(body, db_session, dummy_user)
            assert result["ok"] is True
            cwf.assert_called_once()

    @pytest.mark.asyncio
    async def test_no_script_no_save_only_no_config_fallback(self, db_session, dummy_user):
        """没有 save_only / script / config，走 Coze"""
        from app.studio.router import studio_generate_script
        body = {"product_content": "test", "session_id": SESSION_ID}
        with patch("app.workers.workflow.call_workflow", new_callable=AsyncMock) as cwf, \
             patch("app.studio.router._inject_materials") as inj, \
             patch("app.studio.router._save_script"):
            cwf.return_value = {"script": {"scenes": [{"scene_id": 1}]}}
            inj.return_value = {"ok": True}
            result = await studio_generate_script(body, db_session, dummy_user)
            assert result["ok"] is True


# ── POST /compose-video ───────────────────────────────────

class TestComposeVideo:
    @pytest.mark.asyncio
    async def test_no_clips_raises_400(self, db_session, dummy_user):
        from app.studio.router import studio_compose_video
        with patch("app.agent.models.get_session_files", new_callable=AsyncMock) as gsf:
            gsf.return_value = []
            with pytest.raises(HTTPException) as exc:
                await studio_compose_video({"session_id": SESSION_ID}, db_session, dummy_user)
            assert exc.value.status_code == 400

    @pytest.mark.asyncio
    async def test_no_clips_passed_with_clip_ids_empty(self, db_session, dummy_user):
        """有 clip_ids 但 DB 中没有匹配的 clip"""
        from app.studio.router import studio_compose_video
        from sqlalchemy import delete
        await db_session.execute(delete(SessionFile))
        await db_session.commit()
        # 先插入一个 clip
        sf = SessionFile(session_id=SESSION_ID, file_type="video_clip", file_url="/uploads/clip.mp4")
        db_session.add(sf)
        await db_session.flush()
        with patch("app.agent.models.get_session_files", new_callable=AsyncMock) as gsf:
            gsf.return_value = [sf]
            with pytest.raises(HTTPException) as exc:
                await studio_compose_video({"session_id": SESSION_ID, "clip_ids": [999]}, db_session, dummy_user)
            assert exc.value.status_code == 400


# ── POST /ai-edit ─────────────────────────────────────────

class TestAiEdit:
    @pytest.mark.asyncio
    async def test_no_api_key_config_returns_error(self, db_session, dummy_user):
        from app.studio.router import studio_ai_edit
        body = {
            "session_id": SESSION_ID,
            "messages": [{"role": "user", "content": "改一下"}],
        }
        result = await studio_ai_edit(body, db_session, dummy_user)
        assert "error" in result
        assert "AI API Key" in result["error"]

    @pytest.mark.asyncio
    async def test_with_api_key_calls_llm(self, db_session, dummy_user):
        from app.studio.router import studio_ai_edit
        from app.ai.models import UserAIConfig
        uac = UserAIConfig(
            user_id=str(dummy_user.id),
            api_key="sk-test",
            base_url="https://api.test.com/v1",
            model="test-model",
        )
        db_session.add(uac)
        await db_session.flush()

        body = {
            "session_id": SESSION_ID,
            "messages": [{"role": "user", "content": "改一下"}],
        }

        # mock httpx 调用
        async def fake_post(*a, **kw):
            m = MagicMock()
            m.status_code = 200
            m.json.return_value = {
                "choices": [{
                    "message": {
                        "role": "assistant",
                        "content": "已修改完成",
                    }
                }]
            }
            return m

        with patch("httpx.AsyncClient.post", new=fake_post):
            result = await studio_ai_edit(body, db_session, dummy_user)
            assert "reply" in result
            assert result["reply"] == "已修改完成"
            assert "messages" in result

    @pytest.mark.asyncio
    async def test_llm_returns_tool_call(self, db_session, dummy_user):
        """AI edit tool call 循环"""
        from app.studio.router import studio_ai_edit
        from app.ai.models import UserAIConfig
        uac = UserAIConfig(
            user_id=str(dummy_user.id),
            api_key="sk-test",
            base_url="https://api.test.com/v1",
            model="test-model",
        )
        db_session.add(uac)
        await db_session.flush()

        # 确保脚本文件存在
        body = {
            "session_id": SESSION_ID,
            "messages": [{"role": "user", "content": "改一下"}],
        }
        script_dir = os.path.join(FAKE_ROOT, "scripts")
        script_path = os.path.join(script_dir, f"script_{SESSION_ID}.json")
        script_content = json.dumps({"scenes": [{"scene_id": 1, "lines": [{"speaker": "A", "text": "你好"}], "duration": 5}]})

        call_count = [0]

        async def fake_post(*a, **kw):
            call_count[0] += 1
            m = MagicMock()
            m.status_code = 200
            if call_count[0] == 1:
                # First call: return a tool call
                m.json.return_value = {
                    "choices": [{
                        "message": {
                            "role": "assistant",
                            "content": None,
                            "tool_calls": [{
                                "id": "call_1",
                                "type": "function",
                                "function": {
                                    "name": "read_script",
                                    "arguments": "{}",
                                }
                            }]
                        }
                    }]
                }
            else:
                m.json.return_value = {
                    "choices": [{
                        "message": {"role": "assistant", "content": "好的，已读取"}
                    }]
                }
            return m

        with patch("httpx.AsyncClient.post", new=fake_post), \
             patch("app.studio.router.ensure_session_dir", return_value={"root": FAKE_ROOT, "scripts": script_dir}), \
             patch("os.path.exists", return_value=True), \
             patch("builtins.open", mock_open(read_data=script_content)):
            result = await studio_ai_edit(body, db_session, dummy_user)
            assert "reply" in result
            assert call_count[0] >= 2

    @pytest.mark.asyncio
    async def test_change_text_tool(self, db_session, dummy_user):
        """测试 change_text 工具的执行"""
        from app.studio.router import studio_ai_edit
        from app.ai.models import UserAIConfig
        uac = UserAIConfig(
            user_id=str(dummy_user.id),
            api_key="sk-test",
            base_url="https://api.test.com/v1",
            model="test-model",
        )
        db_session.add(uac)
        await db_session.flush()

        body = {
            "session_id": SESSION_ID,
            "messages": [{"role": "user", "content": "改一下"}],
        }
        script_dir = os.path.join(FAKE_ROOT, "scripts")
        script_path = os.path.join(script_dir, f"script_{SESSION_ID}.json")
        script_content = json.dumps({"scenes": [{"scene_id": 1, "lines": [{"speaker": "A", "text": "旧文本"}], "duration": 5}]})

        call_count = [0]

        async def fake_post(*a, **kw):
            call_count[0] += 1
            m = MagicMock()
            m.status_code = 200
            if call_count[0] == 1:
                m.json.return_value = {
                    "choices": [{
                        "message": {
                            "role": "assistant",
                            "content": None,
                            "tool_calls": [{
                                "id": "call_1",
                                "type": "function",
                                "function": {
                                    "name": "change_text",
                                    "arguments": json.dumps({"old_text": "旧文本", "new_text": "新文本"}),
                                }
                            }]
                        }
                    }]
                }
            else:
                m.json.return_value = {
                    "choices": [{
                        "message": {"role": "assistant", "content": "已修改"}
                    }]
                }
            return m

        written_data = [script_content]

        def _mock_open(*a, **kw):
            if 'w' in str(kw.get('mode', '')) or 'w' in str(a[1] if len(a) > 1 else ''):
                m = MagicMock()
                m.__enter__.return_value.write = lambda s: written_data.__setitem__(0, s)
                m.__enter__.return_value.__enter__ = lambda: m.__enter__.return_value
                return m.__enter__()
            return mock_open(read_data=written_data[0])(*a, **kw)

        with patch("httpx.AsyncClient.post", new=fake_post), \
             patch("app.studio.router.ensure_session_dir", return_value={"root": FAKE_ROOT, "scripts": script_dir}), \
             patch("os.path.exists", return_value=True), \
             patch("builtins.open", _mock_open):
            result = await studio_ai_edit(body, db_session, dummy_user)
            assert "reply" in result
