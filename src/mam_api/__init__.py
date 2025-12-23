"""
MAM (MyAnonamouse) API Client Package

This package provides a clean interface to MAM's JSON API
using httpx for HTTP/2 support and Pydantic for response validation.

The adapter module provides backward compatibility with the old MAMScraper interface.
"""
from src.mam_api.client import MamClient, MamAsyncClient, MamApiError, extract_tid_from_irc
from src.mam_api.models import (
    MamTorrentRaw,
    MamTorrentNormalized,
    MamSearchResponseRaw,
    MamMediaInfo,
)
from src.mam_api.adapter import MAMApiAdapter

# Alias for backward compatibility with old MAMScraper code
MAMScraper = MAMApiAdapter

__all__ = [
    # Core client classes
    "MamClient",
    "MamAsyncClient", 
    "MamApiError",
    "extract_tid_from_irc",
    # Models
    "MamTorrentRaw",
    "MamTorrentNormalized",
    "MamSearchResponseRaw",
    "MamMediaInfo",
    # Adapter (backward compatibility)
    "MAMApiAdapter",
    "MAMScraper",  # Alias for MAMApiAdapter
]
