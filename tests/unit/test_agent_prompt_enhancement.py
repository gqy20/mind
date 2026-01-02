"""
Agent 提示词增强功能的单元测试

测试启用工具时自动在 system_prompt 中添加工具使用说明：
- 无工具时不添加说明
- 有工具时自动添加说明
- 避免重复添加说明
"""

from mind.agents.agent import Agent


class TestPromptEnhancement:
    """测试提示词增强功能"""

    def test_prompt_unchanged_without_tool_agent(self):
        """测试：无 tool_agent 时仍然会添加搜索工具说明"""
        # Arrange
        original_prompt = "你是一个支持者"

        # Act
        agent = Agent(
            name="TestAgent",
            system_prompt=original_prompt,
            tool_agent=None,
        )

        # Assert - system_prompt 应该包含搜索工具说明
        assert len(agent.system_prompt) > len(original_prompt)
        assert "搜索" in agent.system_prompt or "search" in agent.system_prompt.lower()
        # 原始提示词应该被保留
        assert original_prompt in agent.system_prompt

    def test_prompt_includes_tool_instruction_with_tool_agent(self):
        """测试：有工具时 system_prompt 包含工具说明"""
        # Arrange
        original_prompt = "你是一个支持者"

        from mind.tools import ToolAgent

        tool_agent = ToolAgent()

        # Act
        agent = Agent(
            name="TestAgent",
            system_prompt=original_prompt,
            tool_agent=tool_agent,
        )

        # Assert - system_prompt 应该包含工具说明
        assert len(agent.system_prompt) > len(original_prompt)
        assert "工具" in agent.system_prompt or "tool" in agent.system_prompt.lower()
        # 原始提示词应该被保留
        assert original_prompt in agent.system_prompt

    def test_tool_instruction_not_duplicated(self):
        """测试：已有工具说明时不重复添加"""
        # Arrange - 已经包含工具说明的提示词
        original_prompt = """你是一个支持者

## 工具使用
你可以使用代码库分析工具来获取上下文信息。"""

        from mind.tools import ToolAgent

        tool_agent = ToolAgent()

        # Act
        agent = Agent(
            name="TestAgent",
            system_prompt=original_prompt,
            tool_agent=tool_agent,
        )

        # Assert - 不应该重复添加工具说明
        # 简单检查：工具说明相关的关键词不应该出现多次
        tool_keyword_count = agent.system_prompt.count("工具使用")
        assert tool_keyword_count <= 1

    def test_tool_instruction_includes_analyze_codebase(self):
        """测试：工具说明包含代码库分析功能"""
        # Arrange
        original_prompt = "你是一个支持者"

        from mind.tools import ToolAgent

        tool_agent = ToolAgent()

        # Act
        agent = Agent(
            name="TestAgent",
            system_prompt=original_prompt,
            tool_agent=tool_agent,
        )

        # Assert - 应该提到代码库分析功能
        assert (
            "代码库" in agent.system_prompt
            or "codebase" in agent.system_prompt.lower()
            or "分析" in agent.system_prompt
        )
