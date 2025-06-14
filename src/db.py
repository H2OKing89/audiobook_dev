import sqlite3
import json
import threading
import time
from pathlib import Path
from src.config import load_config
from typing import Optional
import logging

# Initialize SQLite database for token storage
db_path = Path(__file__).parent.parent / 'db.sqlite'
_conn = sqlite3.connect(db_path, check_same_thread=False)
_lock = threading.Lock()

# Create table if not exists
with _lock:
    cursor = _conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tokens (
            token TEXT PRIMARY KEY,
            metadata TEXT,
            payload TEXT,
            timestamp INTEGER
        )
    ''')
    _conn.commit()

# Load TTL from config
_config = load_config()
TTL = _config.get('server', {}).get('reply_token_ttl', 3600)


def save_request(token: str, metadata: dict, payload: dict) -> None:
    """Save metadata and payload for a token."""
    ts = int(time.time())
    with _lock:
        _conn.execute(
            'REPLACE INTO tokens(token, metadata, payload, timestamp) VALUES (?, ?, ?, ?)',
            (token, json.dumps(metadata), json.dumps(payload), ts)
        )
        _conn.commit()
    logging.debug(f"DB: Saved token {token} at {ts}")


def get_request(token: str) -> Optional[dict]:
    """Retrieve stored metadata/payload for a token if not expired, else return None."""
    logging.debug(f"DB: Getting token {token}")
    with _lock:
        cursor = _conn.execute(
            'SELECT metadata, payload, timestamp FROM tokens WHERE token = ?', (token,)
        )
        row = cursor.fetchone()
        if not row:
            logging.debug(f"DB: Token {token} not found")
            return None  # token not found
        metadata_json, payload_json, ts = row
        logging.debug(f"DB: Found token {token} with timestamp {ts}")
        if int(time.time()) - ts > TTL:
            # expired, delete
            _conn.execute('DELETE FROM tokens WHERE token = ?', (token,))
            _conn.commit()
            logging.debug(f"DB: Token {token} expired and removed")
            return None  # token expired
        data = {
            'metadata': json.loads(metadata_json),
            'payload': json.loads(payload_json)
        }
        logging.debug(f"DB: Returning data for token {token}")
        return data


def delete_request(token: str) -> None:
    """Delete a token record from the database."""
    with _lock:
        _conn.execute('DELETE FROM tokens WHERE token = ?', (token,))
        _conn.commit()
    logging.debug(f"DB: Deleted token {token}")


def cleanup():
    """Remove expired tokens from the database."""
    cutoff = int(time.time()) - TTL
    with _lock:
        _conn.execute('DELETE FROM tokens WHERE timestamp < ?', (cutoff,))
        _conn.commit()


def list_tokens() -> list[dict]:
    """Return all tokens and their timestamps (for debugging)."""
    with _lock:
        cursor = _conn.execute('SELECT token, timestamp FROM tokens')
        rows = cursor.fetchall()
    return [{'token': token, 'timestamp': ts} for token, ts in rows]
