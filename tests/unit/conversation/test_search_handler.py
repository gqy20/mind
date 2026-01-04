"""测试 SearchHandler 搜索处理功能

测试搜索关键词提取、搜索请求检测和触发条件判断。
"""

from unittest.mock import MagicMock


class TestSearchHandler:
    """测试 SearchHandler 类"""

    def test_search_handler_can_be_imported(self):
        """测试 SearchHandler 可以导入"""
        # 使用 importlib 直接导入模块文件，避免触发 mind.__init__.py
        import importlib.util
        from pathlib import Path

        module_path = (
            Path(__file__).parent.parent.parent.parent
            / "src"
            / "mind"
            / "conversation"
            / "search_handler.py"
        )

        spec = importlib.util.spec_from_file_location("search_handler", module_path)
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            assert module.SearchHandler is not None

    def test_extract_search_query_from_user_message(self):
        """测试从用户消息中提取搜索关键词"""
        from mind.conversation.search_handler import SearchHandler

        # 创建模拟 manager
        manager = MagicMock()
        manager.configure_mock(
            messages=[{"role": "user", "content": "Python 异步编程最佳实践"}],
            topic=None,
        )

        handler = SearchHandler(manager)
        query = handler.extract_search_query()

        assert query == "Python 异步编程最佳实践"

    def test_extract_search_query_with_command_prefix(self):
        """测试过滤命令前缀"""
        from mind.conversation.search_handler import SearchHandler

        manager = MagicMock()
        manager.configure_mock(
            messages=[{"role": "user", "content": "/quit"}],
            topic=None,
        )

        handler = SearchHandler(manager)
        query = handler.extract_search_query()

        assert query is None

    def test_extract_search_query_fallback_to_topic(self):
        """测试回退到对话主题"""
        from mind.conversation.search_handler import SearchHandler

        # 使用简单对象代替 MagicMock，避免属性访问问题
        class SimpleManager:
            messages = []
            topic = "人工智能发展趋势"
            enable_search = False
            search_interval = 0
            turn = 0

        manager = SimpleManager()

        handler = SearchHandler(manager)
        query = handler.extract_search_query()

        assert query == "人工智能发展趋势"

    def test_extract_search_query_from_assistant_response(self):
        """测试从助手回复中提取关键词"""
        from mind.conversation.search_handler import SearchHandler

        manager = MagicMock()
        assistant_msg = "我认为异步编程在 Python 中非常重要"
        manager.configure_mock(
            messages=[{"role": "assistant", "content": assistant_msg}],
            topic=None,
        )

        handler = SearchHandler(manager)
        query = handler.extract_search_query()

        assert query is not None
        assert len(query) > 0

    def test_has_search_request_with_pattern(self):
        """测试检测搜索请求模式"""
        from mind.conversation.search_handler import SearchHandler

        manager = MagicMock()
        handler = SearchHandler(manager)

        response = "我需要了解更多信息 [搜索: Python 装饰器]"
        assert handler.has_search_request(response) is True

    def test_has_search_request_without_pattern(self):
        """测试没有搜索请求模式时返回 False"""
        from mind.conversation.search_handler import SearchHandler

        manager = MagicMock()
        handler = SearchHandler(manager)

        response = "这是一个普通的响应"
        assert handler.has_search_request(response) is False

    def test_extract_search_from_response(self):
        """测试从响应中提取搜索关键词"""
        from mind.conversation.search_handler import SearchHandler

        manager = MagicMock()
        handler = SearchHandler(manager)

        response = "我需要了解更多信息 [搜索: Python 装饰器]"
        query = handler.extract_search_from_response(response)

        assert query == "Python 装饰器"

    def test_should_trigger_search_by_ai_request(self):
        """测试 AI 主动请求时触发搜索"""
        from mind.conversation.search_handler import SearchHandler

        manager = MagicMock()
        manager.enable_search = True
        manager.search_interval = 0
        manager.turn = 1

        handler = SearchHandler(manager)
        last_response = "我需要更多信息 [搜索: 深度学习]"

        assert handler.should_trigger_search(last_response) is True

    def test_should_trigger_search_by_interval(self):
        """测试达到搜索间隔时触发搜索"""
        from mind.conversation.search_handler import SearchHandler

        manager = MagicMock()
        manager.enable_search = True
        manager.search_interval = 3
        manager.turn = 3

        handler = SearchHandler(manager)
        assert handler.should_trigger_search() is True

    def test_should_not_trigger_search_when_disabled(self):
        """测试搜索禁用时不触发"""
        from mind.conversation.search_handler import SearchHandler

        manager = MagicMock()
        manager.enable_search = False
        manager.search_interval = 3
        manager.turn = 3

        handler = SearchHandler(manager)
        assert handler.should_trigger_search() is False

    def test_should_not_trigger_search_on_turn_zero(self):
        """测试第 0 轮不触发间隔搜索"""
        from mind.conversation.search_handler import SearchHandler

        manager = MagicMock()
        manager.enable_search = True
        manager.search_interval = 3
        manager.turn = 0

        handler = SearchHandler(manager)
        assert handler.should_trigger_search() is False

    def test_extract_search_query_limits_length(self):
        """测试搜索关键词长度限制"""
        from mind.conversation.search_handler import SearchHandler

        manager = MagicMock()
        manager.configure_mock(
            messages=[{"role": "user", "content": "a" * 200}],
            topic=None,
        )

        handler = SearchHandler(manager)
        query = handler.extract_search_query()

        assert len(query) == 100

    def test_extract_search_query_skips_turn_marker(self):
        """测试跳过轮次标记"""
        from mind.conversation.search_handler import SearchHandler

        manager = MagicMock()
        manager.configure_mock(
            messages=[
                # 最新的消息是轮次标记
                {"role": "user", "content": "现在由 挑战者 发言"},
                # 之前的消息是真实用户消息
                {"role": "user", "content": "Python 异步编程最佳实践"},
            ],
            topic=None,
        )

        handler = SearchHandler(manager)
        query = handler.extract_search_query()

        # 应该跳过轮次标记，使用真实的用户消息
        assert query == "Python 异步编程最佳实践"

    def test_extract_search_query_multiple_turn_markers(self):
        """测试多个轮次标记的情况"""
        from mind.conversation.search_handler import SearchHandler

        manager = MagicMock()
        manager.configure_mock(
            messages=[
                {"role": "user", "content": "现在由 挑战者 发言"},
                {"role": "assistant", "content": "之前的回答"},
                {"role": "user", "content": "现在由 支持者 发言"},
                {"role": "assistant", "content": "更之前的回答"},
                # 真实的用户消息
                {"role": "user", "content": "什么是同倍体杂交？"},
            ],
            topic="同倍体杂交物种形成",
        )

        handler = SearchHandler(manager)
        query = handler.extract_search_query()

        # 应该跳过所有轮次标记，使用真实的用户消息
        assert query == "什么是同倍体杂交？"

    def test_extract_search_query_skips_tool_analysis_result(self):
        """测试跳过工具分析结果（上下文更新）"""
        from mind.conversation.search_handler import SearchHandler

        manager = MagicMock()
        manager.configure_mock(
            messages=[
                # 最新的消息是工具分析结果
                {
                    "role": "user",
                    "content": (
                        "[上下文更新]\n**对话轮次**: 5 轮交流\n**主要观点**: ..."
                    ),
                },
                # 之前的消息是真实用户消息
                {"role": "user", "content": "同倍体杂交物种形成的研究进展"},
            ],
            topic=None,
        )

        handler = SearchHandler(manager)
        query = handler.extract_search_query()

        # 应该跳过工具分析结果，使用真实的用户消息
        assert query == "同倍体杂交物种形成的研究进展"

    def test_extract_search_query_skips_system_message(self):
        """测试跳过系统消息"""
        from mind.conversation.search_handler import SearchHandler

        manager = MagicMock()
        manager.configure_mock(
            messages=[
                # 最新的消息是系统消息
                {
                    "role": "user",
                    "content": "[系统消息 - 网络搜索结果]\n搜索结果...",
                },
                # 之前的消息是真实用户消息
                {"role": "user", "content": "量子计算的最新突破"},
            ],
            topic=None,
        )

        handler = SearchHandler(manager)
        query = handler.extract_search_query()

        # 应该跳过系统消息，使用真实的用户消息
        assert query == "量子计算的最新突破"
