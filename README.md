# Mind

AI agents that collaborate to spark innovation

[![CI](https://img.shields.io/badge/GitHub-Actions-blue)](https://github.com/gqy20/mind/actions)
[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Tests](https://img.shields.io/badge/tests-79%2B-brightgreen)](https://github.com/gqy20/mind)

## 概述

**Mind** 是一个多智能体对话系统，通过 AI 智能体（支持者 vs 挑战者）的协作交流来激发创新思维。

**核心特性：**
- 🤖 **双智能体对话** - 支持者 vs 挑战者，观点碰撞
- ⚡ **实时流式输出** - 看到智能体思考过程
- 🎯 **随时参与** - 按 Enter 打断，加入讨论
- 🔍 **智能搜索** - AI 主动请求或定时触发网络搜索
- 📚 **Citations API** - 自动引用搜索结果
- 🔧 **工具扩展** - 代码库分析、MCP 集成
- 🤖 **AI 结束检测** - 基于评分机制的智能对话质量分析
- 🛡️ **友好错误处理** - 针对不同错误类型提供具体提示
- 🔒 **类型安全** - 完整的类型注解和 mypy 检查
- ✅ **测试覆盖** - 79+ 测试用例，覆盖核心场景

## 快速开始

**前置要求：**
- Python 3.13+
- [uv](https://github.com/astral-sh/uv)（极速包管理器）
- 智谱 API Key（兼容 Anthropic API 格式）

```bash
# 克隆项目
git clone https://github.com/gqy20/mind.git
cd mind

# 同步依赖（自动安装生产和开发依赖）
uv sync

# 配置 API（二选一）

# 方式一：使用 .env 文件（推荐）
cp .env.example .env
# 编辑 .env 文件，填入您的 API Key
vim .env  # 或使用其他编辑器

# 方式二：直接设置环境变量
export ANTHROPIC_API_KEY="your-zhipu-api-key"
export ANTHROPIC_BASE_URL="https://open.bigmodel.cn/api/anthropic"
export ANTHROPIC_MODEL="glm-4.7"

# 运行
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

**对话结束检测**：当对话充分展开后，AI 可通过 `<!-- END -->` 标记请求结束对话，系统会使用 AI 分析验证对话质量，并进入两轮过渡期自然收尾。

## 配置

**环境变量：**

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `ANTHROPIC_API_KEY` | 智谱 API 密钥（必需） | - |
| `ANTHROPIC_BASE_URL` | API 基础 URL | `https://open.bigmodel.cn/api/anthropic` |
| `ANTHROPIC_MODEL` | 使用的模型 | `glm-4.7` |
| `MIND_USE_SDK_TOOLS` | 是否使用 SDK 工具管理器 | `false` |
| `MIND_ENABLE_MCP` | 是否启用 MCP | `true` |

**配置文件** (`prompts.yaml`)：定义智能体提示词和系统设置

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

## 代码规范

1. **语言**：注释和文档使用**中文**，函数和类使用英文
2. **类型注解**：必需（通过 mypy 检查）
3. **文档字符串**：Google 风格中文文档
4. **测试**：遵循 AAA 模式（Arrange → Act → Assert）
5. **提交规范**：`feat/fix/docs/refactor/test/chore:`

## 文档

- [架构设计](docs/architecture.md) - 系统架构、模块依赖、交互流程
- [组件清单](docs/components.md) - 组件职责、核心方法
- [开发指南](docs/development.md) - 环境设置、代码规范
- [测试策略](docs/testing.md) - 测试框架、测试规范
- [贡献指南](docs/contributing.md) - 贡献流程、提交规范

## 许可证

MIT

Copyright © 2025 gqy20
