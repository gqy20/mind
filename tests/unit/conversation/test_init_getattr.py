"""测试 conversation/__init__.py 的 __getattr__ 延迟导入

测试使用字典映射重构后的 __getattr__ 方法。
"""

import pytest


def test_getattr_progress_display():
    """测试导入 ProgressDisplay

    ProgressDisplay 已移至 mind.display.progress，
    从 conversation.__getattr__ 访问会触发 AttributeError。

    Given: 访问 ProgressDisplay 属性
    When: 调用 __getattr__
    Then: 抛出 AttributeError（已移除）
    """
    module = __import__("mind.conversation", fromlist=["__getattr__"])

    with pytest.raises(AttributeError, match="has no attribute"):
        module.__getattr__("ProgressDisplay")


def test_getattr_search_handler():
    """测试导入 SearchHandler

    Given: 访问 SearchHandler 属性
    When: 调用 __getattr__
    Then: 返回正确的类
    """
    from mind.conversation import search_handler

    module = __import__("mind.conversation", fromlist=["__getattr__"])
    result = module.__getattr__("SearchHandler")

    assert result is search_handler.SearchHandler


def test_getattr_interaction_handler():
    """测试导入 InteractionHandler

    Given: 访问 InteractionHandler 属性
    When: 调用 __getattr__
    Then: 返回正确的类
    """
    from mind.conversation import interaction

    module = __import__("mind.conversation", fromlist=["__getattr__"])
    result = module.__getattr__("InteractionHandler")

    assert result is interaction.InteractionHandler


def test_getattr_ending_handler():
    """测试导入 EndingHandler

    Given: 访问 EndingHandler 属性
    When: 调用 __getattr__
    Then: 返回正确的类
    """
    from mind.conversation import ending

    module = __import__("mind.conversation", fromlist=["__getattr__"])
    result = module.__getattr__("EndingHandler")

    assert result is ending.EndingHandler


def test_getattr_flow_controller():
    """测试导入 FlowController

    Given: 访问 FlowController 属性
    When: 调用 __getattr__
    Then: 返回正确的类
    """
    from mind.conversation import flow

    module = __import__("mind.conversation", fromlist=["__getattr__"])
    result = module.__getattr__("FlowController")

    assert result is flow.FlowController


def test_getattr_invalid_attribute():
    """测试访问不存在的属性

    Given: 访问不存在的属性
    When: 调用 __getattr__
    Then: 抛出 AttributeError
    """
    module = __import__("mind.conversation", fromlist=["__getattr__"])

    with pytest.raises(AttributeError, match="module.*has no attribute.*InvalidClass"):
        module.__getattr__("InvalidClass")


def test_getattr_all_exported_names():
    """测试所有导出的名称都可以通过 __getattr__ 访问

    Given: __all__ 中列出的所有名称
    When: 逐一访问
    Then: 所有名称都能正确返回相应的类
    """
    import mind.conversation

    for name in mind.conversation.__all__:
        if name == "ConversationManager":
            # ConversationManager 直接导入，不通过 __getattr__
            continue
        # 验证可以访问且返回的是类
        result = getattr(mind.conversation, name)
        assert result is not None, f"{name} 应该能被访问"
        assert isinstance(result, type), f"{name} 应该是一个类"
