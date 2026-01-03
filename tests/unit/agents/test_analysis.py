"""测试对话分析功能"""

from unittest.mock import patch

from mind.agents.conversation_analyzer import (
    ConversationAnalyzer,
    analyze_conversation,
)


def test_analyze_conversation_empty_messages():
    """测试空对话返回 None"""
    result = analyze_conversation(messages=[])

    assert result is None


def test_analyze_conversation_with_simple_conversation():
    """测试简单对话分析"""
    messages = [
        {"role": "user", "content": "什么是人工智能？"},
        {"role": "assistant", "content": "人工智能是计算机科学的一个分支。"},
    ]

    result = analyze_conversation(messages)

    assert result is not None
    assert "对话话题" in result
    assert "人工智能" in result
    assert "对话轮次" in result


def test_analyze_conversation_with_structured_content():
    """测试结构化内容的对话分析"""
    messages = [
        {
            "role": "user",
            "content": [{"type": "text", "text": "你好"}],
        },
        {
            "role": "assistant",
            "content": "你好！有什么可以帮助你的吗？",
        },
    ]

    result = analyze_conversation(messages)

    assert result is not None
    assert "对话话题" in result


def test_analyze_conversation_skips_system_messages():
    """测试跳过系统消息"""
    messages = [
        {"role": "system", "content": "你是一个助手"},
        {"role": "user", "content": "你好"},
    ]

    result = analyze_conversation(messages)

    assert result is not None
    # 应该只有用户消息被计入
    assert "对话话题" in result


def test_conversation_analyzer_class():
    """测试 ConversationAnalyzer 类"""
    messages = [
        {"role": "user", "content": "主题1"},
        {"role": "assistant", "content": "回复1"},
        {"role": "user", "content": "主题2"},
        {"role": "assistant", "content": "回复2"},
    ]

    analyzer = ConversationAnalyzer()
    result = analyzer.analyze(messages)

    assert result is not None
    assert "2 轮交流" in result or "2轮交流" in result
    assert "主要观点" in result


def test_analyze_conversation_with_mock_logger():
    """测试分析时记录日志"""
    messages = [
        {"role": "user", "content": "测试"},
        {"role": "assistant", "content": "响应"},
    ]

    with patch("mind.agents.conversation_analyzer.logger") as mock_logger:
        result = analyze_conversation(messages)

        assert result is not None
        # 验证日志被调用
        assert mock_logger.info.called or mock_logger.debug.called
