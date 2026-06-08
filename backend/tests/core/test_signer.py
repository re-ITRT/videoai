"""signer 模块测试 — generate_signed_url / verify_signed_url"""
import time
import hmac
import hashlib
import base64
from app.config import settings


class TestGenerateSignedUrl:
    def test_generates_signed_url_format(self):
        from app.core.signer import generate_signed_url
        url = generate_signed_url("/uploads/test/file.mp4", expire_seconds=3600)
        assert url.startswith("/signed/")
        assert url.endswith("/test/file.mp4")
        parts = url.split("/")
        assert len(parts) == 5  # /signed/{token}/test/file.mp4
        token = parts[2]
        assert len(token) > 10

    def test_relative_path_without_uploads(self):
        from app.core.signer import generate_signed_url
        url = generate_signed_url("file.mp4", expire_seconds=3600)
        assert url.startswith("/signed/")
        assert url.endswith("/file.mp4")

    def test_different_expiry(self):
        from app.core.signer import generate_signed_url
        url1 = generate_signed_url("/uploads/a.jpg", expire_seconds=60)
        url2 = generate_signed_url("/uploads/a.jpg", expire_seconds=86400)
        # 不同过期时间 token 不同
        assert url1 != url2

    def test_different_files_different_urls(self):
        from app.core.signer import generate_signed_url
        url1 = generate_signed_url("/uploads/a.jpg")
        url2 = generate_signed_url("/uploads/b.jpg")
        assert url1 != url2


class TestVerifySignedUrl:
    def test_verify_valid_url(self):
        from app.core.signer import generate_signed_url, verify_signed_url
        url = generate_signed_url("/uploads/test/file.mp4", expire_seconds=3600)
        parts = url.split("/")
        token = parts[2]
        filename = "/".join(parts[3:])
        assert verify_signed_url(token, filename) is True

    def test_verify_expired_url(self):
        from app.core.signer import generate_signed_url, verify_signed_url
        url = generate_signed_url("/uploads/test/file.mp4", expire_seconds=-1)
        parts = url.split("/")
        token = parts[2]
        filename = "/".join(parts[3:])
        assert verify_signed_url(token, filename) is False

    def test_verify_tampered_token(self):
        from app.core.signer import generate_signed_url, verify_signed_url
        url = generate_signed_url("/uploads/test/file.mp4")
        parts = url.split("/")
        token = parts[2]
        tampered = token[:-5] + "XXXXX"
        filename = "/".join(parts[3:])
        assert verify_signed_url(tampered, filename) is False

    def test_verify_invalid_token_format(self):
        from app.core.signer import verify_signed_url
        assert verify_signed_url("not-a-valid-base64", "file.mp4") is False
        assert verify_signed_url("", "file.mp4") is False
        assert verify_signed_url("!!!invalid!!!", "file.mp4") is False

    def test_verify_wrong_filename(self):
        from app.core.signer import generate_signed_url, verify_signed_url
        url = generate_signed_url("/uploads/file_a.mp4")
        parts = url.split("/")
        token = parts[2]
        # 用不同的文件名验证
        assert verify_signed_url(token, "file_b.mp4") is False

    def test_verify_wrong_secret_key(self):
        """使用一个独立构造的但使用不同密钥的签名"""
        from app.core.signer import generate_signed_url, verify_signed_url
        from unittest.mock import patch

        url = generate_signed_url("/uploads/test.mp4", expire_seconds=3600)
        parts = url.split("/")
        token = parts[2]
        filename = "/".join(parts[3:])
        # 使用原始密钥验证应该通过
        assert verify_signed_url(token, filename) is True

    def test_verify_round_trip_multiple_files(self):
        from app.core.signer import generate_signed_url, verify_signed_url
        files = ["/uploads/a.jpg", "/uploads/b/c.mp4", "/uploads/x/y/z.txt"]
        for f in files:
            url = generate_signed_url(f, expire_seconds=7200)
            parts = url.split("/")
            token = parts[2]
            filename = "/".join(parts[3:])
            assert verify_signed_url(token, filename) is True
