"""material/router.py upload_material_file 全覆盖"""
import io, pytest
from unittest.mock import patch, AsyncMock, MagicMock
from app.auth.models import User


@pytest.fixture
def dummy_user():
    return User(id=1, username="cov_user", hashed_password="h", is_active=True, role="user")


class TestUploadFile:
    """upload_material_file 端点覆盖"""

    @pytest.mark.asyncio
    async def test_upload_no_file(self, db_session, dummy_user):
        from app.material.router import upload_material_file
        with patch("app.material.service.create_material", new_callable=AsyncMock) as cm:
            cm.return_value = MagicMock(id=1, material_type="product", input_type="image",
                                         image_url="/u/test.jpg", source="upload",
                                         created_at=MagicMock())
            result = await upload_material_file(
                file=None, material_type="product", input_type="image",
                category="test", name="test", text_content="", product_name="",
                db=db_session, current_user=dummy_user,
            )
            assert result["source"] == "upload"

    @pytest.mark.asyncio
    async def test_upload_with_file_no_ext(self, db_session, dummy_user):
        from app.material.router import upload_material_file
        mock_file = MagicMock()
        mock_file.filename = "noext"
        mock_file.file = io.BytesIO(b"data")

        with patch("shutil.copyfileobj"), \
             patch("app.material.router.generate_signed_url", return_value=None), \
             patch("app.material.service.create_material", new_callable=AsyncMock) as cm:
            cm.return_value = MagicMock(id=2, material_type="product", input_type="image",
                                         image_url="/u/test.bin", source="upload",
                                         created_at=MagicMock())
            result = await upload_material_file(
                file=mock_file, material_type="product", input_type="image",
                category="img", name="img", text_content="", product_name="",
                db=db_session, current_user=dummy_user,
            )
            assert result["source"] == "upload"

    @pytest.mark.asyncio
    async def test_upload_audio_no_librosa(self, db_session, dummy_user):
        from app.material.router import upload_material_file
        mock_file = MagicMock()
        mock_file.filename = "bgm.mp3"
        mock_file.file = io.BytesIO(b"audio_data")

        with patch("shutil.copyfileobj"), \
             patch("app.material.router.generate_signed_url", return_value="/signed/t/u.mp3"), \
             patch("app.material.service.create_material", new_callable=AsyncMock) as cm, \
             patch("librosa.load") as ll:
            ll.side_effect = Exception("librosa failed")
            cm.return_value = MagicMock(id=3, material_type="audio", input_type="audio",
                                         image_url="/u/bgm.mp3", source="upload",
                                         created_at=MagicMock(),
                                         tags=[], audio_features={})
            result = await upload_material_file(
                file=mock_file, material_type="audio", input_type="audio",
                category="BGM", name="bgm", text_content="", product_name="",
                db=db_session, current_user=dummy_user,
            )
            assert result["source"] == "upload"

    @pytest.mark.asyncio
    async def test_upload_non_audio_triggers_embed(self, db_session, dummy_user):
        from app.material.router import upload_material_file
        mock_file = MagicMock()
        mock_file.filename = "product.jpg"
        mock_file.file = io.BytesIO(b"img_data")

        with patch("shutil.copyfileobj"), \
             patch("app.material.router.generate_signed_url", return_value="/signed/t/u.jpg"), \
             patch("app.material.service.create_material", new_callable=AsyncMock) as cm, \
             patch("app.workers.workflow.call_workflow", new_callable=AsyncMock), \
             patch("asyncio.create_task"):
            cm.return_value = MagicMock(id=4, material_type="product", input_type="image",
                                         image_url="/u/product.jpg", source="upload",
                                         created_at=MagicMock())
            result = await upload_material_file(
                file=mock_file, material_type="product", input_type="image",
                category="", name="prod", text_content="test", product_name="",
                db=db_session, current_user=dummy_user,
            )
            assert result["source"] == "upload"
