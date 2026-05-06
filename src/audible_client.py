"""Authenticated client management for the mkb79/Audible package."""

from __future__ import annotations

import os
from pathlib import Path

import audible

from src.config import load_config
from src.logging_setup import get_logger


log = get_logger(__name__)

__all__ = ["AudibleClientProvider"]


class AudibleClientProvider:
    """Load encrypted Audible auth and reuse async clients per marketplace."""

    def __init__(
        self,
        *,
        auth_file: str | None = None,
        auth_file_password: str | None = None,
    ) -> None:
        config = load_config()
        audible_config = config.get("metadata", {}).get("audible", {})

        self.auth_file = auth_file or os.getenv("AUDIBLE_AUTH_FILE") or audible_config.get("auth_file")
        self.auth_file_password = auth_file_password or os.getenv("AUDIBLE_AUTH_FILE_PASSWORD")

        self._auth: audible.Authenticator | None = None
        self._clients: dict[str, audible.AsyncClient] = {}

    @property
    def configured(self) -> bool:
        """Return whether the encrypted auth file and decrypt password are set."""
        return bool(self.auth_file and self.auth_file_password)

    async def get_client(self, region: str) -> audible.AsyncClient | None:
        """Return an authenticated Audible async client for a region."""
        if not self.auth_file:
            log.warning("audible.library.no_auth_file")
            return None

        if not self.auth_file_password:
            log.warning("audible.library.no_auth_file_password")
            return None

        if region in self._clients:
            return self._clients[region]

        auth_path = Path(self.auth_file).expanduser()
        if not auth_path.exists():
            log.warning("audible.library.auth_file_missing", auth_file=self.auth_file)
            return None

        try:
            if self._auth is None:
                self._auth = audible.Authenticator.from_file(
                    auth_path,
                    password=self.auth_file_password,
                )

            client = audible.AsyncClient(auth=self._auth, country_code=region)
        except Exception as exc:
            log.warning("audible.library.auth_failed", error=str(exc))
            return None

        self._clients[region] = client
        return client

    async def aclose(self) -> None:
        """Close any cached Audible async clients."""
        for client in self._clients.values():
            await client.close()
        self._clients.clear()
