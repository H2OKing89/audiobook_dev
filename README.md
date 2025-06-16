# Audiobook Approval Microservice

A modular, production-ready FastAPI microservice for secure, stylish, and automated audiobook approval workflows. Features rich notifications, modern web UI, robust qBittorrent integration, and strong accessibility.

---

## Features

- **Webhook endpoint** for Autobrr/MAM with secure token validation
- **Metadata enrichment** via Audnex API and Audible scraping
- **Persistent SQLite storage** for tokens and metadata
- **Time-limited, one-time-use approval tokens**
- **Rich notifications**: Pushover (with cover), Discord (embed), Gotify (markdown, cover), ntfy
- **Modern, mobile-friendly web UI**: Approve/reject, cyberpunk/anime style, light/dark mode
- **Dynamic OG/Twitter meta tags** for all major pages (social sharing)
- **Robust qBittorrent integration**: .torrent download with MAM cookie, config-driven options
- **Async/threadpool** for blocking calls
- **Centralized, rotating logging** (configurable)
- **Accessibility**: ARIA labels, color contrast, keyboard navigation
- **Unit/integration test scaffolding**

---

## Project Structure

```
audiobook_dev/
├── src/
│   ├── main.py           # FastAPI app: webhooks, routes, logging
│   ├── metadata.py       # Metadata lookup (Audnex, Audible)
│   ├── token_gen.py      # Token creation/validation
│   ├── notify/
│   │   ├── pushover.py   # Pushover notification
│   │   ├── gotify.py     # Gotify notification
│   │   ├── discord.py    # Discord notification
│   │   ├── ntfy.py       # ntfy notification
│   ├── qbittorrent.py    # qBittorrent integration
│   ├── webui.py          # Web UI endpoints
│   ├── db.py             # Persistent SQLite storage
│   ├── config.py         # YAML config loader
│   ├── html.py           # Jinja2 template rendering
│   └── utils.py          # Shared helpers/utilities
├── templates/            # Jinja2 HTML templates
├── config/
│   └── config.yaml       # Main configuration
├── .env                  # Secrets (never commit)
├── requirements.txt      # Python dependencies
├── tests/                # Pytest-based tests
└── README.md
```

---

## Setup

1. **Clone the repo**
   ```bash
   git clone <repo-url>
   cd audiobook_dev
   ```
2. **Create and activate a virtualenv**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```
3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```
4. **Copy and edit config**
   - Edit `config/config.yaml` for your environment (API URLs, notification settings, etc).
   - Create a `.env` file with your secrets (see `.env.example`).

---

## Running

```bash
uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```

- The webhook endpoint is set in `config.yaml` (default: `/webhook/audiobook-requests`).
- The web UI is available at `/`.

---

## Notifications

- **Pushover**: Rich HTML, cover image, approval link.
- **Discord**: Embed with cover, links, and markdown.
- **Gotify**: Markdown, cover image, action links.
- **ntfy**: Markdown, cover image, action links.

Configure each in `config/config.yaml` and `.env`.

---

## Metadata

- Uses Audnex API for fast, reliable metadata.
- Falls back to Audible scraping if needed.
- Cleans and normalizes author, narrator, series, and description fields.
- Caches lookups with LRU cache for efficiency.

---

## Testing

- Run all tests:
  ```bash
  pytest -vv
  ```
- Tests cover:
  - Metadata cleaning and validation
  - Notification formatting
  - Web UI endpoints
  - Error cases
- Fixtures in `tests/conftest.py` for isolation.

---

## Development

- Code style: Black, isort, flake8 recommended.
- Logging is configurable in `config.yaml`.
- All user input is sanitized before rendering or sending to notification services.
- For async/production, consider running with Gunicorn/Uvicorn workers.

---

## Security

- Webhook endpoints require a token (set in `.env`).
- Never commit `.env` or real secrets.
- All user input is sanitized.

---

## License

MIT License. See `LICENSE` for details.