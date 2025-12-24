import logging
from pathlib import Path
from typing import Any

import yaml


# Use stdlib logging here since config loads before structlog is configured
_logger = logging.getLogger(__name__)

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
            _logger.exception("Config file not found: %s", config_path)
            raise RuntimeError(f"Configuration file missing: {config_path}") from e
        except yaml.YAMLError as e:
            _logger.exception("Failed to parse config file %s", config_path)
            raise RuntimeError(f"Invalid YAML in configuration file: {e}") from e
        except Exception:
            _logger.exception("Unexpected error loading config")
            raise RuntimeError("Failed to load configuration") from None
    return _config
