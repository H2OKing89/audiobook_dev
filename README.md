# Audiobook Approval Microservice

A modular, production-ready FastAPI microservice for secure, stylish, and automated audiobook approval workflows. Features rich notifications, modern web UI, robust qBittorrent integration, and strong accessibility.

---

## Features

- **Webhook endpoint** for Autobrr/MAM with secure token validation
- **Metadata enrichment** via Audnex API and Audible scraping
- **Persistent SQLite storage** for tokens and metadata
- **Time-limited, one-time-use approval tokens**
- **Rich notifications**: Pushover (with cover), Discord (embed), Gotify (markdown, cover)
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
│   │   └── discord.py    # Discord notification
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
├── README.md
├── logs/                 # Rotating log files
├── db.sqlite             # SQLite database
└── tests/                # Unit/integration tests
```

---

## Setup & Usage

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd audiobook_dev
   ```

2. **Create a virtual environment:**
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables:**
   - Copy `.env.example` to `.env` and fill in your secrets (tokens, API keys, cookies, etc).
   - Edit `config/config.yaml` for service options, logging, and qBittorrent settings.

5. **Run the application:**
   ```bash
   uvicorn src.main:app --host 0.0.0.0 --port 8000
   ```
   - For production, use a process manager (e.g., systemd, supervisord, Docker).

6. **Access the web UI:**
   - Visit `http://localhost:8000` (or your configured base URL).

---

## Endpoints

- **Webhook:** `/webhook/audiobook-requests` (configurable)
- **Approval:** `/approve/{token}`
- **Approval Action:** `/approve/{token}/action`
- **Rejection:** `/reject/{token}`
- **UI Home:** `/`

---

## Configuration

- **`config/config.yaml`**: All service, logging, and integration options
- **`.env`**: Secrets (tokens, API keys, cookies)
- **Logging**: Rotating, configurable via YAML
- **qBittorrent**: Host, category, tags, cookie, etc.
- **Notification**: Enable/disable, custom icons, sounds, priorities

---

## Notifications

- **Pushover**: Rich HTML, cover image, approval link
- **Discord**: Embed with all info, cover, approve/reject links
- **Gotify**: Markdown, emoji, cover as bigImageUrl

---

## Accessibility & UI

- ARIA labels and color contrast for screen readers
- Responsive, mobile-friendly, light/dark mode
- Dynamic OG/Twitter meta tags for all major pages
- Dedicated favicon for branding

---

## Testing

- Unit/integration tests in `tests/`
- Run with:
  ```bash
  pytest
  ```

---

## Deployment

- For production, use `systemd` or Docker for headless/background operation
- Example `systemd` service:
  ```ini
  [Unit]
  Description=Audiobook FastAPI Service
  After=network.target

  [Service]
  User=quentin
  WorkingDirectory=/home/quentin/scripts/audiobook_dev
  Environment="PATH=/home/quentin/scripts/audiobook_dev/.venv/bin"
  ExecStart=/home/quentin/scripts/audiobook_dev/.venv/bin/python -m src.main
  Restart=always

  [Install]
  WantedBy=multi-user.target
  ```

---

## License

MIT License. See `LICENSE` for details.