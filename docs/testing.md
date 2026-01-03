# 测试策略

> **代码即真相，文档跟随代码**
> 本文档从代码分析生成，最后更新：2026-01-03

## 1. 测试框架

- **测试框架**: pytest + pytest-asyncio
- **覆盖率工具**: pytest-cov
- **Mock 工具**: unittest.mock.AsyncMock

## 2. 测试文件结构

镜像源码目录结构：

```
tests/
├── unit/
│   ├── agents/
│   │   ├── test_agent.py              # Agent 类测试
│   │   ├── test_client.py             # AnthropicClient 测试
│   │   ├── test_response.py           # ResponseHandler 测试
│   │   ├── test_documents.py          # DocumentPool 测试
│   │   ├── test_prompts.py            # PromptBuilder 测试
│   │   ├── test_conversation_analyzer.py  # ConversationAnalyzer 测试
│   │   ├── test_citations.py          # Citations 功能测试
│   │   └── test_summarizer.py         # SummarizerAgent 测试
│   ├── conversation/
│   │   ├── test_flow.py               # FlowController 测试
│   │   ├── test_interaction.py        # InteractionHandler 测试
│   │   ├── test_search_handler.py     # SearchHandler 测试
│   │   ├── test_ending.py             # EndingHandler 测试
│   │   ├── test_ending_detector.py    # ConversationEndDetector 测试
│   │   └── test_memory.py             # MemoryManager 测试
│   ├── display/
│   │   ├── test_citations.py          # display_citations 测试
│   │   └── test_progress.py           # ProgressDisplay 测试
│   ├── tools/
│   │   ├── test_search_tool.py        # search_web 测试
│   │   ├── test_search_history.py     # SearchHistory 测试
│   │   ├── test_tool_agent.py         # ToolAgent 测试
│   │   ├── test_sdk_tool_manager.py   # SDKToolManager 测试
│   │   └── test_tool_adapter.py       # ToolAdapter 测试
│   ├── test_cli.py                    # CLI 测试
│   ├── test_prompts.py                # 配置加载测试
│   ├── test_conversation.py           # 对话管理器测试
│   └── test_conversation_*.py         # 集成测试
└── conftest.py                        # pytest 配置
```

## 3. 测试编写规范

### 3.1 AAA 模式

```python
import pytest
from unittest.mock import AsyncMock, patch

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

### 3.2 Mock 规则

**仅隔离外部依赖**：

```python
async def test_agent_respond_with_mock():
    with patch("mind.agents.client.AsyncAnthropic") as mock_client:
        mock_client.return_value.messages.create = AsyncMock(
            return_value=MockStream()
        )
        agent = Agent(name="Test", ...)
        response = await agent.respond(messages, asyncio.Event())
        assert response is not None
```

### 3.3 异步测试

```python
import pytest

@pytest.mark.asyncio
async def test_async_function():
    result = await some_async_function()
    assert result is not None
```

### 3.4 Fixture 使用

```python
@pytest.fixture
def sample_messages():
    return [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there!"}
    ]

@pytest.mark.asyncio
async def test_with_fixture(sample_messages):
    assert len(sample_messages) == 2
```

## 4. 测试覆盖场景

### 4.1 智能体模块 (`agents/`)

| 测试文件 | 覆盖场景 |
|----------|----------|
| `test_agent.py` | 初始化、respond、query_tool、add_document |
| `test_client.py` | 客户端创建、base_url 配置 |
| `test_response.py` | 流式响应、工具调用、中断机制、API 错误处理 |
| `test_documents.py` | 文档添加、合并到消息、从搜索历史创建 |
| `test_prompts.py` | 提示词构建、时间感知提示 |
| `test_conversation_analyzer.py` | 上下文分析 |
| `test_summarizer.py` | 对话总结 |

### 4.2 对话处理模块 (`conversation/`)

| 测试文件 | 覆盖场景 |
|----------|----------|
| `test_flow.py` | 主循环、轮次执行、响应清理 |
| `test_interaction.py` | 非阻塞输入检测、用户命令处理 |
| `test_search_handler.py` | 搜索触发、关键词提取、AI 请求检测 |
| `test_ending.py` | 结束提议处理 |
| `test_ending_detector.py` | 结束标记检测、响应清理 |
| `test_memory.py` | Token 计数、状态检查、消息清理 |

### 4.3 工具扩展模块 (`tools/`)

| 测试文件 | 覆盖场景 |
|----------|----------|
| `test_search_tool.py` | 网络搜索、结果格式化 |
| `test_search_history.py` | 搜索保存、历史查询 |
| `test_tool_agent.py` | 代码库分析、文件分析 |
| `test_sdk_tool_manager.py` | SDK 初始化、工具调用、MCP 集成 |
| `test_tool_adapter.py` | 统一接口、降级逻辑 |

## 5. 迁移验证测试

当进行模块重构时，添加迁移验证测试：

```python
# test_summarizer_migration.py
async def test_summarizer_backward_compatible():
    """验证 SummarizerAgent 的向后兼容导入"""
    from mind.agents import SummarizerAgent
    assert SummarizerAgent is not None

async def test_summarizer_new_import():
    """验证新的导入路径"""
    from mind.agents.summarizer import SummarizerAgent
    assert SummarizerAgent is not None
```

## 6. 运行测试

```bash
# 运行所有测试
pytest

# 运行单个测试文件
pytest tests/unit/test_agent.py

# 运行单个测试
pytest -k "test_respond_interrupt"

# 运行测试并显示覆盖率
pytest --cov=src/mind --cov-report=term-missing

# 运行测试并生成 HTML 覆盖率报告
pytest --cov=src/mind --cov-report=html
```

## 7. 覆盖率要求

- **核心逻辑**: ≥80%
- **工具模块**: ≥70%
- **总体目标**: ≥75%

## 8. 测试最佳实践

### 8.1 单一职责

每个测试只验证一个行为：

```python
# 好的做法
async def test_agent_respond_returns_text():
    response = await agent.respond(messages, interrupt)
    assert isinstance(response, str)

async def test_agent_respond_includes_content():
    response = await agent.respond(messages, interrupt)
    assert len(response) > 0

# 避免这样做
async def test_agent_respond():
    response = await agent.respond(messages, interrupt)
    assert isinstance(response, str)
    assert len(response) > 0
    assert "hello" in response.lower()
```

### 8.2 描述性测试名称

```python
# 好的做法
async def test_search_handler_returns_query_when_bracket_syntax_used():
    ...

async def test_memory_manager_trims_messages_when_token_limit_exceeded():
    ...

# 避免这样做
async def test_search_1():
    ...

async def test_memory_trim():
    ...
```

### 8.3 隔离测试

每个测试应该独立运行，不依赖其他测试：

```python
@pytest.mark.asyncio
async def test_agent_state_isolated():
    agent1 = Agent(name="Agent1", ...)
    agent2 = Agent(name="Agent2", ...)
    # agent1 和 agent2 的状态互不影响
```

### 8.4 使用参数化测试

```python
@pytest.mark.parametrize("input,expected", [
    ("[搜索: 测试]", "测试"),
    ("[搜索:keyword]", "keyword"),
    ("[搜索:  multiple  words  ]", "multiple  words"),
])
async def test_extract_search_query(input, expected):
    result = extract_search_from_response(input)
    assert result == expected
```

## 9. Mock 最佳实践

### 9.1 只 Mock 外部依赖

```python
# 好的做法：Mock Anthropic API
async def test_agent_respond():
    with patch("mind.agents.client.AsyncAnthropic") as mock_client:
        mock_client.return_value.messages.create = AsyncMock(...)
        agent = Agent(...)
        response = await agent.respond(...)
        assert response is not None

# 避免：Mock 内部方法
async def test_agent_respond_bad():
    agent = Agent(...)
    agent._internal_method = AsyncMock(return_value="mocked")  # 不要这样做
    response = await agent.respond(...)
```

### 9.2 使用 AsyncMock

```python
from unittest.mock import AsyncMock

async def test_async_method():
    mock_client = AsyncMock()
    mock_client.some_method.return_value = "result"
    result = await mock_client.some_method()
    assert result == "result"
```

## 10. 调试测试

```bash
# 显示打印输出
pytest -s

# 在第一个失败时停止
pytest -x

# 显示本地变量
pytest -l

# 进入调试器
pytest --pdb
```
