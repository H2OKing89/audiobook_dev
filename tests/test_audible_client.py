"""Tests for the authenticated Audible client provider."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.audible_client import AudibleClientProvider


@pytest.mark.asyncio
async def test_get_client_loads_auth_file_and_caches_by_region(tmp_path: Path) -> None:
    """Load the encrypted auth file once and reuse the same region client."""
    auth_file = tmp_path / "audible-auth.json"
    auth_file.write_text("{}")

    mock_auth = MagicMock()
    mock_client = MagicMock()
    mock_client.close = AsyncMock()

    provider = AudibleClientProvider(
        auth_file=str(auth_file),
        auth_file_password="test-password",
    )

    with patch("src.audible_client._audible_mod.Authenticator.from_file", return_value=mock_auth) as mock_from_file:
        with patch("src.audible_client._audible_mod.AsyncClient", return_value=mock_client) as mock_async_client:
            first = await provider.get_client("us")
            second = await provider.get_client("us")

    assert first is mock_client
    assert second is mock_client
    called_path = Path(mock_from_file.call_args.args[0])
    assert called_path == auth_file
    assert mock_from_file.call_args.kwargs["password"] == "test-password"
    mock_async_client.assert_called_once_with(auth=mock_auth, country_code="us")


@pytest.mark.asyncio
async def test_get_client_returns_none_without_decrypt_password(tmp_path: Path) -> None:
    """Do not attempt auth loading when the decrypt password is missing."""
    auth_file = tmp_path / "audible-auth.json"
    auth_file.write_text("{}")

    provider = AudibleClientProvider(auth_file=str(auth_file))

    client = await provider.get_client("us")

    assert client is None


@pytest.mark.asyncio
async def test_aclose_closes_cached_clients(tmp_path: Path) -> None:
    """Close every cached Audible async client when the provider shuts down."""
    auth_file = tmp_path / "audible-auth.json"
    auth_file.write_text("{}")

    first_client = MagicMock()
    first_client.close = AsyncMock()
    second_client = MagicMock()
    second_client.close = AsyncMock()

    provider = AudibleClientProvider(
        auth_file=str(auth_file),
        auth_file_password="test-password",
    )

    with patch("src.audible_client._audible_mod.Authenticator.from_file", return_value=MagicMock()):
        with patch("src.audible_client._audible_mod.AsyncClient", side_effect=[first_client, second_client]):
            await provider.get_client("us")
            await provider.get_client("ca")

    await provider.aclose()

    first_client.close.assert_awaited_once()
    second_client.close.assert_awaited_once()
