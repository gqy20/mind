"""提示词配置加载模块

从 YAML 文件加载智能体提示词配置。
"""

from pathlib import Path

import yaml
from pydantic import BaseModel, Field, ValidationError


class AgentConfig(BaseModel):
    """智能体配置模型"""

    name: str = Field(..., description="智能体名称")
    system_prompt: str = Field(..., description="系统提示词")


class ConfigError(ValueError):
    """配置文件格式错误"""

    pass


def load_agent_configs(config_path: str) -> dict[str, AgentConfig]:
    """从 YAML 文件加载智能体配置

    Args:
        config_path: 配置文件路径

    Returns:
        智能体配置字典，键为智能体 ID，值为 AgentConfig 实例

    Raises:
        FileNotFoundError: 配置文件不存在
        yaml.YAMLError: YAML 格式错误
        ConfigError: 配置格式不正确
        ValidationError: 配置字段验证失败
    """
    config_file = Path(config_path)

    if not config_file.exists():
        raise FileNotFoundError(f"配置文件不存在: {config_path}")

    with open(config_file, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not isinstance(data, dict) or "agents" not in data:
        raise ConfigError("配置文件必须包含 'agents' 键")

    configs = {}
    for agent_id, agent_data in data["agents"].items():
        configs[agent_id] = AgentConfig(**agent_data)

    return configs
