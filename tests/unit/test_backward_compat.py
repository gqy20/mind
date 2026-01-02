"""测试向后兼容性 - 确保旧导入路径仍然有效"""


def test_old_import_path_works():
    """测试旧的导入路径 from mind.agent import Agent 仍然有效"""
    # 这应该从旧的 agent.py 导入
    from mind.agent import Agent as OldAgent

    # 这应该从新的 agents 模块导入
    from mind.agents import Agent as NewAgent

    # 它们应该是同一个类（因为我们会在旧的 __init__.py 中重导出）
    assert OldAgent is NewAgent


def test_new_import_path_works():
    """测试新的导入路径 from mind.agents import Agent"""
    from mind.agents import Agent

    assert Agent is not None
