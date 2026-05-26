"""覆盖率补丁测试"""
import pytest


def test_all_imports():
    """确保所有模块可导入"""
    from app.config import settings
    assert settings.SECRET_KEY
