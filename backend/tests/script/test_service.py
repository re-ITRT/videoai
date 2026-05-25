"""Script service tests — real db_session + mocked workflow"""
import pytest
from unittest.mock import AsyncMock, patch


class TestScriptGenerateService:
    """测试剧本生成服务"""

    @pytest.mark.asyncio
    async def test_generate_script_happy_path(self, db_session):
        """完整流程：工作流调用 → 保存剧本 → 返回响应"""
        mock_result = {
            "title": "智能手表带货视频",
            "scenes": [
                {"id": 1, "order": 1, "description": "开场展示", "narration": "大家好", "duration": 5},
                {"id": 2, "order": 2, "description": "功能介绍", "narration": "这款手表", "duration": 5},
            ],
            "constraints": ["时长≤15s"],
        }

        with patch("app.script.service.call_workflow", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = mock_result

            from app.script.schemas import ScriptGenerateRequest
            from app.script.service import generate_script

            request = ScriptGenerateRequest(
                product_info={"name": "智能手表"},
                mode="auto",
                target_duration=15,
                additional_instructions="电商带货",
            )

            result = await generate_script(db_session, request, "user1")

            # 验证工作流被调用
            mock_call.assert_called_once_with("script-generate", {
                "product_info": {"name": "智能手表"},
                "style": "电商带货",
                "video_style": "电商带货",
                "target_duration": 15,
                "selected_materials": [],
                "mode": "auto",
            })

            # 验证返回结果
            assert result.title == "智能手表带货视频"
            assert len(result.scenes) == 2
            assert result.scenes[0].description == "开场展示"
            assert result.scenes[1].narration == "这款手表"
            assert "时长≤15s" in result.constraints
            assert result.mode == "auto"
            assert result.id > 0

    @pytest.mark.asyncio
    async def test_generate_with_template(self, db_session):
        """模板模式：加载模板策略"""
        from app.script.models import InspirationTemplate

        # 先创建模板
        tpl = InspirationTemplate(
            user_id="user1", name="展示型",
            strategy="开场3秒展示产品", factors={"hook": "视觉冲击"},
            category="product_show"
        )
        db_session.add(tpl)
        await db_session.commit()

        mock_result = {
            "title": "模板剧本",
            "scenes": [{"id": 1, "order": 1, "description": "开场", "narration": "test", "duration": 5}],
            "constraints": [],
        }

        with patch("app.script.service.call_workflow", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = mock_result

            from app.script.schemas import ScriptGenerateRequest
            from app.script.service import generate_script

            request = ScriptGenerateRequest(
                product_info={"name": "产品"},
                mode="template",
                template_id=tpl.id,
                target_duration=15,
            )

            result = await generate_script(db_session, request, "user1")

            # 验证模板策略被传入工作流
            call_args = mock_call.call_args[1] if len(mock_call.call_args) > 1 else {}
            payload = mock_call.call_args[0][1] if mock_call.call_args else {}
            assert payload.get("strategy") == "开场3秒展示产品"
            assert result.id > 0

    @pytest.mark.asyncio
    async def test_generate_with_reference_video(self, db_session):
        """仿写模式：加载参考视频分析"""
        from app.script.models import ReferenceVideo

        rv = ReferenceVideo(
            user_id="user1", title="爆款样例", source_url="https://example.com/v.mp4",
            analysis_report={"hook": "痛点开场", "style": "快节奏"}
        )
        db_session.add(rv)
        await db_session.commit()

        mock_result = {
            "title": "仿写剧本",
            "scenes": [{"id": 1, "order": 1, "description": "开场", "narration": "test", "duration": 5}],
            "constraints": [],
        }

        with patch("app.script.service.call_workflow", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = mock_result

            from app.script.schemas import ScriptGenerateRequest
            from app.script.service import generate_script

            request = ScriptGenerateRequest(
                product_info={"name": "产品"},
                mode="imitation",
                reference_video_id=rv.id,
                target_duration=15,
            )

            result = await generate_script(db_session, request, "user1")

            payload = mock_call.call_args[0][1]
            assert "reference_analysis" in payload
            assert payload["reference_analysis"]["hook"] == "痛点开场"
            assert result.id > 0

    @pytest.mark.asyncio
    async def test_analyze_video(self):
        """分析视频（抛出 NotImplementedError）"""
        from app.script.service import analyze_video
        with pytest.raises(NotImplementedError):
            await analyze_video(None, None, None)

    @pytest.mark.asyncio
    async def test_update_scene(self):
        """更新分镜（抛出 NotImplementedError）"""
        from app.script.service import update_scene
        with pytest.raises(NotImplementedError):
            await update_scene(None, None, None, None)

    def test_all_functions_importable(self):
        from app.script.service import generate_script, analyze_video, update_scene
        assert callable(generate_script)
        assert callable(analyze_video)
        assert callable(update_scene)
