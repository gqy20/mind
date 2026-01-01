"""自动生成对话话题

通过 Anthropic API 生成一个有趣、有深度的对话话题。
"""

import os
import sys
from pathlib import Path

from anthropic import AsyncAnthropic

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "src"))


async def generate_topic() -> str:
    """生成对话话题

    Returns:
        生成的对话话题
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY 环境变量未设置")

    base_url = os.getenv("ANTHROPIC_BASE_URL")
    client = AsyncAnthropic(api_key=api_key, base_url=base_url)

    prompt = """请生成一个有趣、有深度的对话话题，供两个 AI 智能体
    （支持者和挑战者）进行探讨。

要求：
1. 话题应该具有开放性和讨论性，能够从不同角度展开
2. 话题应该具有一定的现实意义或哲学思辨价值
3. 避免过于敏感或争议性过强的话题（如政治、宗教极端观点）
4. 话题领域可以包括：科技、哲学、社会现象、科学发现、伦理道德、艺术文化等
5. 每次生成不同的话题，避免重复

请直接输出话题标题，不要任何解释或前缀。

示例格式：
- "人工智能是否应该拥有法律人格？"
- "表观遗传学能否改变我们对遗传的认知？"
- "在信息爆炸时代，深度阅读是否还有必要？"
"""

    response = await client.messages.create(
        model=os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5-20250929"),
        max_tokens=200,
        messages=[{"role": "user", "content": prompt}],
    )

    topic = response.content[0].text.strip()

    # 移除可能的引号
    topic = topic.strip('"\'""')

    return topic


async def main():
    """主函数"""
    try:
        topic = await generate_topic()
        # 保存到文件供后续步骤使用
        output_file = Path("/tmp/generated_topic.txt")
        output_file.write_text(topic, encoding="utf-8")
        print(f"Generated topic: {topic}")
    except Exception as e:
        print(f"Error generating topic: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
