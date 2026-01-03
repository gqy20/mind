"""测试引用显示功能"""

from unittest.mock import patch

from mind.display.citations import display_citations


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

    # Mock console（使用新的导入路径）
    with patch("mind.display.citations.console") as mock_console:
        display_citations(citations)

        # 验证 console.print 被调用
        assert mock_console.print.called


def test_display_citations_empty_list():
    """测试空引用列表不显示"""
    # Mock console（使用新的导入路径）
    with patch("mind.display.citations.console") as mock_console:
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

    with patch("mind.display.citations.console") as mock_console:
        display_citations(citations)

        # 应该只显示一次（去重后）
        # 空行 + 分隔线 + 标题 + 1个引用 + 空行 ≈ 5-6 次
        # 关键是只调用一次引用的打印
        title_calls = [
            call
            for call in mock_console.print.call_args_list
            if "测试文档" in str(call)
        ]
        assert len(title_calls) == 1
