# 数据模型参考

> **代码即真相，文档跟随代码**
> 本文档从代码分析生成，最后更新：2026-01-03

## 1. 核心数据模型

### 1.1 MessageParam

**来源**: `anthropic.types.MessageParam`

对话消息类型：

```python
from anthropic.types import MessageParam

# 用户消息
user_message: MessageParam = {
    "role": "user",
    "content": "Hello"
}

# 助手消息
assistant_message: MessageParam = {
    "role": "assistant",
    "content": "Hi there!"
}

# 带工具结果的消息
tool_result_message: MessageParam = {
    "role": "user",
    "content": [
        {
            "type": "tool_result",
            "tool_use_id": "toolu_xxx",
            "content": "搜索结果..."
        }
    ]
}
```

### 1.2 ToolUseBlock

**来源**: `anthropic.types.ToolUseBlock`

工具调用块：

```python
{
    "type": "tool_use",
    "id": "toolu_xxx",
    "name": "search_web",
    "input": {"query": "测试", "max_results": 5}
}
```

### 1.3 TextDelta

**来源**: `anthropic.types.TextDelta`

文本增量事件：

```python
{
    "type": "text_delta",
    "text": "Hello"
}
```

### 1.4 CitationsDelta

**来源**: `anthropic.types.ContentBlockDeltaEvent.CitationsDelta`

引用增量事件：

```python
{
    "type": "citations_delta",
    "citations": [
        {
            "text": "引用的文本",
            "source": {"id": "doc_xxx", "dataset": "search"}
        }
    ]
}
```

## 2. 搜索数据模型

### 2.1 SearchResult

**来源**: `tools/search_tool.py`

搜索结果：

```python
@dataclass
class SearchResult:
    """搜索结果"""
    title: str
    url: str
    body: str
```

### 2.2 SearchEntry

**来源**: `tools/search_history.py`

搜索历史条目：

```python
@dataclass
class SearchEntry:
    """搜索历史条目"""
    query: str
    timestamp: str
    results: list[SearchResult]
```

## 3. 文档数据模型

### 3.1 Document

**来源**: `anthropic.types.Document`

Citations 文档：

```python
{
    "type": "document",
    "id": "doc_xxx",
    "citations": [
        {
            "text": "引用的文本",
            "source": {"id": "src_xxx", "dataset": "search"}
        }
    ]
}
```

## 4. 工具数据模型

### 4.1 ToolDefinition

**来源**: MCP 工具定义

工具定义：

```python
{
    "name": "search_web",
    "description": "网络搜索",
    "inputSchema": {
        "type": "object",
        "properties": {
            "query": {"type": "string"},
            "max_results": {"type": "integer"}
        },
        "required": ["query"]
    }
}
```

## 5. 配置数据模型

详见 `configuration.md`。

## 6. 状态数据模型

### 6.1 TokenStatus

**来源**: `conversation/memory.py`

Token 状态：

```python
class TokenStatus(Enum):
    """Token 状态"""
    GREEN = "green"      # 正常 (< 80%)
    YELLOW = "yellow"    # 警告 (80-95%)
    RED = "red"         # 危险 (> 95%)
```

## 7. 内部数据模型

### 7.1 _TrimState

**来源**: `conversation/memory.py`

清理状态：

```python
@dataclass
class _TrimState:
    """清理状态"""
    count: int = 0
    original_count: int = 0
    max_count: int = 3
```
