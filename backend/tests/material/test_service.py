"""素材边缘路径测试 — 提升覆盖率"""
import pytest

from app.material import service as svc
from app.material.schemas import SliceCreateRequest, MaterialSearchRequest


class TestMaterialServiceDirect:
    """直接测试 service 层函数（绕过 httpx）"""

    @pytest.mark.asyncio
    async def test_create_product(self, db_session):
        p = await svc.create_product(db_session, user_id=1, name="新产品", category="数码")
        assert p.name == "新产品"
        assert p.category == "数码"

    @pytest.mark.asyncio
    async def test_get_products_empty(self, db_session):
        products = await svc.get_products(db_session, user_id=999)
        assert products == []

    @pytest.mark.asyncio
    async def test_create_material_with_text(self, db_session):
        m = await svc.create_material(
            db_session, user_id="1", material_type="general",
            input_type="text", text_content="纯文本素材", source="manual"
        )
        assert m.text_content == "纯文本素材"
        assert m.source == "manual"

    @pytest.mark.asyncio
    async def test_get_material_nonexistent(self, db_session):
        m = await svc.get_material(db_session, 99999)
        assert m is None

    @pytest.mark.asyncio
    async def test_list_materials_empty(self, db_session):
        mats = await svc.list_materials(db_session, user_id="999", limit=10)
        assert mats == []

    @pytest.mark.asyncio
    async def test_list_materials_filter_type(self, db_session):
        await svc.create_material(db_session, user_id="filter1", material_type="product", input_type="image")
        await svc.create_material(db_session, user_id="filter1", material_type="reference", input_type="video")
        product_mats = await svc.list_materials(db_session, user_id="filter1", material_type="product")
        assert len(product_mats) == 1
        assert product_mats[0].material_type == "product"

    @pytest.mark.asyncio
    async def test_delete_nonexistent(self, db_session):
        ok = await svc.delete_material(db_session, 99999)
        assert ok is False

    @pytest.mark.asyncio
    async def test_create_slice_full_params(self, db_session):
        m = await svc.create_material(db_session, user_id="1", material_type="product", input_type="video")
        s = await svc.create_slice(
            db_session, material_id=m.id, slice_type="keyframe",
            scene_id=1, time_range="0-5s", description="开场",
            image_url="https://example.com/kf.jpg",
        )
        assert s.time_range == "0-5s"
        assert s.description == "开场"

    @pytest.mark.asyncio
    async def test_list_slices_empty(self, db_session):
        slices = await svc.list_slices(db_session, material_id=99999)
        assert slices == []

    @pytest.mark.asyncio
    async def test_list_slices_by_type(self, db_session):
        m = await svc.create_material(db_session, user_id="1", material_type="product", input_type="video")
        await svc.create_video_slices(db_session, m.id, scene_count=2)
        scenes = await svc.list_slices(db_session, m.id, slice_type="video_scene")
        assert len(scenes) == 2

    @pytest.mark.asyncio
    async def test_create_video_slices_custom_count(self, db_session):
        m = await svc.create_material(db_session, user_id="1", material_type="product", input_type="video")
        slices = await svc.create_video_slices(db_session, m.id, scene_count=5)
        assert len(slices) == 5
        assert slices[4].scene_id == 5

    @pytest.mark.asyncio
    async def test_delete_material_cascades(self, db_session):
        m = await svc.create_material(db_session, user_id="1", material_type="product", input_type="video")
        await svc.create_video_slices(db_session, m.id)
        ok = await svc.delete_material(db_session, m.id)
        assert ok is True
        remaining = await svc.list_slices(db_session, m.id)
        assert remaining == []


class TestMaterialSchemasDirect:

    def test_material_upload_response(self):
        from app.material.schemas import MaterialUploadResponse
        r = MaterialUploadResponse(id=1, material_type="product", input_type="image", source="upload")
        assert r.source == "upload"

    def test_material_response(self):
        from app.material.schemas import MaterialResponse
        r = MaterialResponse(id=1, user_id="1", material_type="product", input_type="image")
        assert r.material_type == "product"
        assert r.tags == []
