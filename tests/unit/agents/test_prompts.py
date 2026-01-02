"""测试提示词增强功能"""

from datetime import datetime

from mind.agents.prompts import (
    PromptBuilder,
    get_time_aware_prompt,
)


def test_prompt_builder_without_tools():
    """测试没有工具时的提示词构建"""
    builder = PromptBuilder(base_prompt="你是一个助手")
    result = builder.build(has_tools=False, tool_agent=None)

    assert "你是一个助手" in result
    # 不应该包含工具说明
    assert "工具使用" not in result


def test_prompt_builder_with_tools_no_agent():
    """测试有工具但没有 tool_agent 时的提示词"""
    builder = PromptBuilder(base_prompt="你是一个助手")
    result = builder.build(has_tools=True, tool_agent=None)

    # 应该包含搜索工具说明
    assert "网络搜索工具" in result
    assert "search_web" in result
    # 不应该包含代码库分析工具
    assert "代码库分析工具" not in result


def test_prompt_builder_with_tool_agent():
    """测试有 tool_agent 时的提示词"""
    from unittest.mock import MagicMock

    mock_agent = MagicMock()
    builder = PromptBuilder(base_prompt="你是一个助手")
    result = builder.build(has_tools=True, tool_agent=mock_agent)

    # 应该包含两种工具说明
    assert "网络搜索工具" in result
    assert "代码库分析工具" in result


def test_prompt_builder_no_duplicates():
    """测试不重复添加工具说明"""
    builder = PromptBuilder(base_prompt="你是一个助手\n\n## 工具使用\n已有工具说明")
    result = builder.build(has_tools=True, tool_agent=None)

    # 应该只保留原有说明，不重复添加
    assert result.count("工具使用") == 1


def test_get_time_aware_prompt():
    """测试生成时间感知提示词"""
    result = get_time_aware_prompt()
    current_year = datetime.now().year

    # 应该包含当前年份
    assert str(current_year) in result
    # 应该包含时间相关关键词
    assert "当前时间" in result or "时效性" in result


def test_prompt_builder_includes_time_aware():
    """测试提示词构建器包含时间感知信息"""
    builder = PromptBuilder(base_prompt="你是一个助手")
    result = builder.build(has_tools=True, tool_agent=None)

    # 应该包含当前年份
    current_year = datetime.now().year
    assert str(current_year) in result
