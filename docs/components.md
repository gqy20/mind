# 组件清单

> **代码即真相，文档跟随代码**
> 本文档从代码分析生成，最后更新：2026-01-03

## 1. 概览

| 模块 | 文件 | 导出符号 | 状态 |
|------|------|----------|------|
| **agents** | `agents/__init__.py` | Agent, DocumentPool, PromptBuilder, ConversationAnalyzer, SummarizerAgent | ✅ |
| **conversation** | `conversation/__init__.py` | FlowController, InteractionHandler, SearchHandler, EndingHandler, MemoryManager, ConversationEndDetector | ✅ |
| **display** | `display/__init__.py` | display_citations, ProgressDisplay | ✅ |
| **tools** | `tools/__init__.py` | search_web, ToolAgent, SDKToolManager, ToolAdapter | ✅ |

## 2. 智能体模块 (`agents/`)

### 2.1 Agent (`agents/agent.py`)

**职责**：智能体统一对外接口

**核心方法**：
- `__init__(name, system_prompt, model, settings)`: 初始化
- `respond(messages, interrupt)`: 生成响应（委托给 ResponseHandler）
- `query_tool(question, messages)`: 分析对话上下文（委托给 ConversationAnalyzer）
- `add_document(doc)`: 添加文档到池（委托给 DocumentPool）

### 2.2 AnthropicClient (`agents/client.py`)

**职责**：API 客户端封装

**核心方法**：
- `__init__(base_url)`: 初始化客户端
- `get_client()`: 获取 AsyncAnthropic 实例

### 2.3 ResponseHandler (`agents/response.py`)

**职责**：流式响应和工具调用处理

**核心方法**：
- `respond(messages, system, interrupt)`: 主响应循环
- `_execute_tool_search(tool_call, ...)`: 执行搜索工具（duckduckgo）
- `_continue_response(...)`: 基于工具结果继续生成
- `_handle_api_status_error(e)`: API 错误处理（401/429/5xx）

**关键机制**：
- 处理 `content_block_delta` 事件（新格式）和 `text` 事件（旧格式）
- 检测 `tool_use` 类型的 content_block，收集工具调用
- 支持 Citations API（捕获 `citations_delta` 事件）

### 2.4 DocumentPool (`agents/documents.py`)

**职责**：Citations API 文档池管理

**核心方法**：
- `add_document(doc)`: 添加文档
- `merge_into_messages(messages)`: 合并文档到消息
- `from_search_history(search_entries)`: 搜索历史转文档（静态方法）

### 2.5 PromptBuilder (`agents/prompt_builder.py`)

**职责**：提示词构建器

**核心方法**：
- `build(has_tools, tool_agent)`: 构建最终提示词
- `get_time_aware_prompt()`: 生成时间感知的提示词（包含当前日期和时效性指导）

**特性**：
- 自动检测是否需要添加工具使用说明
- 支持双语搜索策略指导（中文+英文）

### 2.6 ConversationAnalyzer (`agents/conversation_analyzer.py`)

**职责**：对话上下文分析

**核心方法**：
- `analyze_context(messages, question)`: 分析对话上下文回答问题

### 2.7 SummarizerAgent (`agents/summarizer.py`)

**职责**：对话总结智能体

**核心方法**：
- `summarize(messages, topic, interrupt)`: 生成对话总结

### 2.8 Utils (`agents/utils.py`)

**职责**：工具函数

**导出函数**：
- `get_current_date()`: 获取当前日期
- `clean_response_prefix(response, name)`: 清理响应前缀

## 3. 对话处理模块 (`conversation/`)

### 3.1 FlowController (`conversation/flow.py`)

**职责**：对话流程控制器（主循环）

**核心方法**：
- `start(topic)`: 交互式对话循环
- `run_auto(topic, max_turns)`: 非交互式自动运行
- `_turn()`: 执行一轮对话

**内置处理器**：interaction_handler, search_handler, ending_handler

### 3.2 InteractionHandler (`conversation/interaction.py`)

**职责**：用户交互处理

**核心方法**：
- `input_mode()`: 输入模式（等待用户输入）
- `wait_for_user_input()`: 后台监听用户输入（非阻塞）
- `handle_user_input(user_input)`: 处理用户命令（/quit, /clear）

**非阻塞输入检测**：
```python
@staticmethod
def is_input_ready() -> bool:
    if not sys.stdin.isatty():
        return False
    return bool(select.select([sys.stdin], [], [], 0)[0])
```

### 3.3 SearchHandler (`conversation/search_handler.py`)

**职责**：搜索逻辑处理

**核心方法**：
- `should_trigger_search(...)`: 判断是否触发搜索
- `extract_search_query(messages)`: 从对话历史提取关键词
- `has_search_request(response)`: 检测 AI 主动请求
- `extract_search_from_response(response)`: 提取搜索关键词

**智能搜索触发优先级**：
1. AI 主动请求（使用 `[搜索: 关键词]` 语法）
2. 固定间隔兜底（`search_interval`）

### 3.4 EndingHandler (`conversation/ending.py`)

**职责**：对话结束处理

**核心方法**：
- `handle_proposal(agent_name, response)`: 处理 AI 的结束提议

### 3.5 ConversationEndDetector (`conversation/ending_detector.py`)

**职责**：对话结束检测

**核心方法**：
- `detect(response, current_turn)`: 检测 `<!-- END -->` 标记
- `clean_response(response)`: 清理标记用于显示/保存

**配置 (ConversationEndConfig)**：
- `enable_detection`: 是否启用检测
- `end_marker`: 显式结束标记（默认 `<!-- END -->`）
- `require_confirmation`: 是否需要用户确认
- `min_turns_before_end`: 检测结束前所需的最小轮数（默认 20）

### 3.6 MemoryManager (`conversation/memory.py`)

**职责**：Token 计数和状态监控

**核心方法**：
- `trim_messages(messages)`: 清理历史，保留重要消息
- `get_token_status()`: 获取 Token 状态（green/yellow/red）

**配置 (MemoryConfig)**：
- `max_tokens`: 最大 Token 数
- `warning_threshold`: 警告阈值
- `max_trim_count`: 最大清理次数

## 4. 显示模块 (`display/`)

### 4.1 display_citations (`display/citations.py`)

**职责**：引用信息显示

**核心函数**：
- `display_citations(citations)`: 显示引用信息
- `format_citations(citations)`: 格式化引用

### 4.2 ProgressDisplay (`display/progress.py`)

**职责**：进度显示组件

**核心方法**：
- `start(agent_name)`: 开始显示
- `update(text)`: 更新显示文本
- `stop()`: 停止显示

## 5. 工具扩展模块 (`tools/`)

### 5.1 search_tool (`tools/search_tool.py`)

**职责**：DuckDuckGo 网络搜索

**核心函数**：
- `search_web(query, max_results)`: 网络搜索
- `_search_sync(query, max_results)`: 同步包装器

### 5.2 SearchHistory (`tools/search_history.py`)

**职责**：搜索历史持久化（JSON）

**核心方法**：
- `save_search(query, results)`: 保存搜索
- `get_latest(limit)`: 获取最新记录

### 5.3 ToolAgent (`tools/tool_agent.py`)

**职责**：代码库分析、文件分析

**核心方法**：
- `analyze_codebase(path)`: 代码库分析
- `read_file_analysis(path, question)`: 文件分析

### 5.4 SDKToolManager (`tools/sdk_tool_manager.py`)

**职责**：MCP 服务器集成

**核心方法**：
- `initialize()`: 初始化 SDK 客户端和 MCP 服务器
- `query_tool(question, messages)`: 通过 SDK 调用工具
- `cleanup()`: 清理资源

**特性**：
- Hook 系统支持
- 工具权限控制

### 5.5 ToolAdapter (`tools/adapters/tool_adapter.py`)

**职责**：统一工具调用接口

**核心方法**：
- `query_tool(question, messages, agent_name)`: 统一工具调用接口
- `initialize()`: 初始化
- `cleanup()`: 清理资源

**特性**：
- 自动在 SDK ToolManager 和原始 ToolAgent 之间选择
- 错误降级处理
- 使用统计和监控

### 5.6 MCP 模块 (`tools/mcp/`)

| 文件 | 职责 |
|------|------|
| `tools.py` | MCP 工具定义 |
| `servers.py` | MCP 服务器配置 |
| `hooks.py` | MCP Hook 系统实现 |

## 6. 顶层模块

### 6.1 ConversationManager (`manager.py`)

**职责**：核心协调器

**核心方法**：
- `start(topic)`: 启动交互式对话
- `run_auto(topic, max_turns)`: 非交互式运行

**委托模式**：将复杂逻辑委托给专门的处理器

### 6.2 CLI (`cli.py`)

**职责**：命令行入口和配置

**核心函数**：
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

### 6.3 配置加载器 (`config.py`)

**职责**：加载 prompts.yaml 配置

**导出类**：
- `AgentConfig`: 智能体配置
- `SettingsConfig`: 系统设置
- `SearchConfig`: 搜索配置
- `DocumentsConfig`: 文档配置
- `ConversationConfig`: 对话配置
- `ToolsConfig`: 工具配置

### 6.4 日志配置 (`logger.py`)

**职责**：日志配置（loguru）

**导出**：
- `logger`: loguru 实例

## 7. 向后兼容模块

以下模块仅用于重导出新位置的符号，便于渐进式迁移：

| 模块 | 重导出来源 |
|------|-----------|
| `memory.py` | `conversation/memory.py` |
| `search_history.py` | `tools/search_history.py` |
| `agents/analysis.py` | `tools/tool_agent.py` |
| `agents/citations.py` | `display/citations.py` |
