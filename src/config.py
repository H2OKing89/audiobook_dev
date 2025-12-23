import logging
from pathlib import Path
from typing import Any

import yaml


_config: dict[str, Any] | None = None


def load_config() -> dict[str, Any]:
    """Load YAML config from project config/config.yaml"""
    global _config  # noqa: PLW0603 - caching pattern requires global
    if _config is None:
        config_path = Path(__file__).parent.parent / "config" / "config.yaml"
        try:
            with config_path.open() as f:
                _config = yaml.safe_load(f)
        except FileNotFoundError as e:
            logging.error("Config file not found: %s. %s", config_path, e)
            raise RuntimeError(f"Configuration file missing: {config_path}") from e
        except yaml.YAMLError as e:
            logging.error("Failed to parse config file %s: %s", config_path, e)
            raise RuntimeError(f"Invalid YAML in configuration file: {e}") from e
        except Exception as e:
            logging.error("Unexpected error loading config: %s", e)
            raise RuntimeError(f"Failed to load configuration: {e}") from e
    return _config
