# 🎧 Audiobook Automation System

A modern, secure, and delightfully over-engineered FastAPI microservice for automated audiobook approval workflows. Built by Quentin with maximum automation and minimum manual intervention in mind.

## Security and CI

[![CI](https://github.com/H2OKing89/audiobook_dev/actions/workflows/ci.yml/badge.svg)](https://github.com/H2OKing89/audiobook_dev/actions/workflows/ci.yml)
[![Dependency Review](https://github.com/H2OKing89/audiobook_dev/actions/workflows/dependency-review.yml/badge.svg)](https://github.com/H2OKing89/audiobook_dev/actions/workflows/dependency-review.yml)

Current security and test status is tracked in GitHub Actions.

---

## ✨ Features

- **🔒 Secure Webhook Endpoint** - Token-validated integration with Autobrr/MAM
- **📖 Metadata Enrichment** - Audnex API and authenticated Audible lookups for rich book data
- **💾 Persistent Storage** - SQLite database with comprehensive audit trails
- **⏰ Time-Limited Tokens** - Cryptographically secure, single-use approval tokens
- **📱 Multi-Platform Notifications** - Pushover, Discord, Gotify, and Ntfy support
- **🎨 Beautiful Web Interface** - Modern, responsive UI with cyberpunk/anime aesthetics
- **🌐 Social Media Ready** - Dynamic OG/Twitter meta tags for all pages
- **⚙️ qBittorrent Integration** - Automated torrent handling with MAM cookie support
- **🚀 Async Performance** - Threadpool handling for optimal responsiveness
- **📊 Comprehensive Logging** - Centralized, rotating logs with detailed audit trails
- **♿ Accessibility First** - WCAG 2.1 AA compliance with ARIA labels and keyboard navigation
- **🧪 Test Coverage** - Comprehensive unit and integration test suite

---

## 📚 Documentation

Complete documentation is available in the [`docs/`](docs/) directory:

### 🎯 For Users

- **[📖 Getting Started](docs/user-guide/getting-started.md)** - Installation and setup guide
- **[⚙️ Configuration](docs/user-guide/configuration.md)** - Configuration options and examples
- **[🌐 Web Interface](docs/user-guide/web-interface.md)** - Using the web UI
- **[📱 Notifications](docs/user-guide/notifications.md)** - Setting up notification services
- **[🔧 Troubleshooting](docs/user-guide/troubleshooting.md)** - Common issues and solutions

### 🛠️ For Developers

- **[🏗️ Architecture](docs/development/architecture.md)** - System design and component overview
- **[🔐 Security](docs/development/SECURITY.md)** - Security implementation details
- **[🎨 Interactive Fixes](docs/development/INTERACTIVE_FIXES.md)** - UI/UX improvements
- **[📋 Logging](docs/development/LOGGING_IMPROVEMENTS.md)** - Enhanced logging system
- **[🧪 Testing](docs/development/testing.md)** - Testing strategies and guidelines

### 🔌 API Reference

- **[🌐 REST API](docs/api/rest-api.md)** - Complete API documentation
- **[🔗 Webhooks](docs/api/webhooks.md)** - Webhook configuration and payloads
- **[💾 Database](docs/api/database.md)** - Database schema and queries
- **[📋 Configuration](docs/api/config-reference.md)** - Complete configuration reference

---

## 🚀 Quick Start

```bash
# Clone the repository
git clone https://github.com/H2OKing89/audiobook_dev.git
cd audiobook_dev

# Set up virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
make install-dev

# Configure the system
cp config/config.yaml.example config/config.yaml
# Edit config/config.yaml with your settings

# Initialize database
python src/db.py

# Start the application
python src/main.py
```

Visit `http://localhost:8000` to access the beautiful web interface!

For detailed setup instructions, see the [Getting Started Guide](docs/user-guide/getting-started.md).

---

## 🏗️ Project Structure

```text
audiobook_dev/
├── docs/                    # 📚 Comprehensive documentation
│   ├── user-guide/         # User documentation and guides
│   ├── development/        # Developer and architecture docs
│   └── api/                # API reference and webhooks
├── src/                    # 🐍 Python source code
│   ├── main.py            # FastAPI application entry point
│   ├── webui.py           # Web interface and routes
│   ├── metadata.py        # Audiobook metadata handling
│   ├── token_gen.py       # Secure token generation/validation
│   ├── notify/            # 📱 Notification service modules
│   │   ├── pushover.py    # Pushover notifications
│   │   ├── gotify.py      # Gotify notifications
│   │   ├── discord.py     # Discord notifications
│   │   └── ntfy.py        # Ntfy notifications
│   ├── qbittorrent.py     # qBittorrent integration
│   ├── db.py              # SQLite database operations
│   ├── config.py          # Configuration management
│   ├── html.py            # Jinja2 template utilities
│   └── utils.py           # Shared utility functions
├── templates/              # 🎨 Jinja2 HTML templates
│   ├── base.html          # Base template with common elements
│   ├── index.html         # Enhanced home page
│   ├── approval.html      # Approval workflow page
│   ├── rejection.html     # Witty rejection page
│   └── *.html             # Additional UI templates
├── static/                 # 🌐 Static web assets
│   ├── css/style.css      # Enhanced cyberpunk styling
│   └── js/app.js          # Interactive JavaScript features
├── tests/                  # 🧪 Comprehensive test suite
├── config/                 # ⚙️ Configuration files
│   └── config.yaml        # Main application configuration
├── logs/                   # 📋 Application logs
└── db.sqlite              # 💾 SQLite database
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
   make install-dev
   ```

   This installs the upstream `mkb79/Audible` package from GitHub for the authenticated Audible backend.

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
- Uses `mkb79/Audible` with an encrypted auth file for Audible-backed search.
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
