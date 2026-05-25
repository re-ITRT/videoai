"""核心模块测试 — security / config"""

from app.config import settings


class TestConfig:
    """配置默认值验证"""

    def test_secret_key_exists(self):
        assert len(settings.SECRET_KEY) > 8

    def test_jwt_algorithm(self):
        assert settings.JWT_ALGORITHM == "HS256"

    def test_jwt_expire_minutes(self):
        assert settings.JWT_EXPIRE_MINUTES > 0


class TestSecurity:
    """密码哈希 / JWT（sub 使用字符串）"""

    def test_password_hash_and_verify(self):
        from app.core.security import get_password_hash, verify_password
        pw = "TestPassword123!"
        hashed = get_password_hash(pw)
        assert hashed != pw
        assert verify_password(pw, hashed) is True
        assert verify_password("wrong", hashed) is False

    def test_create_and_decode_access_token(self):
        from app.core.security import create_access_token, decode_access_token
        token = create_access_token(data={"sub": "42"})
        payload = decode_access_token(token)
        assert payload is not None
        assert payload["sub"] == "42"

    def test_create_and_decode_refresh_token(self):
        from app.core.security import create_refresh_token, decode_refresh_token
        token = create_refresh_token(data={"sub": "42"})
        payload = decode_refresh_token(token)
        assert payload is not None
        assert payload["sub"] == "42"

    def test_decode_invalid_token(self):
        from app.core.security import decode_access_token
        assert decode_access_token("invalid-token") is None

    def test_access_token_expires(self):
        from app.core.security import create_access_token, decode_access_token
        from datetime import timedelta
        # 过期 token decode 应返回 None
        import time
        token = create_access_token(
            data={"sub": "42"},
            expires_delta=timedelta(seconds=-1)
        )
        time.sleep(0.1)
        payload = decode_access_token(token)
        assert payload is None

    def test_access_token_tampered(self):
        from app.core.security import create_access_token, decode_access_token
        token = create_access_token(data={"sub": "42"})
        tampered = token[:-5] + "XXXXX"
        assert decode_access_token(tampered) is None
