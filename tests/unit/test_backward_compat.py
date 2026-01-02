"""测试向后兼容性 - 确保两个导入路径都有效"""


def test_old_import_path_works():
    """测试旧的导入路径 from mind.agent import Agent 仍然有效"""
    # 旧的 agent.py 保留完整的原始实现
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


def test_both_imports_coexist():
    """测试两种导入可以共存（它们是不同的实现）"""
    from mind.agent import Agent as OldAgent
    from mind.agents import Agent as NewAgent

    # 它们是不同的类
    assert OldAgent is not NewAgent

    # 但都有相同的接口
    old = OldAgent(name="A", system_prompt="提示词")
    new = NewAgent(name="B", system_prompt="提示词")

    assert old.name == "A"
    assert new.name == "B"
