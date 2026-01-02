# Mind 项目混合架构设计文档

## 1. 架构概述

### 1.1 设计原则

- **渐进式迁移**：保持当前主对话实现不变，仅增强工具层
- **职责分离**：主对话负责 Token 管理，工具层负责 MCP 集成
- **可逆性**：保留原有 ToolAgent 作为回退选项
- **最小侵入**：不影响现有 conversation.py 和 agent.py

### 1.2 架构分层

```
┌─────────────────────────────────────────────────────────────┐
│                    应用层 (Application)                      │
│  ConversationManager - 对话管理、Token 控制                  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    抽象层 (Abstraction)                      │
│            ToolAdapter - 统一工具调用接口                    │
└─────────────────────────────────────────────────────────────┘
                              │
            ┌─────────────────┴─────────────────┐
            ▼                                   ▼
┌──────────────────────┐          ┌──────────────────────┐
│   原始实现层          │          │   SDK 增强层          │
│  ToolAgent (原有)     │          │  SDKToolManager (新增)│
│  - 直接 API 调用      │          │  - MCP 集成           │
│  - Read/Grep 工具     │          │  - Hooks              │
└──────────────────────┘          └──────────────────────┘
                                                │
                                                ▼
                                    ┌──────────────────────┐
                                    │    MCP Server 层      │
                                    │  - Knowledge Base    │
                                    │  - Code Analysis     │
                                    │  - Web Search        │
                                    │  - Custom Tools      │
                                    └──────────────────────┘
```

## 2. 核心组件设计

### 2.1 ToolAdapter (适配器层)

**职责**：
- 提供统一的工具调用接口
- 自动选择使用原始 ToolAgent 或 SDK ToolManager
- 处理工具调用的降级逻辑

**接口**：
```python
class ToolAdapter:
    async def query_tool(
        self,
        question: str,
        messages: list[MessageParam],
        agent_name: str
    ) -> str | None

    async def initialize(self) -> None
    async def cleanup(self) -> None
```

### 2.2 SDKToolManager (SDK 工具管理器)

**职责**：
- 管理 ClaudeSDKClient 实例
- 配置 MCP 服务器
- 注册 Hook 回调
- 处理工具权限和统计

**配置**：
```python
@dataclass
class SDKToolConfig:
    """SDK 工具配置"""
    enable_mcp: bool = True
    enable_hooks: bool = True
    mcp_servers: dict[str, McpServerConfig] = field(default_factory=dict)
    tool_permissions: dict[str, Literal["allow", "deny", "ask"]] = field(default_factory=dict)
```

### 2.3 MCP Servers (MCP 服务器)

**内置服务器**：
- `knowledge-mcp`: 对话历史语义搜索
- `code-analysis-mcp`: 代码库分析
- `web-search-mcp`: 网络搜索（扩展现有 search_tool）

**扩展点**：
- 用户自定义 MCP 服务器
- 第三方 MCP 服务器（通过 stdio/HTTP 连接）

## 3. Hook 系统设计

### 3.1 Hook 类型

| Hook 类型 | 触发时机 | 用途 |
|-----------|---------|------|
| PreToolUse | 工具调用前 | 权限检查、输入验证 |
| PostToolUse | 工具调用后 | 使用统计、结果缓存 |
| UserPromptSubmit | 用户提交 | 上下文注入 |
| Stop | 对话停止 | 清理资源 |

### 3.2 Hook 实现

```python
class ToolHooks:
    async def pre_tool_use(
        self,
        input: PreToolUseHookInput,
        tool_use_id: str | None,
        context: HookContext
    ) -> HookJSONOutput:
        # 权限检查逻辑
        ...

    async def post_tool_use(
        self,
        input: PostToolUseHookInput,
        tool_use_id: str | None,
        context: HookContext
    ) -> HookJSONOutput:
        # 使用统计逻辑
        ...
```

## 4. 迁移步骤

### 阶段 1：准备阶段（1 天）

1. 创建新目录结构
2. 安装 SDK 依赖
3. 编写 MCP 服务器原型

### 阶段 2：核心实现（2-3 天）

1. 实现 ToolAdapter
2. 实现 SDKToolManager
3. 实现 MCP Servers

### 阶段 3：集成测试（1-2 天）

1. 单元测试
2. 集成测试
3. 性能对比

### 阶段 4：灰度发布（持续）

1. 添加配置开关
2. 小范围测试
3. 逐步放量

## 5. 配置管理

### 5.1 环境变量

```bash
# 启用 SDK 工具管理器
MIND_USE_SDK_TOOLS=true

# 启用 MCP 服务器
MIND_ENABLE_MCP=true

# MCP 服务器配置
MIND_MCP_KNOWLEDGE_ENABLED=true
MIND_MCP_CODE_ANALYSIS_ENABLED=true
```

### 5.2 配置文件

```yaml
# config/tools.yaml
sdk_tools:
  enabled: true
  fallback_on_error: true

mcp_servers:
  knowledge:
    enabled: true
    type: sdk
    max_documents: 100

  code_analysis:
    enabled: true
    type: sdk
    allowed_paths:
      - src/
      - tests/

hooks:
  pre_tool_use:
    enabled: true
    timeout: 30

  post_tool_use:
    enabled: true
    log_usage: true
```

## 6. 错误处理

### 6.1 降级策略

```python
class ToolAdapter:
    async def query_tool(self, ...):
        try:
            # 优先使用 SDK
            return await self._sdk_manager.query_tool(...)
        except Exception as e:
            logger.warning(f"SDK 工具调用失败: {e}, 降级到原始实现")
            # 降级到原始 ToolAgent
            return await self._fallback_agent.query_tool(...)
```

### 6.2 监控指标

- SDK 调用成功率
- 平均响应时间
- MCP 工具使用次数
- 降级次数

## 7. 性能考虑

### 7.1 连接复用

```python
class SDKToolManager:
    def __init__(self):
        self._client: ClaudeSDKClient | None = None

    async def get_client(self) -> ClaudeSDKClient:
        if self._client is None:
            self._client = ClaudeSDKClient(options=self._options)
            await self._client.connect()
        return self._client
```

### 7.2 缓存策略

- MCP 工具结果缓存
- 对话历史摘要缓存
- 代码分析结果缓存

## 8. 测试策略

### 8.1 单元测试

```python
# tests/unit/test_sdk_tool_manager.py
async def test_sdk_tool_manager_initialization():
    manager = SDKToolManager(config=SDKToolConfig())
    await manager.initialize()
    assert manager.client is not None

async def test_mcp_server_registration():
    manager = SDKToolManager(config=SDKToolConfig())
    server = create_knowledge_mcp_server()
    await manager.register_mcp_server("knowledge", server)
    assert "knowledge" in manager.mcp_servers
```

### 8.2 集成测试

```python
# tests/integration/test_tool_adapter.py
async def test_tool_adapter_fallback():
    adapter = ToolAdapter(use_sdk=True)
    adapter._sdk_manager = None  # 模拟 SDK 失败
    result = await adapter.query_tool("测试", [], "agent_a")
    assert result is not None  # 应该降级到原始实现
```

## 9. 文档

### 9.1 用户文档

- 如何启用 SDK 工具
- 如何配置 MCP 服务器
- 如何自定义 Hook

### 9.2 开发文档

- 架构设计文档
- API 文档
- MCP 服务器开发指南

## 10. 时间线

| 阶段 | 时间 | 交付物 |
|-----|------|--------|
| 准备 | 1 天 | 目录结构、依赖安装 |
| 核心实现 | 2-3 天 | ToolAdapter、SDKToolManager、MCP Servers |
| 测试 | 1-2 天 | 测试用例、性能报告 |
| 文档 | 1 天 | 用户文档、开发文档 |
| **总计** | **5-7 天** | **完整的混合架构** |
