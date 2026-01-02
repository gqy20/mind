"""测试向后兼容性已删除 - 验证旧导入路径不再可用

删除模块化重构后的向后兼容层，只保留新的导入路径。
"""


def test_new_import_path_works():
    """测试新的导入路径 from mind.agents.agent import Agent"""
    from mind.agents.agent import Agent

    assert Agent is not None

    # 验证新版本可以正常工作
    agent = Agent(name="测试", system_prompt="你是助手")
    assert agent.name == "测试"


def test_new_import_from_package_init():
    """测试从 agents 包的 __init__.py 导入"""
    from mind.agents import Agent

    # 验证可以正常导入和初始化
    agent = Agent(name="测试", system_prompt="你是助手")
    assert agent.name == "测试"


def test_old_import_path_not_available():
    """验证旧的导入路径 from mind.agent import Agent 已不可用"""
    # 尝试从旧路径导入应该失败
    try:
        from mind.agent import Agent  # noqa: F401

        # 如果导入成功，说明兼容层还存在，测试失败
        assert False, "旧的导入路径 mind.agent.Agent 仍然存在，应该被删除"
    except (ImportError, AttributeError):
        # 预期的行为：导入失败
        pass
