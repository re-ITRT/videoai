"""
优质视频库 - Service 测试
"""
import pytest
from unittest.mock import AsyncMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from app.reference.service import (
    analyze_and_save_video,
    get_reference_videos,
    get_reference_video_by_id,
    delete_reference_video,
)
from app.reference.schemas import VideoAnalyzeRequest


@pytest.fixture
def mock_db():
    db = AsyncMock(spec=AsyncSession)
    return db


@pytest.mark.asyncio
async def test_analyze_and_save_video(mock_db):
    """测试分析并保存视频"""
    request = VideoAnalyzeRequest(
        source_url="https://example.com/video.mp4",
        source_platform="TikTok",
        title="测试视频",
        category="美妆",
    )

    mock_analysis_result = {
        "hook_method": "痛点直击",
        "selling_points": ["质地清爽", "持久不脱妆"],
        "storyboard": [
            {"type": "开场", "description": "展示产品"},
            {"type": "使用", "description": "演示上妆"},
        ],
        "style": "口播",
        "analysis_report": {"overall": "优秀", "score": 95},
    }

    with patch("app.reference.service.call_workflow", new_callable=AsyncMock) as mock_call:
        mock_call.return_value = mock_analysis_result

        video = await analyze_and_save_video(mock_db, "test_user", request)

        mock_call.assert_called_once_with("video-analyze", {
            "source_url": "https://example.com/video.mp4",
            "source_platform": "TikTok",
            "title": "测试视频",
            "category": "美妆",
        })

        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()

        saved_video = mock_db.add.call_args[0][0]
        assert saved_video.hook_method == "痛点直击"
        assert saved_video.selling_points == ["质地清爽", "持久不脱妆"]
        assert saved_video.style == "口播"


@pytest.mark.asyncio
async def test_analyze_and_save_video_workflow_error(mock_db):
    """测试工作流调用失败"""
    request = VideoAnalyzeRequest(source_url="https://example.com/video.mp4")

    with patch("app.reference.service.call_workflow", new_callable=AsyncMock) as mock_call:
        mock_call.side_effect = Exception("工作流调用失败")

        with pytest.raises(Exception, match="工作流调用失败"):
            await analyze_and_save_video(mock_db, "test_user", request)


@pytest.mark.asyncio
async def test_get_reference_video_by_id_found(mock_db):
    """测试根据ID获取视频 - 找到"""
    mock_result = AsyncMock()
    mock_result.scalar_one_or_none.return_value = {"id": 1, "title": "测试视频"}
    mock_db.execute.return_value = mock_result

    video = await get_reference_video_by_id(mock_db, 1, "test_user")

    assert video is not None
    assert video["id"] == 1


@pytest.mark.asyncio
async def test_get_reference_video_by_id_not_found(mock_db):
    """测试根据ID获取视频 - 未找到"""
    mock_result = AsyncMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_result

    video = await get_reference_video_by_id(mock_db, 999, "test_user")

    assert video is None


@pytest.mark.asyncio
async def test_delete_reference_video_success(mock_db):
    """测试删除视频成功"""
    with patch("app.reference.service.get_reference_video_by_id", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = {"id": 1}

        result = await delete_reference_video(mock_db, 1, "test_user")

        assert result is True
        mock_db.delete.assert_called_once()
        mock_db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_delete_reference_video_not_found(mock_db):
    """测试删除视频 - 视频不存在"""
    with patch("app.reference.service.get_reference_video_by_id", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = None

        result = await delete_reference_video(mock_db, 999, "test_user")

        assert result is False
        mock_db.delete.assert_not_called()
