"""studio/router.py 全覆盖测试 — 直接调 router 函数"""
import json, os
import pytest
from unittest.mock import patch, AsyncMock, MagicMock, mock_open
from fastapi import HTTPException
from app.auth.models import User
from app.agent.models import SessionFile
from app.material.models import Material


@pytest.fixture
def dummy_user():
    return User(id=1, username="cov_user", hashed_password="h", is_active=True, role="user")


SESSION_ID = 42
FAKE_ROOT = f"/fake/sessions/{SESSION_ID}"
FAKE_STATE_PATH = f"{FAKE_ROOT}/workflow_state.json"


# ── helper: add_trace ──────────────────────────────────────

class TestAddTrace:
    @pytest.mark.asyncio
    async def test_add_trace_new_entry(self):
        from app.studio.router import add_trace, get_state_path
        with patch("app.studio.router.get_state_path", return_value=FAKE_STATE_PATH), \
             patch("os.path.exists", return_value=False), \
             patch("builtins.open", mock_open()) as m:
            await add_trace(SESSION_ID, "test_step", "running", "正在测试")
            # verify write happened
            handle = m()
            written = "".join(c for c in handle.write.call_args[0])
            assert "test_step" in written
            assert "running" in written

    @pytest.mark.asyncio
    async def test_add_trace_updates_existing(self):
        from app.studio.router import add_trace
        existing_state = json.dumps({
            "trace": [{"step": "test_step", "status": "pending"}]
        })
        with patch("app.studio.router.get_state_path", return_value=FAKE_STATE_PATH), \
             patch("os.path.exists", return_value=True), \
             patch("builtins.open", mock_open(read_data=existing_state)) as m:
            await add_trace(SESSION_ID, "test_step", "completed", "完成")
            handle = m()
            written = "".join(c.args[0] for c in handle.write.call_args_list)
            assert "completed" in written

    @pytest.mark.asyncio
    async def test_add_trace_with_error(self):
        from app.studio.router import add_trace
        with patch("app.studio.router.get_state_path", return_value=FAKE_STATE_PATH), \
             patch("os.path.exists", return_value=False), \
             patch("builtins.open", mock_open()) as m:
            await add_trace(SESSION_ID, "err_step", "failed", error="出错了")
            handle = m()
            written = "".join(c for c in handle.write.call_args[0])
            assert "err_step" in written
            assert "failed" in written

    @pytest.mark.asyncio
    async def test_add_trace_invalid_json_ignored(self):
        from app.studio.router import add_trace
        with patch("app.studio.router.get_state_path", return_value=FAKE_STATE_PATH), \
             patch("os.path.exists", return_value=True), \
             patch("builtins.open", mock_open(read_data="not valid json")) as m:
            await add_trace(SESSION_ID, "step_a", "running", "测试")
            handle = m()
            written = "".join(c.args[0] for c in handle.write.call_args_list)
            assert "step_a" in written


# ── GET /trace/{session_id} ────────────────────────────────

class TestGetTrace:
    @pytest.mark.asyncio
    async def test_trace_no_file_returns_empty(self):
        from app.studio.router import get_workflow_trace
        with patch("app.studio.router.get_state_path", return_value=FAKE_STATE_PATH), \
             patch("os.path.exists", return_value=False):
            result = await get_workflow_trace(SESSION_ID)
            assert result == {"traces": []}

    @pytest.mark.asyncio
    async def test_trace_with_data(self):
        from app.studio.router import get_workflow_trace
        state = {"trace": [{"step": "s1", "status": "completed"}, {"step": "s2", "status": "running"}]}
        with patch("app.studio.router.get_state_path", return_value=FAKE_STATE_PATH), \
             patch("os.path.exists", return_value=True), \
             patch("builtins.open", mock_open(read_data=json.dumps(state))):
            result = await get_workflow_trace(SESSION_ID)
            assert len(result["traces"]) == 2
            assert result["total"] == 2
            assert result["done"] == 1

    @pytest.mark.asyncio
    async def test_trace_no_trace_key(self):
        from app.studio.router import get_workflow_trace
        with patch("app.studio.router.get_state_path", return_value=FAKE_STATE_PATH), \
             patch("os.path.exists", return_value=True), \
             patch("builtins.open", mock_open(read_data=json.dumps({"products": []}))):
            result = await get_workflow_trace(SESSION_ID)
            assert result == {"traces": [], "total": 0, "done": 0}


# ── GET /state/{session_id} ────────────────────────────────

class TestGetState:
    @pytest.mark.asyncio
    async def test_get_state_returns_default_when_no_file(self, dummy_user):
        from app.studio.router import get_workflow_state
        with patch("app.studio.router.get_state_path", return_value=FAKE_STATE_PATH), \
             patch("os.path.exists", return_value=False), \
             patch("app.studio.router.DEFAULT_STATE", {"products": [], "collections": []}):
            result = await get_workflow_state(SESSION_ID, dummy_user)
            assert result == {"products": [], "collections": []}

    @pytest.mark.asyncio
    async def test_get_state_returns_file_content(self, dummy_user):
        from app.studio.router import get_workflow_state
        with patch("app.studio.router.get_state_path", return_value=FAKE_STATE_PATH), \
             patch("os.path.exists", return_value=True), \
             patch("builtins.open", mock_open(read_data=json.dumps({"products": [{"id": 1}]}))):
            result = await get_workflow_state(SESSION_ID, dummy_user)
            assert result["products"] == [{"id": 1}]


# ── PUT /state/{session_id} ────────────────────────────────

class TestSaveState:
    @pytest.mark.asyncio
    async def test_save_state_writes_file(self, dummy_user):
        from app.studio.router import save_workflow_state
        body = {"products": [{"id": 1}], "selected_product_id": None}
        with patch("app.studio.router.get_state_path", return_value=FAKE_STATE_PATH), \
             patch("builtins.open", mock_open()) as m:
            result = await save_workflow_state(SESSION_ID, body, dummy_user())
            assert result == {"ok": True}
            handle = m()
            written = "".join(c for c in handle.write.call_args[0])
            assert json.loads(written) == body


# ── GET /sign-url ──────────────────────────────────────────

class TestSignUrl:
    @pytest.mark.asyncio
    async def test_sign_url_empty_path(self):
        from app.studio.router import get_signed_url
        result = await get_signed_url(path="")
        assert result["error"] == "path required"

    @pytest.mark.asyncio
    async def test_sign_url_normal_path(self):
        from app.studio.router import get_signed_url
        with patch("app.core.signer.generate_signed_url") as m:
            m.return_value = "/signed/abc/xxx.mp4"
            result = await get_signed_url(path="/uploads/clips/1.mp4")
            assert "url" in result
            assert "114.117.242.17:3000" in result["url"]

    @pytest.mark.asyncio
    async def test_sign_url_http_path_extracts_uploads(self):
        from app.studio.router import get_signed_url
        with patch("app.core.signer.generate_signed_url") as m:
            m.return_value = "/signed/abc/xxx.mp4"
            result = await get_signed_url(path="http://cdn.com/uploads/v/1.mp4")
            assert "url" in result


# ── GET /video-proxy ───────────────────────────────────────

class TestVideoProxy:
    @pytest.mark.asyncio
    async def test_video_proxy_404_no_file(self):
        from app.studio.router import video_proxy
        with patch("os.path.exists", return_value=False):
            with pytest.raises(HTTPException) as exc:
                await video_proxy(path="/uploads/nonexistent.mp4")
            assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_video_proxy_finds_local_uploads(self):
        from app.studio.router import video_proxy
        fake_path = "/app/uploads/exists.mp4"
        with patch("os.path.exists", return_value=True), \
             patch("os.path.isdir", return_value=False), \
             patch("fastapi.responses.FileResponse") as fr_mock:
            fr_mock.return_value = {"mock": "response"}
            result = await video_proxy(path="/uploads/exists.mp4")
            # verify FileResponse was created with correct path
            assert fr_mock.called

    @pytest.mark.asyncio
    async def test_video_proxy_signed_path_resolved(self):
        from app.studio.router import video_proxy
        with patch("os.path.exists", side_effect=lambda p: "/app/uploads/v.mp4" in p), \
             patch("fastapi.responses.FileResponse") as fr_mock:
            fr_mock.return_value = {"mock": "response"}
            await video_proxy(path="/signed/token/v.mp4")
            assert fr_mock.called

    @pytest.mark.asyncio
    async def test_video_proxy_http_path_skipped(self):
        from app.studio.router import video_proxy
        with patch("os.path.exists", return_value=False):
            with pytest.raises(HTTPException) as exc:
                await video_proxy(path="http://cdn.com/video.mp4")
            assert exc.value.status_code == 404


# ── helper: _inject_materials ──────────────────────────────

class TestInjectMaterials:
    def test_injects_to_empty_scenes(self):
        from app.studio.router import _inject_materials
        script_data = {"script": {"scenes": [
            {"scene_id": 1, "lines": []},
            {"scene_id": 2, "lines": [], "materials": [99]},
        ]}}
        materials = [{"material_id": 1}, {"id": 2}]
        result = _inject_materials(script_data, materials)
        scenes = result["script"]["scenes"]
        assert scenes[0]["materials"] == [1, 2]
        assert scenes[1]["materials"] == [99]  # already has materials, unchanged

    def test_injects_script_is_script(self):
        from app.studio.router import _inject_materials
        data = {"scenes": [{"scene_id": 1}]}
        result = _inject_materials(data, [{"id": 10}])
        assert result["scenes"][0]["materials"] == [10]

    def test_empty_materials_noop(self):
        from app.studio.router import _inject_materials
        script = {"script": {"scenes": [{"scene_id": 1, "materials": [5]}]}}
        result = _inject_materials(script, [])
        assert result["script"]["scenes"][0]["materials"] == [5]

    def test_script_as_flat_dict(self):
        """Script data where script body is the dict itself (no 'script' key wrapper)"""
        from app.studio.router import _inject_materials
        data = {"scenes": [{"scene_id": 1}]}
        result = _inject_materials(data, [{"id": 10}])
        assert result["scenes"][0]["materials"] == [10]


# ── helper: _save_script ───────────────────────────────────

class TestSaveScript:
    @pytest.mark.asyncio
    async def test_save_script_writes_file(self):
        from app.studio.router import _save_script
        script = {"scenes": [{"scene_id": 1}]}
        fake_scripts_dir = f"{FAKE_ROOT}/scripts"
        fake_path = f"{fake_scripts_dir}/script_{SESSION_ID}.json"
        with patch("app.agent.models.ensure_session_dir",
                   return_value={"root": FAKE_ROOT, "scripts": fake_scripts_dir}), \
             patch("builtins.open", mock_open()) as m:
            _save_script(SESSION_ID, script)
            handle = m()
            written = "".join(c for c in handle.write.call_args[0])
            assert "scenes" in written


# ── GET /clips/{session_id} ────────────────────────────────

class TestGetClips:
    @pytest.mark.asyncio
    async def test_empty_clips(self, db_session, dummy_user):
        from app.studio.router import get_session_clips
        with patch("app.agent.models.get_session_files", new_callable=AsyncMock) as gsf:
            gsf.return_value = []
            result = await get_session_clips(SESSION_ID, db_session, dummy_user)
            assert result["clips"] == []
            assert result["final_videos"] == []
            assert result["subbed_videos"] == []
            assert result["asr_segments"] == []
            assert result["asr_duration"] == 0

    @pytest.mark.asyncio
    async def test_parses_clip_description(self, db_session, dummy_user):
        from app.studio.router import get_session_clips
        from app.agent.models import SessionFile
        mock_clip = SessionFile(
            id=10, session_id=SESSION_ID, file_type="video_clip",
            file_url="/signed/t/c.mp4",
            description="场景 1 视频片段, dur=5",
        )
        mock_final = SessionFile(
            id=20, session_id=SESSION_ID, file_type="final_video",
            file_url="/signed/t/final.mp4",
            description="合成视频",
        )
        with patch("app.agent.models.get_session_files", new_callable=AsyncMock) as gsf:
            gsf.return_value = [mock_clip, mock_final]
            result = await get_session_clips(SESSION_ID, db_session, dummy_user)
            assert len(result["clips"]) == 1
            assert result["clips"][0]["scene_id"] == "1"
            assert result["clips"][0]["duration"] == 5
            assert len(result["final_videos"]) == 1

    @pytest.mark.asyncio
    async def test_parses_asr_subtitles(self, db_session, dummy_user):
        from app.studio.router import get_session_clips
        subs_json = json.dumps([{"start": 0, "end": 2, "text": "hello"}])
        mock_asr = SessionFile(
            id=30, session_id=SESSION_ID, file_type="asr_subtitles",
            description=subs_json,
        )
        mock_dur = SessionFile(
            id=31, session_id=SESSION_ID, file_type="asr_duration",
            description="5.2",
        )
        with patch("app.agent.models.get_session_files", new_callable=AsyncMock) as gsf:
            gsf.return_value = [mock_asr, mock_dur]
            result = await get_session_clips(SESSION_ID, db_session, dummy_user)
            assert len(result["asr_segments"]) == 1
            assert result["asr_duration"] == 5.2


# ── POST /delete-clip ──────────────────────────────────────

class TestDeleteClip:
    @pytest.mark.asyncio
    async def test_delete_by_id_no_file(self, db_session, dummy_user):
        from app.studio.router import studio_delete_clip
        # clip_id 不存在的场景
        from sqlalchemy import select
        result = await studio_delete_clip({"clip_id": 99999, "file_url": ""}, db_session, dummy_user)
        assert result == {"ok": True}

    @pytest.mark.asyncio
    async def test_delete_by_id_with_file(self, db_session, dummy_user):
        from app.studio.router import studio_delete_clip
        clip = SessionFile(
            session_id=SESSION_ID, file_type="video_clip",
            file_url="/uploads/clips/1.mp4",
            description="test",
        )
        db_session.add(clip)
        await db_session.flush()
        clip_id = clip.id
        with patch("os.path.exists", return_value=True), \
             patch("os.remove") as rm_mock:
            result = await studio_delete_clip({"clip_id": clip_id, "file_url": ""}, db_session, dummy_user)
            assert result == {"ok": True}
            rm_mock.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_by_url_only(self, db_session, dummy_user):
        from app.studio.router import studio_delete_clip
        clip = SessionFile(
            session_id=SESSION_ID, file_type="video_clip",
            file_url="http://114.117.242.17:3000/uploads/clips/2.mp4",
            description="test",
        )
        db_session.add(clip)
        await db_session.flush()
        with patch("os.path.exists", return_value=True), \
             patch("os.remove") as rm_mock:
            result = await studio_delete_clip(
                {"clip_id": None, "file_url": "http://114.117.242.17:3000/uploads/clips/2.mp4"},
                db_session, dummy_user,
            )
            assert result == {"ok": True}
            rm_mock.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_by_url_non_http(self, db_session, dummy_user):
        """When file_url doesn't start with http, try multiple URL formats"""
        from app.studio.router import studio_delete_clip
        clip = SessionFile(
            session_id=SESSION_ID, file_type="video_clip",
            file_url="/uploads/clips/3.mp4",
            description="test",
        )
        db_session.add(clip)
        await db_session.flush()
        with patch("os.path.exists", return_value=True), \
             patch("os.remove") as rm_mock:
            result = await studio_delete_clip(
                {"clip_id": None, "file_url": "/uploads/clips/3.mp4"},
                db_session, dummy_user,
            )
            assert result == {"ok": True}
            # should delete from both DB matches
            assert rm_mock.called


# ── POST /materials/search ─────────────────────────────────

class TestMaterialsSearch:
    @pytest.mark.asyncio
    async def test_search_no_tags(self, db_session, dummy_user):
        from app.studio.router import search_studio_materials
        # 先插入一些素材
        m1 = Material(user_id="1", name="mat1", image_url="/u/1.jpg", tags='["tag1"]', material_type="product")
        m2 = Material(user_id="1", name="mat2", image_url="/u/2.jpg", tags='["tag2"]', material_type="general")
        db_session.add_all([m1, m2])
        await db_session.flush()
        result = await search_studio_materials({"threshold": 30, "tags": []}, db_session, dummy_user)
        assert result["total"] == 2

    @pytest.mark.asyncio
    async def test_search_with_tag_filter(self, db_session, dummy_user):
        from app.studio.router import search_studio_materials
        m1 = Material(user_id="1", name="mat1", image_url="/u/1.jpg", tags='["tag1"]', material_type="product")
        m2 = Material(user_id="1", name="mat2", image_url="/u/2.jpg", tags='["tag2"]', material_type="general")
        db_session.add_all([m1, m2])
        await db_session.flush()
        result = await search_studio_materials({"threshold": 30, "tags": ["tag1"]}, db_session, dummy_user)
        assert result["total"] == 1
        assert result["materials"][0]["image_url"] == "/u/1.jpg"

    @pytest.mark.asyncio
    async def test_search_other_user_not_visible(self, db_session, dummy_user):
        from app.studio.router import search_studio_materials
        m = Material(user_id="99", name="not_mine", image_url="/u/n.jpg", tags="[]", material_type="product")
        db_session.add(m)
        await db_session.flush()
        result = await search_studio_materials({"threshold": 30, "tags": []}, db_session, dummy_user)
        assert result["total"] == 0


# ── route metadata ─────────────────────────────────────────

class TestRouteMeta:
    def test_router_prefix(self):
        from app.studio.router import router
        assert router.prefix == "/api/v1/studio"

    def test_router_tags(self):
        from app.studio.router import router
        assert "studio" in router.tags

    def test_router_routes_defined(self):
        from app.studio.router import router
        paths = [r.path for r in router.routes]
        assert "/api/v1/studio/trace/{session_id}" in paths
        assert "/api/v1/studio/state/{session_id}" in paths
        assert "/api/v1/studio/sign-url" in paths
        assert "/api/v1/studio/video-proxy" in paths
        assert "/api/v1/studio/clips/{session_id}" in paths
        assert "/api/v1/studio/delete-clip" in paths
