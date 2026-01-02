"""测试 agents 模块的初始化和导入"""


def test_agents_module_exists():
    """测试 agents 模块可以被导入"""
    import mind.agents

    assert mind.agents is not None


def test_agent_class_exported():
    """测试 Agent 类可以从 agents 模块导入"""
    from mind.agents import Agent

    assert Agent is not None
