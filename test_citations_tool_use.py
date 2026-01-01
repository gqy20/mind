"""测试 Citations 和 Tool Use API 是否可以共存

测试场景：
1. Citations + Tool Use 在同一个请求中
2. Tool 返回的结果是否能作为 Citations 文档
3. 模型是否会同时使用工具和引用文档
"""

import asyncio
import os

from anthropic import AsyncAnthropic


async def test_citations_with_tool_use():
    """测试：在同一个请求中同时使用 Citations 和 Tool Use"""

    client = AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    print("=" * 60)
    print("测试 1: Citations + Tool Use 在同一个请求中")
    print("=" * 60)

    try:
        response = await client.messages.create(
            model="claude-opus-4-1-20250805",
            max_tokens=1024,
            messages=[
                {
                    "role": "user",
                    "content": [
                        # Citations 文档
                        {
                            "type": "document",
                            "source": {
                                "type": "text",
                                "media_type": "text/plain",
                                "data": "Python 是由 Guido van Rossum 创建的高级语言。",
                            },
                            "title": "Python 简介",
                            "citations": {"enabled": True},
                        },
                        # 用户问题
                        {
                            "type": "text",
                            "text": "请告诉我 Python 的创建年份，然后搜索最新版本号。",
                        },
                    ],
                }
            ],
            # Tool Use 配置
            tools=[
                {
                    "name": "search_web",
                    "description": "搜索网络信息",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "搜索关键词"}
                        },
                        "required": ["query"],
                    },
                }
            ],
        )

        print("✅ 请求成功！")
        print(f"停止原因: {response.stop_reason}")
        print("\n响应内容:")
        for block in response.content:
            if block.type == "text":
                print(f"  文本: {block.text[:100]}...")
                if hasattr(block, "citations") and block.citations:
                    print(f"  引用: {len(block.citations)} 个")
            elif block.type == "tool_use":
                print(f"  工具调用: {block.name}")
                print(f"  输入: {block.input}")

    except Exception as e:
        print(f"❌ 请求失败: {e}")


async def test_tool_result_as_citation():
    """测试：Tool 返回的结果是否能作为 Citations 文档"""

    print("\n" + "=" * 60)
    print("测试 2: Tool 结果作为 Citations 文档")
    print("=" * 60)

    client = AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    try:
        # 第一轮：调用工具
        response1 = await client.messages.create(
            model="claude-opus-4-1-20250805",
            max_tokens=1024,
            messages=[{"role": "user", "content": "搜索 Python 的最新版本号"}],
            tools=[
                {
                    "name": "search_web",
                    "description": "搜索网络信息",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "搜索关键词"}
                        },
                        "required": ["query"],
                    },
                }
            ],
        )

        # 提取工具调用
        tool_use = next(
            (block for block in response1.content if block.type == "tool_use"), None
        )

        if not tool_use:
            print("❌ 模型没有调用工具")
            return

        print(f"模型调用工具: {tool_use.name}")
        print(f"查询参数: {tool_use.input}")

        # 模拟工具返回搜索结果
        search_result = "根据搜索，Python 3.13.0 是最新稳定版本，发布于 2024 年 10 月。"

        # 第二轮：尝试在 tool_result 中启用 citations
        print("\n尝试在 tool_result 中启用 citations...")

        response2 = await client.messages.create(
            model="claude-opus-4-1-20250805",
            max_tokens=1024,
            messages=[
                {"role": "user", "content": "搜索 Python 的最新版本号"},
                {"role": "assistant", "content": response1.content},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": tool_use.id,
                            # 尝试在 tool_result 中添加 citations
                            "content": [
                                {
                                    "type": "document",
                                    "source": {
                                        "type": "text",
                                        "media_type": "text/plain",
                                        "data": search_result,
                                    },
                                    "citations": {"enabled": True},
                                }
                            ],
                        }
                    ],
                },
            ],
        )

        print("✅ 第二轮请求成功")
        print(f"响应: {response2.content[0].text if response2.content else '无内容'}")

    except Exception as e:
        print(f"❌ 请求失败: {e}")
        if "Citations are not supported" in str(e):
            print("💡 确认：Tool Result 不支持 Citations")


async def test_citations_then_tool_use():
    """测试：先提供 Citations 文档，然后模型决定是否使用工具"""

    print("\n" + "=" * 60)
    print("测试 3: Citations 文档 + 模型自主决定是否使用工具")
    print("=" * 60)

    client = AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    try:
        response = await client.messages.create(
            model="claude-opus-4-1-20250805",
            max_tokens=1024,
            messages=[
                {
                    "role": "user",
                    "content": [
                        # Citations 文档
                        {
                            "type": "document",
                            "source": {
                                "type": "text",
                                "media_type": "text/plain",
                                "data": "Python 3.12 于 2023 年 10 月发布。",
                            },
                            "title": "Python 3.12 发布说明",
                            "citations": {"enabled": True},
                        },
                        {
                            "type": "text",
                            "text": "根据文档告诉我 Python 3.12 的新特性，然后验证。",
                        },
                    ],
                }
            ],
            tools=[
                {
                    "name": "search_web",
                    "description": "搜索网络信息",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "搜索关键词"}
                        },
                        "required": ["query"],
                    },
                }
            ],
        )

        print("✅ 请求成功")
        print(f"停止原因: {response.stop_reason}")

        for block in response.content:
            if block.type == "text":
                print(f"  文本: {block.text[:100]}...")
                if hasattr(block, "citations") and block.citations:
                    print(f"  引用: {len(block.citations)} 个")
            elif block.type == "tool_use":
                print(f"  工具调用: {block.name}")

    except Exception as e:
        print(f"❌ 请求失败: {e}")


async def main():
    """运行所有测试"""
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("❌ 请设置 ANTHROPIC_API_KEY 环境变量")
        return

    await test_citations_with_tool_use()
    await test_tool_result_as_citation()
    await test_citations_then_tool_use()

    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
