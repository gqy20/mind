"""自动生成对话话题

通过 Anthropic API 生成一个有趣、有深度的对话话题。
"""

import os
import random
import sys
from datetime import datetime
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

    # 获取当前时间信息
    now = datetime.now()
    weekdays = ["一", "二", "三", "四", "五", "六", "日"]
    time_context = (
        f"当前时间：{now.strftime('%Y年%m月%d日 %H:%M')}，星期{weekdays[now.weekday()]}"
    )

    # 随机选择一个领域作为重点
    domains = [
        "前沿科技（AI、量子计算、生物技术）",
        "哲学思辨（意识、存在、伦理）",
        "社会现象（文化变迁、人类行为）",
        "科学发现（物理、天文、认知科学）",
        "艺术人文（创作、审美、文化传承）",
        "未来趋势（技术发展、人类演变）",
    ]
    focus_domain = random.choice(domains)

    prompt = f"""{time_context}

请生成一个有趣、有深度的对话话题，供两个 AI 智能体（支持者和挑战者）进行探讨。

**本次请重点关注以下领域**：{focus_domain}

要求：
1. 话题应该具有开放性和讨论性，能够从不同角度展开
2. 话题应该具有一定的现实意义或哲学思辨价值
3. 避免过于敏感或争议性过强的话题（如政治、宗教极端观点）
4. 避免生成与以下主题过于相似的话题：
   - 记忆编辑与自我认同
   - 永生与死亡的意义
   - 意识上传与数字生命
   - 痛苦与幸福的辩证关系
5. 尝试探索更新颖的角度，例如：
   - 技术伦理的具体场景（算法偏见、AI 创作版权）
   - 科学发现对日常生活的渗透
   - 文化现象背后的深层逻辑
   - 认知科学的新发现

请直接输出话题标题，不要任何解释或前缀。

示例格式：
- "人工智能生成的艺术品是否应该享有版权保护？"
- "量子计算的现实应用是否会重构当前的网络安全体系？"
- "在注意力经济时代，深度思考能力是否正在退化？"
"""

    response = await client.messages.create(
        model=os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5-20250929"),
        max_tokens=200,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.9,  # 高温度增加多样性
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
