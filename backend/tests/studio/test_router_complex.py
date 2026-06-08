"""studio/router.py generate-video/poll-generate/asr/burn-subtitles 测试"""
import json, os, pytest
from unittest.mock import patch, AsyncMock, MagicMock, mock_open
from fastapi import HTTPException
from app.auth.models import User
from app.agent.models import SessionFile


@pytest.fixture
def dummy_user():
    return User(id=1, username="cov_user", hashed_password="h", is_active=True, role="user")


SESSION_ID = 200
FAKE_ROOT = f"/fake/sessions/{SESSION_ID}"
FAKE_SCRIPTS = f"{FAKE_ROOT}/scripts"
FAKE_SCRIPT_PATH = f"{FAKE_SCRIPTS}/script_{SESSION_ID}.json"


# ── POST /generate-video 错误分支 ─────────────────────────

class TestGenerateVideo:
    @pytest.mark.asyncio
    async def test_script_not_found_404(self, db_session, dummy_user):
        from app.studio.router import studio_generate_video
        with patch("os.path.exists", return_value=False), \
             patch("app.agent.models.ensure_session_dir",
                   return_value={"root": FAKE_ROOT, "scripts": FAKE_SCRIPTS}):
            with pytest.raises(HTTPException) as exc:
                await studio_generate_video({"session_id": SESSION_ID}, db_session, dummy_user)
            assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_no_scenes_raises_400(self, db_session, dummy_user):
        """剧本无场景"""
        from app.studio.router import studio_generate_video
        empty_script = json.dumps({"script": {"scenes": []}})
        with patch("os.path.exists", return_value=True), \
             patch("builtins.open", mock_open(read_data=empty_script)), \
             patch("app.agent.models.ensure_session_dir",
                   return_value={"root": FAKE_ROOT, "scripts": FAKE_SCRIPTS}):
            with pytest.raises(HTTPException) as exc:
                await studio_generate_video({"session_id": SESSION_ID}, db_session, dummy_user)
            assert exc.value.status_code == 400

    @pytest.mark.asyncio
    async def test_no_task_ids_raises_500(self, db_session, dummy_user):
        """生成任务无 task_ids"""
        from app.studio.router import studio_generate_video
        script = json.dumps({
            "script": {
                "scenes": [{"scene_id": 1, "duration": 5}],
                "title": "test",
                "style": "电商",
            }
        })
        with patch("os.path.exists", return_value=True), \
             patch("builtins.open", mock_open(read_data=script)), \
             patch("app.agent.models.ensure_session_dir",
                   return_value={"root": FAKE_ROOT, "scripts": FAKE_SCRIPTS}), \
             patch("app.workers.workflow.call_workflow", new_callable=AsyncMock) as cwf:
            cwf.return_value = {"result": {"task_ids": []}}
            with pytest.raises(HTTPException) as exc:
                await studio_generate_video({"session_id": SESSION_ID}, db_session, dummy_user)
            assert exc.value.status_code == 500

    @pytest.mark.asyncio
    async def test_local_api_key_path_raises_502_on_error(self, db_session, dummy_user):
        """本地模式：run_video_generate 抛异常 -> 502"""
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
                "scenes": [{"scene_id": 1, "duration": 5, "lines": [], "type": "scene"}],
                "title": "test", "style": "电商",
            }
        })
        with patch("os.path.exists", return_value=True), \
             patch("builtins.open", mock_open(read_data=script)), \
             patch("app.agent.models.ensure_session_dir",
                   return_value={"root": FAKE_ROOT, "scripts": FAKE_SCRIPTS}), \
             patch("app.workflow.runners.video_generate.run_video_generate",
                   new_callable=AsyncMock, side_effect=Exception("Seedance error")):
            with pytest.raises(HTTPException) as exc:
                await studio_generate_video({"session_id": SESSION_ID}, db_session, dummy_user)
            assert exc.value.status_code == 502

    @pytest.mark.asyncio
    async def test_scene_materials_from_state_collection(self, db_session, dummy_user):
        """场景无素材时，从 workflow_state 的 collection 取"""
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
                "scenes": [{"scene_id": 1, "duration": 5, "lines": [], "type": "scene"}],
                "title": "test", "style": "电商",
            }
        })
        state_data = json.dumps({
            "selected_collection_id": None,
            "collections": [],
        })

        call_count = [0]

        async def fake_run_video_generate(api_key, params):
            call_count[0] += 1
            return {"result": {"task_ids": [{"scene_id": 1}]}}

        def mock_state_open(*a, **kw):
            if "workflow_state.json" in str(a):
                return mock_open(read_data=state_data)(*a, **kw)
            return mock_open(read_data=script)(*a, **kw)

        with patch("app.studio.router.add_trace", new_callable=AsyncMock), \
             patch("os.path.exists", return_value=True), \
             patch("os.makedirs"), \
             patch("app.agent.models.ensure_session_dir",
                   return_value={"root": FAKE_ROOT, "scripts": FAKE_SCRIPTS}), \
             patch("builtins.open", mock_state_open), \
             patch("app.workflow.runners.video_generate.run_video_generate",
                   new=fake_run_video_generate), \
             patch("app.agent.models.SessionFile", MagicMock()), \
             patch("sqlalchemy.ext.asyncio.AsyncSession.add"), \
             patch("sqlalchemy.ext.asyncio.AsyncSession.commit", new_callable=AsyncMock), \
             patch("sqlalchemy.ext.asyncio.AsyncSession.flush", new_callable=AsyncMock):
            result = await studio_generate_video({"session_id": SESSION_ID, "script_name": "test"}, db_session, dummy_user)
            assert result["submitted"] is True
            assert call_count[0] == 1


# ── POST /poll-generate 错误分支 ──────────────────────────

class TestPollGenerate:
    @pytest.mark.asyncio
    async def test_no_task_returns_no_task(self, db_session):
        from app.studio.router import studio_poll_generate
        with patch("app.agent.models.get_session_files", new_callable=AsyncMock) as gsf:
            gsf.return_value = []
            result = await studio_poll_generate(SESSION_ID, db_session)
            assert result["status"] == "no_task"

    @pytest.mark.asyncio
    async def test_old_format_task_ids(self, db_session):
        """旧格式 task_ids 直接是 list"""
        from app.studio.router import studio_poll_generate
        sf = SessionFile(
            session_id=SESSION_ID, file_type="video_task",
            description=json.dumps([{"scene_id": 1}]),
        )
        with patch("app.agent.models.get_session_files", new_callable=AsyncMock) as gsf, \
             patch("app.workers.workflow.call_workflow", new_callable=AsyncMock) as cwf:
            gsf.return_value = [sf]
            cwf.return_value = {"result": {"status": "running"}}
            result = await studio_poll_generate(SESSION_ID, db_session)
            assert result["status"] == "running"

    @pytest.mark.asyncio
    async def test_new_format_local_mode(self, db_session):
        """新格式 mode=local 模式"""
        from app.studio.router import studio_poll_generate
        sf = SessionFile(
            session_id=SESSION_ID, file_type="video_task",
            description=json.dumps({
                "mode": "local",
                "task_ids": [{"scene_id": 1}],
                "api_key": "sk-test",
            }),
        )
        with patch("app.agent.models.get_session_files", new_callable=AsyncMock) as gsf, \
             patch("app.workflow.runners.video_generate.query_video_status",
                   new_callable=AsyncMock) as qvs:
            gsf.return_value = [sf]
            qvs.return_value = {"status": "running"}
            result = await studio_poll_generate(SESSION_ID, db_session)
            assert result["status"] == "running"

    @pytest.mark.asyncio
    async def test_local_query_error_returns_error(self, db_session):
        """本地查询抛异常"""
        from app.studio.router import studio_poll_generate
        sf = SessionFile(
            session_id=SESSION_ID, file_type="video_task",
            description=json.dumps({
                "mode": "local",
                "task_ids": [{"scene_id": 1}],
                "api_key": "sk-test",
            }),
        )
        with patch("app.agent.models.get_session_files", new_callable=AsyncMock) as gsf, \
             patch("app.workflow.runners.video_generate.query_video_status",
                   new_callable=AsyncMock, side_effect=Exception("query failed")):
            gsf.return_value = [sf]
            result = await studio_poll_generate(SESSION_ID, db_session)
            assert result["status"] == "error"

    @pytest.mark.asyncio
    async def test_coze_query_error(self, db_session):
        """Coze 查询抛异常"""
        from app.studio.router import studio_poll_generate
        sf = SessionFile(
            session_id=SESSION_ID, file_type="video_task",
            description=json.dumps([{"scene_id": 1}]),
        )
        with patch("app.agent.models.get_session_files", new_callable=AsyncMock) as gsf, \
             patch("app.workers.workflow.call_workflow",
                   new_callable=AsyncMock, side_effect=Exception("coze failed")):
            gsf.return_value = [sf]
            result = await studio_poll_generate(SESSION_ID, db_session)
            assert result["status"] == "error"

    @pytest.mark.asyncio
    async def test_unknown_status(self, db_session):
        from app.studio.router import studio_poll_generate
        sf = SessionFile(
            session_id=SESSION_ID, file_type="video_task",
            description=json.dumps([{"scene_id": 1}]),
        )
        with patch("app.agent.models.get_session_files", new_callable=AsyncMock) as gsf, \
             patch("app.workers.workflow.call_workflow", new_callable=AsyncMock) as cwf:
            gsf.return_value = [sf]
            cwf.return_value = {"result": {"status": "weird_status"}}
            result = await studio_poll_generate(SESSION_ID, db_session)
            assert result["status"] == "unknown"

    @pytest.mark.asyncio
    async def test_completed_status_saves_clips(self, db_session):
        from app.studio.router import studio_poll_generate
        sf = SessionFile(
            session_id=SESSION_ID, file_type="video_task",
            description=json.dumps([{"scene_id": 1}]),
        )
        with patch("app.agent.models.get_session_files", new_callable=AsyncMock) as gsf, \
             patch("app.workers.workflow.call_workflow", new_callable=AsyncMock) as cwf, \
             patch("app.studio.router.add_trace", new_callable=AsyncMock), \
             patch("sqlalchemy.ext.asyncio.AsyncSession.add"), \
             patch("sqlalchemy.ext.asyncio.AsyncSession.commit", new_callable=AsyncMock), \
             patch("sqlalchemy.ext.asyncio.AsyncSession.flush", new_callable=AsyncMock):
            async def fake_gsf(db, sid):
                return [sf]
            gsf.side_effect = fake_gsf
            cwf.return_value = {"result": {
                "status": "completed",
                "video_clips": [{"scene_id": 1, "video_url": "http://cdn.com/v.mp4", "duration": 10}],
            }}
            result = await studio_poll_generate(SESSION_ID, db_session)
            assert result["status"] == "completed"


# ── POST /asr 错误分支 ────────────────────────────────────

class TestASR:
    @pytest.mark.asyncio
    async def test_no_video_url_400(self, db_session, dummy_user):
        from app.studio.router import studio_asr
        with pytest.raises(HTTPException) as exc:
            await studio_asr({"session_id": SESSION_ID}, db_session, dummy_user)
        assert exc.value.status_code == 400

    @pytest.mark.asyncio
    async def test_local_path_detected(self, db_session, dummy_user):
        """从 URL 提取本地路径"""
        from app.studio.router import studio_asr
        with patch("os.path.exists", return_value=True), \
             patch("builtins.open", mock_open()), \
             patch("tempfile.mkdtemp", return_value="/tmp/asr_test"), \
             patch("subprocess.run"), \
             patch("shutil.rmtree"):
            from unittest.mock import ANY
            # Mock WhisperModel
            with patch("faster_whisper.WhisperModel") as wm:
                model_instance = MagicMock()
                wm.return_value = model_instance
                model_instance.transcribe.return_value = ([], MagicMock(duration=5.0))
                result = await studio_asr(
                    {"video_url": "/uploads/v.mp4", "session_id": SESSION_ID},
                    db_session, dummy_user,
                )
                assert "segments" in result

    @pytest.mark.asyncio
    async def test_fallback_http_download(self, db_session, dummy_user):
        """本地路径不存在时走 HTTP 下载"""
        from app.studio.router import studio_asr
        with patch("os.path.exists", return_value=False), \
             patch("builtins.open", mock_open()), \
             patch("tempfile.mkdtemp", return_value="/tmp/asr_test2"), \
             patch("subprocess.run"), \
             patch("shutil.rmtree"), \
             patch("httpx.AsyncClient.get") as http_get:
            with patch("faster_whisper.WhisperModel") as wm:
                model_instance = MagicMock()
                wm.return_value = model_instance
                model_instance.transcribe.return_value = ([], MagicMock(duration=5.0))
                http_resp = MagicMock()
                http_resp.status_code = 200
                http_get.return_value = http_resp
                result = await studio_asr(
                    {"video_url": "http://cdn.com/v.mp4", "session_id": SESSION_ID},
                    db_session, dummy_user,
                )
                assert "segments" in result


# ── POST /burn-subtitles 错误分支 ─────────────────────────

class TestBurnSubtitles:
    @pytest.mark.asyncio
    async def test_no_video_url_400(self, db_session, dummy_user):
        from app.studio.router import studio_burn_subtitles
        with pytest.raises(HTTPException) as exc:
            await studio_burn_subtitles({"session_id": SESSION_ID}, db_session, dummy_user)
        assert exc.value.status_code == 400

    @pytest.mark.asyncio
    async def test_no_subtitles_no_bgm_400(self, db_session, dummy_user):
        from app.studio.router import studio_burn_subtitles
        with patch("os.path.exists", return_value=False), \
             patch("builtins.open", mock_open()), \
             patch("tempfile.mkdtemp", return_value="/tmp/burn_test"), \
             patch("httpx.AsyncClient.get") as http_get, \
             patch("shutil.rmtree"):
            http_resp = MagicMock()
            http_resp.status_code = 200
            http_get.return_value = http_resp
            await studio_burn_subtitles(
                {"video_url": "http://cdn.com/v.mp4", "session_id": SESSION_ID,
                 "segments": [], "bgm_url": ""},
                db_session, dummy_user,
            )
            # 无 segments 且 无 bgm 时返回 error，不抛异常
            # 需要确认 error 字段存在
            # 代码逻辑抛出 HTTPException(400, "至少需要字幕或 BGM 其中之一")
            # 但这个需要在本地文件不存在且走 HTTP 下载后才会触发
        with patch("os.path.exists", return_value=False), \
             patch("tempfile.mkdtemp", return_value="/tmp/burn_test2"), \
             patch("httpx.AsyncClient.get") as http_get, \
             patch("builtins.open", mock_open()), \
             patch("subprocess.run") as ffmpeg, \
             patch("shutil.rmtree"):
            http_resp = MagicMock()
            http_resp.status_code = 200
            http_get.return_value = http_resp
            result = await studio_burn_subtitles(
                {"video_url": "http://cdn.com/v.mp4", "session_id": SESSION_ID,
                 "segments": [], "bgm_url": ""},
                db_session, dummy_user,
            )
            # HTTPException(400) 被 try/except 捕获，返回 dict
            assert "error" in result

    @pytest.mark.asyncio
    async def test_bgm_only_ffmpeg_success(self, db_session, dummy_user):
        from app.studio.router import studio_burn_subtitles
        with patch("os.path.exists", return_value=True), \
             patch("builtins.open", mock_open()), \
             patch("tempfile.mkdtemp", return_value="/tmp/burn_bgm"), \
             patch("shutil.rmtree"), \
             patch("subprocess.run") as ffmpeg, \
             patch("os.makedirs"), \
             patch("shutil.copy2"), \
             patch("httpx.AsyncClient.get") as http_get, \
             patch("app.core.signer.generate_signed_url") as sign:
            ffmpeg_res = MagicMock()
            ffmpeg_res.returncode = 0
            ffmpeg.return_value = ffmpeg_res
            sign.return_value = "/signed/t/u.mp4"
            http_resp = MagicMock()
            http_resp.status_code = 200
            http_get.return_value = http_resp
            result = await studio_burn_subtitles(
                {"video_url": "/uploads/v.mp4", "session_id": SESSION_ID,
                 "segments": [{"start": 0, "end": 2, "text": "hello"}], "bgm_url": "http://cdn.com/bgm.mp3"},
                db_session, dummy_user,
            )
            assert "url" in result
