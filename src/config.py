from pathlib import Path

import yaml


_config = None


def load_config():
    """Load YAML config from project config/config.yaml"""
    global _config
    if _config is None:
        config_path = Path(__file__).parent.parent / "config" / "config.yaml"
        with open(config_path) as f:
            _config = yaml.safe_load(f)
    return _config
