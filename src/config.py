import yaml
from pathlib import Path

_config = None

def load_config():
    """Load YAML config from project config/config.yaml"""
    global _config
    if _config is None:
        config_path = Path(__file__).parent.parent / "config" / "config.yaml"
        with open(config_path, 'r') as f:
            _config = yaml.safe_load(f)
    return _config
