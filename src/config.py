import logging
from pathlib import Path

import yaml


_config = None


def load_config():
    """Load YAML config from project config/config.yaml"""
    global _config
    if _config is None:
        config_path = Path(__file__).parent.parent / "config" / "config.yaml"
        try:
            with open(config_path) as f:
                _config = yaml.safe_load(f)
        except FileNotFoundError as e:
            logging.error(f"Config file not found: {config_path}. {e}")
            raise RuntimeError(f"Configuration file missing: {config_path}") from e
        except yaml.YAMLError as e:
            logging.error(f"Failed to parse config file {config_path}: {e}")
            raise RuntimeError(f"Invalid YAML in configuration file: {e}") from e
        except Exception as e:
            logging.error(f"Unexpected error loading config: {e}")
            raise RuntimeError(f"Failed to load configuration: {e}") from e
    return _config
