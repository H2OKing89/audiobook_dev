# Audiobook Automation Project

This project is an automated media microservice platform designed to handle audiobook downloads and notifications. It utilizes FastAPI for the web framework and integrates with various notification services and a torrent client.

## Project Structure

```
audiobook_automation/
├── src/
│   ├── __init__.py
│   ├── main.py           # FastAPI app: receives webhooks, routes requests, serves web UI
│   ├── metadata.py       # Handles metadata lookup (Audnex, OpenLibrary, etc.)
│   ├── token_gen.py      # Handles token creation/approval logic
│   ├── notify/
│   │   ├── __init__.py
│   │   ├── pushover.py   # Notification via Pushover
│   │   ├── gotify.py     # Notification via Gotify
│   │   └── discord.py    # Notification via Discord
│   ├── qbittorrent.py    # Handles interaction with qBittorrent
│   ├── webui.py          # (Optional) HTML endpoints for approve/reject UI
│   └── utils.py          # Any shared helpers/utilities
├── requirements.txt
├── README.md
└── .env                  # For tokens, API keys, secrets (use python-dotenv)
```

## Setup Instructions

1. **Clone the repository:**
   ```
   git clone <repository-url>
   cd audiobook_automation
   ```

2. **Create a virtual environment:**
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   ```

3. **Install dependencies:**
   ```
   pip install -r requirements.txt
   ```

4. **Configure environment variables:**
   Create a `.env` file in the root directory and add your API keys and tokens:
   ```
   AUTOBRR_TOKEN=yourwebhooktoken
   DISCORD_WEBHOOK_URL=https://discord.com/api/...
   PUSHOVER_TOKEN=...
   QB_API_USER=...
   QB_API_PASS=...
   ```

## Usage

- Start the FastAPI application:
  ```
  uvicorn src.main:app --reload
  ```

- The application will be available at `http://127.0.0.1:8000`.

## Endpoints

- **Webhook Endpoint:** `/webhook`
  - Receives incoming JSON payloads from Autobrr.

- **Approval Endpoint:** `/approve/{token}`
  - Displays metadata and allows users to approve or reject requests.

- **Rejection Endpoint:** `/reject/{token}`
  - Handles rejection of requests.

## Notification Services

The project supports notifications through:
- Pushover
- Gotify
- Discord

Each notification service has its own module within the `notify/` directory.

## Future Enhancements

- Consider adding a database for persistent storage of pending approvals.
- Implement background tasks for processing requests asynchronously.
- Expand the web UI for better user experience and mobile support.

## License

This project is licensed under the MIT License. See the LICENSE file for more details.