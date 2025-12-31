"""
Prompts 模块的单元测试

测试提示词配置加载功能：
- 从 YAML 文件加载配置
- 解析智能体配置
- 处理配置文件不存在
- 验证配置格式
"""

from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from mind.prompts import AgentConfig, load_agent_configs


class TestLoadAgentConfigs:
    """测试加载智能体配置"""

    def test_load_agent_configs_from_valid_file(self, tmp_path):
        """测试：从有效的 YAML 文件加载配置"""
        # Arrange
        config_content = {
            "agents": {
                "supporter": {
                    "name": "支持者",
                    "system_prompt": "你是一个支持者"
                },
                "challenger": {
                    "name": "挑战者",
                    "system_prompt": "你是一个挑战者"
                }
            }
        }
        config_file = tmp_path / "prompts.yaml"
        with open(config_file, "w", encoding="utf-8") as f:
            yaml.dump(config_content, f, allow_unicode=True)

        # Act
        configs = load_agent_configs(str(config_file))

        # Assert
        assert len(configs) == 2
        assert configs["supporter"].name == "支持者"
        assert configs["supporter"].system_prompt == "你是一个支持者"
        assert configs["challenger"].name == "挑战者"
        assert configs["challenger"].system_prompt == "你是一个挑战者"

    def test_load_agent_configs_file_not_found(self, tmp_path):
        """测试：文件不存在应抛出 FileNotFoundError"""
        # Arrange
        nonexistent_file = tmp_path / "nonexistent.yaml"

        # Act & Assert
        with pytest.raises(FileNotFoundError, match="配置文件不存在"):
            load_agent_configs(str(nonexistent_file))

    def test_load_agent_configs_invalid_yaml(self, tmp_path):
        """测试：无效的 YAML 应抛出错误"""
        # Arrange
        config_file = tmp_path / "invalid.yaml"
        config_file.write_text("invalid: yaml: content: [", encoding="utf-8")

        # Act & Assert
        with pytest.raises(yaml.YAMLError):
            load_agent_configs(str(config_file))

    def test_load_agent_configs_missing_agents_key(self, tmp_path):
        """测试：缺少 agents 键应抛出 ValidationError"""
        # Arrange
        config_content = {"invalid_key": {}}
        config_file = tmp_path / "prompts.yaml"
        with open(config_file, "w", encoding="utf-8") as f:
            yaml.dump(config_content, f)

        # Act & Assert
        with pytest.raises(ValidationError):
            load_agent_configs(str(config_file))

    def test_load_agent_configs_empty_agents(self, tmp_path):
        """测试：空的 agents 列表应返回空字典"""
        # Arrange
        config_content = {"agents": {}}
        config_file = tmp_path / "prompts.yaml"
        with open(config_file, "w", encoding="utf-8") as f:
            yaml.dump(config_content, f)

        # Act
        configs = load_agent_configs(str(config_file))

        # Assert
        assert configs == {}

    def test_load_agent_configs_missing_required_fields(self, tmp_path):
        """测试：缺少必需字段应抛出 ValidationError"""
        # Arrange
        config_content = {
            "agents": {
                "incomplete": {
                    "name": "测试"
                    # 缺少 system_prompt
                }
            }
        }
        config_file = tmp_path / "prompts.yaml"
        with open(config_file, "w", encoding="utf-8") as f:
            yaml.dump(config_content, f)

        # Act & Assert
        with pytest.raises(ValidationError):
            load_agent_configs(str(config_file))

    def test_load_agent_configs_multiline_prompt(self, tmp_path):
        """测试：支持多行提示词"""
        # Arrange
        config_content = {
            "agents": {
                "test": {
                    "name": "测试",
                    "system_prompt": "第一行\n第二行\n第三行"
                }
            }
        }
        config_file = tmp_path / "prompts.yaml"
        with open(config_file, "w", encoding="utf-8") as f:
            yaml.dump(config_content, f, allow_unicode=True)

        # Act
        configs = load_agent_configs(str(config_file))

        # Assert
        assert configs["test"].system_prompt == "第一行\n第二行\n第三行"


class TestAgentConfig:
    """测试 AgentConfig 数据模型"""

    def test_agent_config_valid(self):
        """测试：有效的配置应创建实例"""
        # Arrange & Act
        config = AgentConfig(name="测试", system_prompt="提示词内容")

        # Assert
        assert config.name == "测试"
        assert config.system_prompt == "提示词内容"

    def test_agent_config_missing_name(self):
        """测试：缺少 name 应抛出 ValidationError"""
        # Act & Assert
        with pytest.raises(ValidationError):
            AgentConfig(system_prompt="提示词")

    def test_agent_config_missing_system_prompt(self):
        """测试：缺少 system_prompt 应抛出 ValidationError"""
        # Act & Assert
        with pytest.raises(ValidationError):
            AgentConfig(name="测试")

    def test_agent_config_empty_fields(self):
        """测试：空字符串应通过验证（允许空配置）"""
        # Arrange & Act
        config = AgentConfig(name="", system_prompt="")

        # Assert
        assert config.name == ""
        assert config.system_prompt == ""
