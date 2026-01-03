"""
模块重命名验证测试

验证 prompts.py 重命名为 config.py 和 prompt_builder.py 后，
所有导入仍能正常工作。
"""

import pytest

# 测试新的导入路径是否可用


def test_config_module_can_be_imported():
    """测试：config 模块可以从 mind 导入"""
    # Arrange & Act
    from mind.config import (
        AgentConfig,
        SearchConfig,
        SettingsConfig,
        get_default_config_path,
    )

    # Assert
    assert AgentConfig is not None
    assert SettingsConfig is not None
    assert SearchConfig is not None
    assert get_default_config_path is not None


def test_prompt_builder_module_can_be_imported():
    """测试：prompt_builder 模块可以从 mind.agents 导入"""
    # Arrange & Act
    from mind.agents.prompt_builder import PromptBuilder, get_time_aware_prompt

    # Assert
    assert PromptBuilder is not None
    assert get_time_aware_prompt is not None


def test_prompt_builder_builds_correctly():
    """测试：PromptBuilder.build() 方法正常工作"""
    # Arrange
    from mind.agents.prompt_builder import PromptBuilder

    builder = PromptBuilder("基础提示词")

    # Act
    result = builder.build(has_tools=False)

    # Assert
    assert "基础提示词" in result
    assert "当前时间" in result  # get_time_aware_prompt 被调用


def test_prompt_builder_with_tools():
    """测试：PromptBuilder.build() 添加工具说明"""
    # Arrange
    from mind.agents.prompt_builder import PromptBuilder

    builder = PromptBuilder("基础提示词")

    # Act
    result = builder.build(has_tools=True, tool_agent=None)

    # Assert
    assert "基础提示词" in result
    assert "工具使用" in result
    assert "网络搜索工具" in result


def test_time_aware_prompt_contains_current_year():
    """测试：时间感知提示词包含当前年份"""
    # Arrange
    from datetime import datetime

    from mind.agents.prompt_builder import get_time_aware_prompt

    current_year = datetime.now().year

    # Act
    prompt = get_time_aware_prompt()

    # Assert
    assert str(current_year) in prompt
    assert "当前时间" in prompt


def test_old_import_paths_no_longer_work():
    """测试：旧的导入路径应该失败"""
    # Arrange & Act & Assert
    with pytest.raises(ImportError):
        from mind.prompts import AgentConfig  # noqa: F401


def test_old_agents_prompts_import_no_longer_works():
    """测试：agents.prompts 的旧导入应该失败"""
    # Arrange & Act & Assert
    with pytest.raises(ImportError):
        from mind.agents.prompts import PromptBuilder  # noqa: F401


# 测试实际使用场景


def test_agent_module_uses_new_imports():
    """测试：agent 模块能使用新的导入路径"""
    # Arrange & Act
    from mind.agents.agent import Agent

    # Assert - Agent 类能正常导入
    assert Agent is not None


def test_cli_module_uses_new_imports():
    """测试：cli 模块能使用新的导入路径"""
    # Arrange & Act
    from mind.cli import parse_args

    # Assert - parse_args 函数能正常导入
    assert parse_args is not None


def test_response_module_uses_new_imports():
    """测试：response 模块能使用新的导入路径"""
    # Arrange & Act
    from mind.agents.response import ResponseHandler

    # Assert - ResponseHandler 类能正常导入
    assert ResponseHandler is not None


def test_summarizer_module_uses_new_imports():
    """测试：summarizer 模块能使用新的导入路径"""
    # Arrange & Act
    from mind.agents import SummarizerAgent

    # Assert - SummarizerAgent 类能正常导入
    assert SummarizerAgent is not None
