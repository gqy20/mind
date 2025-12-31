"""pytest 的配置和 fixture。"""

import pytest


@pytest.fixture(autouse=True)
def set_test_api_key(monkeypatch):
    """为所有测试设置模拟的 API key 环境变量"""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-api-key-for-testing")


@pytest.fixture
def sample_data():
    """提供测试用的示例数据。"""
    return {"name": "测试用户", "age": 30, "email": "test@example.com"}


@pytest.fixture
def sample_numbers():
    """提供测试用的示例数字列表。"""
    return [1, 2, 3, 4, 5]
