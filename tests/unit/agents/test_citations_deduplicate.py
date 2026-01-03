"""测试引用去重方法的提取

测试从 format_citations() 和 display_citations() 中提取的
去重逻辑，确保两个函数使用相同的去重算法。
"""

from mind.display.citations import _deduplicate_citations


def test_deduplicate_citations_basic():
    """测试基本的去重功能

    Given: 包含重复引用的列表
    When: 调用 _deduplicate_citations
    Then: 返回去重后的列表，保留首次出现的顺序
    """
    citations = [
        {
            "document_title": "测试文档",
            "cited_text": "引用文本1",
        },
        {
            "document_title": "测试文档",  # 重复
            "cited_text": "引用文本1",
        },
        {
            "document_title": "另一文档",
            "cited_text": "引用文本2",
        },
    ]

    result = _deduplicate_citations(citations)

    # 验证：去重后只有 2 条记录
    assert len(result) == 2

    # 验证：保留首次出现的顺序
    assert result[0]["document_title"] == "测试文档"
    assert result[0]["cited_text"] == "引用文本1"
    assert result[1]["document_title"] == "另一文档"
    assert result[1]["cited_text"] == "引用文本2"


def test_deduplicate_citations_empty():
    """测试空列表

    Given: 空的引用列表
    When: 调用 _deduplicate_citations
    Then: 返回空列表
    """
    result = _deduplicate_citations([])
    assert result == []


def test_deduplicate_citations_all_duplicates():
    """测试全部重复的情况

    Given: 所有引用都相同的列表
    When: 调用 _deduplicate_citations
    Then: 只返回一条记录
    """
    citations = [
        {"document_title": "文档A", "cited_text": "文本X"},
        {"document_title": "文档A", "cited_text": "文本X"},
        {"document_title": "文档A", "cited_text": "文本X"},
    ]

    result = _deduplicate_citations(citations)

    assert len(result) == 1
    assert result[0]["document_title"] == "文档A"


def test_deduplicate_citations_long_text_truncation():
    """测试长引用文本的截断

    Given: 引用文本超过 100 字符
    When: 调用 _deduplicate_citations
    Then: key 中使用前 100 字符进行去重判断
    """
    long_text = "a" * 150
    long_text_variant = "a" * 100 + "b" * 50  # 前 100 字符相同

    citations = [
        {"document_title": "文档", "cited_text": long_text},
        {"document_title": "文档", "cited_text": long_text_variant},
    ]

    result = _deduplicate_citations(citations)

    # 由于前 100 字符相同，应该被识别为重复
    assert len(result) == 1


def test_deduplicate_citations_partial_title_match():
    """测试标题部分匹配的情况

    Given: 标题不同但文本相同
    When: 调用 _deduplicate_citations
    Then: 不会被去重（因为 key 包含标题）
    """
    citations = [
        {"document_title": "文档A", "cited_text": "相同文本"},
        {"document_title": "文档B", "cited_text": "相同文本"},
    ]

    result = _deduplicate_citations(citations)

    # 标题不同，不应该去重
    assert len(result) == 2


def test_deduplicate_citations_preserves_order():
    """测试保持原始顺序

    Given: 多个引用，中间有重复
    When: 调用 _deduplicate_citations
    Then: 保持首次出现的顺序
    """
    citations = [
        {"document_title": "A", "cited_text": "X"},
        {"document_title": "B", "cited_text": "Y"},
        {"document_title": "A", "cited_text": "X"},  # 重复 A
        {"document_title": "C", "cited_text": "Z"},
        {"document_title": "B", "cited_text": "Y"},  # 重复 B
    ]

    result = _deduplicate_citations(citations)

    # 验证顺序和内容
    assert len(result) == 3
    assert result[0]["document_title"] == "A"
    assert result[1]["document_title"] == "B"
    assert result[2]["document_title"] == "C"


def test_deduplicate_citations_missing_fields():
    """测试缺少字段的情况

    Given: 引用缺少 document_title 或 cited_text
    When: 调用 _deduplicate_citations
    Then: 使用 .get() 的默认值（空字符串），不同字段组合不合并
    """
    citations = [
        {"document_title": "文档A"},  # 缺少 cited_text
        {"document_title": "文档A", "cited_text": ""},  # 空字符串
        {"cited_text": "文本"},  # 缺少 document_title
    ]

    result = _deduplicate_citations(citations)

    # 第一条和第二条有相同的 key，但第三条不同
    # key1 = ("文档A", "")
    # key2 = ("文档A", "")
    # key3 = ("", "文本")
    assert len(result) == 2

    # 验证保留了去重后的结果
    assert any(c.get("document_title") == "文档A" for c in result)
    assert any(c.get("cited_text") == "文本" for c in result)
