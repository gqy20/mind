# 架构设计

> **代码即真相，文档跟随代码**
> 本文档从代码分析生成，最后更新：2026-01-03

## 1. 系统概述

**Mind** 是一个多智能体对话系统，通过两个 AI 智能体（支持者 vs 挑战者）的协作交流来激发创新思维。

### 1.1 设计原则

- **模块化架构**：清晰的模块边界和职责分离
- **渐进式迁移**：保留向后兼容的重导出模块
- **处理器模式**：对话流程使用专门的 Handler 处理
- **延迟初始化**：避免循环导入，按需创建组件
- **非阻塞交互**：使用 `select.select` 检测用户输入

### 1.2 架构分层

```
┌─────────────────────────────────────────────────────────────┐
│                      入口层 (Entry)                          │
│  cli.py - 命令行入口、配置加载                               │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    协调层 (Coordinator)                      │
│  manager.py - ConversationManager (核心协调器)              │
└─────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│   智能体模块      │ │  对话处理模块    │ │   工具扩展模块   │
│  (agents/)      │ │ (conversation/) │ │   (tools/)      │
│                 │ │                 │ │                 │
│ Agent          │ │ FlowController  │ │ search_tool.py  │
│ ResponseHandler│ │ InteractionHand.│ │ search_history  │
│ DocumentPool   │ │ SearchHandler   │ │ ToolAgent       │
│ Conversation.. │ │ EndingHandler   │ │ SDKToolManager  │
│ PromptBuilder  │ │ MemoryManager   │ │ ToolAdapter     │
└─────────────────┘ └─────────────────┘ └─────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      显示层 (Display)                        │
│  display/citations.py - 引用显示                            │
│  display/progress.py  - 进度显示                            │
└─────────────────────────────────────────────────────────────┘
```

## 2. 核心组件

### 2.1 智能体模块 (`agents/`)

| 组件 | 文件 | 职责 |
|------|------|------|
| **Agent** | `agent.py` | 智能体统一对外接口 |
| **AnthropicClient** | `client.py` | Anthropic API 客户端封装 |
| **ResponseHandler** | `response.py` | 流式响应和工具调用处理 |
| **DocumentPool** | `documents.py` | Citations API 文档池管理 |
| **PromptBuilder** | `prompt_builder.py` | 提示词构建（含时间感知） |
| **ConversationAnalyzer** | `conversation_analyzer.py` | 对话上下文分析 |
| **SummarizerAgent** | `summarizer.py` | 对话总结智能体 |
| **utils** | `utils.py` | 工具函数 |

**关键机制**：
- `ResponseHandler` 处理 `content_block_delta` 事件（新格式）和 `text` 事件（旧格式）
- 检测 `tool_use` 类型的 content_block，收集工具调用
- 支持 Citations API（捕获 `citations_delta` 事件）

### 2.2 对话处理模块 (`conversation/`)

采用 **处理器模式** 分离关注点：

| 组件 | 文件 | 职责 |
|------|------|------|
| **FlowController** | `flow.py` | 对话流程控制器（主循环） |
| **InteractionHandler** | `interaction.py` | 用户交互处理 |
| **SearchHandler** | `search_handler.py` | 搜索逻辑处理 |
| **EndingHandler** | `ending.py` | 对话结束处理 |
| **ConversationEndDetector** | `ending_detector.py` | 结束标记检测 |
| **MemoryManager** | `memory.py` | Token 管理和上下文清理 |
| **ProgressDisplay** | `progress.py` | 进度显示 |

**非阻塞输入检测**：
```python
@staticmethod
def is_input_ready() -> bool:
    if not sys.stdin.isatty():
        return False
    return bool(select.select([sys.stdin], [], [], 0)[0])
```

### 2.3 工具扩展模块 (`tools/`)

| 组件 | 文件 | 职责 |
|------|------|------|
| **search_tool** | `search_tool.py` | DuckDuckGo 网络搜索 |
| **search_history** | `search_history.py` | 搜索历史持久化（JSON） |
| **ToolAgent** | `tool_agent.py` | 代码库分析、文件分析 |
| **SDKToolManager** | `sdk_tool_manager.py` | MCP 服务器集成 |
| **ToolAdapter** | `adapters/tool_adapter.py` | 统一工具调用接口 |
| **MCP 工具** | `mcp/tools.py` | MCP 工具定义 |
| **MCP 服务器** | `mcp/servers.py` | MCP 服务器配置 |
| **MCP Hooks** | `mcp/hooks.py` | Hook 系统实现 |

**工具适配器模式**：
- 自动在 SDK ToolManager 和原始 ToolAgent 之间选择
- 错误降级：SDK 失败时自动切换到原始实现
- 环境变量控制：`MIND_USE_SDK_TOOLS`、`MIND_ENABLE_MCP`

### 2.4 显示模块 (`display/`)

| 组件 | 文件 | 职责 |
|------|------|------|
| **display_citations** | `citations.py` | 引用信息显示 |
| **ProgressDisplay** | `progress.py` | 进度显示组件 |

### 2.5 配置系统 (`config.py` + `prompts.yaml`)

**配置结构**：
```yaml
agents:
  supporter/challenger:
    name: "智能体名称"
    system_prompt: "多行提示词..."

settings:
  search: { max_results, history_limit }
  documents: { max_documents, ttl }
  conversation: { turn_interval, max_turns }
  tools: { tool_interval, enable_tools, enable_search }
```

**Pydantic 模型**：
- `AgentConfig`：智能体配置
- `SettingsConfig`：系统设置
- `SearchConfig` / `DocumentsConfig` / `ConversationConfig` / `ToolsConfig`：子配置

## 3. 模块依赖关系

```
cli.py
  ├─> config.py (加载配置)
  ├─> manager.py (创建对话管理器)
  │     ├─> agents/ (智能体)
  │     ├─> conversation/ (处理器)
  │     └─> tools/ (工具扩展)
  └─> prompts.yaml (提示词配置)
```

### 3.1 延迟导入模式

为避免循环导入，项目使用 `__getattr__` 实现延迟导入：

- `agents/__init__.py`：SummarizerAgent、ConversationAnalyzer
- `conversation/__init__.py`：FlowController、各种 Handler
- `display/__init__.py`：display_citations、ProgressDisplay

### 3.2 向后兼容模块

项目保留了一些重导出模块，便于渐进式迁移：

- `memory.py` → `conversation/memory.py`
- `search_history.py` → `tools/search_history.py`
- `agents/analysis.py` → `tools/tool_agent.py`
- `agents/citations.py` → `display/citations.py`

## 4. 交互流程

```
用户启动 CLI
    ↓
加载 prompts.yaml 配置
    ↓
创建两个智能体（支持者 + 挑战者）
    ↓
创建 ConversationManager（初始化 tools/search_history 和 tools/tool_agent）
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
  │   │   └─ 检查 interrupt 标志
  │   ├─ 清理响应前缀
  │   ├─ 记录响应到历史
  │   ├─ 检测对话结束标记（<!-- END -->）
  │   ├─ Token 状态检查和清理
  │   └─ 切换智能体（current = 1 - current）
  └─ 等待轮次间隔
```

## 5. 响应清理机制

### 5.1 前缀清理

`FlowController._clean_response_prefix()`: 清理 AI 响应中的角色名前缀

### 5.2 结束标记清理

`ConversationEndDetector.clean_response()`: 清理 `<!-- END -->` 标记

## 6. Citations API 集成

- `DocumentPool`: 管理搜索历史文档
- `ResponseHandler` 捕获 `citations_delta` 事件
- 引用信息通过 `SearchHistory` 自动持久化
- 引用显示功能在 `display/citations.py` 中实现

## 7. 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `ANTHROPIC_API_KEY` | Anthropic API 密钥（必需） | - |
| `ANTHROPIC_BASE_URL` | API 基础 URL | - |
| `ANTHROPIC_MODEL` | 使用的模型 | claude-sonnet-4-5-20250929 |
| `MIND_USE_SDK_TOOLS` | 是否使用 SDK 工具管理器 | false |
| `MIND_ENABLE_MCP` | 是否启用 MCP | true |

## 8. 相关设计文档

- `docs/architecture/mcp-integration-design.md` - MCP 集成设计
- `docs/architecture/conversation-ending-design.md` - 对话结束设计
- `docs/refactor/conversation_split.md` - 对话模块重构记录
