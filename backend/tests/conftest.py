"""
Pytest fixtures
"""
import pytest


@pytest.fixture
def sample_product_info():
    return {
        "id": 1,
        "name": "防晒喷雾",
        "category": "美妆",
        "features": ["轻薄不油腻", "防水防汗", "SPF50+"],
    }
