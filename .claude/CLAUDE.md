# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

**Mind** 是一个多智能体对话系统，通过两个 AI 智能体（支持者 vs 挑战者）的协作交流来激发创新思维。

- **Python 版本**: 3.13+
- **包管理**: uv（极速包管理器）
- **项目结构**: src layout
- **代码规范**: ruff（检查 + 格式化）
- **测试框架**: pytest
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

# 测试
make test
pytest
pytest tests/unit/test_agent.py           # 运行单个测试文件
pytest -k "test_respond_interrupt"        # 运行单个测试

# 测试覆盖率
make test-cov
pytest --cov=src/mind

# 运行程序
uv run python -m mind.cli

# 完整检查
python scripts/check.py
```

## 代码规范

1. **语言**: 所有注释、文档字符串使用中文，函数和类使用英文命名
2. **类型注解**: 必需
3. **文档字符串**: Google 风格中文文档
4. **提交规范**: `feat/fix/docs/refactor/test/chore:`

## 核心架构

### 三个核心组件

```
src/mind/
├── agent.py           # Agent 类 - 单个对话智能体
├── conversation.py    # ConversationManager - 对话管理器
└── cli.py            # CLI 入口和配置
```

### 1. Agent 类 (`agent.py`)

单个对话智能体的抽象。核心方法：
- `__init__(name, system_prompt, model)`: 初始化智能体，创建 AsyncAnthropic 客户端
- `respond(messages, interrupt)`: 异步流式响应，支持中断

**关键机制**：
- 使用 AsyncAnthropic 客户端，通过 `messages.stream()` 获取流式响应
- 每收到一个文本块就打印（`print(event.text, end="", flush=True)`）
- 每次迭代检查 `interrupt.is_set()`，如果被中断则返回 None

### 2. ConversationManager 类 (`conversation.py`)

协调两个智能体的对话循环。

**状态字段**：
- `messages`: 对话历史（Anthropic 格式的消息列表）
- `interrupt`: asyncio.Event，用于中断当前 AI 输出
- `current`: 0=A, 1=B，控制轮次切换
- `is_running`: 控制主循环

**核心方法**：
- `start(topic)`: 主对话循环
- `_input_mode()`: 用户输入模式（设置中断标志，等待输入）
- `_turn()`: 执行一轮对话（A 或 B 发言）
- `_handle_user_input()`: 处理用户输入（/quit, /exit, /clear 或正常消息）

**关键机制 - 非阻塞输入检测**：
```python
def _is_input_ready():
    return select.select([sys.stdin], [], [], 0)[0]
```
在主循环中检查用户是否按下 Enter，如果有则进入输入模式。

### 3. CLI 入口 (`cli.py`)

- `check_config()`: 检查 ANTHROPIC_API_KEY 环境变量
- `main()`: 创建两个智能体（支持者 vs 挑战者），启动对话管理器

## 环境变量

- `ANTHROPIC_API_KEY`: Anthropic API 密钥（必需）
- `ANTHROPIC_BASE_URL`: API 基础 URL（可选，默认使用官方）
- `ANTHROPIC_MODEL`: 使用的模型（默认: claude-sonnet-4-5-20250929）

## 交互流程

```
用户启动 CLI
    ↓
配置两个智能体（支持者 + 挑战者）
    ↓
用户输入主题
    ↓
主循环:
  ├─ 检查用户输入（非阻塞 select.select）
  │   └─ 有输入 → 进入 _input_mode()
  ├─ 执行一轮对话（A 或 B）
  │   ├─ 打印智能体名称
  │   ├─ 流式响应（实时打印）
  │   ├─ 检查中断标志
  │   └─ 记录响应到历史
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
- 测试覆盖：初始化、流式响应、中断机制、文本累积、轮次管理
