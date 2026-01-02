"""测试向后兼容性 - 确保导入路径有效

现在 mind.agent 重新导出 mind.agents.Agent，所以两个导入指向同一个类。
"""


def test_old_import_path_works():
    """测试旧的导入路径 from mind.agent import Agent 仍然有效"""
    # 现在 agent.py 重新导出模块化的 Agent
    from mind.agent import Agent

    # 验证它可以正常导入和初始化
    agent = Agent(name="测试", system_prompt="你是助手")
    assert agent.name == "测试"


def test_new_import_path_works():
    """测试新的导入路径 from mind.agents import Agent"""
    from mind.agents import Agent

    assert Agent is not None

    # 验证新版本可以正常工作
    agent = Agent(name="测试", system_prompt="你是助手")
    assert agent.name == "测试"


def test_both_imports_refer_same_class():
    """测试两种导入指向同一个类（重新导出）"""
    from mind.agent import Agent as OldAgent
    from mind.agents import Agent as NewAgent

    # 现在它们是同一个类（重新导出）
    assert OldAgent is NewAgent

    # 都有相同的接口
    old = OldAgent(name="A", system_prompt="提示词")
    new = NewAgent(name="B", system_prompt="提示词")

    assert old.name == "A"
    assert new.name == "B"

    # 验证新架构的属性
    assert hasattr(old, "documents")
    assert hasattr(new, "documents")
    assert hasattr(old, "analyzer")
    assert hasattr(new, "analyzer")
