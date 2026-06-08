"""studio/router.py 剩余边缘行覆盖"""
import json, pytest
from unittest.mock import patch, AsyncMock, MagicMock, mock_open
from fastapi import HTTPException
from app.auth.models import User


@pytest.fixture
def dummy_user():
    return User(id=1, username="cov_user", hashed_password="h", is_active=True, role="user")


class TestTraceEdge:
    @pytest.mark.asyncio
    async def test_get_state_path(self):
        """覆盖 get_state_path 的保证存活行"""
        from app.studio.router import get_state_path
        with patch("app.agent.models.ensure_session_dir",
                   return_value={"root": "/tmp/sessions/1"}):
            path = get_state_path(1)
            assert "workflow_state.json" in path


class TestSemanticSearchEdge:
    @pytest.mark.asyncio
    async def test_empty_body_handles(self, db_session, dummy_user):
        """覆盖 semantic-search 空返回路径"""
        from app.studio.router import semantic_search
        with patch("app.workers.workflow.call_workflow", new_callable=AsyncMock) as cwf:
            cwf.return_value = {}
            result = await semantic_search({"product_info": {}}, db_session, dummy_user)
            assert result["total"] == 0


class TestGenerateVideoEdge:
    @pytest.mark.asyncio
    async def test_custom_script_name(self, db_session, dummy_user):
        """覆盖自定义 script_name 路径"""
        from app.studio.router import studio_generate_video
        with patch("os.path.exists", return_value=False), \
             patch("app.agent.models.ensure_session_dir",
                   return_value={"root": "/tmp", "scripts": "/tmp/scripts"}):
            with pytest.raises(HTTPException) as exc:
                await studio_generate_video(
                    {"session_id": 1, "script_name": "custom_script", "aspect_ratio": "16:9"},
                    db_session, dummy_user,
                )
            assert exc.value.status_code == 404


class TestDeleteClipEdge:
    @pytest.mark.asyncio
    async def test_delete_no_clip_id_no_file_url(self, db_session, dummy_user):
        """delete-clip clip_id 和 file_url 都为空"""
        from app.studio.router import studio_delete_clip
        result = await studio_delete_clip({"clip_id": None, "file_url": ""}, db_session, dummy_user)
        assert result == {"ok": True}


class TestComposeEdge:
    @pytest.mark.asyncio
    async def test_cleanup_on_ffmpeg_fail(self, db_session, dummy_user):
        """compose-video FFmpeg 失败后清理 tempdir"""
        from app.studio.router import studio_compose_video
        from app.agent.models import SessionFile as SF
        clip = SF(session_id=1, file_type="video_clip", file_url="/uploads/clips/1.mp4")
        db_session.add(clip)
        await db_session.flush()

        class FakeResp:
            status_code = 200
            content = b"fake"
            def raise_for_status(self): pass

        with patch("app.agent.models.get_session_files", new_callable=AsyncMock) as gsf, \
             patch("httpx.AsyncClient.get", new_callable=AsyncMock) as http_get, \
             patch("subprocess.run") as ffmpeg, \
             patch("tempfile.mkdtemp", return_value="/tmp/compose_clean"), \
             patch("shutil.rmtree") as rm:
            gsf.return_value = [clip]
            http_get.return_value = FakeResp()
            ffmpeg_res = MagicMock()
            ffmpeg_res.returncode = 1
            ffmpeg_res.stderr = "error"
            ffmpeg.return_value = ffmpeg_res
            result = await studio_compose_video({"session_id": 1}, db_session, dummy_user)
            assert result["composed"] is False
            rm.assert_called()  # 确认清理被调用


class TestPollGenerateEdge:
    @pytest.mark.asyncio
    async def test_old_format_direct_list(self, db_session):
        """旧格式 task_ids 直接是 list，非 dict 格式"""
        from app.studio.router import studio_poll_generate
        from app.agent.models import SessionFile as SF
        sf = SF(session_id=1, file_type="video_task",
                description=json.dumps([{"scene_id": 1}]))
        with patch("app.agent.models.get_session_files", new_callable=AsyncMock) as gsf, \
             patch("app.workers.workflow.call_workflow", new_callable=AsyncMock) as cwf:
            gsf.return_value = [sf]
            mock_resp = {"result": {"status": "running", "video_clips": []}}
            cwf.return_value = mock_resp
            result = await studio_poll_generate(1, db_session)
            assert result["status"] == "running"


class TestAgentEditEdge:
    @pytest.mark.asyncio
    async def test_bgm_style_no_match(self, db_session, dummy_user):
        """agent-edit BGM 风格无匹配"""
        from app.studio.router import studio_agent_edit
        from app.material.models import Material
        bgm = Material(
            user_id="1", material_type="audio", name="jazz",
            image_url="/u/j.mp3", tags='["bgm"]', input_type="image",
            audio_features=json.dumps({"mood": "jazz"}),
        )
        db_session.add(bgm)
        await db_session.flush()
        clips = [{"id": 1, "url": "", "scene_id": "1", "duration": 5}]
        result = await studio_agent_edit(
            {"clips": clips, "session_id": 1, "bgm_style": "classical"},
            db_session, dummy_user,
        )
        assert result["bgm"] is None


class TestVideoUrlEdge:
    @pytest.mark.asyncio
    async def test_http_url_no_uploads_400(self, db_session, dummy_user):
        from app.studio.router import get_signed_video_url
        from app.agent.models import SessionFile as SF
        sf = SF(session_id=1, file_type="video_clip",
                file_url="http://cdn.com/nouploads/v.mp4")
        db_session.add(sf)
        await db_session.flush()
        with pytest.raises(HTTPException) as exc:
            await get_signed_video_url(sf.id, db_session, dummy_user)
        assert exc.value.status_code == 400
