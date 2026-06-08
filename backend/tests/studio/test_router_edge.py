"""studio/router.py 第三批测试 — semantic-search, compose-video (FFmpeg成功路径), agent-edit"""
import json, os
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi import HTTPException
from app.auth.models import User


@pytest.fixture
def dummy_user():
    return User(id=1, username="cov_user", hashed_password="h", is_active=True, role="user")


SESSION_ID = 100
FAKE_ROOT = f"/fake/sessions/{SESSION_ID}"


# ── POST /semantic-search ─────────────────────────────────

class TestSemanticSearch:
    @pytest.mark.asyncio
    async def test_empty_product_queries(self, db_session, dummy_user):
        """call_workflow 返回空列表"""
        from app.studio.router import semantic_search
        body = {"product_info": {"title": "测试", "content": "产品描述"}}

        async def fake_call_workflow(name, params):
            if name == "query-generate":
                return {"product_queries": [], "general_queries": []}
            elif name == "material-search":
                return {"product_embeddings": []}
            return {}

        with patch("app.workers.workflow.call_workflow", new=fake_call_workflow), \
             patch("app.material.search.search_materials_by_embeddings", new_callable=AsyncMock) as sm:
            sm.return_value = []
            result = await semantic_search(body, db_session, dummy_user)
            assert result["total"] == 0
            assert result["materials"] == []

    @pytest.mark.asyncio
    async def test_with_embeddings(self, db_session, dummy_user):
        from app.studio.router import semantic_search
        body = {"product_info": {"title": "测试", "content": "产品"}}

        async def fake_call_workflow(name, params):
            if name == "query-generate":
                return {"product_queries": ["q1"], "general_queries": []}
            elif name == "material-search":
                return {"product_embeddings": [{"embedding": [0.1, 0.2]}]}
            return {}

        with patch("app.workers.workflow.call_workflow", new=fake_call_workflow), \
             patch("app.material.search.search_materials_by_embeddings", new_callable=AsyncMock) as sm:
            sm.return_value = [{"id": 1, "similarity": 0.85, "text_content": "hidden"}]
            result = await semantic_search(body, db_session, dummy_user)
            assert result["total"] == 1
            # text_content should be removed
            assert "text_content" not in result["materials"][0]

    @pytest.mark.asyncio
    async def test_deduplicates_results(self, db_session, dummy_user):
        from app.studio.router import semantic_search
        body = {"product_info": {"title": "测试"}}

        async def fake_call_workflow(name, params):
            if name == "query-generate":
                return {"product_queries": ["q1", "q2"], "general_queries": []}
            elif name == "material-search":
                return {"product_embeddings": [{"embedding": [0.1, 0.2]}, {"embedding": [0.3, 0.4]}]}
            return {}

        with patch("app.workers.workflow.call_workflow", new=fake_call_workflow), \
             patch("app.material.search.search_materials_by_embeddings", new_callable=AsyncMock) as sm:
            # 两个搜索返回同一个素材
            sm.side_effect = [
                [{"id": 1, "similarity": 0.85}],
                [{"id": 1, "similarity": 0.90}],
            ]
            result = await semantic_search(body, db_session, dummy_user)
            assert result["total"] == 1  # dedup


# ── POST /compose-video 成功路径 ──────────────────────────

class TestComposeVideoSuccess:
    @pytest.mark.asyncio
    async def test_ffmpeg_concat_success(self, db_session, dummy_user):
        from app.studio.router import studio_compose_video
        from app.agent.models import SessionFile as SF

        clip = SF(session_id=SESSION_ID, file_type="video_clip", file_url="/uploads/clips/1.mp4")
        db_session.add(clip)
        await db_session.flush()

        class FakeResp:
            status_code = 200
            def raise_for_status(self): pass
            content = b"fake_video_data"

        with patch("app.agent.models.get_session_files", new_callable=AsyncMock) as gsf, \
             patch("httpx.AsyncClient.get", new_callable=AsyncMock) as http_get, \
             patch("builtins.open", MagicMock()), \
             patch("subprocess.run") as ffmpeg, \
             patch("tempfile.mkdtemp", return_value="/tmp/test_compose"), \
             patch("os.path.exists", return_value=True), \
             patch("os.makedirs"), \
             patch("shutil.copy2"), \
             patch("shutil.rmtree"), \
             patch("app.core.signer.generate_signed_url") as sign:
            gsf.return_value = [clip]
            http_get.return_value = FakeResp()
            ffmpeg_res = MagicMock()
            ffmpeg_res.returncode = 0
            ffmpeg.return_value = ffmpeg_res
            sign.return_value = "/signed/t/u.mp4"

            result = await studio_compose_video(
                {"session_id": SESSION_ID}, db_session, dummy_user
            )
            assert result["composed"] is True
            assert "videos" in result
            assert len(result["videos"]) == 1

    @pytest.mark.asyncio
    async def test_ffmpeg_failure_returns_error(self, db_session, dummy_user):
        from app.studio.router import studio_compose_video
        from app.agent.models import SessionFile as SF

        clip = SF(session_id=SESSION_ID, file_type="video_clip", file_url="/uploads/clips/1.mp4")
        db_session.add(clip)
        await db_session.flush()

        with patch("app.agent.models.get_session_files", new_callable=AsyncMock) as gsf, \
             patch("httpx.AsyncClient.get") as http_get, \
             patch("subprocess.run") as ffmpeg, \
             patch("tempfile.mkdtemp", return_value="/tmp/test_compose_fail"), \
             patch("os.path.exists", return_value=True), \
             patch("shutil.rmtree"):
            gsf.return_value = [clip]
            http_resp = MagicMock()
            http_resp.status_code = 200
            http_resp.raise_for_status = MagicMock()
            http_get.return_value = http_resp
            ffmpeg_res = MagicMock()
            ffmpeg_res.returncode = 1
            ffmpeg_res.stderr = "concat error"
            ffmpeg.return_value = ffmpeg_res

            result = await studio_compose_video(
                {"session_id": SESSION_ID}, db_session, dummy_user
            )
            assert result["composed"] is False
            assert "error" in result

    @pytest.mark.asyncio
    async def test_http_download_failure_skipped(self, db_session, dummy_user):
        """下载 clip 失败时跳过该 clip"""
        from app.studio.router import studio_compose_video
        from app.agent.models import SessionFile as SF

        clip1 = SF(session_id=SESSION_ID, file_type="video_clip", file_url="/uploads/clips/1.mp4")
        clip2 = SF(session_id=SESSION_ID, file_type="video_clip", file_url="/uploads/clips/2.mp4")
        db_session.add_all([clip1, clip2])
        await db_session.flush()

        call_count = [0]

        class FakeResp:
            def __init__(self, fail=False):
                self.fail = fail
                self.status_code = 200
            def raise_for_status(self):
                if self.fail:
                    raise Exception("download failed")
            content = b"fake"

        class FakeAsyncGet:
            async def __call__(self, url):
                call_count[0] += 1
                return FakeResp(fail="1.mp4" in url)

        with patch("app.agent.models.get_session_files", new_callable=AsyncMock) as gsf, \
             patch("httpx.AsyncClient.get", new=FakeAsyncGet()), \
             patch("builtins.open", MagicMock()), \
             patch("subprocess.run") as ffmpeg, \
             patch("tempfile.mkdtemp", return_value="/tmp/test_compose_skip"), \
             patch("os.path.exists", return_value=True), \
             patch("os.makedirs"), \
             patch("shutil.copy2"), \
             patch("shutil.rmtree"), \
             patch("app.core.signer.generate_signed_url") as sign:
            gsf.return_value = [clip1, clip2]
            ffmpeg_res = MagicMock()
            ffmpeg_res.returncode = 0
            ffmpeg.return_value = ffmpeg_res
            sign.return_value = "/signed/t/u.mp4"

            result = await studio_compose_video(
                {"session_id": SESSION_ID}, db_session, dummy_user
            )
            assert result["composed"] is True


# ── POST /agent-edit ──────────────────────────────────────

class TestAgentEdit:
    @pytest.mark.asyncio
    async def test_empty_clips(self, db_session, dummy_user):
        from app.studio.router import studio_agent_edit
        result = await studio_agent_edit({"clips": [], "session_id": SESSION_ID}, db_session, dummy_user)
        assert result["clips"] == []

    @pytest.mark.asyncio
    async def test_clips_no_url_returned_as_is(self, db_session, dummy_user):
        from app.studio.router import studio_agent_edit
        clips = [{"id": 1, "url": "", "scene_id": "1", "duration": 5}]
        with patch("httpx.AsyncClient.get"):
            result = await studio_agent_edit({"clips": clips, "session_id": SESSION_ID}, db_session, dummy_user)
            assert len(result["clips"]) == 1
            assert result["clips"][0]["transition"] == "cut"

    @pytest.mark.asyncio
    async def test_clip_with_url_ffprobe_analysis(self, db_session, dummy_user):
        from app.studio.router import studio_agent_edit
        clips = [{"id": 1, "url": "/uploads/clips/1.mp4", "scene_id": "1", "duration": 5}]

        class FakeResp:
            status_code = 200
            content = b"fake"

        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as http_get, \
             patch("subprocess.run") as ffprobe, \
             patch("tempfile.mkdtemp", return_value="/tmp/test_agent"), \
             patch("builtins.open", MagicMock()), \
             patch("shutil.rmtree"):
            http_get.return_value = FakeResp()
            ffprobe_res = MagicMock()
            ffprobe_res.stdout = "10.5"
            ffprobe.return_value = ffprobe_res
            result = await studio_agent_edit({"clips": clips, "session_id": SESSION_ID}, db_session, dummy_user)
            assert len(result["clips"]) == 1
            assert result["clips"][0]["duration"] == 10.5
            assert result["clips"][0]["transition"] == "dissolve"

    @pytest.mark.asyncio
    async def test_bgm_style_filtering(self, db_session, dummy_user):
        from app.studio.router import studio_agent_edit
        from app.material.models import Material
        # 插入一个 BGM 素材
        bgm = Material(
            user_id=str(dummy_user.id), material_type="audio",
            name="happy_bgm", image_url="/uploads/bgm.mp3",
            tags='["bgm"]', input_type="image",
            audio_features=json.dumps({"mood": "happy"}),
        )
        db_session.add(bgm)
        await db_session.flush()
        clips = [{"id": 1, "url": "", "scene_id": "1", "duration": 5}]
        result = await studio_agent_edit(
            {"clips": clips, "session_id": SESSION_ID, "bgm_style": "happy"},
            db_session, dummy_user,
        )
        assert result["bgm"] is not None
        assert result["bgm"]["name"] == "happy_bgm"
