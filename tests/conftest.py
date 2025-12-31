"""pytest 的配置和 fixture。"""

import pytest


@pytest.fixture
def sample_data():
    """提供测试用的示例数据。"""
    return {"name": "测试用户", "age": 30, "email": "test@example.com"}


@pytest.fixture
def sample_numbers():
    """提供测试用的示例数字列表。"""
    return [1, 2, 3, 4, 5]
