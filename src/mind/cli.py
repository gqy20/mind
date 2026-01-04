"""
Mind - AI agents that collaborate to spark innovation

使用方式:
    python -m mind.cli                    # 交互式输入主题
    python -m mind.cli "主题内容"         # 直接指定主题
    python -m mind.cli --max-turns 10     # 限制对话轮数

命令:
    /quit, /exit - 退出对话
    /clear - 重置对话历史
"""

import argparse
import asyncio
import os

from dotenv import load_dotenv

from mind.agents.agent import DEFAULT_MODEL, Agent
from mind.config import get_default_config_path, load_all_configs
from mind.logger import get_logger
from mind.manager import ConversationManager

logger = get_logger("mind.cli")


def check_config() -> bool:
    """检查配置是否完整

    Returns:
        bool: 配置是否有效
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")
    base_url = os.getenv("ANTHROPIC_BASE_URL")

    print("📋 配置检查:")
    print(f"   API Key: {'✅ 已设置' if api_key else '❌ 未设置 (ANTHROPIC_API_KEY)'}")
    print(f"   Base URL: {'✅ ' + base_url if base_url else '✅ 使用默认'}")
    print(f"   模型: ✅ {DEFAULT_MODEL}")
    print()

    if not api_key:
        logger.error("ANTHROPIC_API_KEY 未设置")
        print("❌ 错误: 请设置 ANTHROPIC_API_KEY 环境变量")
        print("   示例: export ANTHROPIC_API_KEY='your-key-here'")
        return False

    logger.info(f"配置检查通过: Base URL={base_url or '默认'}, 模型={DEFAULT_MODEL}")
    return True


def parse_args() -> argparse.Namespace:
    """解析命令行参数

    Returns:
        解析后的参数
    """
    parser = argparse.ArgumentParser(
        description="Mind - AI Agents for Innovation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "topic",
        nargs="?",
        help="对话主题（不指定则交互式输入）",
    )
    parser.add_argument(
        "--max-turns",
        type=int,
        default=None,
        help="最大对话轮数（用于非交互式模式）",
    )
    parser.add_argument(
        "--non-interactive",
        action="store_true",
        help="非交互式模式（自动运行对话）",
    )
    parser.add_argument(
        "--test-tools",
        action="store_true",
        help="测试工具扩展功能（阶段一）",
    )
    parser.add_argument(
        "--no-tools",
        action="store_true",
        help="禁用工具扩展能力（默认启用）",
    )
    parser.add_argument(
        "--no-search",
        action="store_true",
        help="禁用网络搜索功能（默认启用）",
    )
    parser.add_argument(
        "--tool-interval",
        type=int,
        default=None,
        help="工具调用间隔（轮数），默认从配置文件读取，0 表示禁用自动调用",
    )
    # 使用 parse_known_args 忽略未知参数（如 pytest 的 -v）
    args, _ = parser.parse_known_args()

    # 如果 topic 是 .py 文件路径（可能是测试时误解析），则清空
    if args.topic and (
        args.topic.endswith(".py") or "/" in args.topic or "\\" in args.topic
    ):
        args.topic = None

    return args


async def main():
    """主函数 - 配置并启动双智能体对话"""
    # 加载 .env 文件中的环境变量
    load_dotenv()

    args = parse_args()

    logger.info("=" * 20 + " 程序启动 " + "=" * 20)

    # 测试工具扩展功能
    if args.test_tools:
        print("=" * 60)
        print("🧪 测试工具扩展功能")
        print("=" * 60)

        from mind.tools import ToolAgent

        # 测试 1: 代码库分析
        print("\n[测试 1] 代码库分析...")
        agent = ToolAgent()
        analyze_result = await agent.analyze_codebase(".")

        if analyze_result["success"]:
            print(f"✅ 成功\n{analyze_result['summary']}")
        else:
            print(f"❌ 失败: {analyze_result['error']}")

        # 测试 2: 文件读取
        print("\n[测试 2] 文件读取...")
        file_result = await agent.read_file_analysis(
            "src/mind/agents/agent.py", "这个文件的主要功能是什么？"
        )

        if file_result["success"]:
            print(f"✅ 成功\n{file_result['content']}")
        else:
            print(f"❌ 失败: {file_result['error']}")

        print("\n" + "=" * 60)
        print("测试完成")
        print("=" * 60)
        return

    # 检查配置
    if not check_config():
        return

    # 从配置文件加载所有配置
    config_path = get_default_config_path()
    agent_configs, settings = load_all_configs(config_path)

    # 命令行参数可以覆盖配置文件
    enable_tools = settings.tools.enable_tools and not args.no_tools
    enable_search = settings.tools.enable_search and not args.no_search
    tool_interval = args.tool_interval or settings.tools.tool_interval
    turn_interval = settings.conversation.turn_interval

    # 使用工厂创建智能体
    from mind.agents import AgentFactory

    factory = AgentFactory(settings)
    agents = factory.create_conversation_agents(
        {
            "supporter": agent_configs["supporter"],
            "challenger": agent_configs["challenger"],
        }
    )

    supporter: Agent = agents["supporter"]  # type: ignore[assignment]
    challenger: Agent = agents["challenger"]  # type: ignore[assignment]

    logger.info("双智能体创建完成: 支持者 vs 挑战者")

    # 创建对话管理器
    manager = ConversationManager(
        agent_a=supporter,
        agent_b=challenger,
        turn_interval=turn_interval,
        enable_tools=enable_tools,
        tool_interval=tool_interval,
        enable_search=enable_search,
    )

    # 获取主题
    topic = args.topic
    if not topic:
        print("=" * 60)
        print("🧠 Mind - AI Agents for Innovation")
        print("=" * 60)
        print("\n命令:")
        print("  /quit 或 /exit - 退出对话")
        print("  /clear - 重置对话")
        print("\n")

        topic = input("请输入对话主题: ").strip()

        if not topic:
            topic = "人工智能是否应该拥有法律人格？"
            print(f"使用默认主题: {topic}")

    logger.info(f"用户选择主题: {topic}")

    print(f"\n{'=' * 60}")
    print(f"🎯 对话主题: {topic}")
    print(f"{'=' * 60}\n")

    # 非交互式模式
    if args.non_interactive or args.max_turns:
        max_turns = args.max_turns or settings.conversation.max_turns
        result = await manager.run_auto(topic, max_turns=max_turns)
        print(result)
        logger.info("程序正常退出")
        return

    # 交互式模式
    await manager.start(topic)
    logger.info("程序正常退出")


def run() -> None:
    """同步入口函数 - 供 uv run 调用"""
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("用户通过 Ctrl+C 中断程序")
        print("\n\n👋 对话已结束")


if __name__ == "__main__":
    run()
