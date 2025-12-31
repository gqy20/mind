# Mind

AI agents that collaborate to spark innovation

[![CI](https://img.shields.io/badge/GitHub-Actions-blue)](https://github.com/gqy20/mind/actions)
[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

## 概述

**Mind** 是一个多智能体对话系统，通过 AI 智能体的协作交流激发创新思维。

**核心特性：**
- 🤖 **双智能体对话** - 支持者 vs 挑战者，观点碰撞
- ⚡ **实时流式输出** - 看到智能体思考过程
- 🎯 **随时参与** - 按 Enter 打断，加入讨论
- 📦 **uv** - 极速包管理器
- ⚡ **ruff** - 代码检查和格式化
- ✅ **pytest** - 测试框架

## 快速开始

**前置要求：**
- Python 3.13+
- [uv](https://github.com/astral-sh/uv)
- ANTHROPIC_API_KEY 环境变量

```bash
# 克隆项目
git clone https://github.com/gqy20/mind.git
cd mind

# 创建虚拟环境并安装依赖
uv venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
uv pip install -e ".[dev]"

# 设置 API Key
export ANTHROPIC_API_KEY="your-key-here"

# 运行
uv run python -m mind.cli
```

## 使用方式

```bash
# 启动对话
uv run python -m mind.cli

# 交互命令
/quit 或 /exit    # 退出对话
/clear            # 重置对话
Enter             # 随时打断并输入消息
```

## 项目结构

```
mind/
├── src/mind/
│   ├── __init__.py       # 包导出
│   ├── agent.py          # 智能体类
│   ├── conversation.py   # 对话管理器
│   └── cli.py           # 命令行入口
├── tests/
│   └── unit/            # 单元测试
└── pyproject.toml
```

## 代码规范

1. **语言**：注释和文档使用**中文**
2. **命名**：函数和类使用英文
3. **类型注解**：必需
4. **文档字符串**：Google 风格

## 许可证

MIT

Copyright © 2025 gqy20
