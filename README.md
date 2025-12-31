# Mind

AI agents that collaborate to spark innovation

[![CI](https://img.shields.io/badge/GitHub-Actions-blue)](https://github.com/gqy20/mind/actions)
[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Tests](https://img.shields.io/badge/tests-25%20passed-brightgreen)](https://github.com/gqy20/mind)

## 概述

**Mind** 是一个多智能体对话系统，通过 AI 智能体的协作交流激发创新思维。

**核心特性：**
- 🤖 **双智能体对话** - 支持者 vs 挑战者，观点碰撞
- ⚡ **实时流式输出** - 看到智能体思考过程
- 🎯 **随时参与** - 按 Enter 打断，加入讨论
- 🛡️ **友好错误处理** - 针对不同错误类型提供具体提示
- 🔒 **类型安全** - 完整的类型注解和 mypy 检查
- ✅ **测试覆盖** - 25+ 测试用例，覆盖核心场景

## 快速开始

**前置要求：**
- Python 3.13+
- [uv](https://github.com/astral-sh/uv)
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
```

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
│   ├── __init__.py       # 包导出
│   ├── agent.py          # 智能体类（含错误处理）
│   ├── conversation.py   # 对话管理器
│   └── cli.py           # 命令行入口
├── tests/
│   ├── unit/            # 单元测试
│   │   ├── test_agent.py
│   │   ├── test_agent_error_handling.py
│   │   ├── test_conversation.py
│   │   └── test_cli.py
│   └── conftest.py      # pytest 配置
├── .github/workflows/   # CI/CD
├── docs/                # 项目文档
└── pyproject.toml       # 项目配置
```

## 代码规范

1. **语言**：注释和文档使用**中文**
2. **命名**：函数和类使用英文
3. **类型注解**：必需（通过 mypy 检查）
4. **文档字符串**：Google 风格
5. **测试**：遵循 AAA 模式（Arrange → Act → Assert）

## 许可证

MIT

Copyright © 2025 gqy20
