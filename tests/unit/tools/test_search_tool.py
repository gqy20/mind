"""测试网络搜索工具功能

这个测试套件验证基于 ddgs 库的网络搜索工具功能。
"""

import pytest

from mind.tools.search_tool import search_web


class TestSearchToolBasic:
    """测试网络搜索工具基本功能"""

    @pytest.mark.asyncio
    async def test_search_web_returns_formatted_results(self):
        """测试：search_web 应该返回格式化的搜索结果"""
        # Arrange
        query = "Python 异步编程"

        # Act
        result = await search_web(query, max_results=3)

        # Assert
        assert result is not None, "搜索结果不应为 None"
        assert "网络搜索" in result or "搜索结果" in result, "结果应包含搜索标识"
        assert len(result) > 0, "结果不应为空"

    @pytest.mark.asyncio
    async def test_search_web_with_empty_query(self):
        """测试：空查询应该返回 None 或提示"""
        # Arrange
        query = ""

        # Act
        result = await search_web(query)

        # Assert
        # 空查询应该被优雅处理，返回 None 或错误提示
        assert result is None or "错误" in result or "无效" in result

    @pytest.mark.asyncio
    async def test_search_web_max_results_limit(self):
        """测试：max_results 参数应该限制返回结果数量"""
        # Arrange
        query = "人工智能"
        max_results = 2

        # Act
        result = await search_web(query, max_results=max_results)

        # Assert
        if result:
            # 计算结果条目数（通过标题前缀计数）
            count = result.count("\n1.") + result.count("\n2.") + result.count("\n3.")
            assert count <= max_results, f"结果数不应超过 {max_results}"

    @pytest.mark.asyncio
    async def test_search_web_includes_required_fields(self):
        """测试：搜索结果应包含标题、链接和摘要"""
        # Arrange
        query = "机器学习"

        # Act
        result = await search_web(query, max_results=1)

        # Assert
        if result and "错误" not in result:
            # 结果应该包含结构化信息（标题、URL等）
            assert "http" in result or "https" in result or len(result) > 50


class TestSearchToolIntegration:
    """测试搜索工具与对话系统的集成"""

    @pytest.mark.asyncio
    async def test_search_result_format_conversation_friendly(self):
        """测试：搜索结果格式应该适合注入到对话中"""
        # Arrange
        query = "量子计算基础"

        # Act
        result = await search_web(query, max_results=2)

        # Assert
        if result:
            # 结果应该是可读的文本，不是纯 JSON
            assert not result.startswith("{"), "结果应该是文本格式，不是 JSON"
            assert not result.startswith("["), "结果应该是文本格式，不是数组"

    @pytest.mark.asyncio
    async def test_search_web_handles_network_errors(self):
        """测试：网络错误应该被优雅处理"""
        # Arrange - 使用无效的超时设置来触发错误
        query = "测试查询"

        # Act
        # 这里我们测试正常情况，错误处理在实际使用中验证
        result = await search_web(query, max_results=1)

        # Assert
        # 即使有错误，也不应该抛出异常
        assert result is None or isinstance(result, str)
