# 贡献指南

> **代码即真相，文档跟随代码**
> 本文档从代码分析生成，最后更新：2026-01-03

欢迎为 Mind 项目贡献代码！

## 1. 贡献流程

### 1.1 Fork 和克隆

```bash
# Fork 项目到你的账号
# 克隆你的 fork
git clone https://github.com/YOUR_USERNAME/mind.git
cd mind
```

### 1.2 创建分支

```bash
# 从 main 分支创建功能分支
git checkout -b feature/your-feature-name
# 或修复分支
git checkout -b fix/your-bug-fix
```

### 1.3 开发和测试

```bash
# 安装开发依赖
make install

# 运行测试
make test

# 运行完整检查
make all
```

### 1.4 提交和推送

```bash
# 提交代码（遵循提交规范）
git commit -m "feat: 添加新功能"

# 推送到你的 fork
git push origin feature/your-feature-name
```

### 1.5 创建 Pull Request

在 GitHub 上创建 Pull Request，描述你的变更。

## 2. 提交规范

### 2.1 提交前缀

| 前缀 | 说明 | 示例 |
|------|------|------|
| `feat:` | 新功能 | `feat: 添加对话历史导出功能` |
| `fix:` | 修复 bug | `fix: 修复 token 计数错误` |
| `docs:` | 文档更新 | `docs: 更新架构文档` |
| `refactor:` | 重构 | `refactor: 重构搜索逻辑` |
| `test:` | 测试 | `test: 添加 MemoryManager 测试` |
| `chore:` | 构建/工具链 | `chore: 升级 ruff 到最新版本` |

### 2.2 提交格式

```
<前缀>: <简短描述>

<详细描述（可选）>

<相关 issue（可选）>
```

**示例**：
```
feat: 添加对话结束检测功能

- 添加 ConversationEndDetector 类
- 支持 <!-- END --> 标记检测
- 添加配置选项控制检测行为

Closes #42
```

## 3. 代码规范

### 3.1 命名约定

| 类型 | 约定 | 示例 |
|------|------|------|
| **模块** | 小写+下划线 | `agent.py`, `search_handler.py` |
| **类** | 大驼峰 | `Agent`, `ResponseHandler` |
| **函数** | 小写+下划线 | `respond()`, `should_trigger_search()` |
| **常量** | 大写+下划线 | `MAX_TOKENS` |

**特殊后缀**：
- `*Handler`: 处理器类
- `*Config`: 配置类
- `*Manager`: 管理器类

### 3.2 类型注解

必需（通过 mypy 检查）：

```python
from anthropic.types import MessageParam

def respond(
    self,
    messages: list[MessageParam],
    interrupt: asyncio.Event,
) -> str:
    ...
```

### 3.3 文档字符串

Google 风格中文文档：

```python
def analyze_context(
    self,
    messages: list[MessageParam],
    question: str,
) -> str:
    """分析对话上下文回答问题

    Args:
        messages: 对话消息历史
        question: 需要回答的问题

    Returns:
        分析结果文本
    """
    ...
```

### 3.4 格式化

项目使用 ruff 进行格式化和检查：

```bash
# 自动修复
make format
ruff format .

# 检查
make check
ruff check .
```

## 4. 测试要求

### 4.1 测试覆盖

- 新功能必须有测试
- 核心逻辑覆盖率 ≥80%
- 使用 AAA 模式（Arrange → Act → Assert）

### 4.2 测试位置

镜像源码目录结构：

```
tests/unit/agents/test_*.py  # 对应 src/mind/agents/*.py
tests/unit/conversation/test_*.py  # 对应 src/mind/conversation/*.py
...
```

### 4.3 Mock 规则

只隔离外部依赖（Anthropic API、文件系统等）：

```python
from unittest.mock import AsyncMock, patch

async def test_agent_respond():
    with patch("mind.agents.client.AsyncAnthropic") as mock_client:
        mock_client.return_value.messages.create = AsyncMock(...)
        agent = Agent(...)
        response = await agent.respond(...)
        assert response is not None
```

## 5. 文档要求

### 5.1 代码文档

- 所有公开类和方法必须有文档字符串
- 复杂逻辑必须有行内注释
- 使用中文编写文档

### 5.2 文档更新

当修改代码时，同步更新相关文档：

| 代码变更 | 更新文档 |
|----------|----------|
| 新增模块 | `components.md` |
| 修改导入关系 | `architecture.md` |
| 修改配置文件 | `development.md` |
| 新增测试 | `testing.md` |

## 6. Pull Request 检查清单

提交 PR 前，确保：

- [ ] 所有测试通过（`make test`）
- [ ] 代码检查通过（`make check`）
- [ ] 类型检查通过（`make type`）
- [ ] 新功能有测试覆盖
- [ ] 文档已更新
- [ ] 提交信息遵循规范
- [ ] PR 描述清晰

## 7. 代码审查

### 7.1 审查重点

- 功能正确性
- 代码可读性
- 测试完整性
- 文档准确性
- 性能影响

### 7.2 反馈处理

- 及时回应审查意见
- 讨论分歧意见
- 按要求修改代码

## 8. 发布流程

### 8.1 版本号

遵循语义化版本 (Semantic Versioning)：

- **MAJOR.MINOR.PATCH**
- MAJOR: 不兼容的 API 变更
- MINOR: 向后兼容的新功能
- PATCH: 向后兼容的 bug 修复

### 8.2 发布步骤

1. 更新版本号（`pyproject.toml`）
2. 更新 CHANGELOG.md
3. 创建 tag
4. 推送 tag（触发自动发布）

```bash
git tag -a v0.2.0 -m "Release 0.2.0"
git push origin v0.2.0
```

## 9. 社区准则

- 尊重所有贡献者
- 建设性反馈
- 乐于助人
- 开放讨论

## 10. 获取帮助

- **Issues**: 报告 bug 或请求功能
- **Discussions**: 讨论设计和问题
- **Documentation**: 查看项目文档

感谢你的贡献！
