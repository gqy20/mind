"""测试工具函数"""

from mind.agents.utils import KNOWN_AGENTS, _clean_agent_name_prefix


def test_known_agents_constant():
    """测试 KNOWN_AGENTS 常量存在"""

    assert isinstance(KNOWN_AGENTS, list)
    assert "支持者" in KNOWN_AGENTS
    assert "挑战者" in KNOWN_AGENTS


def test_clean_agent_name_prefix_with_brackets():
    """测试清理带方括号的角色名前缀"""
    result = _clean_agent_name_prefix("[支持者]: 你好，世界")

    assert result == "你好，世界"


def test_clean_agent_name_prefix_without_brackets():
    """测试清理不带方括号的角色名前缀"""
    result = _clean_agent_name_prefix("支持者: 你好")

    assert result == "你好"


def test_clean_agent_name_prefix_challenger():
    """测试清理挑战者前缀"""
    result = _clean_agent_name_prefix("[挑战者]: 我同意")

    assert result == "我同意"


def test_clean_agent_name_prefix_unknown_format():
    """测试清理未知格式的角色名前缀"""
    result = _clean_agent_name_prefix("[某角色]: 测试文本")

    assert result == "测试文本"


def test_clean_agent_name_prefix_no_prefix():
    """测试没有前缀的文本保持不变"""
    result = _clean_agent_name_prefix("普通文本")

    assert result == "普通文本"


def test_clean_agent_name_prefix_preserves_citations():
    """测试不清理引用标记如 [1]"""
    result = _clean_agent_name_prefix("[1] 这是引用")

    assert result == "[1] 这是引用"
