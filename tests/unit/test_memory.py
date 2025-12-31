"""
记忆管理模块的单元测试

测试基于 Token 监控的对话历史管理：
- Token 计数
- 状态判断（green/yellow/red）
- 消息添加和更新
- 清理策略（从后往前保留）
- 边界保护（最少保留轮数）
"""

import pytest

from mind.memory import MemoryManager, TokenConfig


class TestTokenConfig:
    """测试 TokenConfig 配置类"""

    def test_default_values(self):
        """测试：应有合理的默认值"""
        # Arrange & Act
        config = TokenConfig()

        # Assert
        assert config.max_context == 150_000
        assert config.warning_threshold == 120_000
        assert config.target_after_trim == 80_000
        assert config.min_keep_recent == 10

    def test_custom_values(self):
        """测试：应支持自定义配置"""
        # Arrange & Act
        config = TokenConfig(
            max_context=100_000,
            warning_threshold=80_000,
            target_after_trim=50_000,
            min_keep_recent=5,
        )

        # Assert
        assert config.max_context == 100_000
        assert config.warning_threshold == 80_000
        assert config.target_after_trim == 50_000
        assert config.min_keep_recent == 5


class TestMemoryManagerInit:
    """测试 MemoryManager 初始化"""

    def test_init_with_default_config(self):
        """测试：应使用默认配置初始化"""
        # Arrange & Act
        manager = MemoryManager()

        # Assert
        assert manager._total_tokens == 0
        assert manager._message_tokens == []
        assert manager.config.max_context == 150_000

    def test_init_with_custom_config(self):
        """测试：应使用自定义配置初始化"""
        # Arrange
        config = TokenConfig(max_context=100_000)

        # Act
        manager = MemoryManager(config)

        # Assert
        assert manager.config is config
        assert manager.config.max_context == 100_000


class TestCountTokens:
    """测试 Token 计数功能"""

    def test_count_empty_string(self):
        """测试：空字符串应为 0 tokens"""
        # Arrange
        manager = MemoryManager()

        # Act
        tokens = manager._count_tokens("")

        # Assert
        assert tokens == 0

    def test_count_short_text(self):
        """测试：短文本应正确估算"""
        # Arrange
        manager = MemoryManager()

        # Act - 100 字符约为 25 tokens
        tokens = manager._count_tokens("a" * 100)

        # Assert
        assert tokens == 25

    def test_count_long_text(self):
        """测试：长文本应正确估算"""
        # Arrange
        manager = MemoryManager()

        # Act - 1000 字符约为 250 tokens
        tokens = manager._count_tokens("a" * 1000)

        # Assert
        assert tokens == 250

    def test_count_chinese_text(self):
        """测试：中文文本应正确估算"""
        # Arrange
        manager = MemoryManager()

        # Act - 中文字符也按 4 字符/token 估算
        tokens = manager._count_tokens("你好世界" * 25)  # 100 字符

        # Assert
        assert tokens == 25


class TestAddMessage:
    """测试添加消息功能"""

    def test_add_first_message(self):
        """测试：添加第一条消息应正确更新计数"""
        # Arrange
        manager = MemoryManager()

        # Act
        message = manager.add_message("user", "Hello world")

        # Assert
        assert message == {"role": "user", "content": "Hello world"}
        assert manager._total_tokens > 0
        assert len(manager._message_tokens) == 1

    def test_add_multiple_messages(self):
        """测试：添加多条消息应累加计数"""
        # Arrange
        manager = MemoryManager()

        # Act
        manager.add_message("user", "First message")
        manager.add_message("assistant", "Second message")
        manager.add_message("user", "Third message")

        # Assert
        assert len(manager._message_tokens) == 3
        assert manager._total_tokens == sum(manager._message_tokens)

    def test_add_message_updates_total(self):
        """测试：添加消息应更新总 token 数"""
        # Arrange
        manager = MemoryManager()
        initial = manager._total_tokens

        # Act
        manager.add_message("user", "This is a test message")

        # Assert
        assert manager._total_tokens > initial


class TestGetStatus:
    """测试状态判断功能"""

    def test_status_green_when_under_warning(self):
        """测试：低于警告阈值应为 green"""
        # Arrange
        manager = MemoryManager(TokenConfig(
            max_context=150_000,
            warning_threshold=100_000,
        ))
        manager._total_tokens = 50_000

        # Act
        status = manager.get_status()

        # Assert
        assert status == "green"

    def test_status_yellow_when_between_warning_and_max(self):
        """测试：在警告阈值和上限之间应为 yellow"""
        # Arrange
        manager = MemoryManager(TokenConfig(
            max_context=150_000,
            warning_threshold=100_000,
        ))
        manager._total_tokens = 120_000

        # Act
        status = manager.get_status()

        # Assert
        assert status == "yellow"

    def test_status_red_when_over_max(self):
        """测试：超过上限应为 red"""
        # Arrange
        manager = MemoryManager(TokenConfig(
            max_context=150_000,
            warning_threshold=100_000,
        ))
        manager._total_tokens = 160_000

        # Act
        status = manager.get_status()

        # Assert
        assert status == "red"

    def test_status_boundary_at_warning_threshold(self):
        """测试：正好在警告阈值应为 yellow"""
        # Arrange
        manager = MemoryManager(TokenConfig(
            max_context=150_000,
            warning_threshold=100_000,
        ))
        manager._total_tokens = 100_000

        # Act
        status = manager.get_status()

        # Assert
        assert status == "yellow"

    def test_status_boundary_at_max(self):
        """测试：正好在上限应为 red"""
        # Arrange
        manager = MemoryManager(TokenConfig(
            max_context=150_000,
            warning_threshold=100_000,
        ))
        manager._total_tokens = 150_000

        # Act
        status = manager.get_status()

        # Assert
        assert status == "red"


class TestShouldTrim:
    """测试清理判断功能"""

    def test_should_not_trim_when_under_max(self):
        """测试：低于上限时不应清理"""
        # Arrange
        manager = MemoryManager(TokenConfig(max_context=150_000))
        manager._total_tokens = 100_000

        # Act
        should_trim = manager.should_trim()

        # Assert
        assert should_trim is False

    def test_should_not_trim_at_exactly_max(self):
        """测试：正好在上限时应清理"""
        # Arrange
        manager = MemoryManager(TokenConfig(max_context=150_000))
        manager._total_tokens = 150_000

        # Act
        should_trim = manager.should_trim()

        # Assert
        assert should_trim is True

    def test_should_trim_when_over_max(self):
        """测试：超过上限时应清理"""
        # Arrange
        manager = MemoryManager(TokenConfig(max_context=150_000))
        manager._total_tokens = 160_000

        # Act
        should_trim = manager.should_trim()

        # Assert
        assert should_trim is True


class TestTrimMessages:
    """测试消息清理功能"""

    def test_trim_no_action_when_under_limit(self):
        """测试：未超限时不应清理"""
        # Arrange
        manager = MemoryManager(TokenConfig(
            max_context=150_000,
            target_after_trim=80_000,
        ))
        messages = [
            {"role": "user", "content": "Message 1"},
            {"role": "assistant", "content": "Response 1"},
            {"role": "user", "content": "Message 2"},
        ]
        manager._total_tokens = 50_000
        for msg in messages:
            manager._message_tokens.append(manager._count_tokens(msg["content"]))

        # Act
        result = manager.trim_messages(messages)

        # Assert
        assert len(result) == len(messages)
        assert result == messages

    def test_trim_keeps_recent_messages(self):
        """测试：清理时应保留最近的消息"""
        # Arrange
        manager = MemoryManager(TokenConfig(
            max_context=20_000,  # 较小值便于测试，确保会触发清理
            target_after_trim=10_000,
            min_keep_recent=2,
        ))

        # 创建 5 条消息，每条约 5000 tokens（20000 字符）
        messages = []
        for i in range(5):
            content = "M" * 20_000  # ~5000 tokens
            msg = {"role": "user", "content": f"Message {i}: {content}"}
            messages.append(msg)
            # 使用 add_message 来正确更新状态
            manager.add_message(msg["role"], msg["content"])

        # 现在总 tokens 应该是 5 * 5000 = 25000，超过 max_context (20000)

        # Act
        result = manager.trim_messages(messages)

        # Assert - 应保留最近的消息（从后往前）
        assert len(result) < len(messages)
        # 最后一条消息应在结果中
        assert result[-1]["content"].startswith("Message 4:")

    def test_trim_respects_min_keep_recent(self):
        """测试：清理时应遵守最少保留轮数"""
        # Arrange
        manager = MemoryManager(TokenConfig(
            max_context=10_000,  # 确保触发清理
            target_after_trim=5_000,
            min_keep_recent=3,
        ))

        # 创建消息，每条约 3000 tokens（12000 字符）
        messages = []
        for i in range(10):
            content = "M" * 12_000  # ~3000 tokens
            msg = {"role": "user", "content": f"Message {i}: {content}"}
            messages.append(msg)
            manager.add_message(msg["role"], msg["content"])

        # 总 tokens 应该是 10 * 3000 = 30000，远超 max_context (10000)

        # Act
        result = manager.trim_messages(messages)

        # Assert - 至少保留 min_keep_recent 条
        assert len(result) >= manager.config.min_keep_recent

    def test_trim_updates_token_counts(self):
        """测试：清理后应更新 token 计数"""
        # Arrange
        manager = MemoryManager(TokenConfig(
            max_context=10_000,  # 确保触发清理
            target_after_trim=5_000,
            min_keep_recent=2,
        ))

        messages = []
        for i in range(5):
            content = "M" * 12_000  # ~3000 tokens
            msg = {"role": "user", "content": f"Message {i}: {content}"}
            messages.append(msg)
            manager.add_message(msg["role"], msg["content"])

        initial_total = manager._total_tokens  # 5 * 3000 = 15000

        # Act
        _ = manager.trim_messages(messages)

        # Assert
        assert manager._total_tokens < initial_total
        # 清理后的 tokens 应该接近 target + min_keep 的 tokens
        expected_max = manager.config.target_after_trim + 3000 * manager.config.min_keep_recent
        assert manager._total_tokens <= expected_max


class TestEdgeCases:
    """测试边界情况"""

    def test_empty_message_list(self):
        """测试：空消息列表应正常处理"""
        # Arrange
        manager = MemoryManager()

        # Act
        result = manager.trim_messages([])

        # Assert
        assert result == []

    def test_single_message(self):
        """测试：单条消息应正常处理"""
        # Arrange
        manager = MemoryManager()
        messages = [{"role": "user", "content": "Hello"}]
        manager.add_message("user", "Hello")

        # Act
        result = manager.trim_messages(messages)

        # Assert
        assert len(result) == 1

    def test_all_messages_fit_in_target(self):
        """测试：所有消息都能放入目标时应全部保留"""
        # Arrange
        manager = MemoryManager(TokenConfig(
            max_context=150_000,
            target_after_trim=100_000,
            min_keep_recent=2,
        ))

        # 创建总 token 数小于 target 的消息
        messages = []
        for i in range(5):
            content = "M" * 1000  # ~250 tokens
            msg = {"role": "user", "content": f"Message {i}: {content}"}
            messages.append(msg)
            manager.add_message(msg["role"], msg["content"])

        # 总 tokens 应该是 5 * 250 = 1250，远小于 target

        # Act
        result = manager.trim_messages(messages)

        # Assert
        assert len(result) == len(messages)
