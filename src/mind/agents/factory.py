"""智能体工厂 - 负责创建智能体实例

工厂模式封装智能体创建逻辑，使 CLI 和其他入口都能复用。
"""

from typing import TYPE_CHECKING

from mind.logger import get_logger

if TYPE_CHECKING:
    from mind.agents.agent import Agent
    from mind.agents.summarizer import SummarizerAgent
    from mind.config import AgentConfig, SettingsConfig

logger = get_logger("mind.agents.factory")


class AgentFactory:
    """智能体工厂

    封装智能体创建逻辑，使 CLI 和其他入口都能复用。
    """

    def __init__(self, settings: "SettingsConfig"):
        """初始化工厂

        Args:
            settings: 系统设置配置
        """
        self.settings = settings
        logger.info("智能体工厂初始化完成")

    def create_conversation_agent(self, config: "AgentConfig") -> "Agent":
        """从配置创建对话智能体（supporter/challenger）

        Args:
            config: 智能体配置

        Returns:
            智能体实例
        """
        from mind.agents.agent import Agent

        agent = Agent(
            name=config.name,
            system_prompt=config.system_prompt,
            settings=self.settings,
        )
        logger.info(f"对话智能体创建完成: {agent.name}")
        return agent

    def create_conversation_agents(
        self, configs: dict[str, "AgentConfig"]
    ) -> dict[str, "Agent | SummarizerAgent"]:
        """批量创建对话智能体

        Args:
            configs: 智能体配置字典

        Returns:
            智能体实例字典
        """
        from mind.agents.agent import Agent

        agents: dict[str, Agent | SummarizerAgent] = {}
        for agent_id, config in configs.items():
            agents[agent_id] = Agent(
                name=config.name,
                system_prompt=config.system_prompt,
                settings=self.settings,
            )
            logger.info(f"对话智能体创建完成: {agents[agent_id].name}")

        return agents

    def create_summarizer(self, config: "AgentConfig") -> "SummarizerAgent":
        """创建总结智能体

        Args:
            config: 智能体配置

        Returns:
            SummarizerAgent 实例
        """
        from mind.agents.summarizer import SummarizerAgent

        summarizer = SummarizerAgent(
            name=config.name,
            system_prompt=config.system_prompt,
        )
        logger.info(f"总结智能体创建完成: {summarizer.name}")
        return summarizer

    def create_all(
        self,
        configs: dict[str, "AgentConfig"],
        agent_ids: list[str] | None = None,
    ) -> dict[str, "Agent | SummarizerAgent"]:
        """创建所有类型智能体

        Args:
            configs: 智能体配置字典
            agent_ids: 要创建的智能体 ID 列表，None 表示全部

        Returns:
            智能体实例字典（可能包含 Agent 和 SummarizerAgent）

        Raises:
            ValueError: 智能体配置不存在
        """
        if agent_ids is None:
            agent_ids = list(configs.keys())

        agents: dict[str, Agent | SummarizerAgent] = {}
        for agent_id in agent_ids:
            if agent_id not in configs:
                raise ValueError(f"智能体配置不存在: {agent_id}")

            config = configs[agent_id]

            # 根据智能体类型选择创建方法
            if agent_id == "summarizer":
                agents[agent_id] = self.create_summarizer(config)
            else:
                agents[agent_id] = self.create_conversation_agent(config)

        return agents
