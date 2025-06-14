# DEPRECATED: This in-memory store is no longer used. Use src/db.py for persistent storage.
# This file can be removed.

from src.config import load_config
import time
from threading import Lock
import logging

_config = load_config()
_server_cfg = _config.get('server', {})
# Token expires after configured TTL seconds
TTL = _server_cfg.get('reply_token_ttl', 3600)
logging.info(f"Token TTL is set to {TTL} seconds.")

_store = {}
_lock = Lock()

def cleanup():
    """Remove expired tokens from the store."""
    with _lock:
        now = time.time()
        for t, (_, ts) in list(_store.items()):
            if now - ts > TTL:
                del _store[t]

def save_request(token: str, metadata: dict):
    """Save metadata for a generated token."""
    with _lock:
        _store[token] = (metadata, time.time())

def get_request(token: str):
    """Retrieve metadata for a token if valid and not expired."""
    with _lock:
        entry = _store.get(token)
        if not entry:
            return None
        metadata, ts = entry
        if time.time() - ts > TTL:
            logging.warning(f"Token expired: {token}")
            del _store[token]
            return None
        return metadata
