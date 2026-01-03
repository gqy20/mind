# AI 主动结束对话功能设计

## 设计原则

1. **简单可靠**：只检测显式标记，0 误判
2. **利用 LLM**：让 AI 自己判断何时结束，不用规则去猜
3. **可选确认**：提供用户确认机制，避免意外结束
4. **易于集成**：最小化对现有代码的修改

## 核心组件

### 1. ConversationEndConfig（配置类）

```python
@dataclass
class ConversationEndConfig:
    """对话结束检测配置"""
    # 是否启用检测
    enable_detection: bool = True

    # 显式结束标记
    end_marker: str = "<!-- END -->"

    # 是否需要用户确认
    require_confirmation: bool = True

    # 检测后是否自动结束（False 时仅提示用户）
    auto_end: bool = False
```

### 2. EndDetectionResult（检测结果）

```python
@dataclass
class EndDetectionResult:
    """结束检测结果"""
    detected: bool
    method: Literal["marker"]  # 只支持显式标记
    reason: str = "检测到显式结束标记"
```

### 3. EndProposal（结束提议）

```python
@dataclass
class EndProposal:
    """结束提议

    当检测到结束时创建此提议，
    用于用户确认或自动执行。
    """
    agent_name: str
    response_text: str  # 完整响应（包含标记）
    response_clean: str  # 清理后的响应（移除标记）
    confirmed: bool = False

    def confirm(self) -> None:
        """用户确认结束"""
        self.confirmed = True
```

### 4. ConversationEndDetector（检测器）

```python
class ConversationEndDetector:
    """对话结束检测器

    只检测显式标记，不做语义猜测。
    充分利用 LLM 的判断能力。
    """

    def detect(self, response: str) -> EndDetectionResult:
        """检测响应中是否包含结束标记

        Args:
            response: AI 的完整响应

        Returns:
            检测结果
        """
        if self.config.end_marker in response:
            return EndDetectionResult(detected=True)
        return EndDetectionResult(detected=False)

    def clean_response(self, response: str) -> str:
        """清理响应（移除结束标记）用于显示"""
        return response.replace(self.config.end_marker, "").strip()
```

## Prompt 指令设计

在两个智能体的 system prompt 中添加：

```
## 对话结束

当满足以下条件时，你可以在响应末尾输出 <!-- END --> 来建议结束对话：

1. 双方已充分交换观点，无明显分歧
2. 讨论已达成共识或结论
3. 没有更多需要补充的内容

注意：只有在真正认为对话应该结束时才使用此标记。
```

## 与 ConversationManager 集成

### 检测流程

```python
async def _turn(self) -> None:
    """执行一轮对话"""
    # ... 现有逻辑 ...

    # 检测结束信号
    if self.end_detector:
        result = self.end_detector.detect(response)
        if result.detected:
            # 创建结束提议
            proposal = EndProposal(
                agent_name=agent_name,
                response_text=response,
                response_clean=self.end_detector.clean_response(response)
            )

            # 处理结束
            if self.config.require_confirmation:
                # 需要用户确认
                self._handle_end_proposal(proposal)
            else:
                # 自动结束
                await self._end_conversation(proposal)
```

### 确认机制

```python
def _handle_end_proposal(self, proposal: EndProposal) -> None:
    """处理结束提议（需要用户确认）"""
    print(f"\n💡 {proposal.agent_name} 建议结束对话")
    print(f"最后发言：{proposal.response_clean}")
    print("\n按 Enter 确认结束，输入其他内容继续...")

    # 等待用户输入
    user_input = input("> ").strip()

    if not user_input:  # 用户直接按 Enter
        proposal.confirm()
        asyncio.create_task(self._end_conversation(proposal))
    else:
        # 用户想继续，添加到消息历史
        self.messages.append({
            "role": "user",
            "content": user_input
        })
```

## TDD 实现计划

### 🔴 阶段 1：测试用例

1. **测试配置类**
   - 默认值
   - 自定义标记
   - 禁用检测

2. **测试检测器**
   - 检测显式标记
   - 清理响应
   - 未检测到标记

3. **测试结束提议**
   - 创建提议
   - 确认机制

4. **测试集成**
   - 完整流程

### 🟢 阶段 2：实现代码

1. 实现 `ConversationEndConfig`
2. 实现 `EndDetectionResult`
3. 实现 `EndProposal`
4. 实现 `ConversationEndDetector`

### ♻️ 阶段 3：集成重构

1. 修改 `ConversationManager` 添加检测器
2. 更新 `cli.py` 的 prompt
3. 添加确认机制

## 与旧方案对比

| 特性 | 旧方案（语义检测） | 新方案（显式标记） |
|------|------------------|------------------|
| 实现复杂度 | 高（10+ 正则模式） | 低（字符串包含） |
| 误判率 | 中（语义模糊） | 0（只有显式标记） |
| 维护成本 | 高（需维护模式） | 低（无需维护） |
| LLM 能力利用 | 否（传统 NLP） | 是（AI 判断） |
| 可靠性 | 中 | 高 |
| 扩展性 | 低 | 高 |

## 文件结构

```
src/mind/
├── conversation/
│   └── ending_detector.py      # 结束检测模块（已迁移）
├── conversation.py              # 对话管理器（manager.py，添加集成）
└── cli.py                      # CLI 入口（更新 prompt）

tests/unit/
├── test_conversation_ending.py         # 单元测试（已保留）
├── test_conversation_ending_migration.py # 迁移验证测试
└── conversation/
    └── test_ending_detector.py         # 结束检测器测试
```

## 实施步骤

1. **第一步**：删除旧实现，重写测试（🔴 红）
2. **第二步**：实现新的检测器（🟢 绿）
3. **第三步**：更新 prompt 指令（🟢 绿）
4. **第四步**：集成到 ConversationManager（♻️ 重构）
