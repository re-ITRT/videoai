"""
Tests for script schemas
"""
import pytest
import sys
from pathlib import Path

backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from app.script.schemas import ScriptGenerateRequest, ScriptGenerateResponse, Scene


class TestScriptGenerateRequest:
    def test_default_values(self):
        request = ScriptGenerateRequest(product_info={"name": "test"})
        assert request.target_duration == 15
        assert request.mode == "auto"
        assert request.num_variants == 1
        assert request.aspect_ratio == "9:16"
        assert request.selected_materials == []

    def test_custom_values(self):
        request = ScriptGenerateRequest(
            product_info={"name": "test"},
            target_duration=30,
            mode="template",
            num_variants=3,
            aspect_ratio="16:9",
            selected_materials=[1, 2, 3],
        )
        assert request.target_duration == 30
        assert request.mode == "template"
        assert request.num_variants == 3
        assert request.aspect_ratio == "16:9"
        assert request.selected_materials == [1, 2, 3]

    def test_optional_fields(self):
        request = ScriptGenerateRequest(
            product_info={"name": "test"},
            style="lifestyle",
            video_style="trending",
            template_id=1,
            reference_video_id=2,
            additional_instructions="test instructions",
        )
        assert request.style == "lifestyle"
        assert request.video_style == "trending"
        assert request.template_id == 1
        assert request.reference_video_id == 2
        assert request.additional_instructions == "test instructions"

    def test_product_info_required(self):
        with pytest.raises(ValueError):
            ScriptGenerateRequest()


class TestScene:
    def test_default_values(self):
        scene = Scene(
            id=1,
            order=1,
            description="test description",
            narration="test narration",
            duration=5,
        )
        assert scene.dialogue is None
        assert scene.visual_style is None
        assert scene.camera_movement is None
        assert scene.bgm_type is None
        assert scene.transition is None
        assert scene.material_slice_ids is None

    def test_full_fields(self):
        scene = Scene(
            id=1,
            order=1,
            description="test description",
            narration="test narration",
            dialogue="test dialogue",
            visual_style="bright_fresh",
            camera_movement="pan",
            bgm_type="upbeat",
            duration=8,
            transition="fade",
            material_slice_ids=[1, 2, 3],
        )
        assert scene.id == 1
        assert scene.order == 1
        assert scene.description == "test description"
        assert scene.narration == "test narration"
        assert scene.dialogue == "test dialogue"
        assert scene.visual_style == "bright_fresh"
        assert scene.bgm_type == "upbeat"
        assert scene.duration == 8
        assert scene.transition == "fade"
        assert scene.material_slice_ids == [1, 2, 3]


class TestScriptGenerateResponse:
    def test_success_response(self):
        scenes = [
            Scene(id=1, order=1, description="d1", narration="n1", duration=5),
            Scene(id=2, order=2, description="d2", narration="n2", duration=6),
        ]
        response = ScriptGenerateResponse(
            success=True,
            script_id=123,
            scenes=scenes,
            total_duration=11,
            aspect_ratio="9:16",
        )
        assert response.success is True
        assert response.script_id == 123
        assert len(response.scenes) == 2
        assert response.total_duration == 11
        assert response.aspect_ratio == "9:16"
        assert response.error is None

    def test_error_response(self):
        response = ScriptGenerateResponse(
            success=False,
            scenes=[],
            total_duration=0,
            aspect_ratio="9:16",
            error="Workflow failed",
        )
        assert response.success is False
        assert response.error == "Workflow failed"

    def test_metadata(self):
        response = ScriptGenerateResponse(
            success=True,
            scenes=[],
            total_duration=0,
            aspect_ratio="9:16",
            metadata={"workflow_result": {"data": "test"}},
        )
        assert response.metadata["workflow_result"]["data"] == "test"
