"""
MAM (MyAnonamouse) API Client Package

This package provides a clean interface to MAM's JSON API
using httpx for HTTP/2 support and Pydantic for response validation.
"""

from src.mam_api.adapter import MAMApiAdapter
from src.mam_api.client import MamApiError, MamAsyncClient, MamClient, extract_tid_from_irc
from src.mam_api.models import (
    MamMediaInfo,
    MamSearchResponseRaw,
    MamTorrentNormalized,
    MamTorrentRaw,
)


__all__ = [
    "MAMApiAdapter",
    "MamApiError",
    "MamAsyncClient",
    "MamClient",
    "MamMediaInfo",
    "MamSearchResponseRaw",
    "MamTorrentNormalized",
    "MamTorrentRaw",
    "extract_tid_from_irc",
]
