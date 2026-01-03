"""测试 DocumentPool 文档池管理"""

from anthropic.types import MessageParam


def test_document_pool_add():
    """测试添加文档"""
    from mind.agents.documents import DocumentPool

    pool = DocumentPool(max_documents=3)
    doc = {"type": "document", "title": "test"}

    pool.add(doc)

    assert len(pool.documents) == 1
    assert pool.documents[0] == doc


def test_document_pool_max_documents():
    """测试超过最大数量时移除旧文档"""
    from mind.agents.documents import DocumentPool

    pool = DocumentPool(max_documents=2)
    pool.add({"type": "document", "title": "doc1"})
    pool.add({"type": "document", "title": "doc2"})
    pool.add({"type": "document", "title": "doc3"})

    assert len(pool.documents) == 2
    assert pool.documents[0]["title"] == "doc2"
    assert pool.documents[1]["title"] == "doc3"


def test_document_pool_merge_into_messages():
    """测试将文档合并到消息"""
    from mind.agents.documents import DocumentPool

    pool = DocumentPool()
    pool.add({"type": "document", "title": "doc1"})
    pool.add({"type": "text", "text": "context"})

    messages = [
        MessageParam(role="user", content="Hello"),
        MessageParam(role="assistant", content="Hi"),
    ]

    merged = pool.merge_into_messages(messages)

    assert len(merged) == 2
    # 用户消息应该包含文档
    assert merged[0]["role"] == "user"
    # 助手消息不变
    assert merged[1]["role"] == "assistant"
    assert merged[1]["content"] == "Hi"


def test_document_pool_from_search_history():
    """测试从搜索历史创建文档列表"""
    from mind.agents.documents import DocumentPool

    searches = [
        {
            "query": "test query",
            "results": [
                {
                    "title": "Result 1",
                    "href": "http://example.com",
                    "body": "Content 1",
                },
            ],
        }
    ]

    docs = DocumentPool.from_search_history(searches)

    # 应返回文档列表
    assert isinstance(docs, list)
    assert len(docs) == 1
    doc = docs[0]
    assert doc["type"] == "document"
    assert "test query" in doc["title"]
    assert doc["citations"]["enabled"] is True


def test_document_pool_from_search_history_multiple():
    """测试从多条搜索历史创建多个文档"""
    from mind.agents.documents import DocumentPool

    searches = [
        {
            "query": "query 1",
            "results": [
                {
                    "title": "Result 1",
                    "href": "http://example.com/1",
                    "body": "Content 1",
                },
            ],
        },
        {
            "query": "query 2",
            "results": [
                {
                    "title": "Result 2",
                    "href": "http://example.com/2",
                    "body": "Content 2",
                },
            ],
        },
    ]

    docs = DocumentPool.from_search_history(searches)

    # 每次搜索生成独立的文档
    assert len(docs) == 2
    assert "query 1" in docs[0]["title"]
    assert "query 2" in docs[1]["title"]
