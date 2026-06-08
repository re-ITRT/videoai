"""studio/router.py + material/router.py 最后一批边缘行覆盖"""
import json, pytest
from unittest.mock import patch, AsyncMock, MagicMock, mock_open
from app.auth.models import User


@pytest.fixture
def dummy_user():
    return User(id=1, username="cov_user", hashed_password="h", is_active=True, role="user")


class TestMaterialUploadAudioLibrosa:
    """覆盖 material/router.py lines 117-133: librosa 分析成功路径"""

    @pytest.mark.asyncio
    async def test_audio_librosa_analysis_success(self, db_session, dummy_user):
        from app.material.router import upload_material_file
        import numpy as np
        mock_file = MagicMock()
        mock_file.filename = "song.mp3"
        mock_file.file = MagicMock()

        fake_y = np.zeros(22050)

        with patch("shutil.copyfileobj"), \
             patch("app.material.router.generate_signed_url", return_value="/signed/t/s.mp3"), \
             patch("app.material.service.create_material", new_callable=AsyncMock) as cm, \
             patch("librosa.load", return_value=(fake_y, 22050)), \
             patch("librosa.get_duration", return_value=60.0), \
             patch("librosa.beat.beat_track", return_value=(140.0, [])), \
             patch("librosa.feature.spectral_centroid") as cent, \
             patch("librosa.feature.zero_crossing_rate") as zcr, \
             patch("librosa.feature.spectral_rolloff") as roff, \
             patch("librosa.feature.mfcc") as mfcc:
            cent.return_value.mean.return_value = 3000.0
            zcr.return_value.mean.return_value = 0.08
            roff.return_value.mean.return_value = 5000.0
            mfcc.return_value = np.zeros((13, 50))

            cm.return_value = MagicMock(id=10, material_type="audio", input_type="audio",
                                         image_url="/u/song.mp3", source="upload",
                                         created_at=MagicMock(),
                                         tags=[], audio_features={})

            result = await upload_material_file(
                file=mock_file, material_type="audio", input_type="audio",
                category="BGM", name="song", text_content="", product_name="",
                db=db_session, current_user=dummy_user,
            )
            assert result["source"] == "upload"


class TestStudioEdgeLines:
    """studio/router.py 剩余单行边缘覆盖"""

    @pytest.mark.asyncio
    async def test_sign_url_empty_returns_error(self):
        from app.studio.router import get_signed_url
        result = await get_signed_url(path="")
        assert result["error"] == "path required"

    @pytest.mark.asyncio
    async def test_sign_url_http_no_uploads(self):
        from app.studio.router import get_signed_url
        with patch("app.core.signer.generate_signed_url") as m:
            m.return_value = "/signed/t/file"
            result = await get_signed_url(path="http://cdn.com/something/v.mp4")
            assert "url" in result

    @pytest.mark.asyncio
    async def test_video_proxy_signed_path(self):
        from app.studio.router import video_proxy
        with patch("os.path.exists", side_effect=lambda p: "/app/uploads/v.mp4" in str(p)), \
             patch("fastapi.responses.FileResponse") as fr:
            fr.return_value = {"ok": True}
            result = await video_proxy(path="/signed/token/uploads/v.mp4")
            assert result == {"ok": True}
