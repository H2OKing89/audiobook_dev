"""MAM API client package for MyAnonamouse torrent search."""
from src.mam_api.client import MamClient, MamAsyncClient, MamApiError, extract_tid_from_irc
from src.mam_api.models import (
    MamTorrentRaw,
    MamTorrentNormalized,
    MamSearchResponseRaw,
    MamMediaInfo,
)

__all__ = [
    "MamClient",
    "MamAsyncClient", 
    "MamApiError",
    "extract_tid_from_irc",
    "MamTorrentRaw",
    "MamTorrentNormalized",
    "MamSearchResponseRaw",
    "MamMediaInfo",
]
