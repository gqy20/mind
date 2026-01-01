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

from mind.agent import DEFAULT_MODEL, Agent
from mind.conversation import ConversationManager
from mind.logger import get_logger
from mind.prompts import get_default_config_path, load_agent_configs

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
        result = await agent.analyze_codebase(".")

        if result["success"]:
            print(f"✅ 成功\n{result['summary']}")
        else:
            print(f"❌ 失败: {result['error']}")

        # 测试 2: 文件读取
        print("\n[测试 2] 文件读取...")
        result = await agent.read_file_analysis(
            "src/mind/agent.py", "这个文件的主要功能是什么？"
        )

        if result["success"]:
            print(f"✅ 成功\n{result['content']}")
        else:
            print(f"❌ 失败: {result['error']}")

        print("\n" + "=" * 60)
        print("测试完成")
        print("=" * 60)
        return

    # 检查配置
    if not check_config():
        return

    # 从配置文件加载提示词
    config_path = str(get_default_config_path())
    agent_configs = load_agent_configs(config_path)

    # 配置两个智能体
    supporter_config = agent_configs["supporter"]
    supporter = Agent(
        name=supporter_config.name,
        system_prompt=supporter_config.system_prompt,
    )

    challenger_config = agent_configs["challenger"]
    challenger = Agent(
        name=challenger_config.name,
        system_prompt=challenger_config.system_prompt,
    )

    logger.info("双智能体创建完成: 支持者 vs 挑战者")

    # 创建对话管理器
    manager = ConversationManager(
        agent_a=supporter,
        agent_b=challenger,
        turn_interval=1.0,
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
        max_turns = args.max_turns or 500
        result = await manager.run_auto(topic, max_turns=max_turns)
        print(result)
        logger.info("程序正常退出")
        return

    # 交互式模式
    await manager.start(topic)
    logger.info("程序正常退出")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("用户通过 Ctrl+C 中断程序")
        print("\n\n👋 对话已结束")
