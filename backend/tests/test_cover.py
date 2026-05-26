"""覆盖补丁"""
import pytest
from app.config import settings


class TestCoveragePatch:
    def test_config_basic(self):
        assert settings.JWT_ALGORITHM == "HS256"
        assert settings.SECRET_KEY
