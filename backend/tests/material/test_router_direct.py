"""素材路由边缘测试 — 直接调用 handler 绕过 ASGI"""
import pytest
from app.auth.models import User


@pytest.fixture
def dummy_user():
    """创建一个最小 User 实例用于直接调用 handler"""
    return User(id=1, username="direct_test", hashed_password="hash", is_active=True, role="user")


class TestMaterialRouterDirect:

    @pytest.mark.asyncio
    async def test_get_material_handler(self, db_session, dummy_user):
        from app.material.router import get_material, upload_material
        from app.material.schemas import MaterialUploadRequest

        upload_resp = await upload_material(
            request=MaterialUploadRequest(material_type="product", input_type="image"),
            db=db_session, current_user=dummy_user,
        )
        mid = upload_resp.id

        resp = await get_material(material_id=mid, db=db_session, current_user=dummy_user)
        assert resp.id == mid
        assert resp.material_type == "product"

    @pytest.mark.asyncio
    async def test_get_material_404(self, db_session, dummy_user):
        from app.material.router import get_material
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            await get_material(material_id=99999, db=db_session, current_user=dummy_user)
        assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_upload_video_creates_slices(self, db_session, dummy_user):
        from app.material.router import upload_material, list_slices
        from app.material.schemas import MaterialUploadRequest

        resp = await upload_material(
            request=MaterialUploadRequest(material_type="product", input_type="video"),
            db=db_session, current_user=dummy_user,
        )
        slices = await list_slices(material_id=resp.id, slice_type=None, db=db_session, current_user=dummy_user)
        assert len(slices) == 3

    @pytest.mark.asyncio
    async def test_list_slices_filtered(self, db_session, dummy_user):
        from app.material.router import upload_material, list_slices
        from app.material.schemas import MaterialUploadRequest

        resp = await upload_material(
            request=MaterialUploadRequest(material_type="product", input_type="video"),
            db=db_session, current_user=dummy_user,
        )
        slices = await list_slices(material_id=resp.id, slice_type="video_scene", db=db_session, current_user=dummy_user)
        assert all(s.slice_type == "video_scene" for s in slices)

    @pytest.mark.asyncio
    async def test_delete_material_404(self, db_session, dummy_user):
        from app.material.router import delete_material
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            await delete_material(material_id=99999, db=db_session, current_user=dummy_user)
        assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_create_slice_nonexistent(self, db_session, dummy_user):
        from app.material.router import create_slice
        from app.material.schemas import SliceCreateRequest
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            await create_slice(
                material_id=99999,
                request=SliceCreateRequest(slice_type="video_scene"),
                db=db_session, current_user=dummy_user,
            )
        assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_search_returns_empty(self, db_session, dummy_user):
        from app.material.router import search_materials
        from app.material.schemas import MaterialSearchRequest
        resp = await search_materials(
            request=MaterialSearchRequest(query="test"),
            db=db_session, current_user=dummy_user,
        )
        assert resp == []

    @pytest.mark.asyncio
    async def test_list_materials_handler(self, db_session, dummy_user):
        from app.material.router import list_materials
        resp = await list_materials(
            material_type=None, skip=0, limit=10,
            db=db_session, current_user=dummy_user,
        )
        assert isinstance(resp, list)

    @pytest.mark.asyncio
    async def test_upload_material_text(self, db_session, dummy_user):
        from app.material.router import upload_material
        from app.material.schemas import MaterialUploadRequest
        resp = await upload_material(
            request=MaterialUploadRequest(
                material_type="general", input_type="text",
                text_content="纯文本素材", source="manual",
            ),
            db=db_session, current_user=dummy_user,
        )
        assert resp.text_content == "纯文本素材"
