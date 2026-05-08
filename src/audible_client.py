"""Authenticated client management for the mkb79/Audible package."""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    import audible

try:
    import audible as _audible_mod

    _AUDIBLE_AVAILABLE = True
except ModuleNotFoundError:
    _audible_mod = None  # type: ignore[assignment]
    _AUDIBLE_AVAILABLE = False

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
        env_auth_file = os.getenv("AUDIBLE_AUTH_FILE")
        env_auth_file_password = os.getenv("AUDIBLE_AUTH_FILE_PASSWORD")
        audible_config: dict[str, str] = {}
        if auth_file is None and env_auth_file is None:
            config = load_config()
            audible_config = config.get("metadata", {}).get("audible", {})

        self.auth_file = auth_file or env_auth_file or audible_config.get("auth_file")
        self.auth_file_password = auth_file_password or env_auth_file_password

        self._auth: audible.Authenticator | None = None
        self._clients: dict[str, audible.AsyncClient] = {}
        self._init_lock = asyncio.Lock()
        self._shutting_down = False

    @property
    def configured(self) -> bool:
        """Return whether the encrypted auth file and decrypt password are set."""
        return bool(self.auth_file and self.auth_file_password)

    async def get_client(self, region: str) -> audible.AsyncClient | None:
        """Return an authenticated Audible async client for a region."""
        if not _AUDIBLE_AVAILABLE:
            log.warning("audible.library.package_not_installed")
            return None

        if not self.auth_file:
            log.warning("audible.library.no_auth_file")
            return None

        if not self.auth_file_password:
            log.warning("audible.library.no_auth_file_password")
            return None

        auth_path = Path(self.auth_file).expanduser()
        if not auth_path.exists():
            log.warning("audible.library.auth_file_missing", auth_file=auth_path.name)
            return None

        async with self._init_lock:
            if self._shutting_down:
                log.warning("audible.library.shutting_down", region=region)
                return None

            # Re-check inside the lock in case another coroutine already initialised this region.
            if region in self._clients:
                return self._clients[region]

            try:
                if self._auth is None:
                    self._auth = _audible_mod.Authenticator.from_file(
                        auth_path,
                        password=self.auth_file_password,
                    )

                client = _audible_mod.AsyncClient(auth=self._auth, country_code=region)
            except Exception as exc:
                log.warning("audible.library.auth_failed", error=str(exc))
                return None

            self._clients[region] = client
            return client

    async def _close_all_clients(self) -> None:
        """Close cached Audible clients without aborting on the first failure."""
        async with self._init_lock:
            self._shutting_down = True
            for client in list(self._clients.values()):
                try:
                    await client.close()
                except Exception as close_exc:
                    log.warning("audible.client.close_error", error=str(close_exc))
            self._clients.clear()

    async def aclose(self) -> None:
        """Close any cached Audible async clients."""
        await self._close_all_clients()

    async def __aenter__(self) -> AudibleClientProvider:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: object,
    ) -> None:
        """Close all cached clients on context-manager exit."""
        await self._close_all_clients()
