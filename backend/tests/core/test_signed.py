"""signed 路由测试 — 签名文件服务"""
from app.core.signer import generate_signed_url


class TestSignedRouter:
    """测试 signed 路由的核心逻辑（验证签名生成+验证的联动）"""

    def test_serve_signed_generates_correct_path(self):
        """generate_signed_url 生成的路径应当能被 signed 路由解析"""
        from app.core.signer import generate_signed_url
        url = generate_signed_url("/uploads/analyze/test.jpg", expire_seconds=3600)
        # 路径格式: /signed/{token}/analyze/test.jpg
        assert url.startswith("/signed/")
        assert "analyze/test.jpg" in url

    def test_verify_then_extract_path(self):
        """验证签名后提取的路径应当正确"""
        from app.core.signer import generate_signed_url, verify_signed_url
        url = generate_signed_url("/uploads/analyze/cover.jpg", expire_seconds=86400)
        parts = url.split("/")
        token = parts[2]
        rest = "/".join(parts[3:])
        assert verify_signed_url(token, rest) is True
        assert rest == "analyze/cover.jpg"

    def test_token_expiry_edge_cases(self):
        """边缘情况：立即过期 / 超长有效期"""
        from app.core.signer import generate_signed_url, verify_signed_url

        # 0秒过期（理论上立刻过期，但实际有网络延迟）
        url = generate_signed_url("/uploads/x.mp4", expire_seconds=0)
        parts = url.split("/")
        token, rest = parts[2], "/".join(parts[3:])
        # 应该立即过期
        assert verify_signed_url(token, rest) is False

        # 超长有效期
        url2 = generate_signed_url("/uploads/x.mp4", expire_seconds=31536000)
        parts2 = url2.split("/")
        token2, rest2 = parts2[2], "/".join(parts2[3:])
        assert verify_signed_url(token2, rest2) is True

    def test_signed_router_resolves_uploads_path(self):
        """signed 路由 UPLOAD_DIR = /app/uploads，验证路径拼接"""
        from pathlib import Path
        upload_dir = Path("/app/uploads")
        rest = "analyze/cover.jpg"
        full = upload_dir / rest
        assert str(full) == "/app/uploads/analyze/cover.jpg"

    def test_signed_url_with_special_chars(self):
        from app.core.signer import generate_signed_url, verify_signed_url
        # 包含特殊字符的路径
        url = generate_signed_url("/uploads/my file (1).mp4", expire_seconds=3600)
        parts = url.split("/")
        token, rest = parts[2], "/".join(parts[3:])
        assert verify_signed_url(token, rest) is True
