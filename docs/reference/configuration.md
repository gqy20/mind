# 配置参考

> **代码即真相，文档跟随代码**
> 本文档从代码分析生成，最后更新：2026-01-03

## 1. 配置文件 (`prompts.yaml`)

### 1.1 结构概览

```yaml
agents:
  supporter: { ... }
  challenger: { ... }

settings:
  search: { ... }
  documents: { ... }
  conversation: { ... }
  tools: { ... }
  conversation_end: { ... }
  memory: { ... }
```

### 1.2 智能体配置

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
```

### 1.3 搜索配置

```yaml
settings:
  search:
    max_results: 5        # 最大搜索结果数
    history_limit: 100    # 搜索历史限制
```

### 1.4 文档配置

```yaml
settings:
  documents:
    max_documents: 20     # 最大文档数
    ttl: 3600            # 文档生存时间（秒）
```

### 1.5 对话配置

```yaml
settings:
  conversation:
    turn_interval: 1.0    # 轮次间隔（秒）
    max_turns: 100       # 最大轮数
```

### 1.6 工具配置

```yaml
settings:
  tools:
    tool_interval: 5     # 工具调用间隔（轮）
    enable_tools: true   # 启用工具
    enable_search: true  # 启用搜索
```

### 1.7 对话结束配置

```yaml
settings:
  conversation_end:
    enable_detection: true          # 启用结束检测
    end_marker: "<!-- END -->"      # 结束标记
    require_confirmation: false     # 需要用户确认
    min_turns_before_end: 20        # 检测结束前最小轮数
```

### 1.8 记忆配置

```yaml
settings:
  memory:
    max_tokens: 100000            # 最大 Token 数
    warning_threshold: 0.8        # 警告阈值（80%）
    max_trim_count: 3             # 最大清理次数
    trim_target_ratio: 0.7        # 清理目标比例（70%）
    keep_recent_count: 5          # 保留最近消息数
```

## 2. 环境变量

| 变量 | 说明 | 默认值 | 必需 |
|------|------|--------|------|
| `ANTHROPIC_API_KEY` | Anthropic API 密钥 | - | ✅ |
| `ANTHROPIC_BASE_URL` | API 基础 URL | https://api.anthropic.com | ❌ |
| `ANTHROPIC_MODEL` | 使用的模型 | claude-sonnet-4-5-20250929 | ❌ |
| `MIND_USE_SDK_TOOLS` | 是否使用 SDK 工具管理器 | false | ❌ |
| `MIND_ENABLE_MCP` | 是否启用 MCP | true | ❌ |

## 3. 命令行参数

```bash
mind [OPTIONS] [TOPIC]

选项:
  --max-turns N          限制对话轮数
  --non-interactive      非交互式模式
  --no-tools            禁用工具扩展
  --no-search           禁用网络搜索
  --tool-interval N     覆盖工具调用间隔
  --test-tools          测试工具扩展功能
  --help                显示帮助信息
```

## 4. Pydantic 配置模型

### 4.1 AgentConfig

```python
@dataclass
class AgentConfig:
    """智能体配置"""
    name: str
    system_prompt: str
```

### 4.2 SettingsConfig

```python
@dataclass
class SettingsConfig:
    """系统设置"""
    search: SearchConfig
    documents: DocumentsConfig
    conversation: ConversationConfig
    tools: ToolsConfig
    conversation_end: ConversationEndConfig
    memory: MemoryConfig
```

### 4.3 SearchConfig

```python
@dataclass
class SearchConfig:
    """搜索配置"""
    max_results: int = 5
    history_limit: int = 100
```

### 4.4 DocumentsConfig

```python
@dataclass
class DocumentsConfig:
    """文档配置"""
    max_documents: int = 20
    ttl: int = 3600
```

### 4.5 ConversationConfig

```python
@dataclass
class ConversationConfig:
    """对话配置"""
    turn_interval: float = 1.0
    max_turns: int = 100
```

### 4.6 ToolsConfig

```python
@dataclass
class ToolsConfig:
    """工具配置"""
    tool_interval: int = 5
    enable_tools: bool = True
    enable_search: bool = True
```

### 4.7 ConversationEndConfig

```python
@dataclass
class ConversationEndConfig:
    """对话结束配置"""
    enable_detection: bool = True
    end_marker: str = "<!-- END -->"
    require_confirmation: bool = False
    min_turns_before_end: int = 20
```

### 4.8 MemoryConfig

```python
@dataclass
class MemoryConfig:
    """记忆配置"""
    max_tokens: int = 100000
    warning_threshold: float = 0.8
    max_trim_count: int = 3
    trim_target_ratio: float = 0.7
    keep_recent_count: int = 5
```

## 5. 配置加载

### 5.1 加载流程

```python
from mind.config import load_config

# 加载配置
agent_configs, settings = load_config("prompts.yaml")
```

### 5.2 配置验证

配置在加载时通过 Pydantic 验证，确保类型正确。

## 6. 配置优先级

1. 命令行参数（最高）
2. 环境变量
3. 配置文件 (`prompts.yaml`)
4. 默认值（最低）
