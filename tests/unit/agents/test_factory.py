"""测试 AgentFactory 工厂模式"""

import os
from unittest.mock import patch

import pytest


class TestAgentFactory:
    """测试 AgentFactory 类"""

    def test_factory_create_conversation_agent(self):
        """测试工厂创建对话智能体（supporter/challenger）"""
        from mind.agents.factory import AgentFactory
        from mind.config import AgentConfig, SettingsConfig

        # Arrange - 准备配置
        settings = SettingsConfig()
        factory = AgentFactory(settings)
        config = AgentConfig(
            name="测试助手",
            system_prompt="你是一个测试助手",
        )

        # Act - 创建智能体
        agent = factory.create_conversation_agent(config)

        # Assert - 验证结果
        assert agent is not None
        assert agent.name == "测试助手"
        assert agent.system_prompt is not None
        assert "你是一个测试助手" in agent.system_prompt

    def test_factory_create_all_conversation_agents(self):
        """测试工厂批量创建对话智能体"""
        from mind.agents.factory import AgentFactory
        from mind.config import AgentConfig, SettingsConfig

        # Arrange - 准备配置
        settings = SettingsConfig()
        factory = AgentFactory(settings)
        configs = {
            "supporter": AgentConfig(
                name="支持者",
                system_prompt="赞同对方观点",
            ),
            "challenger": AgentConfig(
                name="挑战者",
                system_prompt="质疑对方观点",
            ),
        }

        # Act - 批量创建
        agents = factory.create_conversation_agents(configs)

        # Assert - 验证结果
        assert len(agents) == 2
        assert "supporter" in agents
        assert "challenger" in agents
        assert agents["supporter"].name == "支持者"
        assert agents["challenger"].name == "挑战者"

    def test_factory_create_summarizer_agent(self):
        """测试工厂创建总结智能体"""
        from mind.agents.factory import AgentFactory
        from mind.config import AgentConfig, SettingsConfig

        # Arrange - 准备配置
        settings = SettingsConfig()
        factory = AgentFactory(settings)
        config = AgentConfig(
            name="总结助手",
            system_prompt="你是一个总结助手",
        )

        # Act - 创建总结智能体
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            summarizer = factory.create_summarizer(config)

        # Assert - 验证结果
        assert summarizer is not None
        assert summarizer.name == "总结助手"
        assert summarizer.system_prompt == "你是一个总结助手"

    def test_factory_create_all_agents(self):
        """测试工厂创建所有类型智能体"""
        from mind.agents.factory import AgentFactory
        from mind.config import AgentConfig, SettingsConfig

        # Arrange - 准备配置
        settings = SettingsConfig()
        factory = AgentFactory(settings)
        configs = {
            "supporter": AgentConfig(name="支持者", system_prompt="赞同"),
            "challenger": AgentConfig(name="挑战者", system_prompt="质疑"),
            "summarizer": AgentConfig(name="总结助手", system_prompt="总结"),
        }

        # Act - 创建所有智能体
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            agents = factory.create_all(configs)

        # Assert - 验证结果
        assert len(agents) == 3
        assert "supporter" in agents
        assert "challenger" in agents
        assert "summarizer" in agents
        # 验证类型
        from mind.agents.agent import Agent
        from mind.agents.summarizer import SummarizerAgent

        assert isinstance(agents["supporter"], Agent)
        assert isinstance(agents["challenger"], Agent)
        assert isinstance(agents["summarizer"], SummarizerAgent)

    def test_factory_create_with_missing_agent_id(self):
        """测试工厂处理缺失的智能体 ID"""
        from mind.agents.factory import AgentFactory
        from mind.config import AgentConfig, SettingsConfig

        # Arrange - 准备配置
        settings = SettingsConfig()
        factory = AgentFactory(settings)
        configs = {
            "supporter": AgentConfig(name="支持者", system_prompt="赞同"),
        }

        # Act & Assert - 应该抛出 ValueError
        with pytest.raises(ValueError, match="智能体配置不存在"):
            factory.create_all(configs, agent_ids=["supporter", "missing"])

    def test_factory_create_all_with_filter(self):
        """测试工厂只创建指定的智能体"""
        from mind.agents.factory import AgentFactory
        from mind.config import AgentConfig, SettingsConfig

        # Arrange - 准备配置
        settings = SettingsConfig()
        factory = AgentFactory(settings)
        configs = {
            "supporter": AgentConfig(name="支持者", system_prompt="赞同"),
            "challenger": AgentConfig(name="挑战者", system_prompt="质疑"),
            "summarizer": AgentConfig(name="总结助手", system_prompt="总结"),
        }

        # Act - 只创建指定的智能体（使用 create_all + agent_ids 参数）
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            agents = factory.create_all(configs, agent_ids=["supporter", "challenger"])

        # Assert - 验证结果
        assert len(agents) == 2
        assert "supporter" in agents
        assert "challenger" in agents
        assert "summarizer" not in agents
