"""提示词配置加载模块

从 YAML 文件加载智能体提示词配置和系统设置。
"""

import os
import re
from pathlib import Path

import yaml
from pydantic import BaseModel, Field, field_validator


def _expand_env_vars(value: str) -> str:
    """展开环境变量 ${VAR_NAME} 为实际值

    Args:
        value: 可能包含环境变量引用的字符串

    Returns:
        展开后的字符串

    Raises:
        ValueError: 环境变量未定义

    Examples:
        >>> os.environ['TEST'] = 'value'
        >>> _expand_env_vars('${TEST}')
        'value'
        >>> _expand_env_vars('prefix_${TEST}_suffix')
        'prefix_value_suffix'
    """
    if not isinstance(value, str):
        return value

    # 匹配 ${VAR_NAME} 格式
    pattern = re.compile(r"\$\{([A-Z_][A-Z0-9_]*)\}")

    def replace_var(match: re.Match[str]) -> str:
        var_name = match.group(1)
        if var_name not in os.environ:
            raise ValueError(
                f"环境变量 '{var_name}' 未定义，请在启动前设置: export {var_name}=..."
            )
        return os.environ[var_name]

    return pattern.sub(replace_var, value)


class AgentConfig(BaseModel):
    """智能体配置模型"""

    name: str = Field(..., description="智能体名称")
    system_prompt: str = Field(..., description="系统提示词")


class SearchConfig(BaseModel):
    """搜索配置模型"""

    max_results: int = Field(default=10, description="每次搜索最大结果数")
    history_limit: int = Field(default=5, description="提供给 AI 的搜索记录数")


class DocumentsConfig(BaseModel):
    """文档池配置模型"""

    max_documents: int = Field(default=10, description="文档池最大数量")
    ttl: int = Field(default=5, description="文档过期时间（轮数）")


class ConversationConfig(BaseModel):
    """对话配置模型"""

    turn_interval: float = Field(default=1.0, description="对话轮次间隔（秒）")
    max_turns: int = Field(default=500, description="非交互模式最大轮数")


class MCPServerConfig(BaseModel):
    """MCP 服务器配置模型"""

    command: str = Field(..., description="服务器启动命令")
    args: list[str] = Field(default_factory=list, description="命令参数")
    env: dict[str, str] = Field(default_factory=dict, description="环境变量")

    @field_validator("env", mode="before")
    @classmethod
    def expand_env_values(cls, value: dict[str, str] | None) -> dict[str, str]:
        """展开环境变量字典中的 ${VAR_NAME} 引用"""
        if not value:
            return {}

        expanded = {}
        for key, val in value.items():
            try:
                expanded[key] = _expand_env_vars(val)
            except ValueError:
                # 保持原值，让错误在实际使用时抛出
                expanded[key] = val
        return expanded


class HookConfig(BaseModel):
    """Hook 配置模型"""

    timeout: float = Field(default=30.0, description="Hook 超时时间（秒）")
    enabled: bool = Field(default=True, description="是否启用 Hook")


class ToolsConfig(BaseModel):
    """工具配置模型"""

    tool_interval: int = Field(default=5, description="工具调用间隔（轮数）")
    enable_tools: bool = Field(default=True, description="是否启用工具")
    enable_search: bool = Field(default=True, description="是否启用搜索")
    mcp_servers: dict[str, MCPServerConfig] = Field(
        default_factory=dict, description="MCP 服务器配置"
    )
    pre_tool_use: HookConfig | None = Field(
        default=None, description="工具调用前 Hook 配置"
    )
    post_tool_use: HookConfig | None = Field(
        default=None, description="工具调用后 Hook 配置"
    )


class SettingsConfig(BaseModel):
    """系统设置配置模型"""

    search: SearchConfig = Field(default_factory=SearchConfig)
    documents: DocumentsConfig = Field(default_factory=DocumentsConfig)
    conversation: ConversationConfig = Field(default_factory=ConversationConfig)
    tools: ToolsConfig = Field(default_factory=ToolsConfig)
    stop_tokens: list[str] = Field(
        default_factory=lambda: [
            # 注意：Anthropic API 限制 stop_sequences 最多 4 个元素
            # 我们只保留最常见的内部思考标签
            "<thinking>",
            "</thinking>",
            "<reflection>",
            "</reflection>",
        ],
        description="停止序列，遇到这些标记时停止生成（最多 4 个，API 限制）",
    )


class ConfigError(ValueError):
    """配置文件格式错误"""

    pass


def get_default_config_path() -> Path:
    """获取默认配置文件路径

    Returns:
        默认配置文件的完整路径
    """
    return Path(__file__).parent / "prompts.yaml"


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

    with open(config_file, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not isinstance(data, dict) or "agents" not in data:
        raise ConfigError("配置文件必须包含 'agents' 键")

    configs = {}
    for agent_id, agent_data in data["agents"].items():
        configs[agent_id] = AgentConfig(**agent_data)

    return configs


def load_settings(config_path: str | Path) -> SettingsConfig:
    """从 YAML 文件加载系统设置配置

    Args:
        config_path: 配置文件路径

    Returns:
        SettingsConfig 实例

    Raises:
        FileNotFoundError: 配置文件不存在
        yaml.YAMLError: YAML 格式错误
        ValidationError: 配置字段验证失败
    """
    config_file = Path(config_path) if isinstance(config_path, str) else config_path

    if not config_file.exists():
        raise FileNotFoundError(f"配置文件不存在: {config_file}")

    with open(config_file, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    # 如果没有 settings 键，返回默认配置
    if not isinstance(data, dict) or "settings" not in data:
        return SettingsConfig()

    return SettingsConfig(**data["settings"])


def load_all_configs(
    config_path: str | Path,
) -> tuple[dict[str, AgentConfig], SettingsConfig]:
    """从 YAML 文件加载所有配置

    Args:
        config_path: 配置文件路径

    Returns:
        (智能体配置字典, 系统设置配置)
    """
    configs = load_agent_configs(str(config_path))
    settings = load_settings(config_path)
    return configs, settings
