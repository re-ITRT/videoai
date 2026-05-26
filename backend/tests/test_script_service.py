"""
Tests for script service
"""
import pytest
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from app.script.service import generate_script
from app.script.schemas import ScriptGenerateRequest


class TestGenerateScript:
    @pytest.mark.asyncio
    async def test_generate_script_success(self, sample_product_info):
        mock_workflow_result = {
            "scenes": [
                {
                    "id": 1,
                    "order": 1,
                    "description": "产品特写开场",
                    "narration": "夏天到了，防晒可别忘了",
                    "duration": 5,
                },
                {
                    "id": 2,
                    "order": 2,
                    "description": "使用场景展示",
                    "narration": "这款喷雾轻薄不油腻",
                    "duration": 6,
                },
            ],
            "metadata": {"source": "coze-workflow"},
        }

        with patch("app.script.service.call_workflow", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = mock_workflow_result

            request = ScriptGenerateRequest(
                product_info=sample_product_info,
                target_duration=30,
                aspect_ratio="16:9",
            )

            response = await generate_script(request)

            assert response.success is True
            assert len(response.scenes) == 2
            assert response.total_duration == 11
            assert response.aspect_ratio == "16:9"
            assert response.scenes[0].description == "产品特写开场"
            assert response.scenes[1].narration == "这款喷雾轻薄不油腻"
            assert "workflow_result" in response.metadata

            # Verify call_workflow was called with correct params
            mock_call.assert_called_once_with(
                "script-generate",
                {
                    "product_info": sample_product_info,
                    "style": None,
                    "target_duration": 30,
                    "selected_materials": [],
                    "mode": "auto",
                    "template_id": None,
                    "reference_video_id": None,
                    "additional_instructions": None,
                    "num_variants": 1,
                    "aspect_ratio": "16:9",
                },
            )

    @pytest.mark.asyncio
    async def test_generate_script_with_style_fallback(self, sample_product_info):
        """Test that video_style is used when style is None"""
        with patch("app.script.service.call_workflow", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = {"scenes": []}

            request = ScriptGenerateRequest(
                product_info=sample_product_info,
                style=None,
                video_style="lifestyle",
            )

            await generate_script(request)

            call_args = mock_call.call_args
            assert call_args[0][1]["style"] == "lifestyle"

    @pytest.mark.asyncio
    async def test_generate_script_with_style_precedence(self, sample_product_info):
        """Test that style takes precedence over video_style"""
        with patch("app.script.service.call_workflow", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = {"scenes": []}

            request = ScriptGenerateRequest(
                product_info=sample_product_info,
                style="professional",
                video_style="lifestyle",
            )

            await generate_script(request)

            call_args = mock_call.call_args
            assert call_args[0][1]["style"] == "professional"

    @pytest.mark.asyncio
    async def test_generate_script_empty_scenes(self, sample_product_info):
        with patch("app.script.service.call_workflow", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = {"scenes": []}

            request = ScriptGenerateRequest(product_info=sample_product_info)
            response = await generate_script(request)

            assert response.success is True
            assert len(response.scenes) == 0
            assert response.total_duration == 0

    @pytest.mark.asyncio
    async def test_generate_script_with_materials(self, sample_product_info):
        with patch("app.script.service.call_workflow", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = {"scenes": []}

            request = ScriptGenerateRequest(
                product_info=sample_product_info,
                selected_materials=[1, 2, 3],
            )

            await generate_script(request)

            call_args = mock_call.call_args
            assert call_args[0][1]["selected_materials"] == [1, 2, 3]

    @pytest.mark.asyncio
    async def test_generate_script_template_mode(self, sample_product_info):
        with patch("app.script.service.call_workflow", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = {"scenes": []}

            request = ScriptGenerateRequest(
                product_info=sample_product_info,
                mode="template",
                template_id=5,
            )

            await generate_script(request)

            call_args = mock_call.call_args
            assert call_args[0][1]["mode"] == "template"
            assert call_args[0][1]["template_id"] == 5

    @pytest.mark.asyncio
    async def test_generate_script_imitation_mode(self, sample_product_info):
        with patch("app.script.service.call_workflow", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = {"scenes": []}

            request = ScriptGenerateRequest(
                product_info=sample_product_info,
                mode="imitation",
                reference_video_id=10,
            )

            await generate_script(request)

            call_args = mock_call.call_args
            assert call_args[0][1]["mode"] == "imitation"
            assert call_args[0][1]["reference_video_id"] == 10

    @pytest.mark.asyncio
    async def test_generate_script_with_instructions(self, sample_product_info):
        with patch("app.script.service.call_workflow", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = {"scenes": []}

            instructions = "强调产品的防水功能"
            request = ScriptGenerateRequest(
                product_info=sample_product_info,
                additional_instructions=instructions,
            )

            await generate_script(request)

            call_args = mock_call.call_args
            assert call_args[0][1]["additional_instructions"] == instructions

    @pytest.mark.asyncio
    async def test_generate_script_multiple_variants(self, sample_product_info):
        with patch("app.script.service.call_workflow", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = {"scenes": []}

            request = ScriptGenerateRequest(
                product_info=sample_product_info,
                num_variants=5,
            )

            await generate_script(request)

            call_args = mock_call.call_args
            assert call_args[0][1]["num_variants"] == 5

    @pytest.mark.asyncio
    async def test_generate_script_workflow_error(self, sample_product_info):
        with patch("app.script.service.call_workflow", new_callable=AsyncMock) as mock_call:
            mock_call.side_effect = Exception("Workflow execution failed")

            request = ScriptGenerateRequest(product_info=sample_product_info)

            with pytest.raises(Exception, match="Workflow execution failed"):
                await generate_script(request)

    @pytest.mark.asyncio
    async def test_generate_script_all_aspect_ratios(self, sample_product_info):
        aspect_ratios = ["9:16", "16:9", "1:1", "4:3"]

        with patch("app.script.service.call_workflow", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = {"scenes": []}

            for ratio in aspect_ratios:
                request = ScriptGenerateRequest(
                    product_info=sample_product_info,
                    aspect_ratio=ratio,
                )
                response = await generate_script(request)
                assert response.aspect_ratio == ratio
