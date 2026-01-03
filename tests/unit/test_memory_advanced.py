"""记忆管理模块的高级测试

补充测试更多边界情况和实际场景：
- 混合语言 Token 计数
- 特殊字符和格式化内容
- 消息格式处理
- 清理策略的边界条件
"""

from mind.conversation.memory import MemoryManager, TokenConfig


class TestTokenCountingAdvanced:
    """测试高级 Token 计数场景"""

    def test_count_mixed_chinese_english(self):
        """测试：中英文混合文本应正确估算"""
        # Arrange
        manager = MemoryManager()

        # Act - 中英文混合，实际测量长度
        text = "你好Hello世界Test测试" * 10  # 实际 150 字符 (15 字符/次 * 10)
        tokens = manager._count_tokens(text)

        # Assert - 150 字符整除 4 = 37 tokens
        assert tokens == 37

    def test_count_with_special_characters(self):
        """测试：包含特殊字符的文本应正确估算"""
        # Arrange
        manager = MemoryManager()

        # Act - 包含标点、符号，实际长度是 152 字符
        text = "Hello! @#$%^&*()_+-={}[]|\\:;\"'<>,.?/~`" * 4
        tokens = manager._count_tokens(text)

        # Assert - 152 字符整除 4 = 38 tokens
        assert tokens == 38

    def test_count_with_markdown_formatting(self):
        """测试：包含 Markdown 格式的文本应正确估算"""
        # Arrange
        manager = MemoryManager()

        # Act - Markdown 内容，实际约 212 字符
        text = (
            """
        # 标题
        **粗体** 和 *斜体*
        - 列表项1
        - 列表项2
        `代码块`
        [链接](url)
        """
            * 2
        )
        tokens = manager._count_tokens(text)

        # Assert - 212 字符整除 4 = 53 tokens
        assert tokens == 53

    def test_count_very_long_message(self):
        """测试：超长消息应正确估算"""
        # Arrange
        manager = MemoryManager()

        # Act - 10,000 字符
        text = "A" * 10000
        tokens = manager._count_tokens(text)

        # Assert - 10000 字符约为 2500 tokens
        assert tokens == 2500

    def test_count_single_character(self):
        """测试：单个字符的 token 计数"""
        # Arrange
        manager = MemoryManager()

        # Act
        tokens = manager._count_tokens("A")

        # Assert - 1 字符，整除 4 = 0
        assert tokens == 0

    def test_count_whitespace_only(self):
        """测试：只有空白字符的文本"""
        # Arrange
        manager = MemoryManager()

        # Act - 实际 6 个可见空白字符
        tokens = manager._count_tokens("   \n\t  ")

        # Assert - 6 字符整除 4 = 1 token
        assert tokens == 1


class TestAddMessageEdgeCases:
    """测试添加消息的边界情况"""

    def test_add_empty_content(self):
        """测试：添加空内容消息"""
        # Arrange
        manager = MemoryManager()

        # Act
        message = manager.add_message("user", "")

        # Assert
        assert message["role"] == "user"
        assert message["content"] == ""
        assert manager._total_tokens == 0
        assert len(manager._message_tokens) == 1
        assert manager._message_tokens[0] == 0

    def test_add_very_long_content(self):
        """测试：添加超长内容消息"""
        # Arrange
        manager = MemoryManager()
        long_content = "X" * 100000  # 10 万字符

        # Act
        message = manager.add_message("assistant", long_content)

        # Assert
        assert message["content"] == long_content
        assert manager._total_tokens == 25000  # 100000 // 4

    def test_add_multiple_empty_messages(self):
        """测试：添加多条空消息"""
        # Arrange
        manager = MemoryManager()

        # Act
        manager.add_message("user", "")
        manager.add_message("assistant", "")
        manager.add_message("user", "")

        # Assert
        assert manager._total_tokens == 0
        assert len(manager._message_tokens) == 3

    def test_add_message_with_newlines(self):
        """测试：包含换行符的消息"""
        # Arrange
        manager = MemoryManager()

        # Act - 换行符也算字符
        content = "Line 1\nLine 2\nLine 3\n"  # 23 字符
        manager.add_message("user", content)

        # Assert - 23 // 4 = 5
        assert manager._total_tokens == 5


class TestTrimBehaviorAdvanced:
    """测试高级清理行为"""

    def test_trim_exact_target(self):
        """测试：清理到精确目标值附近"""
        # Arrange
        manager = MemoryManager(
            TokenConfig(
                max_context=10_000,
                target_after_trim=5_000,
                min_keep_recent=2,
            )
        )

        # 创建消息，每条 2500 tokens（10000 字符）
        messages = []
        for i in range(5):
            content = "M" * 10000
            msg = {"role": "user", "content": f"Message {i}: {content}"}
            messages.append(msg)
            manager.add_message(msg["role"], msg["content"])

        # 总 tokens: 5 * 2500 = 12500，需要清理

        # Act
        manager.trim_messages(messages)

        # Assert - 应该接近目标 (5000) ± 一条消息的误差
        assert manager._total_tokens <= 7500  # target + 1条消息
        assert manager._total_tokens >= 2500  # 至少 min_keep_recent * 2500

    def test_trim_preserves_message_order(self):
        """测试：清理后应保持消息顺序"""
        # Arrange
        manager = MemoryManager(
            TokenConfig(
                max_context=10_000,
                target_after_trim=5_000,
                min_keep_recent=2,
            )
        )

        messages = []
        for i in range(5):
            content = "M" * 10000  # 2500 tokens
            msg = {"role": "user", "content": f"Message {i}: {content}"}
            messages.append(msg)
            manager.add_message(msg["role"], msg["content"])

        # Act
        result = manager.trim_messages(messages)

        # Assert - 验证顺序
        for i in range(len(result) - 1):
            msg_num = int(result[i]["content"].split(":")[0].split()[1])
            next_msg_num = int(result[i + 1]["content"].split(":")[0].split()[1])
            assert msg_num < next_msg_num

    def test_trim_with_exact_max_context(self):
        """测试：正好达到 max_context 时应触发清理"""
        # Arrange
        manager = MemoryManager(
            TokenConfig(
                max_context=10_000,
                target_after_trim=5_000,
                min_keep_recent=2,
            )
        )

        # 创建恰好 10000 tokens 的消息
        messages = []
        for i in range(4):
            content = "M" * 10000  # 2500 tokens
            msg = {"role": "user", "content": f"Message {i}: {content}"}
            messages.append(msg)
            manager.add_message(msg["role"], msg["content"])

        # 总 tokens: 4 * 2500 = 10000 = max_context

        # Act
        result = manager.trim_messages(messages)

        # Assert - 应该触发清理
        assert len(result) < len(messages)

    def test_trim_updates_internal_state(self):
        """测试：清理后内部状态应同步更新"""
        # Arrange
        manager = MemoryManager(
            TokenConfig(
                max_context=10_000,
                target_after_trim=5_000,
                min_keep_recent=2,
            )
        )

        messages = []
        for i in range(5):
            content = "M" * 10000  # 2500 tokens
            msg = {"role": "user", "content": f"Message {i}: {content}"}
            messages.append(msg)
            manager.add_message(msg["role"], msg["content"])

        # Act
        result = manager.trim_messages(messages)

        # Assert - _message_tokens 应该被正确更新
        assert len(manager._message_tokens) == len(result)
        # 验证每个 token 计数与消息内容匹配
        for i, msg in enumerate(result):
            expected_tokens = manager._count_tokens(msg["content"])
            assert manager._message_tokens[i] == expected_tokens


class TestStatusTransitions:
    """测试状态转换"""

    def test_status_transition_green_to_yellow(self):
        """测试：从 green 到 yellow 的转换"""
        # Arrange
        manager = MemoryManager(
            TokenConfig(
                max_context=150_000,
                warning_threshold=100_000,
            )
        )

        # 初始状态: green
        manager._total_tokens = 50_000
        assert manager.get_status() == "green"

        # Act - 增加到 yellow
        manager._total_tokens = 120_000

        # Assert
        assert manager.get_status() == "yellow"

    def test_status_transition_yellow_to_red(self):
        """测试：从 yellow 到 red 的转换"""
        # Arrange
        manager = MemoryManager(
            TokenConfig(
                max_context=150_000,
                warning_threshold=100_000,
            )
        )

        # 初始状态: yellow
        manager._total_tokens = 120_000
        assert manager.get_status() == "yellow"

        # Act - 增加到 red
        manager._total_tokens = 160_000

        # Assert
        assert manager.get_status() == "red"

    def test_status_transition_red_to_green_after_trim(self):
        """测试：清理后从 red 到 green 的转换"""
        # Arrange
        manager = MemoryManager(
            TokenConfig(
                max_context=12_000,  # 降低 max_context 确保 red 状态
                warning_threshold=8_000,
                target_after_trim=5_000,
                min_keep_recent=2,
            )
        )

        # 创建超过 max 的消息
        messages = []
        for i in range(5):
            content = "M" * 10000  # 2500 tokens
            msg = {"role": "user", "content": f"Message {i}: {content}"}
            messages.append(msg)
            manager.add_message(msg["role"], msg["content"])

        # 状态应该是 red (12500 > 12000)
        assert manager.get_status() == "red"

        # Act - 清理
        manager.trim_messages(messages)

        # Assert - 应该回到 green
        assert manager.get_status() == "green"


class TestConfigValidation:
    """测试配置验证"""

    def test_config_with_min_keep_too_large(self):
        """测试：min_keep_recent 大于消息列表"""
        # Arrange
        manager = MemoryManager(
            TokenConfig(
                max_context=10_000,
                target_after_trim=5_000,
                min_keep_recent=100,  # 超大值
            )
        )

        messages = [
            {"role": "user", "content": "Message 1"},
            {"role": "assistant", "content": "Response 1"},
        ]
        for msg in messages:
            manager.add_message(msg["role"], msg["content"])

        # Act - 不应该报错，min_idx 应该被限制为 0
        result = manager.trim_messages(messages)

        # Assert
        assert result is not None

    def test_config_with_zero_min_keep(self):
        """测试：min_keep_recent 为 0"""
        # Arrange
        manager = MemoryManager(
            TokenConfig(
                max_context=10_000,
                target_after_trim=5_000,
                min_keep_recent=0,  # 不保留任何消息
            )
        )

        # 创建超限消息
        messages = []
        for i in range(3):
            content = "M" * 10000  # 2500 tokens
            msg = {"role": "user", "content": f"Message {i}: {content}"}
            messages.append(msg)
            manager.add_message(msg["role"], msg["content"])

        # Act
        result = manager.trim_messages(messages)

        # Assert - 可能返回空列表或只保留能放入目标的消息
        assert isinstance(result, list)
