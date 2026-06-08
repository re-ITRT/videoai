"""published/router.py 全覆盖测试 — 直接调用 handler 模式"""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi import HTTPException
from datetime import datetime, timezone

# 确保 PublishedVideo model 在 Base.metadata 中注册（用于 SQLite 表创建）
from app.published.models import PublishedVideo  # noqa: F401
from app.published.router import (
    publish_video,
    list_published,
    increment_view,
    update_published_play_count,
    delete_published,
)
from app.auth.models import User
from sqlalchemy import delete as sa_delete


@pytest.fixture
def dummy_user():
    return User(id=1, username="publish_test", hashed_password="hash", is_active=True, role="user")


@pytest.fixture
def dummy_user2():
    return User(id=2, username="other_user", hashed_password="hash", is_active=True, role="user")


# Patch call_workflow at its module definition site (used via local import inside handlers)
CW_PATH = "app.workers.workflow.call_workflow"


# ======================================================
# publish_video / POST /export
# ======================================================

class TestPublishVideo:

    @pytest.mark.asyncio
    async def test_missing_video_url_400(self, db_session, dummy_user):
        """video_url 缺失 → 400"""
        with pytest.raises(HTTPException) as exc:
            await publish_video(body={}, db=db_session, user=dummy_user)
        assert exc.value.status_code == 400
        assert "video_url" in str(exc.value.detail)

    @pytest.mark.asyncio
    async def test_success_basic(self, db_session, dummy_user):
        """最小参数成功导出"""
        with patch(CW_PATH, new_callable=AsyncMock) as cw:
            cw.return_value = {"data": {"scenes": [], "video_tags": []}}

            result = await publish_video(
                body={"video_url": "http://example.com/video.mp4", "title": "测试视频"},
                db=db_session, user=dummy_user,
            )

        assert result["success"] is True
        assert result["video_url"] == "http://example.com/video.mp4"
        assert result["id"] > 0

        # Verify DB record
        pv = await db_session.get(PublishedVideo, result["id"])
        assert pv is not None
        assert pv.title == "测试视频"
        assert pv.play_count == 2000

    @pytest.mark.asyncio
    async def test_success_with_full_body(self, db_session, dummy_user):
        """全字段 body 成功导出"""
        body = {
            "video_url": "http://example.com/video.mp4",
            "title": "完整测试",
            "session_id": 42,
            "cover_url": "http://example.com/cover.jpg",
            "script_template": "premium",
            "audio_features": {"bpm": 120, "mood": "轻快"},
            "bgm_url": "http://example.com/bgm.mp3",
            "bgm_name": "bgm_song",
        }

        with patch(CW_PATH, new_callable=AsyncMock) as cw:
            cw.return_value = {
                "tags": ["tag1", "tag2"],
                "hook_method": "hook_A",
                "selling_points": ["点1", "点2"],
                "style": "快节奏",
            }

            result = await publish_video(body=body, db=db_session, user=dummy_user)

        assert result["success"] is True
        pv = await db_session.get(PublishedVideo, result["id"])
        assert pv.title == "完整测试"
        assert pv.cover_url == "http://example.com/cover.jpg"
        assert pv.script_template == "premium"
        assert pv.source_session_id == 42
        # audio_features from body should be used directly
        assert pv.audio_features == {"bpm": 120, "mood": "轻快"}
        # style/hook_method/selling_points from analyze result
        assert pv.style == "快节奏"
        assert pv.hook_method == "hook_A"
        assert pv.selling_points == ["点1", "点2"]
        # BGM stored in analysis_report
        assert pv.analysis_report.get("bgm") == {"url": "http://example.com/bgm.mp3", "name": "bgm_song"}

    @pytest.mark.asyncio
    async def test_material_embed_returns_scenes_and_tags(self, db_session, dummy_user):
        """material-embed 返回 scenes 和 tags → 正确传递"""
        with patch(CW_PATH, new_callable=AsyncMock) as cw:
            async def mock_call(name, payload):
                if name == "material-embed":
                    return {
                        "data": {
                            "scenes": [
                                {"scene_id": 1, "time_range": "<00:00-00:03>", "description": "开场", "script": "你好"},
                                {"scene_id": 2, "time_range": "<00:03-00:08>", "description": "展示", "script": "看这里"},
                            ],
                            "video_tags": ["科技", "创新"],
                        }
                    }
                elif name == "video-analyze":
                    return {"tags": ["额外标签"]}
                return {}
            cw.side_effect = mock_call

            result = await publish_video(
                body={"video_url": "http://example.com/v.mp4"},
                db=db_session, user=dummy_user,
            )

        pv = await db_session.get(PublishedVideo, result["id"])
        assert len(pv.scenes) == 2
        assert pv.scenes[0]["scene_id"] == 1
        # tags merged from both embed and analyze
        assert "科技" in pv.tags
        assert "创新" in pv.tags
        assert "额外标签" in pv.tags

    @pytest.mark.asyncio
    async def test_material_embed_fails_fallback(self, db_session, dummy_user):
        """material-embed 抛出异常 → 使用默认 scenes"""
        with patch(CW_PATH, new_callable=AsyncMock) as cw:
            cw.side_effect = RuntimeError("network error")

            result = await publish_video(
                body={"video_url": "http://example.com/v.mp4", "title": "失败测试"},
                db=db_session, user=dummy_user,
            )

        pv = await db_session.get(PublishedVideo, result["id"])
        # Falls back to default single scene
        assert len(pv.scenes) == 1
        assert pv.scenes[0]["scene_id"] == 1
        assert pv.scenes[0]["description"] == "失败测试"

    @pytest.mark.asyncio
    async def test_video_analyze_fails(self, db_session, dummy_user):
        """video-analyze 抛出异常 → 不传递 analyze fields"""
        with patch(CW_PATH, new_callable=AsyncMock) as cw:
            async def side_effect(name, payload):
                if name == "material-embed":
                    return {"data": {"scenes": [], "video_tags": []}}
                elif name == "video-analyze":
                    raise RuntimeError("analyze failed")
                return {}
            cw.side_effect = side_effect

            result = await publish_video(
                body={"video_url": "http://example.com/v.mp4"},
                db=db_session, user=dummy_user,
            )

        pv = await db_session.get(PublishedVideo, result["id"])
        assert pv.hook_method == ""
        assert pv.style == ""
        assert pv.selling_points == []

    @pytest.mark.asyncio
    async def test_rhythm_calculation(self, db_session, dummy_user):
        """场景时间差 → rhythm 正确计算（nums[-1] - nums[0] 逻辑）"""
        with patch(CW_PATH, new_callable=AsyncMock) as cw:
            cw.return_value = {
                "data": {
                    "scenes": [
                        {"scene_id": 1, "time_range": "<00:00-00:05>"},
                        {"scene_id": 2, "time_range": "<00:05-00:15>"},
                        {"scene_id": 3, "time_range": "<00:15-00:20>"},
                    ],
                    "tags": [],
                }
            }

            result = await publish_video(
                body={"video_url": "http://example.com/v.mp4"},
                db=db_session, user=dummy_user,
            )

        pv = await db_session.get(PublishedVideo, result["id"])
        # Code uses: nums = re.findall(r"[\d.]+", time_range)
        # nums[-1] - nums[0] → for "<00:00-00:05>": 05-00=5, "<00:05-00:15>": 15-00=15, "<00:15-00:20>": 20-00=20
        # avg = (5+15+20)/3 = 13.33
        assert pv.rhythm == 13.33

    @pytest.mark.asyncio
    async def test_rhythm_empty_scenes(self, db_session, dummy_user):
        """没有场景 → 使用默认 scene → rhythm 为 5.0"""
        with patch(CW_PATH, new_callable=AsyncMock) as cw:
            cw.return_value = {"data": {"scenes": [], "tags": []}}

            result = await publish_video(
                body={"video_url": "http://example.com/v.mp4"},
                db=db_session, user=dummy_user,
            )

        pv = await db_session.get(PublishedVideo, result["id"])
        # Default scene: time_range="<00:00-00:05>" → nums = ['00','00','00','05'], d = 5-0 = 5.0
        assert pv.rhythm == 5.0

    @pytest.mark.asyncio
    async def test_audio_extraction_from_local(self, db_session, dummy_user):
        """无 body audio_features，视频路径匹配 signed → 本地音频提取"""
        import numpy as np

        # Create a mock for mfcc that supports [i].mean() chain
        mfcc_row_mock = MagicMock()
        mfcc_row_mock.mean.return_value = np.float64(0.1)
        mfcc_mock = MagicMock()
        mfcc_mock.__getitem__.return_value = mfcc_row_mock

        with (
            patch(CW_PATH, new_callable=AsyncMock) as cw,
            patch("os.path.exists", return_value=True),
            patch("subprocess.run"),
            patch("tempfile.mkdtemp", return_value="/tmp/test_audio"),
            patch("shutil.rmtree"),
            patch("librosa.load", return_value=(np.zeros(16000), 16000)),
            patch("librosa.get_duration", return_value=30.0),
            patch("librosa.beat.beat_track", return_value=(120.0, np.array([1, 2, 3]))),
            patch("librosa.feature.spectral_centroid") as sc,
            patch("librosa.feature.zero_crossing_rate") as zcr,
            patch("librosa.feature.spectral_rolloff") as sr,
            patch("librosa.feature.mfcc", return_value=mfcc_mock) as _mfcc,
        ):
            cw.return_value = {"data": {"scenes": [], "tags": []}}
            sc.return_value = MagicMock()
            sc.return_value.mean.return_value = np.float64(2000.0)
            zcr.return_value = MagicMock()
            zcr.return_value.mean.return_value = np.float64(0.05)
            sr.return_value = MagicMock()
            sr.return_value.mean.return_value = np.float64(4000.0)

            result = await publish_video(
                body={"video_url": "http://example.com/signed/token/videos/test.mp4"},
                db=db_session, user=dummy_user,
            )

        pv = await db_session.get(PublishedVideo, result["id"])
        assert pv.audio_features["bpm"] == 120.0
        assert pv.audio_features["mood"] == "轻快"
        assert pv.audio_features["lightness_score"] > 0

    @pytest.mark.asyncio
    async def test_audio_extraction_no_local_file(self, db_session, dummy_user):
        """本地文件不存在 → audio_features 为空"""
        with (
            patch(CW_PATH, new_callable=AsyncMock) as cw,
            patch("os.path.exists", return_value=False),
        ):
            cw.return_value = {"data": {"scenes": [], "tags": []}}

            result = await publish_video(
                body={"video_url": "http://example.com/video.mp4"},
                db=db_session, user=dummy_user,
            )

        pv = await db_session.get(PublishedVideo, result["id"])
        assert pv.audio_features == {}

    @pytest.mark.asyncio
    async def test_thumbnail_signed_path(self, db_session, dummy_user):
        """signed URL → 缩略图生成（本地文件存在）"""
        with (
            patch(CW_PATH, new_callable=AsyncMock) as cw,
            patch("os.path.exists") as mock_exists,
            patch("subprocess.run"),
            patch("uuid.uuid4", return_value=MagicMock(hex="abcdef123456")),
        ):
            cw.return_value = {"data": {"scenes": [], "tags": []}}

            def exists_side_effect(p):
                if "uploads" in str(p) or "thumb" in str(p):
                    return True
                return False
            mock_exists.side_effect = exists_side_effect

            result = await publish_video(
                body={"video_url": "http://example.com/signed/token/videos/test.mp4"},
                db=db_session, user=dummy_user,
            )

        pv = await db_session.get(PublishedVideo, result["id"])
        assert "thumb_" in pv.cover_url
        assert "uploads/analyze" in pv.cover_url

    @pytest.mark.asyncio
    async def test_thumbnail_uploads_path(self, db_session, dummy_user):
        """/uploads/ 路径 → 缩略图生成"""
        with (
            patch(CW_PATH, new_callable=AsyncMock) as cw,
            patch("os.path.exists", return_value=True),
            patch("subprocess.run"),
            patch("uuid.uuid4", return_value=MagicMock(hex="fedcba654321")),
        ):
            cw.return_value = {"data": {"scenes": [], "tags": []}}

            result = await publish_video(
                body={"video_url": "http://example.com/uploads/videos/test.mp4"},
                db=db_session, user=dummy_user,
            )

        pv = await db_session.get(PublishedVideo, result["id"])
        assert "thumb_" in pv.cover_url

    @pytest.mark.asyncio
    async def test_thumbnail_failure(self, db_session, dummy_user):
        """缩略图生成失败 → 不阻断正常流程"""
        with (
            patch(CW_PATH, new_callable=AsyncMock) as cw,
            patch("os.path.exists", return_value=True),
            patch("subprocess.run", side_effect=RuntimeError("ffmpeg error")),
        ):
            cw.return_value = {"data": {"scenes": [], "tags": []}}

            result = await publish_video(
                body={"video_url": "http://example.com/signed/token/videos/test.mp4"},
                db=db_session, user=dummy_user,
            )

        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_audio_extraction_failure(self, db_session, dummy_user):
        """本地音频提取抛出异常 → audio_features 保持空"""
        with (
            patch(CW_PATH, new_callable=AsyncMock) as cw,
            patch("os.path.exists", return_value=True),
            patch("subprocess.run", side_effect=RuntimeError("ffmpeg crashed")),
        ):
            cw.return_value = {"data": {"scenes": [], "tags": []}}

            result = await publish_video(
                body={"video_url": "http://example.com/signed/token/videos/test.mp4"},
                db=db_session, user=dummy_user,
            )

        pv = await db_session.get(PublishedVideo, result["id"])
        assert pv.audio_features == {}

    @pytest.mark.asyncio
    async def test_no_analyze_tags_no_embed_tags(self, db_session, dummy_user):
        """analyze_result 非 dict → tags 仅来自 embed"""
        with patch(CW_PATH, new_callable=AsyncMock) as cw:
            async def mock_call(name, payload):
                if name == "material-embed":
                    return {"data": {"scenes": [], "video_tags": ["tag_a"]}}
                elif name == "video-analyze":
                    return "not_a_dict"
                return {}
            cw.side_effect = mock_call

            result = await publish_video(
                body={"video_url": "http://example.com/v.mp4"},
                db=db_session, user=dummy_user,
            )

        pv = await db_session.get(PublishedVideo, result["id"])
        assert pv.tags == ["tag_a"]

    @pytest.mark.asyncio
    async def test_analyze_result_not_dict(self, db_session, dummy_user):
        """analyze_result 非 dict → analysis_report 保存为 {}"""
        with patch(CW_PATH, new_callable=AsyncMock) as cw:
            cw.return_value = "string_result"
            result = await publish_video(
                body={"video_url": "http://example.com/v.mp4"},
                db=db_session, user=dummy_user,
            )
        pv = await db_session.get(PublishedVideo, result["id"])
        assert pv.analysis_report == {}
        assert pv.hook_method == ""
        assert pv.selling_points == []

    @pytest.mark.asyncio
    async def test_bgm_no_url_saved(self, db_session, dummy_user):
        """bgm_url 为空 → 不保存 bgm 信息"""
        with patch(CW_PATH, new_callable=AsyncMock) as cw:
            cw.return_value = {"data": {"scenes": [], "tags": []}}
            result = await publish_video(
                body={"video_url": "http://example.com/v.mp4", "bgm_url": "", "bgm_name": ""},
                db=db_session, user=dummy_user,
            )
        pv = await db_session.get(PublishedVideo, result["id"])
        assert pv.analysis_report.get("bgm") is None

    @pytest.mark.asyncio
    async def test_video_url_empty_string(self, db_session, dummy_user):
        """video_url 为空字符串 → 400"""
        with pytest.raises(HTTPException) as exc:
            await publish_video(
                body={"video_url": "", "title": "test"},
                db=db_session, user=dummy_user,
            )
        assert exc.value.status_code == 400


# ======================================================
# list_published / GET /videos
# ======================================================

class TestListPublished:

    @pytest.fixture(autouse=True)
    async def cleanup_published(self, db_session):
        """Ensure clean PublishedVideo table before each list test"""
        # Delete all PublishedVideo records to avoid cross-test contamination
        from app.published.models import PublishedVideo as PV
        stmt = sa_delete(PV)
        await db_session.execute(stmt)
        await db_session.commit()

    @pytest.mark.asyncio
    async def test_empty_list(self, db_session, dummy_user):
        """无数据 → empty list"""
        result = await list_published(
            skip=0, limit=20, sort="created_at", order="desc",
            db=db_session, user=dummy_user,
        )
        assert result["total"] == 0
        assert result["items"] == []

    @pytest.mark.asyncio
    async def test_with_items(self, db_session, dummy_user):
        """有数据 → 返回 items"""
        pv = PublishedVideo(
            user_id=1, title="视频1", video_url="http://ex.com/1.mp4",
            play_count=2000, tags=["a", "b"], scenes=[],
            analysis_report={}, audio_features={},
            script_template="default",
            created_at=datetime(2026, 6, 1, tzinfo=timezone.utc),
        )
        db_session.add(pv)
        await db_session.flush()

        result = await list_published(
            skip=0, limit=20, sort="created_at", order="desc",
            db=db_session, user=dummy_user,
        )
        assert result["total"] == 1
        assert len(result["items"]) == 1
        assert result["items"][0]["title"] == "视频1"
        assert result["items"][0]["play_count"] == 2000

    @pytest.mark.asyncio
    async def test_sort_play_count_asc(self, db_session, dummy_user):
        """按 play_count 升序排序"""
        for i, pc in enumerate([5000, 3000, 8000]):
            pv = PublishedVideo(
                user_id=1, title=f"视频{i}", video_url=f"http://ex.com/{i}.mp4",
                play_count=pc, tags=[], scenes=[], analysis_report={},
                audio_features={}, script_template="default",
                created_at=datetime(2026, 6, 1, tzinfo=timezone.utc),
            )
            db_session.add(pv)
        await db_session.flush()

        result = await list_published(
            skip=0, limit=20, sort="play_count", order="asc",
            db=db_session, user=dummy_user,
        )
        counts = [item["play_count"] for item in result["items"]]
        assert counts == sorted(counts)

    @pytest.mark.asyncio
    async def test_skip_limit(self, db_session, dummy_user):
        """分页参数 skip/limit 生效"""
        for i in range(5):
            pv = PublishedVideo(
                user_id=1, title=f"视频{i}", video_url=f"http://ex.com/{i}.mp4",
                play_count=2000 + i, tags=[], scenes=[], analysis_report={},
                audio_features={}, script_template="default",
            )
            db_session.add(pv)
        await db_session.flush()

        result = await list_published(
            skip=2, limit=2, sort="created_at", order="desc",
            db=db_session, user=dummy_user,
        )
        assert len(result["items"]) == 2
        assert result["total"] == 5

    @pytest.mark.asyncio
    async def test_predicted_play_count(self, db_session, dummy_user):
        """参考视频 >=3 个 → 预测播放量"""
        from app.script.models import ReferenceVideo

        for i in range(3):
            ref = ReferenceVideo(
                user_id="1", source_url=f"http://ref.com/{i}",
                rhythm=float(i * 2), play_count=5000 + i * 1000,
                analysis_report={"hook_quality": 8 - i, "pacing_score": 7, "overall_score": 6},
                audio_features={"bpm": 120 + i * 10},
            )
            db_session.add(ref)
        await db_session.flush()

        pv = PublishedVideo(
            user_id=1, title="预测测试", video_url="http://ex.com/p.mp4",
            play_count=2000, tags=[], scenes=[], analysis_report={},
            audio_features={}, rhythm=3.0, script_template="default",
        )
        db_session.add(pv)
        await db_session.flush()

        result = await list_published(
            skip=0, limit=20, sort="created_at", order="desc",
            db=db_session, user=dummy_user,
        )
        assert result["items"][0]["predicted_play_count"] >= 2000

    @pytest.mark.asyncio
    async def test_prediction_few_references(self, db_session, dummy_user):
        """参考视频 < 3 个 → 不使用预测"""
        from app.script.models import ReferenceVideo

        ref = ReferenceVideo(user_id="1", source_url="http://ref.com/0",
                              play_count=5000)
        db_session.add(ref)
        pv = PublishedVideo(
            user_id=1, title="无预测", video_url="http://ex.com/p.mp4",
            play_count=2000, tags=[], scenes=[], analysis_report={},
            audio_features={}, rhythm=3.0, script_template="default",
        )
        db_session.add(pv)
        await db_session.flush()

        result = await list_published(
            skip=0, limit=20, sort="created_at", order="desc",
            db=db_session, user=dummy_user,
        )
        # prediction skipped, predicted = play_count
        assert result["items"][0]["predicted_play_count"] == 2000

    @pytest.mark.asyncio
    async def test_prediction_exception_handled(self, db_session, dummy_user):
        """预测代码抛出异常 → 不阻断列表返回"""
        from app.script.models import ReferenceVideo

        for i in range(3):
            ref = ReferenceVideo(user_id="1", source_url=f"http://ref.com/{i}",
                                  play_count=5000, analysis_report={}, audio_features={})
            db_session.add(ref)
        await db_session.flush()

        pv = PublishedVideo(
            user_id=1, title="异常预测", video_url="http://ex.com/p.mp4",
            play_count=2000, tags=[], scenes=[], analysis_report={},
            audio_features={}, script_template="default",
        )
        db_session.add(pv)
        await db_session.flush()

        result = await list_published(
            skip=0, limit=20, sort="created_at", order="desc",
            db=db_session, user=dummy_user,
        )
        assert result["total"] == 1
        assert result["items"][0]["predicted_play_count"] >= 2000

    @pytest.mark.asyncio
    async def test_items_serialization(self, db_session, dummy_user):
        """items 序列化字段完整性"""
        pv = PublishedVideo(
            user_id=1, title="序列化测试", video_url="http://ex.com/v.mp4",
            cover_url="http://ex.com/cover.jpg", play_count=3000,
            hook_method="痛点开场", style="快节奏",
            tags=["tag1"], rhythm=4.5, scenes=[{"id": 1}],
            analysis_report={"score": 85}, audio_features={"bpm": 110},
            script_template="custom",
            created_at=datetime(2026, 6, 1, 12, 0, 0, tzinfo=timezone.utc),
        )
        db_session.add(pv)
        await db_session.flush()

        result = await list_published(
            skip=0, limit=20, sort="created_at", order="desc",
            db=db_session, user=dummy_user,
        )
        item = result["items"][0]
        assert item["id"] == pv.id
        assert item["title"] == "序列化测试"
        assert item["video_url"] == "http://ex.com/v.mp4"
        assert item["cover_url"] == "http://ex.com/cover.jpg"
        assert item["play_count"] == 3000
        assert item["hook_method"] == "痛点开场"
        assert item["style"] == "快节奏"
        assert item["tags"] == ["tag1"]
        assert item["rhythm"] == 4.5
        assert item["scenes"] == [{"id": 1}]
        assert item["analysis_report"] == {"score": 85}
        assert item["audio_features"] == {"bpm": 110}
        assert item["script_template"] == "custom"
        assert item["created_at"] == "2026-06-01T12:00:00+00:00"

    @pytest.mark.asyncio
    async def test_other_user_videos_excluded(self, db_session, dummy_user, dummy_user2):
        """其他用户的视频不显示"""
        pv_other = PublishedVideo(
            user_id=2, title="别人的视频", video_url="http://ex.com/o.mp4",
            play_count=2000, tags=[], scenes=[], analysis_report={},
            audio_features={}, script_template="default",
        )
        db_session.add(pv_other)
        await db_session.flush()

        result = await list_published(
            skip=0, limit=20, sort="created_at", order="desc",
            db=db_session, user=dummy_user,
        )
        assert result["total"] == 0


# ======================================================
# increment_view / POST /{video_id}/view
# ======================================================

class TestIncrementView:

    @pytest.fixture(autouse=True)
    async def cleanup_published(self, db_session):
        """Ensure clean PublishedVideo table before each increment view test"""
        from app.published.models import PublishedVideo as PV
        stmt = sa_delete(PV)
        await db_session.execute(stmt)
        await db_session.commit()

    @pytest.mark.asyncio
    async def test_increment_success(self, db_session, dummy_user):
        pv = PublishedVideo(
            user_id=1, title="播放测试", video_url="http://ex.com/v.mp4",
            play_count=1000, tags=[], scenes=[], analysis_report={},
            audio_features={}, script_template="default",
        )
        db_session.add(pv)
        await db_session.flush()

        result = await increment_view(
            video_id=pv.id, db=db_session, user=dummy_user,
        )
        assert result["play_count"] == 1001

    @pytest.mark.asyncio
    async def test_increment_404_not_found(self, db_session, dummy_user):
        with pytest.raises(HTTPException) as exc:
            await increment_view(
                video_id=99999, db=db_session, user=dummy_user,
            )
        assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_increment_404_wrong_user(self, db_session, dummy_user, dummy_user2):
        pv = PublishedVideo(
            user_id=2, title="别人的视频", video_url="http://ex.com/o.mp4",
            play_count=2000, tags=[], scenes=[], analysis_report={},
            audio_features={}, script_template="default",
        )
        db_session.add(pv)
        await db_session.flush()

        with pytest.raises(HTTPException) as exc:
            await increment_view(
                video_id=pv.id, db=db_session, user=dummy_user,
            )
        assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_increment_none_play_count(self, db_session, dummy_user):
        """play_count 为 None → 模型默认 2000 → 2000+1"""
        pv = PublishedVideo(
            user_id=1, title="空播放量", video_url="http://ex.com/v.mp4",
            play_count=None, tags=[], scenes=[], analysis_report={},
            audio_features={}, script_template="default",
        )
        db_session.add(pv)
        await db_session.flush()

        result = await increment_view(
            video_id=pv.id, db=db_session, user=dummy_user,
        )
        # PublishedVideo model defaults play_count=2000, so None→2000→2000+1=2001
        assert result["play_count"] == 2001


# ======================================================
# update_published_play_count / PUT /{video_id}/play-count
# ======================================================

class TestUpdatePlayCount:

    @pytest.fixture(autouse=True)
    async def cleanup_published(self, db_session):
        """Ensure clean PublishedVideo table before each update play count test"""
        from app.published.models import PublishedVideo as PV
        stmt = sa_delete(PV)
        await db_session.execute(stmt)
        await db_session.commit()

    @pytest.mark.asyncio
    async def test_update_success(self, db_session, dummy_user):
        pv = PublishedVideo(
            user_id=1, title="更新播放量", video_url="http://ex.com/v.mp4",
            play_count=1000, tags=[], scenes=[], analysis_report={},
            audio_features={}, script_template="default",
        )
        db_session.add(pv)
        await db_session.flush()

        result = await update_published_play_count(
            video_id=pv.id, body={"play_count": 9999},
            db=db_session, user=dummy_user,
        )
        assert result["play_count"] == 9999

    @pytest.mark.asyncio
    async def test_update_404_not_found(self, db_session, dummy_user):
        with pytest.raises(HTTPException) as exc:
            await update_published_play_count(
                video_id=99999, body={"play_count": 5000},
                db=db_session, user=dummy_user,
            )
        assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_update_404_wrong_user(self, db_session, dummy_user, dummy_user2):
        pv = PublishedVideo(
            user_id=2, title="别人的视频", video_url="http://ex.com/o.mp4",
            play_count=2000, tags=[], scenes=[], analysis_report={},
            audio_features={}, script_template="default",
        )
        db_session.add(pv)
        await db_session.flush()

        with pytest.raises(HTTPException) as exc:
            await update_published_play_count(
                video_id=pv.id, body={"play_count": 5000},
                db=db_session, user=dummy_user,
            )
        assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_update_default_play_count(self, db_session, dummy_user):
        """body 无 play_count → 默认 2000"""
        pv = PublishedVideo(
            user_id=1, title="默认播放量", video_url="http://ex.com/v.mp4",
            play_count=1000, tags=[], scenes=[], analysis_report={},
            audio_features={}, script_template="default",
        )
        db_session.add(pv)
        await db_session.flush()

        result = await update_published_play_count(
            video_id=pv.id, body={},
            db=db_session, user=dummy_user,
        )
        assert result["play_count"] == 2000


# ======================================================
# delete_published / DELETE /{video_id}
# ======================================================

class TestDeletePublished:

    @pytest.fixture(autouse=True)
    async def cleanup_published(self, db_session):
        """Ensure clean PublishedVideo table before each delete test"""
        from app.published.models import PublishedVideo as PV
        stmt = sa_delete(PV)
        await db_session.execute(stmt)
        await db_session.commit()

    @pytest.mark.asyncio
    async def test_delete_success(self, db_session, dummy_user):
        pv = PublishedVideo(
            user_id=1, title="删除测试", video_url="http://ex.com/v.mp4",
            play_count=2000, tags=[], scenes=[], analysis_report={},
            audio_features={}, script_template="default",
        )
        db_session.add(pv)
        await db_session.flush()

        result = await delete_published(
            video_id=pv.id, db=db_session, user=dummy_user,
        )
        assert result["success"] is True

        # Verify deleted
        deleted = await db_session.get(PublishedVideo, pv.id)
        assert deleted is None

    @pytest.mark.asyncio
    async def test_delete_404_not_found(self, db_session, dummy_user):
        with pytest.raises(HTTPException) as exc:
            await delete_published(
                video_id=99999, db=db_session, user=dummy_user,
            )
        assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_404_wrong_user(self, db_session, dummy_user, dummy_user2):
        pv = PublishedVideo(
            user_id=2, title="别人的视频", video_url="http://ex.com/o.mp4",
            play_count=2000, tags=[], scenes=[], analysis_report={},
            audio_features={}, script_template="default",
        )
        db_session.add(pv)
        await db_session.flush()

        with pytest.raises(HTTPException) as exc:
            await delete_published(
                video_id=pv.id, db=db_session, user=dummy_user,
            )
        assert exc.value.status_code == 404
