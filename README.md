# Mind

AI agents that collaborate to spark innovation

[![CI](https://img.shields.io/badge/GitHub-Actions-blue)](https://github.com/gqy20/mind/actions)
[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Tests](https://img.shields.io/badge/tests-50%2B-brightgreen)](https://github.com/gqy20/mind)

## 概述

**Mind** 是一个多智能体对话系统，通过 AI 智能体（支持者 vs 挑战者）的协作交流来激发创新思维。

**核心特性：**
- 🤖 **双智能体对话** - 支持者 vs 挑战者，观点碰撞
- ⚡ **实时流式输出** - 看到智能体思考过程
- 🎯 **随时参与** - 按 Enter 打断，加入讨论
- 🔍 **智能搜索** - AI 主动请求或定时触发网络搜索
- 📚 **Citations API** - 自动引用搜索结果
- 🔧 **工具扩展** - 代码库分析、MCP 集成
- 🛡️ **友好错误处理** - 针对不同错误类型提供具体提示
- 🔒 **类型安全** - 完整的类型注解和 mypy 检查
- ✅ **测试覆盖** - 50+ 测试用例，覆盖核心场景

## 快速开始

**前置要求：**
- Python 3.13+
- [uv](https://github.com/astral-sh/uv)（极速包管理器）
- ANTHROPIC_API_KEY 环境变量

```bash
# 克隆项目
git clone https://github.com/gqy20/mind.git
cd mind

# 安装依赖
uv pip install -e ".[dev]"

# 设置 API Key
export ANTHROPIC_API_KEY="your-key-here"

# 运行
mind
# 或
uv run mind
```

## 使用方式

```bash
# 启动对话
mind

# 交互命令
/quit 或 /exit    # 退出对话
/clear            # 重置对话
Enter             # 随时打断并输入消息

# 非交互式运行（自动进行 N 轮对话）
mind --max-turns 20 --non-interactive
```

**AI 搜索请求**：智能体可使用 `[搜索: 关键词]` 语法主动请求网络搜索

## 开发

```bash
# 安装开发依赖
make install

# 代码检查
make check

# 格式化
make format

# 运行测试
make test

# 测试覆盖率
make test-cov

# 类型检查
make type

# 完整检查（代码 + 类型 + 测试）
make all

# 清理缓存
make clean
```

## 项目结构

```
mind/
├── src/mind/
│   ├── __init__.py           # 包导出
│   ├── cli.py                # 命令行入口
│   ├── config.py             # 配置加载器（Pydantic）
│   ├── logger.py             # 日志配置（loguru）
│   ├── manager.py            # ConversationManager（核心协调器）
│   │
│   ├── agents/               # 智能体模块
│   │   ├── agent.py          # Agent 类（统一接口）
│   │   ├── client.py         # AnthropicClient（API 封装）
│   │   ├── response.py       # ResponseHandler（流式响应）
│   │   ├── documents.py      # DocumentPool（Citations 文档池）
│   │   ├── prompt_builder.py # PromptBuilder（提示词构建）
│   │   ├── conversation_analyzer.py # ConversationAnalyzer
│   │   ├── summarizer.py     # SummarizerAgent（对话总结）
│   │   └── utils.py          # 工具函数
│   │
│   ├── conversation/         # 对话处理模块
│   │   ├── flow.py           # FlowController（流程控制）
│   │   ├── interaction.py    # InteractionHandler（用户交互）
│   │   ├── search_handler.py # SearchHandler（搜索逻辑）
│   │   ├── ending.py         # EndingHandler（对话结束）
│   │   ├── ending_detector.py # ConversationEndDetector
│   │   ├── memory.py         # MemoryManager（Token 管理）
│   │   └── progress.py       # ProgressDisplay（进度显示）
│   │
│   ├── display/              # 显示模块
│   │   ├── citations.py      # 引用显示
│   │   └── progress.py       # 进度显示
│   │
│   └── tools/                # 工具扩展模块
│       ├── search_tool.py    # 网络搜索（duckduckgo）
│       ├── search_history.py # 搜索历史持久化
│       ├── tool_agent.py     # 代码库分析
│       ├── sdk_tool_manager.py # MCP 集成
│       ├── adapters/         # 工具适配器
│       │   └── tool_adapter.py # ToolAdapter（统一接口）
│       └── mcp/              # MCP 服务器
│           ├── tools.py      # MCP 工具定义
│           ├── servers.py    # MCP 服务器配置
│           └── hooks.py      # MCP Hook 系统
│
├── tests/
│   ├── unit/                 # 单元测试（镜像源码结构）
│   │   ├── agents/
│   │   ├── conversation/
│   │   ├── display/
│   │   └── tools/
│   └── conftest.py           # pytest 配置
│
├── docs/                     # 项目文档
│   ├── architecture.md       # 系统架构
│   ├── components.md         # 组件清单
│   ├── development.md        # 开发指南
│   ├── testing.md            # 测试策略
│   ├── contributing.md       # 贡献指南
│   ├── reference/            # 参考文档
│   │   ├── configuration.md  # 配置参考
│   │   └── data-models.md    # 数据模型
│   └── architecture/         # 设计文档
│
├── .github/workflows/        # CI/CD
├── prompts.yaml              # 智能体提示词和配置
└── pyproject.toml            # 项目配置
```

## 代码规范

1. **语言**：注释和文档使用**中文**，函数和类使用英文
2. **类型注解**：必需（通过 mypy 检查）
3. **文档字符串**：Google 风格中文文档
4. **测试**：遵循 AAA 模式（Arrange → Act → Assert）
5. **提交规范**：`feat/fix/docs/refactor/test/chore:`

## 配置

**环境变量**：
- `ANTHROPIC_API_KEY`: Anthropic API 密钥（必需）
- `ANTHROPIC_BASE_URL`: API 基础 URL（可选）
- `ANTHROPIC_MODEL`: 使用的模型（默认: claude-sonnet-4-5-20250929）
- `MIND_USE_SDK_TOOLS`: 是否使用 SDK 工具管理器（默认: false）
- `MIND_ENABLE_MCP`: 是否启用 MCP（默认: true）

**配置文件** (`prompts.yaml`)：定义智能体提示词和系统设置

## 文档

- [架构设计](docs/architecture.md) - 系统架构、模块依赖、交互流程
- [组件清单](docs/components.md) - 组件职责、核心方法
- [开发指南](docs/development.md) - 环境设置、代码规范
- [测试策略](docs/testing.md) - 测试框架、测试规范
- [贡献指南](docs/contributing.md) - 贡献流程、提交规范

## 许可证

MIT

Copyright © 2025 gqy20
