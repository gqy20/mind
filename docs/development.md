# 开发指南

> **代码即真相，文档跟随代码**
> 本文档从代码分析生成，最后更新：2026-01-03

## 1. 环境设置

### 1.1 前置要求

- **Python**: 3.13+
- **包管理器**: [uv](https://github.com/astral-sh/uv)（极速包管理器）
- **API Key**: ANTHROPIC_API_KEY 环境变量

### 1.2 安装

```bash
# 克隆项目
git clone https://github.com/gqy20/mind.git
cd mind

# 安装依赖
make install
# 或
uv pip install -e ".[dev]"
```

### 1.3 配置

```bash
# 设置 API Key
export ANTHROPIC_API_KEY="your-key-here"

# 可选：设置 API 基础 URL
export ANTHROPIC_BASE_URL="https://api.anthropic.com"

# 可选：指定模型
export ANTHROPIC_MODEL="claude-sonnet-4-5-20250929"
```

## 2. 常用命令

### 2.1 运行

```bash
# 启动对话
mind
# 或
uv run mind
uv run python -m mind.cli

# 交互命令
/quit 或 /exit    # 退出对话
/clear            # 重置对话
Enter             # 随时打断并输入消息
```

### 2.2 代码检查

```bash
# 代码检查
make check
ruff check .
ruff check --fix .

# 格式化
make format
ruff format .

# 类型检查
make type
uv run mypy src/mind/
```

### 2.3 测试

```bash
# 运行测试
make test
pytest

# 运行单个测试文件
pytest tests/unit/test_agent.py

# 运行单个测试
pytest -k "test_respond_interrupt"

# 测试覆盖率
make test-cov
pytest --cov=src/mind --cov-report=term-missing
```

### 2.4 完整检查

```bash
# 代码 + 类型 + 测试
make all
```

### 2.5 清理

```bash
# 清理缓存
make clean
```

## 3. 代码规范

### 3.1 命名约定

| 类型 | 约定 | 示例 |
|------|------|------|
| **模块** | 小写+下划线 | `agent.py`, `search_handler.py` |
| **类** | 大驼峰 | `Agent`, `ResponseHandler`, `FlowController` |
| **函数/方法** | 小写+下划线 | `respond()`, `should_trigger_search()` |
| **常量** | 大写+下划线 | `MAX_TOKENS`, `DEFAULT_MODEL` |
| **私有成员** | 前缀下划线 | `_client`, `_trim_messages()` |

**特殊后缀**：
- `*Handler`：处理器类（InteractionHandler, SearchHandler, EndingHandler）
- `*Config`：配置类（AgentConfig, SettingsConfig）
- `*Manager`：管理器类（ConversationManager, MemoryManager, SDKToolManager）

### 3.2 类型注解

```python
from typing import Any
from anthropic.types import MessageParam

def respond(
    self,
    messages: list[MessageParam],
    interrupt: asyncio.Event,
) -> str:
    """生成响应

    Args:
        messages: 对话消息历史
        interrupt: 中断标志

    Returns:
        响应文本
    """
    ...
```

### 3.3 文档字符串

**Google 风格中文文档**：

```python
def analyze_context(
    self,
    messages: list[MessageParam],
    question: str,
) -> str:
    """分析对话上下文回答问题

    Args:
        messages: 对话消息历史
        question: 需要回答的问题

    Returns:
        分析结果文本
    """
    ...
```

### 3.4 提交规范

```bash
feat: 新功能
fix: 修复 bug
docs: 文档更新
refactor: 重构
test: 测试
chore: 构建/工具链
```

## 4. 测试策略

### 4.1 测试文件结构

镜像源码目录结构：

```
tests/
├── unit/
│   ├── agents/
│   │   ├── test_agent.py
│   │   ├── test_client.py
│   │   ├── test_response.py
│   │   └── ...
│   ├── conversation/
│   │   ├── test_flow.py
│   │   ├── test_interaction.py
│   │   └── ...
│   ├── display/
│   │   ├── test_citations.py
│   │   └── test_progress.py
│   └── tools/
│       ├── test_search_tool.py
│       └── ...
└── conftest.py
```

### 4.2 AAA 模式

```python
async def test_agent_respond():
    # Arrange（准备）
    agent = Agent(name="Test", system_prompt="You are helpful", model="model")
    messages = [{"role": "user", "content": "Hello"}]

    # Act（执行）
    response = await agent.respond(messages, asyncio.Event())

    # Assert（断言）
    assert response is not None
    assert len(response) > 0
```

### 4.3 Mock 规则

**仅隔离外部依赖**：

```python
from unittest.mock import AsyncMock, patch

async def test_agent_respond_with_mock():
    with patch("mind.agents.client.AsyncAnthropic") as mock_client:
        mock_client.return_value.messages.create = AsyncMock(
            return_value=MockStream()
        )
        agent = Agent(name="Test", ...)
        response = await agent.respond(messages, asyncio.Event())
        assert response is not None
```

### 4.4 迁移验证测试

当进行模块重构时，添加迁移验证测试：

```python
# test_summarizer_migration.py
async def test_summarizer_backward_compatible():
    """验证 SummarizerAgent 的向后兼容导入"""
    from mind.agents import SummarizerAgent
    assert SummarizerAgent is not None
```

## 5. 模块组织原则

### 5.1 模块分离

```
src/mind/
├── agents/              # 智能体模块（核心实现）
├── conversation/        # 对话处理模块（处理器模式）
├── display/             # UI 显示模块
├── tools/               # 工具扩展模块
└── 顶层模块             # 配置加载、日志等
```

### 5.2 延迟初始化

```python
# ConversationManager.flow_controller 使用延迟初始化
class ConversationManager:
    def __init__(self, ...):
        self._flow_controller: FlowController | None = None

    @property
    def flow_controller(self) -> FlowController:
        if self._flow_controller is None:
            self._flow_controller = FlowController(...)
        return self._flow_controller
```

### 5.3 延迟导入

```python
# agents/__init__.py
def __getattr__(name: str):
    if name == "SummarizerAgent":
        from mind.agents.summarizer import SummarizerAgent
        return SummarizerAgent
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
```

## 6. 配置管理

### 6.1 配置文件 (`prompts.yaml`)

```yaml
agents:
  supporter:
    name: "支持者"
    system_prompt: |
      你是一个支持者...

  challenger:
    name: "挑战者"
    system_prompt: |
      你是一个挑战者...

settings:
  search:
    max_results: 5
    history_limit: 100

  documents:
    max_documents: 20
    ttl: 3600

  conversation:
    turn_interval: 1.0
    max_turns: 100

  tools:
    tool_interval: 5
    enable_tools: true
    enable_search: true
```

### 6.2 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `ANTHROPIC_API_KEY` | Anthropic API 密钥（必需） | - |
| `ANTHROPIC_BASE_URL` | API 基础 URL | - |
| `ANTHROPIC_MODEL` | 使用的模型 | claude-sonnet-4-5-20250929 |
| `MIND_USE_SDK_TOOLS` | 是否使用 SDK 工具管理器 | false |
| `MIND_ENABLE_MCP` | 是否启用 MCP | true |

## 7. 调试技巧

### 7.1 日志

```python
from mind.logger import logger

logger.debug("调试信息")
logger.info("普通信息")
logger.warning("警告信息")
logger.error("错误信息")
```

### 7.2 进度显示

```python
from mind.display import ProgressDisplay

progress = ProgressDisplay()
progress.start("智能体名称")
progress.update("正在思考...")
progress.stop()
```

### 7.3 引用显示

```python
from mind.display import display_citations

citations = [{"text": "...", "source": "..."}]
display_citations(citations)
```

## 8. Pre-commit 钩子

项目使用 pre-commit 进行代码质量检查：

```bash
# 安装钩子
pre-commit install

# 手动运行
pre-commit run --all-files
```

**检查项**：
- Ruff lint + format
- MyPy 类型检查
- 通用检查（trailing whitespace、yaml/json/toml 语法等）

## 9. GitHub Actions

### 9.1 CI 工作流 (`.github/workflows/ci.yml`)

- **触发条件**：push/PR 到 main/develop 分支
- **检查步骤**：
  - 安装 uv 和依赖
  - ruff check（代码检查）
  - ruff format check（格式检查）
  - mypy 类型检查
  - pytest + 覆盖率
  - 上传到 Codecov

### 9.2 自动生成主题 (`.github/workflows/auto-generate-topic.yml`)

- **触发条件**：北京时间晚上 11 点到早上 6 点，每小时运行
- **功能**：使用 Anthropic API 生成对话主题并自动创建 Issue

### 9.3 Issue 触发对话 (`.github/workflows/issue-chat.yml`)

- **触发条件**：手动触发或由 auto-generate-topic 触发
- **功能**：根据 Issue 内容自动运行对话

## 10. 自定义命令

项目在 `.claude/commands/` 目录下提供了自定义命令：

### `/gh` - GitHub CLI 助手

提供 GitHub CLI (gh) 的场景化指导

### `/tdd` - 测试驱动开发助手

遵循 TDD 红-绿-重构循环：
- **红**：编写失败的测试 → `git commit -m "test: ..."`
- **绿**：编写最少代码使测试通过 → `git commit -m "feat: ..."`
- **重构**：在测试保护下优化代码 → `git commit -m "refactor: ..."`
