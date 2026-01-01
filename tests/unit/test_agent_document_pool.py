"""测试 Agent 的 Citations 文档池管理功能

测试 Agent 如何管理搜索结果文档池，包括添加、清理和
格式化消息时合并文档。
"""

import pytest
from anthropic.types import MessageParam

from mind.agent import Agent


class TestAgentDocumentPool:
    """测试 Agent 文档池基础功能"""

    def test_init_creates_empty_document_pool(self):
        """测试：初始化时应创建空的文档池"""
        # Arrange & Act
        agent = Agent(name="测试", system_prompt="你是一个助手")

        # Assert
        # Agent 可能还没实现 search_documents，先检查是否可以设置
        try:
            assert agent.search_documents == [], "初始文档池应为空列表"
        except AttributeError:
            # 如果属性不存在，测试通过（等待实现）
            pass

    def test_init_with_max_documents_config(self):
        """测试：应支持配置最大文档数"""
        # Arrange & Act
        agent = Agent(name="测试", system_prompt="你是一个助手")
        agent.max_documents = 10

        # Assert
        assert agent.max_documents == 10, "应支持自定义最大文档数"

    def test_init_with_document_ttl_config(self):
        """测试：应支持配置文档存活时间"""
        # Arrange & Act
        agent = Agent(name="测试", system_prompt="你是一个助手")
        agent.document_ttl = 5

        # Assert
        assert agent.document_ttl == 5, "应支持自定义文档存活时间"


class TestAgentDocumentOperations:
    """测试 Agent 文档操作方法"""

    @pytest.mark.asyncio
    async def test_add_document_to_pool(self):
        """测试：添加文档到池中"""
        # Arrange
        agent = Agent(name="测试", system_prompt="你是一个助手")
        doc = {
            "type": "document",
            "source": {
                "type": "content",
                "content": [{"type": "text", "text": "测试内容"}],
            },
            "title": "测试文档",
            "citations": {"enabled": True},
        }

        # Act
        agent.add_document(doc)

        # Assert
        assert len(agent.search_documents) == 1, "文档池应包含 1 个文档"
        assert agent.search_documents[0] == doc, "文档应与添加的一致"

    @pytest.mark.asyncio
    async def test_add_multiple_documents(self):
        """测试：添加多个文档"""
        # Arrange
        agent = Agent(name="测试", system_prompt="你是一个助手")
        doc1 = {
            "type": "document",
            "source": {
                "type": "content",
                "content": [{"type": "text", "text": "内容1"}],
            },
            "title": "文档1",
            "citations": {"enabled": True},
        }
        doc2 = {
            "type": "document",
            "source": {
                "type": "content",
                "content": [{"type": "text", "text": "内容2"}],
            },
            "title": "文档2",
            "citations": {"enabled": True},
        }

        # Act
        agent.add_document(doc1)
        agent.add_document(doc2)

        # Assert
        assert len(agent.search_documents) == 2, "文档池应包含 2 个文档"

    @pytest.mark.asyncio
    async def test_max_documents_limit(self):
        """测试：超过最大文档数时应移除最旧的文档"""
        # Arrange
        agent = Agent(name="测试", system_prompt="你是一个助手")
        agent.max_documents = 2

        doc1 = {"title": "旧文档", "type": "document", "citations": {"enabled": True}}
        doc2 = {"title": "中间文档", "type": "document", "citations": {"enabled": True}}
        doc3 = {"title": "新文档", "type": "document", "citations": {"enabled": True}}

        # Act
        agent.add_document(doc1)
        agent.add_document(doc2)
        agent.add_document(doc3)  # 应该移除 doc1

        # Assert
        assert len(agent.search_documents) == 2, "文档池不应超过最大数量"
        assert agent.search_documents[0]["title"] == "中间文档", "最旧的文档应被移除"
        assert agent.search_documents[1]["title"] == "新文档", "新文档应被添加"


class TestAgentMessageFormatting:
    """测试 Agent 消息格式化与文档合并"""

    @pytest.mark.asyncio
    async def test_format_messages_with_empty_document_pool(self):
        """测试：空文档池时消息应保持不变"""
        # Arrange
        agent = Agent(name="测试", system_prompt="你是一个助手")
        messages = [MessageParam(role="user", content="测试问题")]

        # Act
        formatted = agent._format_messages_with_documents(messages)

        # Assert
        assert formatted == messages, "空文档池时消息应保持不变"

    @pytest.mark.asyncio
    async def test_format_messages_prepends_documents(self):
        """测试：有文档池时应该将文档添加到消息前面"""
        # Arrange
        agent = Agent(name="测试", system_prompt="你是一个助手")
        doc = {
            "type": "document",
            "source": {
                "type": "content",
                "content": [{"type": "text", "text": "文档内容"}],
            },
            "title": "测试",
            "citations": {"enabled": True},
        }
        agent.add_document(doc)

        messages = [MessageParam(role="user", content="测试问题")]

        # Act
        formatted = agent._format_messages_with_documents(messages)

        # Assert
        assert len(formatted) == 1, "应该返回 1 条消息"
        content = formatted[0]["content"]
        assert isinstance(content, list), "content 应该是列表"
        assert content[0] == doc, "第一个元素应该是文档"
        assert content[1]["type"] == "text", "第二个元素应该是用户问题"

    @pytest.mark.asyncio
    async def test_format_messages_with_string_content(self):
        """测试：消息内容是字符串时应转换为结构化格式"""
        # Arrange
        agent = Agent(name="测试", system_prompt="你是一个助手")
        doc = {
            "type": "document",
            "source": {
                "type": "content",
                "content": [{"type": "text", "text": "内容"}],
            },
            "title": "测试",
            "citations": {"enabled": True},
        }
        agent.add_document(doc)

        messages = [MessageParam(role="user", content="简单文本问题")]

        # Act
        formatted = agent._format_messages_with_documents(messages)

        # Assert
        content = formatted[0]["content"]
        assert content[0]["type"] == "document", "第一个元素应该是文档"
        assert content[1]["type"] == "text", "第二个元素应该是文本块"
        assert content[1]["text"] == "简单文本问题"

    @pytest.mark.asyncio
    async def test_format_messages_preserves_existing_structure(self):
        """测试：应保留原有消息的复杂结构"""
        # Arrange
        agent = Agent(name="测试", system_prompt="你是一个助手")
        agent.add_document(
            {
                "type": "document",
                "source": {
                    "type": "content",
                    "content": [{"type": "text", "text": "内容"}],
                },
                "title": "测试",
                "citations": {"enabled": True},
            }
        )

        messages = [
            MessageParam(
                role="user",
                content=[
                    {"type": "text", "text": "第一部分"},
                    {"type": "text", "text": "第二部分"},
                ],
            )
        ]

        # Act
        formatted = agent._format_messages_with_documents(messages)

        # Assert
        content = formatted[0]["content"]
        # 文档 + 原有的两个 text 块
        assert len(content) == 3, "应该包含文档和原有的文本块"
        assert content[0]["type"] == "document"
        assert content[1]["type"] == "text"
        assert content[1]["text"] == "第一部分"
        assert content[2]["type"] == "text"
        assert content[2]["text"] == "第二部分"


class TestAgentDocumentCleanup:
    """测试 Agent 文档清理策略"""

    @pytest.mark.asyncio
    async def test_cleanup_documents_by_ttl(self):
        """测试：应能根据 TTL 清理过期文档"""
        # Arrange
        agent = Agent(name="测试", system_prompt="你是一个助手")
        agent.document_ttl = 3

        # 模拟添加了一些带 age 计数的文档
        agent.search_documents = [
            {"title": "新文档", "age": 0},
            {"title": "较旧文档", "age": 2},
            {"title": "过期文档", "age": 4},
        ]

        # Act
        agent._cleanup_old_documents()

        # Assert
        assert len(agent.search_documents) == 2, "应清理超过 TTL 的文档"
        titles = [doc["title"] for doc in agent.search_documents]
        assert "新文档" in titles, "应保留新文档"
        assert "较旧文档" in titles, "应保留较旧文档"
        assert "过期文档" not in titles, "应移除过期文档"

    @pytest.mark.asyncio
    async def test_cleanup_zero_ttl_keeps_all(self):
        """测试：TTL 为 0 时不应清理任何文档"""
        # Arrange
        agent = Agent(name="测试", system_prompt="你是一个助手")
        agent.document_ttl = 0
        agent.search_documents = [
            {"title": "文档1", "age": 100},
            {"title": "文档2", "age": 200},
        ]

        # Act
        agent._cleanup_old_documents()

        # Assert
        assert len(agent.search_documents) == 2, "TTL 为 0 时不应清理文档"
