from unittest.mock import mock_open, patch

import pytest
import yaml

import src.config
from src.config import load_config


class TestConfig:
    def setup_method(self):
        # Reset global config before each test
        src.config._config = None

    def test_load_config_success(self):
        mock_yaml_content = """
server:
  host: "0.0.0.0"
  port: 8000
  base_url: "https://example.com"
notifications:
  pushover:
    enabled: true
    priority: 0
  discord:
    enabled: true
logging:
  level: "INFO"
  file: "logs/test.log"
"""
        with patch("builtins.open", mock_open(read_data=mock_yaml_content)):
            config = load_config()
            assert config["server"]["host"] == "0.0.0.0"
            assert config["server"]["port"] == 8000
            assert config["notifications"]["pushover"]["enabled"] is True
            assert config["logging"]["level"] == "INFO"

    def test_load_config_file_not_found(self):
        with patch("builtins.open", side_effect=FileNotFoundError("Config file not found")):
            with pytest.raises(RuntimeError, match="Configuration file missing"):
                load_config()

    def test_load_config_invalid_yaml(self):
        invalid_yaml = "invalid: yaml: content: ["
        with patch("builtins.open", mock_open(read_data=invalid_yaml)), pytest.raises(RuntimeError, match="Invalid YAML"):
            load_config()

    def test_load_config_empty_file(self):
        with patch("builtins.open", mock_open(read_data="")):
            config = load_config()
            assert config is None or config == {}

    def test_load_config_nested_structure(self):
        mock_yaml_content = """
notifications:
  discord:
    icon_url: "https://example.com/icon.png"
    footer_text: "Test Footer"
  pushover:
    sound: "magic"
    html: 1
audnex:
  api_url: "https://api.audnex.us/books"
"""
        with patch("builtins.open", mock_open(read_data=mock_yaml_content)):
            config = load_config()
            assert config["notifications"]["discord"]["icon_url"] == "https://example.com/icon.png"
            assert config["notifications"]["pushover"]["sound"] == "magic"
            assert config["audnex"]["api_url"] == "https://api.audnex.us/books"
