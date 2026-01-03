"""测试搜索历史管理功能

测试 SearchHistory 类如何持久化和管理搜索结果，
包括保存、读取最新和历史搜索功能。
"""

import json


class TestSearchHistoryInit:
    """测试 SearchHistory 初始化"""

    def test_init_creates_file_if_not_exists(self, tmp_path):
        """测试：初始化时应创建文件"""
        # Arrange
        from mind.tools.search_history import SearchHistory

        file_path = tmp_path / "search_history.json"

        # Act
        history = SearchHistory(file_path=file_path)

        # Assert
        assert file_path.exists(), "应该创建历史文件"
        assert history.file_path == file_path

    def test_init_loads_existing_file(self, tmp_path):
        """测试：初始化时应加载已有文件"""
        # Arrange
        from mind.tools.search_history import SearchHistory

        file_path = tmp_path / "search_history.json"
        existing_data = {
            "searches": [
                {
                    "query": "test",
                    "timestamp": "2025-01-01T12:00:00",
                    "results": [{"title": "Test"}],
                }
            ]
        }
        file_path.write_text(json.dumps(existing_data))

        # Act
        history = SearchHistory(file_path=file_path)

        # Assert
        assert len(history.data["searches"]) == 1
        assert history.data["searches"][0]["query"] == "test"


class TestSearchHistorySave:
    """测试搜索保存功能"""

    def test_save_search_adds_to_history(self, tmp_path):
        """测试：保存搜索应添加到历史记录"""
        # Arrange
        from mind.tools.search_history import SearchHistory

        history = SearchHistory(file_path=tmp_path / "test.json")
        results = [{"title": "Python", "href": "http://test.com", "body": "..."}]

        # Act
        history.save_search("Python test", results)

        # Assert
        assert len(history.data["searches"]) == 1
        assert history.data["searches"][0]["query"] == "Python test"
        assert history.data["searches"][0]["results"] == results

    def test_save_search_includes_timestamp(self, tmp_path):
        """测试：保存搜索应包含时间戳"""
        # Arrange
        from mind.tools.search_history import SearchHistory

        history = SearchHistory(file_path=tmp_path / "test.json")
        results = [{"title": "Test"}]

        # Act
        history.save_search("query", results)

        # Assert
        assert "timestamp" in history.data["searches"][0]
        # ISO 8601 格式应该包含 T
        assert "T" in history.data["searches"][0]["timestamp"]

    def test_save_search_persists_to_file(self, tmp_path):
        """测试：保存搜索应持久化到文件"""
        # Arrange
        from mind.tools.search_history import SearchHistory

        file_path = tmp_path / "persist.json"
        history = SearchHistory(file_path=file_path)
        results = [{"title": "Test"}]

        # Act
        history.save_search("test query", results)

        # Assert
        content = file_path.read_text()
        data = json.loads(content)
        assert len(data["searches"]) == 1
        assert data["searches"][0]["query"] == "test query"

    def test_save_multiple_searches(self, tmp_path):
        """测试：应支持保存多个搜索"""
        # Arrange
        from mind.tools.search_history import SearchHistory

        history = SearchHistory(file_path=tmp_path / "test.json")

        # Act
        history.save_search("query1", [{"title": "1"}])
        history.save_search("query2", [{"title": "2"}])
        history.save_search("query3", [{"title": "3"}])

        # Assert
        assert len(history.data["searches"]) == 3
        queries = [s["query"] for s in history.data["searches"]]
        assert queries == ["query1", "query2", "query3"]


class TestSearchHistoryGetLatest:
    """测试获取最新搜索功能"""

    def test_get_latest_returns_most_recent_first(self, tmp_path):
        """测试：应按时间倒序返回"""
        # Arrange
        from mind.tools.search_history import SearchHistory

        history = SearchHistory(file_path=tmp_path / "test.json")
        history.save_search("old", [{"title": "Old"}])
        history.save_search("new", [{"title": "New"}])

        # Act
        latest = history.get_latest(2)

        # Assert
        assert len(latest) == 2
        # 最新的应该在前面
        assert latest[0]["query"] == "new"
        assert latest[1]["query"] == "old"

    def test_get_latest_respects_limit(self, tmp_path):
        """测试：应遵守数量限制"""
        # Arrange
        from mind.tools.search_history import SearchHistory

        history = SearchHistory(file_path=tmp_path / "test.json")
        for i in range(5):
            history.save_search(f"query{i}", [{"title": f"Result {i}"}])

        # Act
        latest = history.get_latest(3)

        # Assert
        assert len(latest) == 3
        # 应该返回最后 3 个
        queries = [s["query"] for s in latest]
        assert queries == ["query4", "query3", "query2"]

    def test_get_latest_when_empty(self, tmp_path):
        """测试：空历史应返回空列表"""
        # Arrange
        from mind.tools.search_history import SearchHistory

        history = SearchHistory(file_path=tmp_path / "test.json")

        # Act
        latest = history.get_latest(5)

        # Assert
        assert latest == []

    def test_get_latest_limit_exceeds_history(self, tmp_path):
        """测试：限制超过历史数量时应返回全部"""
        # Arrange
        from mind.tools.search_history import SearchHistory

        history = SearchHistory(file_path=tmp_path / "test.json")
        history.save_search("only", [{"title": "Only"}])

        # Act
        latest = history.get_latest(10)

        # Assert
        assert len(latest) == 1
        assert latest[0]["query"] == "only"


class TestSearchHistorySearch:
    """测试历史搜索功能"""

    def test_search_history_finds_matches(self, tmp_path):
        """测试：应在历史中找到匹配项"""
        # Arrange
        from mind.tools.search_history import SearchHistory

        history = SearchHistory(file_path=tmp_path / "test.json")
        history.save_search("Python programming", [{"title": "Python Guide"}])
        history.save_search("Java tutorial", [{"title": "Java Guide"}])
        history.save_search("Python advanced", [{"title": "Advanced Python"}])

        # Act
        results = history.search_history("Python")

        # Assert
        assert len(results) == 2
        queries = [r["query"] for r in results]
        assert "Python programming" in queries
        assert "Python advanced" in queries

    def test_search_history_case_insensitive(self, tmp_path):
        """测试：搜索应不区分大小写"""
        # Arrange
        from mind.tools.search_history import SearchHistory

        history = SearchHistory(file_path=tmp_path / "test.json")
        history.save_search("Python", [{"title": "Test"}])

        # Act
        results = history.search_history("python")

        # Assert
        assert len(results) == 1

    def test_search_history_no_matches(self, tmp_path):
        """测试：无匹配时应返回空列表"""
        # Arrange
        from mind.tools.search_history import SearchHistory

        history = SearchHistory(file_path=tmp_path / "test.json")
        history.save_search("Python", [{"title": "Test"}])

        # Act
        results = history.search_history("golang")

        # Assert
        assert results == []

    def test_search_history_empty_pattern(self, tmp_path):
        """测试：空模式应返回所有"""
        # Arrange
        from mind.tools.search_history import SearchHistory

        history = SearchHistory(file_path=tmp_path / "test.json")
        history.save_search("query1", [{"title": "1"}])
        history.save_search("query2", [{"title": "2"}])

        # Act
        results = history.search_history("")

        # Assert
        assert len(results) == 2
