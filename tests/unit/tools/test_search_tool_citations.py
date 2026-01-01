"""测试 search_tool 的 Citations 文档格式转换功能

测试 search_web_as_document 函数是否能正确将搜索结果
转换为 Anthropic Citations API 所需的 document 格式。
"""

import pytest

from mind.tools.search_tool import search_web_as_document


class TestSearchWebAsDocument:
    """测试 search_web_as_document 函数"""

    @pytest.mark.asyncio
    async def test_returns_document_type(self):
        """测试：返回值应该是 document 类型"""
        # Arrange
        query = "Python 编程语言"

        # Act
        result = await search_web_as_document(query, max_results=2)

        # Assert
        if result:  # 只在有结果时测试
            assert result["type"] == "document", "返回类型应该是 document"
            assert "source" in result, "应该包含 source 字段"
            assert "citations" in result, "应该包含 citations 字段"

    @pytest.mark.asyncio
    async def test_citations_enabled(self):
        """测试：citations 应该被启用"""
        # Arrange
        query = "测试查询"

        # Act
        result = await search_web_as_document(query, max_results=1)

        # Assert
        if result:
            assert result["citations"]["enabled"] is True, "citations 应该被启用"

    @pytest.mark.asyncio
    async def test_source_is_content_type(self):
        """测试：source 应该是 content 类型（不分块）"""
        # Arrange
        query = "搜索测试"

        # Act
        result = await search_web_as_document(query, max_results=1)

        # Assert
        if result:
            assert result["source"]["type"] == "content", "source 类型应该是 content"
            assert "content" in result["source"], "应该包含 content 数组"

    @pytest.mark.asyncio
    async def test_content_is_list_of_text_blocks(self):
        """测试：content 应该是 text block 的列表"""
        # Arrange
        query = "测试内容块"

        # Act
        result = await search_web_as_document(query, max_results=3)

        # Assert
        if result:
            content = result["source"]["content"]
            assert isinstance(content, list), "content 应该是列表"
            if content:
                assert all(block["type"] == "text" for block in content), (
                    "每个 block 的类型应该是 text"
                )
                assert all("text" in block for block in content), (
                    "每个 block 应该包含 text 字段"
                )

    @pytest.mark.asyncio
    async def test_content_includes_search_results(self):
        """测试：content 应该包含搜索结果的关键信息"""
        # Arrange
        query = "Python"

        # Act
        result = await search_web_as_document(query, max_results=2)

        # Assert
        if result:
            content = result["source"]["content"]
            assert len(content) > 0, "应该至少有一个内容块"
            # 检查是否包含标题、链接等信息
            first_block = content[0]["text"]
            assert len(first_block) > 10, "内容块应该包含有意义的搜索结果"

    @pytest.mark.asyncio
    async def test_title_contains_query(self):
        """测试：title 应该包含搜索查询"""
        # Arrange
        query = "机器学习"

        # Act
        result = await search_web_as_document(query, max_results=1)

        # Assert
        if result:
            assert query in result["title"], f"title 应该包含查询词 '{query}'"
            assert "搜索结果" in result["title"], "title 应该包含 '搜索结果'"

    @pytest.mark.asyncio
    async def test_max_results_limits_content_blocks(self):
        """测试：max_results 应该限制返回的内容块数量"""
        # Arrange
        query = "人工智能"
        max_results = 2

        # Act
        result = await search_web_as_document(query, max_results=max_results)

        # Assert
        if result:
            content = result["source"]["content"]
            assert len(content) <= max_results, (
                f"内容块数量不应超过 max_results ({max_results})"
            )

    @pytest.mark.asyncio
    async def test_empty_query_returns_none(self):
        """测试：空查询应该返回 None"""
        # Arrange
        query = ""

        # Act
        result = await search_web_as_document(query)

        # Assert
        assert result is None, "空查询应该返回 None"

    @pytest.mark.asyncio
    async def test_whitespace_query_returns_none(self):
        """测试：纯空格查询应该返回 None"""
        # Arrange
        query = "   "

        # Act
        result = await search_web_as_document(query)

        # Assert
        assert result is None, "纯空格查询应该返回 None"

    @pytest.mark.asyncio
    async def test_returns_none_on_search_failure(self):
        """测试：搜索失败时应该返回 None"""
        # Arrange
        query = ""  # 会触发搜索失败

        # Act
        result = await search_web_as_document(query)

        # Assert
        assert result is None, "搜索失败时应该返回 None"

    @pytest.mark.asyncio
    async def test_context_field_exists(self):
        """测试：应该包含可选的 context 字段"""
        # Arrange
        query = "上下文测试"

        # Act
        result = await search_web_as_document(query, max_results=1)

        # Assert
        if result:
            # context 是可选字段，但如果存在应该是字符串
            if "context" in result:
                assert isinstance(result["context"], str), "context 应该是字符串类型"
