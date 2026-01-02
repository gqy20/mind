# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

**Mind** 是一个多智能体对话系统，通过两个 AI 智能体（支持者 vs 挑战者）的协作交流来激发创新思维。

- **Python 版本**: 3.13+
- **包管理**: uv（极速包管理器）
- **项目结构**: src layout
- **代码规范**: ruff（检查 + 格式化）+ mypy（类型检查）
- **测试框架**: pytest + pytest-asyncio
- **API**: Anthropic Claude (AsyncAnthropic，流式响应)

## 常用命令

```bash
# 安装依赖
make install
uv pip install -e ".[dev]"

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

# 测试
make test
pytest
pytest tests/unit/test_agent.py           # 运行单个测试文件
pytest -k "test_respond_interrupt"        # 运行单个测试

# 测试覆盖率
make test-cov
pytest --cov=src/mind --cov-report=term-missing

# 运行程序
make run
uv run mind
uv run python -m mind.cli

# 完整检查
make all  # 等价于 make check + make type + make test

# 清理缓存
make clean
```

## 代码规范

1. **语言**: 所有注释、文档字符串使用中文，函数和类使用英文命名
2. **类型注解**: 必需（通过 mypy 检查）
3. **文档字符串**: Google 风格中文文档
4. **提交规范**: `feat/fix/docs/refactor/test/chore:`

## 核心架构

项目采用模块化架构，核心组件分为三个层次：

```
src/mind/
├── agent.py              # Agent 类 - 对外统一接口（向后兼容）
├── conversation.py       # ConversationManager - 对话管理器
├── cli.py               # CLI 入口和配置
│
├── agents/              # 智能体模块（核心实现）
│   ├── agent.py         # Agent 类 - 对外统一接口
│   ├── client.py        # AnthropicClient - API 客户端封装
│   ├── response.py      # ResponseHandler - 流式响应和工具调用
│   ├── documents.py     # DocumentPool - Citations 文档池管理
│   ├── prompts.py       # PromptBuilder - 提示词构建
│   ├── analysis.py      # ConversationAnalyzer - 对话分析
│   ├── citations.py     # 引用显示工具
│   └── utils.py         # 工具函数
│
├── tools/               # 工具扩展模块
│   ├── search_tool.py   # 网络搜索工具（duckduckgo）
│   ├── tool_agent.py    # ToolAgent - 工具智能体（代码分析等）
│   ├── sdk_tool_manager.py  # SDK 工具管理器（MCP 集成）
│   └── mcp/             # MCP 服务器实现
│
├── prompts.yaml         # 智能体提示词和系统配置
├── prompts.py           # 配置加载器（Pydantic 模型）
├── search_history.py    # SearchHistory - 搜索历史持久化
├── memory.py            # MemoryManager - token 管理和上下文清理
├── conversation_ending.py  # ConversationEndDetector - 对话结束检测
├── summarizer.py        # SummarizerAgent - 对话总结智能体
└── logger.py            # 日志配置（loguru）
```

### 1. 智能体模块 (`agents/`)

这是核心对话引擎，采用组件分离设计：

**Agent 类** (`agents/agent.py`)：对外统一接口
- `__init__(name, system_prompt, model, settings)`: 初始化
- `respond(messages, interrupt)`: 生成响应（委托给 ResponseHandler）
- `query_tool(question, messages)`: 分析对话上下文（委托给 ConversationAnalyzer）
- `add_document(doc)`: 添加文档到池（委托给 DocumentPool）

**AnthropicClient** (`agents/client.py`)：API 客户端封装
- 封装 AsyncAnthropic 客户端创建
- 支持 ANTHROPIC_BASE_URL 环境变量

**ResponseHandler** (`agents/response.py`)：流式响应和工具调用
- `respond(messages, system, interrupt)`: 主响应循环
- `_execute_tool_search(tool_call, ...)`: 执行搜索工具
- `_continue_response(...)`: 基于工具结果继续生成
- `_handle_api_status_error(e)`: API 错误处理（401/429/5xx）

**关键机制**：
- 处理 `content_block_delta` 事件（新格式）和 `text` 事件（旧格式）
- 检测 `tool_use` 类型的 content_block，收集工具调用
- 支持 Citations API（捕获 `citations_delta` 事件）

### 2. ConversationManager 类 (`conversation.py`)

协调两个智能体的对话循环。

**状态字段**：
- `messages`: 对话历史（Anthropic 格式）
- `interrupt`: asyncio.Event，用于中断
- `current`: 0=A, 1=B（轮次切换）
- `turn`: 当前轮次计数
- `memory`: MemoryManager（token 管理）
- `search_history`: SearchHistory（搜索历史）
- `enable_tools/enable_search`: 功能开关
- `end_detector`: ConversationEndDetector（对话结束检测）

**核心方法**：
- `start(topic)`: 交互式对话循环
- `run_auto(topic, max_turns)`: 非交互式自动运行
- `_turn()`: 执行一轮对话
- `_input_mode()`: 用户输入模式
- `_handle_user_input(user_input)`: 处理用户输入
- `save_conversation()`: 保存对话到 JSON

**关键机制 - 非阻塞输入检测**：
```python
def _is_input_ready():
    if not sys.stdin.isatty():
        return False
    return select.select([sys.stdin], [], [], 0)[0]
```

**智能搜索触发**（优先级）：
1. AI 主动请求（使用 `[搜索: 关键词]` 语法）
2. 固定间隔兜底（`search_interval`）

### 3. CLI 入口 (`cli.py`)

- `check_config()`: 检查 ANTHROPIC_API_KEY
- `parse_args()`: 解析命令行参数
- `main()`: 加载配置、创建智能体、启动对话管理器

**命令行参数**：
- `topic`: 对话主题
- `--max-turns N`: 限制轮数
- `--non-interactive`: 非交互式模式
- `--no-tools/--no-search`: 禁用功能
- `--tool-interval N`: 覆盖工具调用间隔
- `--test-tools`: 测试工具扩展功能

### 4. 配置系统 (`prompts.yaml` + `prompts.py`)

**配置结构**：
```yaml
agents:
  supporter/challenger:
    name: "智能体名称"
    system_prompt: |
      多行提示词...

settings:
  search: { max_results, history_limit }
  documents: { max_documents, ttl }
  conversation: { turn_interval, max_turns }
  tools: { tool_interval, enable_tools, enable_search }
```

**Pydantic 模型**：
- `AgentConfig`: 智能体配置
- `SettingsConfig`: 系统设置
- `SearchConfig/DocumentsConfig/ConversationConfig/ToolsConfig`: 子配置

### 5. 工具扩展模块 (`tools/`)

**搜索工具** (`search_tool.py`)：
- `search_web(query, max_results)`: duckduckgo 搜索
- `_search_sync(query, max_results)`: 同步包装器

**ToolAgent** (`tool_agent.py`)：
- `analyze_codebase(path)`: 代码库分析
- `read_file_analysis(path, question)`: 文件分析

**SDKToolManager** (`sdk_tool_manager.py`)：
- MCP 服务器集成（knowledge/code-analysis/web-search）
- Hook 系统支持
- 工具权限控制

### 6. 记忆和上下文管理

**MemoryManager** (`memory.py`)：
- Token 计数和状态监控（green/yellow/red）
- `trim_messages(messages)`: 清理历史，保留重要消息
- 最大清理次数限制（`max_trim_count`）

**DocumentPool** (`agents/documents.py`)：
- Citations API 文档池
- `merge_into_messages(messages)`: 合并文档到消息
- `from_search_history(search_entries)`: 搜索历史转文档

**SearchHistory** (`search_history.py`)：
- 搜索历史持久化（JSON）
- `save_search(query, results)`: 保存搜索
- `get_latest(limit)`: 获取最新记录

### 7. 对话结束检测 (`conversation_ending.py`)

**ConversationEndDetector**：
- `detect(response, current_turn)`: 检测 `<!-- END -->` 标记
- `clean_response(response)`: 清理标记用于显示/保存

**结束条件**：
- 前 20 轮禁止结束
- 需要用户确认（`require_confirmation`）

### 8. 对话总结 (`summarizer.py`)

**SummarizerAgent**：
- `summarize(messages, topic, interrupt)`: 生成对话总结
- 在达到最大清理次数时自动调用

## 环境变量

- `ANTHROPIC_API_KEY`: Anthropic API 密钥（必需）
- `ANTHROPIC_BASE_URL`: API 基础 URL（可选）
- `ANTHROPIC_MODEL`: 使用的模型（默认: claude-sonnet-4-5-20250929）

## 交互流程

```
用户启动 CLI
    ↓
加载 prompts.yaml 配置
    ↓
创建两个智能体（支持者 + 挑战者）
    ↓
创建 ConversationManager（初始化 search_history/tool_agent）
    ↓
用户输入主题
    ↓
主循环:
  ├─ 检查用户输入（非阻塞 select.select）
  │   └─ 有输入 → 进入 _input_mode()
  ├─ 工具调用检查（tool_interval 兜底）
  ├─ 智能搜索触发（AI 请求或间隔）
  ├─ 执行一轮对话（A 或 B）
  │   ├─ 打印智能体名称
  │   ├─ 流式响应（ResponseHandler.respond）
  │   │   ├─ 处理 content_block_delta（text_delta/citations_delta）
  │   │   ├─ 检测 tool_use 并执行
  │   │   └─ 检查 interrupt 标志
  │   ├─ 记录响应到历史
  │   ├─ 检测对话结束标记（<!-- END -->）
  │   └─ Token 状态检查和清理
  └─ 等待轮次间隔

用户输入模式:
  ├─ 设置中断标志（interrupt.set()）
  ├─ 显示输入提示
  ├─ 获取用户输入
  ├─ 处理命令或添加消息
  └─ 清除中断标志（interrupt.clear()）
```

## 测试策略

- 使用 `pytest` + `pytest-asyncio`
- 测试文件镜像源码目录结构（`tests/unit/` 对应 `src/mind/`）
- 使用 `unittest.mock.AsyncMock` 隔离 Anthropic API 调用
- 测试覆盖：初始化、流式响应、中断机制、工具调用、搜索集成

**测试文件示例**：
- `tests/unit/agents/test_*.py`: 智能体模块测试
- `tests/unit/test_conversation*.py`: 对话管理器测试
- `tests/unit/tools/test_*.py`: 工具模块测试

## Pre-commit 钩子

项目使用 pre-commit 进行代码质量检查：
- Ruff lint + format
- MyPy 类型检查
- 通用检查（trailing whitespace、yaml/json/toml 语法等）

安装：`pre-commit install`
