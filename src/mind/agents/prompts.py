"""提示词增强功能

提供提示词构建和增强功能。
"""

from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


def get_time_aware_prompt() -> str:
    """生成时间感知的提示词

    Returns:
        包含当前时间和时间感知指令的提示词
    """
    now = datetime.now()
    current_year = now.year
    current_date = now.strftime("%Y年%m月%d日")

    return f"""
## 当前时间

**当前时间**: {current_date}

在进行网络搜索时，请特别注意信息的**时效性**：

1. **优先关注最新资料**: 涉及时间敏感的话题（如技术版本、统计数据、
   最新进展）时，请优先关注 {current_year} 年和 {current_year - 1} 年的资料
2. **验证发布时间**: 当需要最新数据时，请注意确认信息发布时间，
   避免引用已过时的技术规范或统计数据
3. **经典资料仍可引用**: 对于基础理论、历史背景、经典研究等不随
   时间变化的内容，早期资料同样有价值，可以正常引用

**重要**: 请根据话题的性质判断时效性要求，技术/数据类话题需要关注
最新资料，而理论/历史类话题的经典资料仍有重要价值。
"""


class PromptBuilder:
    """提示词构建器"""

    def __init__(self, base_prompt: str):
        """初始化提示词构建器

        Args:
            base_prompt: 基础提示词
        """
        self.base_prompt = base_prompt

    def build(self, has_tools: bool = False, tool_agent=None) -> str:
        """构建最终提示词

        Args:
            has_tools: 是否有工具
            tool_agent: 可选的工具智能体

        Returns:
            构建后的提示词
        """
        prompt = self.base_prompt

        # 检查是否已包含工具说明（避免重复添加）
        if has_tools and not self._has_tool_instructions(prompt):
            prompt += self._get_tool_instructions(tool_agent)

        # 添加时间感知信息
        prompt += get_time_aware_prompt()

        return prompt

    def _has_tool_instructions(self, prompt: str) -> bool:
        """检查提示词是否已包含工具说明

        Args:
            prompt: 提示词

        Returns:
            是否已包含工具说明
        """
        tool_keywords = ["工具使用", "## 工具", "工具功能", "可用工具"]
        return any(keyword in prompt for keyword in tool_keywords)

    def _get_tool_instructions(self, tool_agent) -> str:
        """生成工具使用说明

        Args:
            tool_agent: 可选的工具智能体

        Returns:
            工具使用说明文本
        """
        parts = ["\n\n## 工具使用\n"]

        # 搜索工具（所有智能体都有）
        parts.append("""### 网络搜索工具

你可以使用 search_web 工具搜索网络信息，获取最新数据、事实、定义等。

**双语搜索策略**（重要）：
- 当讨论学术概念、技术术语时，请同时搜索中文和英文关键词
- 例如：讨论"表观遗传学"时，可以搜索 "表观遗传学 epigenetics" 或分别搜索
- 例如：讨论"机器学习"时，可以搜索 "机器学习 machine learning"
- 这样可以获得更全面、更权威的信息

""")

        # 代码库分析工具（仅当有 tool_agent 时）
        if tool_agent is not None:
            parts.append("""### 代码库分析工具

你配备了代码库分析工具，可以：
- 分析代码库结构和内容
- 读取特定文件的内容
- 搜索代码中的关键词

当需要分析代码时，直接使用相应的工具即可。
""")

        parts.append("""
**重要提示**：
- 直接使用工具即可，无需在文字中描述工具调用
- 不要写"让我搜索..."、"我调用工具..."之类的描述
- 工具结果会自动返回，你可以基于结果继续讨论
""")

        return "".join(parts)
