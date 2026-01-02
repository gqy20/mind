"""
Unit tests for Time-Aware Prompt Enhancement

测试时间感知提示词增强功能：
- 当前时间注入到 system prompt
- 验证 prompt 包含时间信息
"""

from datetime import datetime

import pytest

from mind.agents.agent import Agent


class TestTimeAwarePrompt:
    """测试时间感知提示词功能"""

    def test_system_prompt_contains_current_date(self):
        """测试：system prompt 应包含当前日期"""
        # Arrange
        model = "claude-sonnet-4-5-20250929"
        system_prompt = "你是一个对话助手。"

        # Act
        agent = Agent(name="测试助手", system_prompt=system_prompt, model=model)

        # Assert - 获取当前日期
        today = datetime.now()
        expected_patterns = [
            str(today.year),  # 年份
            today.strftime("%Y年%m月"),  # 年月格式
        ]

        # 检查 system_prompt 是否包含时间信息
        for pattern in expected_patterns:
            assert pattern in agent.system_prompt, (
                f"system_prompt 应包含当前日期信息 '{pattern}'"
            )

    def test_system_prompt_contains_time_aware_instruction(self):
        """测试：system prompt 应包含时间感知提示"""
        # Arrange
        model = "claude-sonnet-4-5-20250929"
        system_prompt = "你是一个观点支持者。"

        # Act
        agent = Agent(name="支持者", system_prompt=system_prompt, model=model)

        # Assert - 检查是否有时间感知的关键词
        time_aware_keywords = [
            "当前时间",
            "搜索时请优先关注",
            "时效性",
        ]

        has_time_aware = any(
            keyword in agent.system_prompt for keyword in time_aware_keywords
        )
        assert has_time_aware, "system_prompt 应包含时间感知相关的提示"

    def test_system_prompt_contains_recent_year_preference(self):
        """测试：system prompt 应提示关注最新年份"""
        # Arrange
        model = "claude-sonnet-4-5-20250929"
        system_prompt = "你是一个观点挑战者。"

        # Act
        agent = Agent(name="挑战者", system_prompt=system_prompt, model=model)

        # Assert - 当前是 2026 年，应该提到 2025 或 2026
        current_year = datetime.now().year
        recent_years = [str(current_year), str(current_year - 1)]

        has_recent_year = any(year in agent.system_prompt for year in recent_years)
        assert has_recent_year, f"system_prompt 应提及最近的年份 {recent_years}"

    def test_system_prompt_preserves_original_content(self):
        """测试：system prompt 应保留原始内容"""
        # Arrange
        model = "claude-sonnet-4-5-20250929"
        original_prompt = "你是一个观点支持者。你的任务是与对方进行有建设性的对话。"

        # Act
        agent = Agent(name="支持者", system_prompt=original_prompt, model=model)

        # Assert - 原始内容应该保留
        assert "观点支持者" in agent.system_prompt
        assert "有建设性的对话" in agent.system_prompt

    def test_system_prompt_format_is_correct(self):
        """测试：system prompt 格式应该正确"""
        # Arrange
        model = "claude-sonnet-4-5-20250929"
        system_prompt = "你是一个对话助手。"

        # Act
        agent = Agent(name="助手", system_prompt=system_prompt, model=model)

        # Assert - 检查格式规范
        # 应该有清晰的分段
        assert "**" in agent.system_prompt or "\n\n" in agent.system_prompt

    @pytest.mark.parametrize(
        "original_prompt",
        [
            "简单提示词",
            "你是一个助手。请回答问题。",
            "",
        ],
    )
    def test_time_info_injected_for_various_prompts(self, original_prompt):
        """测试：各种类型的 prompt 都应该注入时间信息"""
        # Arrange
        model = "claude-sonnet-4-5-20250929"

        # Act
        agent = Agent(name="测试", system_prompt=original_prompt, model=model)

        # Assert
        current_year = str(datetime.now().year)
        assert current_year in agent.system_prompt


class TestTimeAwarePromptIntegration:
    """测试时间感知提示词的集成场景"""

    def test_multiple_agents_have_consistent_time_info(self):
        """测试：多个智能体应该有一致的时间信息"""
        # Arrange
        model = "claude-sonnet-4-5-20250929"

        # Act
        agent_a = Agent(name="智能体A", system_prompt="提示词A", model=model)
        agent_b = Agent(name="智能体B", system_prompt="提示词B", model=model)

        # Assert - 两者都应该包含当前年份
        current_year = str(datetime.now().year)
        assert current_year in agent_a.system_prompt
        assert current_year in agent_b.system_prompt
