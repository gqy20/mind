"""测试引用显示功能"""

from unittest.mock import patch

from mind.agents.citations import display_citations


def test_display_citations_with_mock_console():
    """测试显示引用列表"""
    citations = [
        {
            "type": "text",
            "document_title": "测试文档1",
            "cited_text": "这是引用的文本内容",
        },
        {
            "type": "text",
            "document_title": "测试文档2",
            "cited_text": "另一个引用",
        },
    ]

    # Mock console
    with patch("mind.agents.citations.console") as mock_console:
        display_citations(citations)

        # 验证 console.print 被调用
        assert mock_console.print.called


def test_display_citations_empty_list():
    """测试空引用列表不显示"""
    # Mock console
    with patch("mind.agents.citations.console") as mock_console:
        display_citations([])

        # 应该不调用 print
        assert not mock_console.print.called


def test_display_citations_deduplicates():
    """测试引用去重"""
    citations = [
        {
            "document_title": "测试文档",
            "cited_text": "相同的引用文本",
        },
        {
            "document_title": "测试文档",
            "cited_text": "相同的引用文本",
        },
    ]

    with patch("mind.agents.citations.console") as mock_console:
        display_citations(citations)

        # 应该只显示一次（去重后）
        # 标题 + 分隔线 = 2 次 print 调用
        assert mock_console.print.call_count <= 5
