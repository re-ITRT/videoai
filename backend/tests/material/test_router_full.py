"""material/router.py 全覆盖测试"""
import json, pytest
from unittest.mock import patch, AsyncMock, MagicMock, mock_open
from fastapi import HTTPException
from app.auth.models import User
from app.material.models import Material
from app.material.schemas import MaterialUploadRequest, MaterialSearchRequest, SliceCreateRequest


@pytest.fixture
def dummy_user():
    return User(id=1, username="cov_user", hashed_password="h", is_active=True, role="user")


class TestUploadMaterial:
    @pytest.mark.asyncio
    async def test_upload_without_scenes(self, db_session, dummy_user):
        from app.material.router import upload_material
        req = MaterialUploadRequest(
            material_type="product", input_type="image",
            image_url="/u/test.jpg",
        )
        with patch("app.material.service.create_material", new_callable=AsyncMock) as cm:
            cm.return_value = Material(
                id=1, user_id="1", material_type="product", input_type="image",
                image_url="/u/test.jpg",
            )
            result = await upload_material(req, db_session, dummy_user)
            assert hasattr(result, "id") or isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_upload_with_scenes(self, db_session, dummy_user):
        from app.material.router import upload_material
        req = MaterialUploadRequest(
            material_type="product", input_type="image",
            image_url="/u/test.jpg",
            scenes=[{"time_range": "0-10", "description": "intro"}],
        )
        with patch("app.material.service.create_material", new_callable=AsyncMock) as cm, \
             patch("app.material.service.parse_and_create_slices", new_callable=AsyncMock):
            cm.return_value = Material(
                id=1, user_id="1", material_type="product", input_type="image",
                image_url="/u/test.jpg",
            )
            result = await upload_material(req, db_session, dummy_user)
            assert hasattr(result, "id") or isinstance(result, dict)


class TestListMaterials:
    @pytest.mark.asyncio
    async def test_empty_list(self, db_session, dummy_user):
        from app.material.router import list_materials
        with patch("app.material.service.list_materials", new_callable=AsyncMock) as lm:
            lm.return_value = []
            result = await list_materials(db=db_session, current_user=dummy_user)
            assert result == []

    @pytest.mark.asyncio
    async def test_with_items(self, db_session, dummy_user):
        from app.material.router import list_materials
        m = Material(id=1, name="test", user_id="1", material_type="product", input_type="image")
        with patch("app.material.service.list_materials", new_callable=AsyncMock) as lm:
            lm.return_value = [m]
            result = await list_materials(db=db_session, current_user=dummy_user)
            assert len(result) == 1

    @pytest.mark.asyncio
    async def test_filter_by_type(self, db_session, dummy_user):
        from app.material.router import list_materials
        with patch("app.material.service.list_materials", new_callable=AsyncMock) as lm:
            lm.return_value = []
            result = await list_materials(
                material_type="product", db=db_session, current_user=dummy_user
            )
            assert result == []


class TestGetMaterial:
    @pytest.mark.asyncio
    async def test_not_found_404(self, db_session, dummy_user):
        from app.material.router import get_material
        with patch("app.material.service.get_material", new_callable=AsyncMock, return_value=None):
            with pytest.raises(HTTPException) as exc:
                await get_material(999, db_session, dummy_user)
            assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_found(self, db_session, dummy_user):
        from app.material.router import get_material
        m = Material(id=1, name="test", user_id="1", material_type="product", input_type="image")
        with patch("app.material.service.get_material", new_callable=AsyncMock, return_value=m):
            result = await get_material(1, db_session, dummy_user)
            assert hasattr(result, "id") or isinstance(result, dict)


class TestDeleteMaterial:
    @pytest.mark.asyncio
    async def test_not_found_404(self, db_session, dummy_user):
        from app.material.router import delete_material
        with patch("app.material.service.delete_material", new_callable=AsyncMock, return_value=False):
            with pytest.raises(HTTPException) as exc:
                await delete_material(999, db_session, dummy_user)
            assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_success_204(self, db_session, dummy_user):
        from app.material.router import delete_material
        with patch("app.material.service.delete_material", new_callable=AsyncMock, return_value=True):
            result = await delete_material(1, db_session, dummy_user)
            assert result is None  # 204 No Content


class TestSearchMaterials:
    @pytest.mark.asyncio
    async def test_search_success(self, db_session, dummy_user):
        from app.material.router import search_materials
        req = MaterialSearchRequest(query="test", threshold=0.5)
        with patch("app.material.search.search_materials", new_callable=AsyncMock) as sm:
            sm.return_value = [{"id": 1, "similarity": 0.8, "image_url": "/u/1.jpg", "tags": []}]
            result = await search_materials(req, db_session, dummy_user)
            assert len(result) == 1
            assert result[0].similarity == 0.8

    @pytest.mark.asyncio
    async def test_search_fallback_on_error(self, db_session, dummy_user):
        from app.material.router import search_materials
        req = MaterialSearchRequest(query="test", threshold=0.5)
        with patch("app.material.search.search_materials", new_callable=AsyncMock,
                   side_effect=Exception("pgvector error")), \
             patch("app.material.search.search_materials_fallback", new_callable=AsyncMock) as smf:
            smf.return_value = [{"id": 2, "similarity": 0.6, "image_url": "/u/2.jpg", "tags": []}]
            result = await search_materials(req, db_session, dummy_user)
            assert len(result) == 1

    @pytest.mark.asyncio
    async def test_search_both_fail_returns_empty(self, db_session, dummy_user):
        from app.material.router import search_materials
        req = MaterialSearchRequest(query="test", threshold=0.5)
        with patch("app.material.search.search_materials", new_callable=AsyncMock,
                   side_effect=Exception("pgvector error")), \
             patch("app.material.search.search_materials_fallback", new_callable=AsyncMock,
                   side_effect=Exception("text search error")):
            result = await search_materials(req, db_session, dummy_user)
            assert len(result) == 0


class TestListSlices:
    @pytest.mark.asyncio
    async def test_material_not_found_404(self, db_session, dummy_user):
        from app.material.router import list_slices
        with patch("app.material.service.get_material", new_callable=AsyncMock, return_value=None):
            with pytest.raises(HTTPException) as exc:
                await list_slices(999, db=db_session, current_user=dummy_user)
            assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_list_slices_success(self, db_session, dummy_user):
        from app.material.router import list_slices
        m = Material(id=1, name="test", user_id="1", material_type="product", input_type="image")
        with patch("app.material.service.get_material", new_callable=AsyncMock, return_value=m), \
             patch("app.material.service.list_slices", new_callable=AsyncMock, return_value=[]):
            result = await list_slices(1, db=db_session, current_user=dummy_user)
            assert result == []


class TestCreateSlice:
    @pytest.mark.asyncio
    async def test_material_not_found_404(self, db_session, dummy_user):
        from app.material.router import create_slice
        req = SliceCreateRequest(slice_type="keyframe", time_range="0-5")
        with patch("app.material.service.get_material", new_callable=AsyncMock, return_value=None):
            with pytest.raises(HTTPException) as exc:
                await create_slice(999, req, db_session, dummy_user)
            assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_create_slice_success(self, db_session, dummy_user):
        from app.material.router import create_slice
        m = Material(id=1, name="test", user_id="1", material_type="product", input_type="image")
        req = SliceCreateRequest(slice_type="keyframe", time_range="0-5", description="test")
        with patch("app.material.service.get_material", new_callable=AsyncMock, return_value=m), \
             patch("app.material.service.create_slice", new_callable=AsyncMock) as cs:
            cs.return_value = MagicMock(id=1, material_id=1, slice_type="keyframe", time_range="0-5")
            result = await create_slice(1, req, db_session, dummy_user)
            assert hasattr(result, "id") or isinstance(result, dict)
