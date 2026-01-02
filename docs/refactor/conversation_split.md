# Conversation.py 模块拆分重构文档

## 1. 重构背景

### 1.1 当前问题

`src/mind/conversation.py` 文件有 **1009 行**，包含：
- 1 个数据类 `ConversationManager`
- 17 个方法
- 多个职责混杂（对话控制、用户交互、搜索、结束检测、UI显示等）

这是一个典型的"上帝类"（God Class）反模式，违反了单一职责原则（SRP）。

### 1.2 重构目标

1. **提高可维护性**：将大文件拆分为多个小模块，每个模块职责单一
2. **提高可测试性**：独立模块更容易编写单元测试
3. **降低复杂度**：每个文件约 50-250 行，易于理解
4. **保持兼容性**：对外接口保持不变，不影响现有代码

---

## 2. 拆分方案（方案一：按功能域）

### 2.1 目录结构

```
src/mind/conversation/
├── __init__.py          # 模块入口，延迟导入
├── manager.py           # 核心协调器（精简后）
├── flow.py              # 对话流程控制
├── interaction.py       # 用户交互处理
├── search_handler.py    # 搜索功能
├── ending.py            # 对话结束处理
└── progress.py          # UI/进度显示 ✅ 已完成
```

### 2.2 各模块职责

#### 2.2.1 `progress.py` ✅ 已完成

**职责**：Token 使用进度显示

**类和方法**：
- `ProgressDisplay.show_token_progress(tokens, max_tokens)` - 显示进度条

**代码行数**：~50 行

**状态**：✅ 已完成并提交

---

#### 2.2.2 `search_handler.py`

**职责**：搜索功能处理

**类和方法**：
- `SearchHandler.__init__(manager)`
- `SearchHandler.extract_search_query() -> str | None` - 从对话历史提取关键词
- `SearchHandler.has_search_request(response: str) -> bool` - 检测搜索请求
- `SearchHandler.should_trigger_search(last_response: str | None) -> bool` - 判断是否触发搜索
- `SearchHandler.execute_search(query: str) -> str | None` - 执行搜索（新增）

**原代码位置**：`conversation.py:543-647`

**代码行数**：~120 行

**依赖**：
- `re` - 正则表达式
- `logging` - 日志

---

#### 2.2.3 `interaction.py`

**职责**：用户交互处理

**类和方法**：
- `InteractionHandler.is_input_ready() -> bool` - 检查输入就绪（静态方法）
- `InteractionHandler.__init__(manager)`
- `InteractionHandler.input_mode()` - 输入模式
- `InteractionHandler.wait_for_user_input()` - 后台监听用户输入
- `InteractionHandler.handle_user_input(user_input: str)` - 处理用户输入

**原代码位置**：
- `conversation.py:46-54` (_is_input_ready)
- `conversation.py:496-521` (_input_mode)
- `conversation.py:523-541` (_wait_for_user_input)
- `conversation.py:905-933` (_handle_user_input)

**代码行数**：~150 行

**依赖**：
- `asyncio`, `select`, `sys` - 异步 I/O
- `rich.console.Console` - UI 输出

---

#### 2.2.4 `ending.py`

**职责**：对话结束处理

**类和方法**：
- `EndingHandler.__init__(manager)`
- `EndingHandler.handle_proposal(agent_name: str, response: str)` - 处理结束提议

**原代码位置**：`conversation.py:935-1008`

**代码行数**：~100 行

**依赖**：
- `asyncio` - 异步操作
- `rich.console.Console` - UI 输出

---

#### 2.2.5 `flow.py`

**职责**：对话流程控制

**类和方法**：
- `FlowController.__init__(manager)`
- `FlowController.start(topic: str)` - 交互式对话主循环
- `FlowController.run_auto(topic: str, max_turns: int) -> str` - 非交互式自动对话
- `FlowController._turn()` - 执行一轮对话

**原代码位置**：
- `conversation.py:231-276` (start)
- `conversation.py:278-494` (run_auto)
- `conversation.py:649-903` (_turn)

**代码行数**：~250 行

**依赖**：
- 其他处理器（InteractionHandler, SearchHandler, EndingHandler）
- `anthropic.types.MessageParam`
- `datetime`, `json`, `pathlib`

---

#### 2.2.6 `manager.py`

**职责**：核心数据类和协调器

**类和方法**：
- `ConversationManager` (dataclass) - 核心数据类
- `ConversationManager.__post_init__()` - 初始化处理器
- `ConversationManager.start(topic: str)` - 委托给 FlowController
- `ConversationManager.run_auto(topic: str, max_turns: int)` - 委托给 FlowController
- `ConversationManager.save_conversation()` - 保持原有
- `ConversationManager.should_exit_after_trim()` - 保持原有
- `ConversationManager._summarize_conversation()` - 保持原有
- `ConversationManager._show_token_progress()` - 委托给 ProgressDisplay

**代码行数**：~200 行

**依赖**：
- `FlowController`, `InteractionHandler`, `SearchHandler`, `EndingHandler`, `ProgressDisplay`
- 原有依赖（Agent, MemoryManager, SearchHistory, SummarizerAgent 等）

---

## 3. 迁移步骤

### 3.1 已完成

| 步骤 | 状态 | Git 提交 |
|------|------|----------|
| 创建目录结构和测试 | ✅ | `eb63f04` test: 添加 conversation 子模块导入测试 |
| 实现 ProgressDisplay | ✅ | `0558023` feat: 实现 ProgressDisplay 模块 |

### 3.2 待完成（按顺序）

#### 步骤 1：实现 SearchHandler

```bash
# 1. 创建模块
touch src/mind/conversation/search_handler.py

# 2. 从 conversation.py 迁移代码（543-647 行）
#    - _extract_search_query -> SearchHandler.extract_search_query
#    - _has_search_request -> SearchHandler.has_search_request
#    - _extract_search_from_response -> SearchHandler.extract_search_from_response
#    - _should_trigger_search -> SearchHandler.should_trigger_search

# 3. 更新 __init__.py 添加到 __getattr__

# 4. 编写测试
touch tests/unit/conversation/test_search_handler.py

# 5. 运行测试并提交
```

#### 步骤 2：实现 InteractionHandler

```bash
# 类似步骤 1
# 从 conversation.py 迁移：46-54, 496-521, 523-541, 905-933
```

#### 步骤 3：实现 EndingHandler

```bash
# 从 conversation.py 迁移：935-1008
```

#### 步骤 4：实现 FlowController

```bash
# 从 conversation.py 迁移：231-276, 278-494, 649-903
# 这个模块依赖其他所有处理器
```

#### 步骤 5：重构 Manager

```bash
# 1. 创建 manager.py
# 2. 将 ConversationManager 转换为数据类 + 委托模式
# 3. 更新 __init__.py
# 4. 原 conversation.py 保留为兼容层或删除
```

---

## 4. 测试策略

### 4.1 单元测试

每个模块都应有独立的单元测试：

```
tests/unit/conversation/
├── test_module_imports.py       ✅ 已完成
├── test_progress.py              # ProgressDisplay 测试
├── test_search_handler.py        # SearchHandler 测试
├── test_interaction.py           # InteractionHandler 测试
├── test_ending.py                # EndingHandler 测试
├── test_flow.py                  # FlowController 测试
└── test_manager.py               # ConversationManager 测试
```

### 4.2 测试覆盖率目标

- **核心模块**（FlowController, Manager）：≥80%
- **处理器模块**（SearchHandler, InteractionHandler, EndingHandler）：≥70%
- **工具模块**（ProgressDisplay）：≥90%

### 4.3 集成测试

确保拆分后，`ConversationManager` 的行为与原有一致：

```python
# tests/integration/test_conversation_integration.py
async def test_conversation_manager_basic_flow():
    """测试基本对话流程"""
    manager = ConversationManager(agent_a, agent_b)
    result = await manager.run_auto("测试主题", max_turns=2)
    assert "测试主题" in result
```

---

## 5. 兼容性保证

### 5.1 向后兼容

拆分后，原有 API 保持不变：

```python
# 原有代码继续工作
from mind.conversation import ConversationManager

manager = ConversationManager(agent_a, agent_b)
await manager.start("主题")
result = await manager.run_auto("主题", max_turns=10)
```

### 5.2 渐进迁移

可以采用以下策略之一：

**策略 A：原地重构**
- 直接在 `conversation.py` 中拆分类
- 优点：一次性完成
- 缺点：中间状态难以测试

**策略 B：创建新模块，逐步替换（推荐）**
- 创建 `conversation/` 子模块
- 逐步迁移功能
- 原文件作为兼容层
- 优点：每步可测试，可回滚
- 缺点：过渡期有代码重复

**策略 C：分支重构**
- 创建 `refactor/conversation` 分支
- 完成重构后合并
- 优点：不影响主分支
- 缺点：合并冲突可能较多

---

## 6. 时间估算

| 模块 | 复杂度 | 预计时间 | 状态 |
|------|--------|----------|------|
| ProgressDisplay | 低 | 0.5h | ✅ 完成 |
| SearchHandler | 中 | 1.5h | ⏳ 待开始 |
| InteractionHandler | 中 | 2h | ⏳ 待开始 |
| EndingHandler | 中 | 1.5h | ⏳ 待开始 |
| FlowController | 高 | 3h | ⏳ 待开始 |
| Manager | 高 | 2h | ⏳ 待开始 |
| 测试与调试 | - | 2h | ⏳ 待开始 |
| **总计** | - | **12.5h** | **~20% 完成** |

---

## 7. 风险与缓解

### 7.1 风险

| 风险 | 影响 | 概率 | 缓解措施 |
|------|------|------|----------|
| 循环导入 | 编译失败 | 中 | 使用延迟导入 (`__getattr__`) |
| 破坏现有功能 | 回归 | 中 | 完善的单元测试和集成测试 |
| 类型注解错误 | 类型检查失败 | 低 | 使用 `TYPE_CHECKING` 和 `# type: ignore` |
| Git 冲突 | 合并困难 | 低 | 频繁提交小改动 |

### 7.2 回滚计划

如果重构出现严重问题：
1. 使用 `git revert` 回滚有问题的提交
2. 或直接回滚到重构前的 commit：
   ```bash
   git log --oneline  # 找到重构前的 commit
   git reset --hard <commit-sha>
   ```

---

## 8. 验收标准

重构完成后，应满足：

1. ✅ 所有测试通过（单元测试 + 集成测试）
2. ✅ mypy 类型检查通过
3. ✅ ruff 代码检查通过
4. ✅ 每个文件 ≤300 行
5. ✅ 每个类职责单一
6. ✅ 对外 API 保持兼容
7. ✅ 测试覆盖率 ≥70%

---

## 9. 参考资料

- [Python 软件设计模式](https://refactoring.guru/design-patterns/python)
- [单一职责原则 (SRP)](https://en.wikipedia.org/wiki/Single-responsibility_principle)
- [TDD 最佳实践](https://testdrivendevelopment.best/)
- [项目 CLAUDE.md](../../CLAUDE.md)

---

**文档版本**：v1.0
**创建日期**：2026-01-02
**最后更新**：2026-01-02
**负责人**：Claude Code AI Assistant
