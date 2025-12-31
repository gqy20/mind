"""
Mind - AI agents that collaborate to spark innovation

使用方式:
    python -m mind.cli

命令:
    /quit, /exit - 退出对话
    /clear - 重置对话历史
"""

import asyncio
import os

from mind.agent import DEFAULT_MODEL, Agent
from mind.conversation import ConversationManager
from mind.logger import get_logger

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


async def main():
    """主函数 - 配置并启动双智能体对话"""

    logger.info("=" * 20 + " 程序启动 " + "=" * 20)

    # 检查配置
    if not check_config():
        return

    # 配置两个智能体
    supporter = Agent(
        name="支持者",
        system_prompt="""你是一个观点支持者。你的任务是：
1. 赞同并补充对方的观点
2. 提供有力的论据支持
3. 保持建设性和积极性
4. 回复简洁，不超过 100 字""",
    )

    challenger = Agent(
        name="挑战者",
        system_prompt="""你是一个观点挑战者。你的任务是：
1. 质疑对方的观点
2. 提出反例或不同视角
3. 保持批判性思维但有礼貌
4. 回复简洁，不超过 100 字""",
    )

    logger.info("双智能体创建完成: 支持者 vs 挑战者")

    # 创建对话管理器
    manager = ConversationManager(
        agent_a=supporter,
        agent_b=challenger,
        turn_interval=1.0,
    )

    # 获取主题并开始
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

    await manager.start(topic)
    logger.info("程序正常退出")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("用户通过 Ctrl+C 中断程序")
        print("\n\n👋 对话已结束")
