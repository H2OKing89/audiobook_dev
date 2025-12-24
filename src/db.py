import json
import sqlite3
import threading
import time
from pathlib import Path

from src.config import load_config, ConfigurationError
from src.logging_setup import get_logger


log = get_logger(__name__)

# Initialize SQLite database for token storage
db_path = Path(__file__).parent.parent / "db.sqlite"
_conn = sqlite3.connect(db_path, check_same_thread=False)
_lock = threading.Lock()

# Create table if not exists
with _lock:
    cursor = _conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tokens (
            token TEXT PRIMARY KEY,
            metadata TEXT,
            payload TEXT,
            timestamp INTEGER
        )
    """)
    _conn.commit()

# Default TTL, will be loaded from config on first use
_ttl: int | None = None


def _get_ttl() -> int:
    """Lazy load TTL from config."""
    global _ttl  # noqa: PLW0603 - caching pattern requires global
    if _ttl is None:
        try:
            config = load_config()
            _ttl = config.get("server", {}).get("reply_token_ttl", 3600)
        except (ConfigurationError, FileNotFoundError):
            # Config not available (e.g., in tests), use default
            _ttl = 3600
    return _ttl


def save_request(token: str, metadata: dict, payload: dict) -> None:
    """Save metadata and payload for a token."""
    ts = int(time.time())
    with _lock:
        _conn.execute(
            "REPLACE INTO tokens(token, metadata, payload, timestamp) VALUES (?, ?, ?, ?)",
            (token, json.dumps(metadata), json.dumps(payload), ts),
        )
        _conn.commit()
    log.debug("db.token.saved", token=token, timestamp=ts)


def get_request(token: str) -> dict | None:
    """Retrieve stored metadata/payload for a token if not expired, else return None."""
    log.debug("db.token.get", token=token)
    ttl = _get_ttl()
    with _lock:
        cursor = _conn.execute("SELECT metadata, payload, timestamp FROM tokens WHERE token = ?", (token,))
        row = cursor.fetchone()
        if not row:
            log.debug("db.token.not_found", token=token)
            return None  # token not found
        metadata_json, payload_json, ts = row
        log.debug("db.token.found", token=token, timestamp=ts)
        if int(time.time()) - ts > ttl:
            # expired, delete
            _conn.execute("DELETE FROM tokens WHERE token = ?", (token,))
            _conn.commit()
            log.debug("db.token.expired", token=token)
            return None  # token expired
        data = {"metadata": json.loads(metadata_json), "payload": json.loads(payload_json)}
        log.debug("db.token.retrieved", token=token)
        return data


def delete_request(token: str) -> None:
    """Delete a token record from the database."""
    with _lock:
        _conn.execute("DELETE FROM tokens WHERE token = ?", (token,))
        _conn.commit()
    log.debug("db.token.deleted", token=token)


def cleanup():
    """Remove expired tokens from the database."""
    ttl = _get_ttl()
    cutoff = int(time.time()) - ttl
    with _lock:
        _conn.execute("DELETE FROM tokens WHERE timestamp < ?", (cutoff,))
        _conn.commit()


def list_tokens() -> list[dict]:
    """Return all tokens and their timestamps (for debugging)."""
    with _lock:
        cursor = _conn.execute("SELECT token, timestamp FROM tokens")
        rows = cursor.fetchall()
    return [{"token": token, "timestamp": ts} for token, ts in rows]
