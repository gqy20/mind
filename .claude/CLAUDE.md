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
├── manager.py           # ConversationManager - 对话管理器（主入口）
├── cli.py               # CLI 入口和配置
│
├── agents/              # 智能体模块（核心实现）
│   ├── agent.py         # Agent 类 - 对外统一接口
│   ├── client.py        # AnthropicClient - API 客户端封装
│   ├── response.py      # ResponseHandler - 流式响应和工具调用
│   ├── documents.py     # DocumentPool - Citations 文档池管理
│   ├── prompt_builder.py # PromptBuilder - 提示词构建
│   ├── conversation_analyzer.py # ConversationAnalyzer - 对话分析
│   ├── utils.py         # 工具函数
│   └── summarizer.py    # SummarizerAgent - 对话总结智能体
│
├── conversation/        # 对话处理模块（处理器模式）
│   ├── flow.py          # FlowController - 流程控制器（主循环）
│   ├── interaction.py   # InteractionHandler - 用户交互处理
│   ├── search_handler.py # SearchHandler - 搜索逻辑处理
│   ├── ending.py        # EndingHandler - 对话结束处理
│   ├── ending_detector.py # ConversationEndDetector - 结束检测器
│   ├── memory.py        # MemoryManager - token 管理和上下文清理
│   └── progress.py      # ProgressDisplay - 进度显示
│
├── display/             # UI 显示模块
│   ├── citations.py     # 引用显示工具
│   └── progress.py      # 进度显示
│
├── tools/               # 工具扩展模块
│   ├── search_tool.py   # 网络搜索工具（duckduckgo）
│   ├── search_history.py # SearchHistory - 搜索历史持久化
│   ├── tool_agent.py    # ToolAgent - 工具智能体（代码分析等）
│   ├── hooks.py         # ToolHooks - Hook 回调实现
│   └── mcp/             # MCP 服务器配置
│       ├── tools.py     # MCP 工具定义
│       └── servers.py   # MCP 服务器配置
│
├── prompts.yaml         # 智能体提示词和系统配置
├── config.py            # 配置加载器（Pydantic 模型）
└── logger.py            # 日志配置（loguru）
```

### 1. 智能体模块 (`agents/`)

这是核心对话引擎，采用组件分离设计：

**Agent 类** (`agents/agent.py`)：对外统一接口
- `__init__(name, system_prompt, model, settings)`: 初始化
- `respond(messages, interrupt)`: 生成响应（委托给 ResponseHandler）
- `query_tool(question, messages)`: 分析对话上下文（委托给 ConversationAnalyzer）
- `add_document(doc)`: 添加文档到池（委托给 DocumentPool）

**ConversationAnalyzer** (`agents/conversation_analyzer.py`)：对话分析
- `analyze_context(messages, question)`: 分析对话上下文回答问题
- 通过 `agents/__init__.py` 的延迟导入导出

**AnthropicClient** (`agents/client.py`)：API 客户端封装
- 封装 AsyncAnthropic 客户端创建
- 支持 ANTHROPIC_BASE_URL 环境变量

**ResponseHandler** (`agents/response.py`)：流式响应和工具调用
- `respond(messages, system, interrupt)`: 主响应循环
- `_execute_tool_search(tool_call, ...)`: 执行搜索工具（duckduckgo）
- `_continue_response(...)`: 基于工具结果继续生成
- `_handle_api_status_error(e)`: API 错误处理（401/429/5xx）

**关键机制**：
- 处理 `content_block_delta` 事件（新格式）和 `text` 事件（旧格式）
- 检测 `tool_use` 类型的 content_block，收集工具调用
- 支持 Citations API（捕获 `citations_delta` 事件）

**SummarizerAgent** (`agents/summarizer.py`)：对话总结
- `summarize(messages, topic, interrupt)`: 生成对话总结
- 在达到最大清理次数时自动调用
- 通过 `agents/__init__.py` 的延迟导入导出

**PromptBuilder** (`agents/prompt_builder.py`)：提示词构建器
- `build(has_tools, tool_agent)`: 构建最终提示词
- `get_time_aware_prompt()`: 生成时间感知的提示词（包含当前日期和时效性指导）
- 自动检测是否需要添加工具使用说明
- 支持双语搜索策略指导（中文+英文）

### 2. 对话管理架构（`manager.py` + `conversation/` + `display/`）

采用 **处理器模式** 分离关注点：

**ConversationManager** (`manager.py`)：核心协调器
- 委托模式：将复杂逻辑委托给专门的处理器
- `flow_controller`: FlowController 实例（延迟初始化）

**FlowController** (`conversation/flow.py`)：对话流程控制
- `start(topic)`: 交互式对话循环
- `run_auto(topic, max_turns)`: 非交互式自动运行
- `_turn()`: 执行一轮对话
- 内置三个处理器：interaction_handler, search_handler, ending_handler

**InteractionHandler** (`conversation/interaction.py`)：用户交互处理
- `input_mode()`: 输入模式（等待用户输入）
- `wait_for_user_input()`: 后台监听用户输入（非阻塞）
- `handle_user_input(user_input)`: 处理用户命令（/quit, /clear）

**SearchHandler** (`conversation/search_handler.py`)：搜索逻辑
- `should_trigger_search()`: 判断是否触发搜索
- `extract_search_query()`: 从对话历史提取关键词
- `has_search_request()` / `extract_search_from_response()`: 检测 AI 主动请求

**EndingHandler** (`conversation/ending.py`)：对话结束处理
- `handle_proposal(agent_name, response)`: 处理 AI 的结束提议

**关键机制 - 非阻塞输入检测**：
```python
@staticmethod
def is_input_ready() -> bool:
    if not sys.stdin.isatty():
        return False
    return bool(select.select([sys.stdin], [], [], 0)[0])
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

### 4. 配置系统 (`prompts.yaml` + `config.py`)

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
  # MCP 服务器配置（可选）
  mcp_servers:
    knowledge: { command, args, env }
    code-analysis: { command, args, env }
  # Hook 配置（可选）
  pre_tool_use: { enabled, timeout }
  post_tool_use: { enabled, timeout }
```

**Pydantic 模型**：
- `AgentConfig`: 智能体配置
- `SettingsConfig`: 系统设置
- `SearchConfig/DocumentsConfig/ConversationConfig/ToolsConfig`: 子配置

### 5. 工具扩展和显示模块 (`tools/` + `display/`)

**搜索工具** (`tools/search_tool.py`)：
- `search_web(query, max_results)`: duckduckgo 搜索
- `_search_sync(query, max_results)`: 同步包装器

**搜索历史** (`tools/search_history.py`)：
- 搜索历史持久化（JSON）
- `save_search(query, results)`: 保存搜索
- `get_latest(limit)`: 获取最新记录

**引用显示** (`display/citations.py`)：
- `display_citations(citations)`: 显示引用信息
- `format_citations(citations)`: 格式化引用

**进度显示** (`display/progress.py`)：
- `ProgressDisplay`: 进度显示组件

**ToolAgent** (`tools/tool_agent.py`)：
- `analyze_codebase(path)`: 代码库分析
- `read_file_analysis(path, question)`: 文件分析

**ToolHooks** (`tools/hooks.py`)：
- `pre_tool_use()`: 工具调用前回调
- `post_tool_use()`: 工具调用后回调
- 配合 SDK Hook 系统使用

**SDK 原生集成**（`manager.py:_setup_sdk_tools()`）：
- 使用 SDK 原生的 `mcp_servers` 和 `hooks` 配置
- 支持 MCP 服务器配置（`prompts.yaml` 中的 `tools.mcp_servers`）
- 支持 Hook 配置（`pre_tool_use`、`post_tool_use`）
- 通过 `ConversationManager._setup_sdk_tools()` 方法初始化

### 6. 记忆和上下文管理

**MemoryManager** (`conversation/memory.py`)：
- Token 计数和状态监控（green/yellow/red）
- `trim_messages(messages)`: 清理历史，保留重要消息
- 最大清理次数限制（`max_trim_count`）

**DocumentPool** (`agents/documents.py`)：
- Citations API 文档池
- `merge_into_messages(messages)`: 合并文档到消息
- `from_search_history(search_entries)`: 搜索历史转文档

### 7. 对话结束检测 (`conversation/ending_detector.py`)

**ConversationEndDetector**：
- `detect(response, current_turn)`: 检测 `<!-- END -->` 标记
- `clean_response(response)`: 清理标记用于显示/保存

**配置 (ConversationEndConfig)**：
- `enable_detection`: 是否启用检测
- `end_marker`: 显式结束标记（默认 `<!-- END -->`）
- `require_confirmation`: 是否需要用户确认
- `min_turns_before_end`: 检测结束前所需的最小轮数（默认 20）

## 环境变量

- `ANTHROPIC_API_KEY`: Anthropic API 密钥（必需）
- `ANTHROPIC_BASE_URL`: API 基础 URL（可选）
- `ANTHROPIC_MODEL`: 使用的模型（默认: claude-sonnet-4-5-20250929）

**MCP 和 Hook 配置**：
- MCP 服务器和 Hook 通过 `prompts.yaml` 中的 `settings.tools.mcp_servers` 和 `settings.tools.pre_tool_use/post_tool_use` 配置
- 不再需要环境变量控制，直接在配置文件中定义

## 交互流程

```
用户启动 CLI
    ↓
加载 prompts.yaml 配置（包括 MCP 服务器和 Hook 配置）
    ↓
创建两个智能体（支持者 + 挑战者）
    ↓
创建 ConversationManager
    ├─ 初始化 SearchHistory（如果启用搜索）
    ├─ 初始化 ToolAgent（如果启用工具）
    ├─ 初始化 SummarizerAgent
    └─ 调用 _setup_sdk_tools() 设置 SDK 原生集成
    ↓
用户输入主题
    ↓
主循环 (FlowController.start):
  ├─ 检查用户输入（非阻塞 select.select）
  │   └─ 有输入 → 进入 InteractionHandler.input_mode()
  ├─ 智能搜索触发（SearchHandler.should_trigger_search）
  │   ├─ AI 主动请求（检测 [搜索: 关键词]）
  │   └─ 固定间隔兜底（search_interval）
  ├─ 执行一轮对话（_turn）
  │   ├─ 打印智能体名称
  │   ├─ 流式响应（ResponseHandler.respond）
  │   │   ├─ 处理 content_block_delta（text_delta/citations_delta）
  │   │   ├─ 检测 tool_use 并执行搜索或工具调用
  │   │   │   ├─ search_web: 执行网络搜索（duckduckgo）
  │   │   │   └─ query_tool: 调用工具扩展（ToolAgent）
  │   │   └─ 检查 interrupt 标志
  │   ├─ 清理响应前缀
  │   ├─ 记录响应到历史
  │   ├─ 检测对话结束标记（<!-- END -->）
  │   │   └─ 触发 EndingHandler.handle_proposal
  │   ├─ Token 状态检查和清理（conversation/memory.py）
  │   └─ 切换智能体（current = 1 - current）
  └─ 等待轮次间隔

用户输入模式 (InteractionHandler):
  ├─ 设置中断标志（interrupt.set()）
  ├─ 显示输入提示
  ├─ 获取用户输入
  ├─ 处理命令（/quit, /clear）或添加消息
  └─ 清除中断标志（interrupt.clear()）
```

## 测试策略

- 使用 `pytest` + `pytest-asyncio`
- 测试文件镜像源码目录结构（`tests/unit/` 对应 `src/mind/`）
- 使用 `unittest.mock.AsyncMock` 隔离 Anthropic API 调用
- 测试覆盖：初始化、流式响应、中断机制、工具调用、搜索集成

**测试迁移验证**：
- 当进行模块重构时（如移动文件到子包），添加迁移验证测试
- 使用 `test_*_migration.py` 命名约定，确保旧的导入路径仍然有效或明确失败
- 示例：`test_summarizer_migration.py`、`test_rename_modules.py`

**测试文件结构**：
- `tests/unit/agents/test_*.py`: 智能体模块测试
  - `test_agent.py`, `test_client.py`, `test_response.py`
  - `test_documents.py`, `test_prompts.py`, `test_conversation_analyzer.py`
  - `test_citations.py`, `test_summarizer.py`
- `tests/unit/conversation/test_*.py`: 对话处理器测试
  - `test_flow.py`, `test_interaction.py`, `test_search_handler.py`
  - `test_ending.py`, `test_ending_detector.py`, `test_memory.py`
- `tests/unit/display/test_*.py`: 显示模块测试
  - `test_citations.py`, `test_progress.py`
- `tests/unit/tools/test_*.py`: 工具模块测试
  - `test_search_tool.py`, `test_search_history.py`
  - `test_tool_agent.py`
- `tests/unit/test_*.py`: 顶层模块测试
  - `test_cli.py`, `test_prompts.py`（配置加载测试）
  - `test_conversation*.py`: 对话管理器集成测试
  - `test_sdk_native_config.py`: SDK 原生配置测试
  - `test_manager_sdk_tools.py`: SDK 工具管理测试

## 重要架构细节

### 模块组织原则
项目采用清晰的模块分离策略：
- **agents/**: 所有智能体相关实现（Agent、ResponseHandler、DocumentPool、ConversationAnalyzer 等）
- **conversation/**: 对话流程控制（FlowController、各种 Handler、MemoryManager）
- **display/**: UI 显示功能（引用显示、进度显示）
- **tools/**: 工具扩展（搜索、搜索历史、代码分析、Hook 回调）
- **顶层模块**: 配置加载、日志等跨领域功能

**命名约定**：
- 模块文件名使用描述性名称（如 `prompt_builder.py` 而非 `prompts.py`）
- Handler 类统一使用 `*Handler` 后缀（InteractionHandler、SearchHandler、EndingHandler）
- 配置相关类使用 `*Config` 后缀（AgentConfig、SettingsConfig 等）

### 延迟初始化和导入模式
- `ConversationManager.flow_controller`: 使用延迟初始化，避免循环导入
- `agents/__init__.py`: 使用 `__getattr__` 实现延迟导入（如 SummarizerAgent、ConversationAnalyzer）
- `conversation/__init__.py`: 使用 `__getattr__` 实现延迟导入（如 FlowController、各种 Handler）
- `display/__init__.py`: 使用 `__getattr__` 实现延迟导入（如 display_citations、ProgressDisplay）
- 处理器在 `FlowController.__init__` 中创建

### 非阻塞输入监听
- `InteractionHandler.wait_for_user_input()` 在后台运行
- 检测到输入时立即设置 `interrupt` 标志
- 响应完成后取消监听任务

### 响应清理机制
- `FlowController._clean_response_prefix()`: 清理 AI 响应中的角色名前缀
- `ConversationEndDetector.clean_response()`: 清理 `<!-- END -->` 标记

### SDK 原生集成模式
- 使用 SDK 原生的 `mcp_servers` 和 `hooks` 配置
- `ConversationManager._setup_sdk_tools()`: 初始化 SDK 工具
- `ConversationManager._build_hooks_config()`: 构建 Hook 配置
- MCP 服务器和 Hook 配置在 `prompts.yaml` 中定义
- ToolHooks (`tools/hooks.py`): 提供 pre/post_tool_use 回调实现

### Citations API 集成
- `DocumentPool`: 管理搜索历史文档
- `ResponseHandler` 捕获 `citations_delta` 事件
- 引用信息通过 `SearchHistory` 自动持久化
- 引用显示功能在 `display/citations.py` 中实现

## Pre-commit 钩子

项目使用 pre-commit 进行代码质量检查：
- Ruff lint + format
- MyPy 类型检查
- 通用检查（trailing whitespace、yaml/json/toml 语法等）

安装：`pre-commit install`

## Claude Code 自定义命令

项目在 `.claude/commands/` 目录下提供了两个自定义命令：

### `/gh` - GitHub CLI 助手
提供 GitHub CLI (gh) 的场景化指导，涵盖：
- Issue 和 PR 管理
- 仓库操作
- Actions 和 CI/CD
- Secrets 和 Variables
- Codespaces 管理
- Release 管理
- 高级 API 操作

### `/tdd` - 测试驱动开发助手
遵循 TDD 红-绿-重构循环：
- **红**：编写失败的测试 → `git commit -m "test: ..."`
- **绿**：编写最少代码使测试通过 → `git commit -m "feat: ..."`
- **重构**：在测试保护下优化代码 → `git commit -m "refactor: ..."`

测试规范包括：
- 测试文件镜像源码目录结构
- AAA 模式（Arrange → Act → Assert）
- 单一职责原则
- Mock 规则（仅隔离外部依赖）
- 覆盖率要求（核心逻辑 ≥80%）

## GitHub Actions 工作流

项目配置了三个 GitHub Actions 工作流（`.github/workflows/`）：

### CI 工作流 (`ci.yml`)
- **触发条件**：push/PR 到 main/develop 分支
- **检查步骤**：
  - 安装 uv 和依赖
  - ruff check（代码检查）
  - ruff format check（格式检查）
  - mypy 类型检查
  - pytest + 覆盖率
  - 上传到 Codecov

### 自动生成主题 (`auto-generate-topic.yml`)
- **触发条件**：北京时间晚上 11 点到早上 6 点，每小时运行
- **功能**：使用 Anthropic API 生成对话主题并自动创建 Issue

### Issue 触发对话 (`issue-chat.yml`)
- **触发条件**：手动触发或由 auto-generate-topic 触发
- **功能**：根据 Issue 内容自动运行对话
