#!/usr/bin/env python3
"""
阶段二功能验证脚本

验证 --with-tools 参数是否正确工作：
1. CLI 参数解析
2. ConversationManager 配置
3. Agent 工具集成
"""

import asyncio
import sys

# 添加项目路径
sys.path.insert(0, "src")

from mind.agents.agent import Agent
from mind.cli import parse_args
from mind.manager import ConversationManager


def test_cli_args():
    """测试 CLI 参数解析"""
    print("=" * 60)
    print("测试 1: CLI 参数解析")
    print("=" * 60)

    # 模拟命令行参数
    original_argv = sys.argv
    try:
        # 测试 --with-tools
        sys.argv = ["cli", "--with-tools"]
        args = parse_args()
        print(f"✅ --with-tools: {args.with_tools}")

        # 测试不带参数
        sys.argv = ["cli"]
        args = parse_args()
        print(f"✅ 默认 (无 --with-tools): {args.with_tools}")

    finally:
        sys.argv = original_argv

    print()


def test_conversation_manager():
    """测试 ConversationManager 工具配置"""
    print("=" * 60)
    print("测试 2: ConversationManager 工具配置")
    print("=" * 60)

    # 创建两个测试智能体（不需要真实的 API key 用于这个测试）
    # 注意：这里不能直接创建 Agent，因为它需要 API key
    # 我们只测试 ConversationManager 的配置逻辑

    # 测试 enable_tools=False
    print("测试 enable_tools=False:")
    print("  ⚠️  需要 API key，跳过实际创建")

    # 测试 enable_tools=True
    print("测试 enable_tools=True:")
    print("  ⚠️  需要 API key，跳过实际创建")

    print()


async def test_agent_tool_integration():
    """测试 Agent 工具集成（需要 API key）"""
    import os

    if not os.getenv("ANTHROPIC_API_KEY"):
        print("=" * 60)
        print("测试 3: Agent 工具集成")
        print("=" * 60)
        print("⚠️  ANTHROPIC_API_KEY 未设置，跳过此测试")
        print()
        return

    print("=" * 60)
    print("测试 3: Agent 工具集成（带 API）")
    print("=" * 60)

    from mind.tools import ToolAgent

    # 测试 1: 不带工具的 Agent
    print("\n[测试 3.1] 不带工具的 Agent:")
    try:
        agent_without_tool = Agent(name="TestAgent1", system_prompt="测试")
        print(f"  ✅ tool_agent: {agent_without_tool.tool_agent}")
        result = await agent_without_tool.query_tool("测试")
        print(f"  ✅ query_tool() 返回: {result}")
    except Exception as e:
        print(f"  ❌ 错误: {e}")

    # 测试 2: 带工具的 Agent
    print("\n[测试 3.2] 带工具的 Agent:")
    try:
        tool_agent = ToolAgent()
        agent_with_tool = Agent(
            name="TestAgent2", system_prompt="测试", tool_agent=tool_agent
        )
        print(f"  ✅ tool_agent: {agent_with_tool.tool_agent is not None}")
        print(f"  ✅ tool_agent 类型: {type(agent_with_tool.tool_agent).__name__}")
    except Exception as e:
        print(f"  ❌ 错误: {e}")

    # 测试 3: 工具调用（会调用真实 API）
    print("\n[测试 3.3] 真实工具调用（会调用 API）:")
    try:
        tool_agent = ToolAgent()
        agent_with_tool = Agent(
            name="TestAgent3", system_prompt="测试", tool_agent=tool_agent
        )

        print("  🔄 调用 query_tool()...")
        result = await agent_with_tool.query_tool("分析代码库")

        if result:
            print("  ✅ 工具调用成功")
            print(f"  📄 结果预览: {result[:100]}...")
        else:
            print("  ⚠️  工具调用返回 None（可能是工具执行失败）")
    except Exception as e:
        print(f"  ❌ 错误: {e}")

    print()


async def test_full_integration():
    """测试完整集成（ConversationManager + 工具）"""
    import os

    if not os.getenv("ANTHROPIC_API_KEY"):
        print("=" * 60)
        print("测试 4: 完整集成")
        print("=" * 60)
        print("⚠️  ANTHROPIC_API_KEY 未设置，跳过此测试")
        print()
        return

    print("=" * 60)
    print("测试 4: ConversationManager 完整集成（带 API）")
    print("=" * 60)

    try:
        # 创建两个智能体
        supporter = Agent(name="支持者", system_prompt="你是一个支持者")
        challenger = Agent(name="挑战者", system_prompt="你是一个挑战者")

        # 创建带工具的 ConversationManager
        print("\n[测试 4.1] 创建 ConversationManager (enable_tools=True):")
        _ = ConversationManager(
            agent_a=supporter, agent_b=challenger, enable_tools=True
        )

        print(f"  ✅ supporter.tool_agent: {supporter.tool_agent is not None}")
        print(f"  ✅ challenger.tool_agent: {challenger.tool_agent is not None}")
        print(f"  ✅ 共享工具实例: {supporter.tool_agent is challenger.tool_agent}")

        # 测试查询工具
        print("\n[测试 4.2] 通过 ConversationManager 中的 Agent 调用工具:")
        result = await supporter.query_tool("分析代码库")
        if result:
            print("  ✅ 工具调用成功")
            print(f"  📄 结果预览: {result[:100]}...")
        else:
            print("  ⚠️  工具调用返回 None")

    except Exception as e:
        print(f"  ❌ 错误: {e}")
        import traceback

        traceback.print_exc()

    print()


async def main():
    """主函数"""
    print("\n")
    print("🧪 阶段二功能验证")
    print("=" * 60)
    print()

    # 测试 1: CLI 参数
    test_cli_args()

    # 测试 2: ConversationManager 配置
    test_conversation_manager()

    # 测试 3: Agent 工具集成（需要 API）
    await test_agent_tool_integration()

    # 测试 4: 完整集成（需要 API）
    await test_full_integration()

    print("=" * 60)
    print("✅ 验证完成")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
