"""signed.py 路由函数直接测试"""
import pytest
from unittest.mock import patch, MagicMock
from fastapi import HTTPException


class TestServeSignedFile:
    """直接调用 serve_signed_file 函数覆盖路由代码"""

    @pytest.mark.asyncio
    async def test_invalid_token_403(self):
        from app.signed import serve_signed_file
        with patch("app.signed.verify_signed_url", return_value=False):
            with pytest.raises(HTTPException) as exc:
                await serve_signed_file("bad_token", "analyze/test.jpg")
            assert exc.value.status_code == 403

    @pytest.mark.asyncio
    async def test_valid_token_file_not_found_404(self):
        from app.signed import serve_signed_file
        with patch("app.signed.verify_signed_url", return_value=True), \
             patch("pathlib.Path.exists", return_value=False):
            with pytest.raises(HTTPException) as exc:
                await serve_signed_file("good_token", "analyze/missing.jpg")
            assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_valid_token_file_found_returns_file(self):
        from app.signed import serve_signed_file
        with patch("app.signed.verify_signed_url", return_value=True), \
             patch("pathlib.Path.exists", return_value=True), \
             patch("fastapi.responses.FileResponse") as fr:
            fr.return_value = {"file": "mock"}
            result = await serve_signed_file("good_token", "analyze/exists.jpg")
            assert result == {"file": "mock"}
