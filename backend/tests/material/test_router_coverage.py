"""material/router 覆盖补充测试"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException


@pytest.mark.asyncio
class TestDeleteMaterial:
    async def test_delete_nonexistent_returns_false(self):
        from app.material.router import delete_material
        mock_db = AsyncMock()
        mock_db.execute.return_value.scalar_one_or_none.return_value = None
        mock_user = MagicMock()
        mock_user.id = "test_user"
        with patch("app.material.router.os.path.exists", return_value=False):
            result = await delete_material(999, db=mock_db, current_user=mock_user)
            assert result is False

    async def test_delete_own_material(self):
        from app.material.router import delete_material
        mock_db = AsyncMock()
        mock_mat = MagicMock()
        mock_mat.id = 1
        mock_mat.user_id = "test_user"
        mock_mat.image_url = "/uploads/test.jpg"
        mock_db.execute.return_value.scalar_one_or_none.return_value = mock_mat
        mock_user = MagicMock()
        mock_user.id = "test_user"
        with patch("app.material.router.os.path.exists", return_value=True):
            with patch("app.material.router.os.remove"):
                result = await delete_material(1, db=mock_db, current_user=mock_user)
                assert result is True


@pytest.mark.asyncio
class TestGetMaterial:
    async def test_get_nonexistent_raises(self):
        from app.material.router import get_material
        mock_db = AsyncMock()
        mock_db.execute.return_value.scalar_one_or_none.return_value = None
        mock_user = MagicMock()
        mock_user.id = "test_user"
        with pytest.raises(HTTPException) as exc:
            await get_material(999, db=mock_db, current_user=mock_user)
        assert exc.value.status_code == 404

    async def test_get_existing_returns_material(self):
        from app.material.router import get_material
        mock_db = AsyncMock()
        mock_mat = MagicMock()
        mock_mat.id = 1
        mock_mat.user_id = "test_user"
        mock_mat.name = "test material"
        mock_mat.material_type = "image"
        mock_db.execute.return_value.scalar_one_or_none.return_value = mock_mat
        mock_user = MagicMock()
        mock_user.id = "test_user"
        result = await get_material(1, db=mock_db, current_user=mock_user)
        assert result.id == 1
        assert result.name == "test material"


@pytest.mark.asyncio
class TestListMaterials:
    async def test_list_materials_returns_dict(self):
        from app.material.router import list_materials
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_scalars = AsyncMock()
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result
        mock_user = MagicMock()
        mock_user.id = "test_user"
        result = await list_materials(db=mock_db, current_user=mock_user)
        assert isinstance(result, dict) or isinstance(result, list)


class TestMaterialTypes:
    def test_material_types_defined(self):
        from app.material.models import Material
        assert hasattr(Material, "material_type")

    def test_material_has_required_fields(self):
        from app.material.models import Material
        assert hasattr(Material, "name")
        assert hasattr(Material, "image_url")
        assert hasattr(Material, "user_id")
