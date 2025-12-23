"""
Pydantic models for MAM (MyAnonamouse) JSON API responses.

This module provides:
- Raw models that mirror MAM's API payloads (with JSON-inside-string decoding)
- Normalized models for internal use with clean, typed fields

IMPORTANT: Several MAM fields are JSON-encoded strings that must be parsed:
- author_info, narrator_info, series_info, mediainfo, ownership
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, ConfigDict, Field, field_validator

logger = logging.getLogger(__name__)


def _safe_json_loads(value: Any, *, default: Any) -> Any:
    """
    MAM returns several fields as JSON-encoded strings (e.g. author_info).
    This helper accepts dict/list already, or parses JSON strings.
    """
    if value is None:
        return default
    if isinstance(value, (dict, list)):
        return value
    if isinstance(value, str):
        s = value.strip()
        if s == "" or s.lower() == "null":
            return default
        try:
            return json.loads(s)
        except json.JSONDecodeError:
            return default
    return default


def _to_bool(value: Any) -> bool:
    """Convert MAM's 0/1 ints or string values to boolean."""
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    if isinstance(value, (int, float)):
        return bool(int(value))
    if isinstance(value, str):
        v = value.strip().lower()
        if v in {"1", "true", "yes", "y"}:
            return True
        if v in {"0", "false", "no", "n", ""}:
            return False
    return False


def _to_int(value: Any, *, default: int = 0) -> int:
    """Convert various types to int with fallback default."""
    if value is None:
        return default
    if isinstance(value, int):
        return value
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        s = value.strip()
        if not s:
            return default
        try:
            return int(float(s))
        except ValueError:
            return default
    return default


def _parse_added_datetime(value: Any) -> Optional[datetime]:
    """
    Parse MAM's 'added' field to UTC datetime.
    
    Docs say 'added' is UTC. MAM returns string like 'YYYY-MM-DD HH:MM:SS'.
    We normalize into an aware datetime in UTC. If parsing fails, return None.
    """
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, str):
        s = value.strip()
        if not s:
            return None
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
            try:
                dt = datetime.strptime(s, fmt)
                return dt.replace(tzinfo=timezone.utc)
            except ValueError:
                continue
    return None


class MamMediaInfoGeneral(BaseModel):
    """General section of mediainfo."""
    model_config = ConfigDict(extra="allow")

    Title: Optional[str] = None
    Format: Optional[str] = None
    Duration: Optional[str] = None


class MamMediaInfoAudio(BaseModel):
    """Audio section of mediainfo."""
    model_config = ConfigDict(extra="allow")

    Format: Optional[str] = None
    BitRate: Optional[str] = None
    BitRate_Mode: Optional[str] = None
    Channels: Optional[int] = None
    SamplingRate: Optional[str] = None
    BitRate_Maximum: Optional[str] = None
    Compression_Mode: Optional[str] = None


class MamMediaInfo(BaseModel):
    """
    Parsed form of the `mediainfo` JSON string.
    
    MAM's structure varies slightly by upload; keep it permissive.
    """
    model_config = ConfigDict(extra="allow")

    General: Optional[MamMediaInfoGeneral] = None
    Audio1: Optional[MamMediaInfoAudio] = None
    menu: Optional[Dict[str, Any]] = None


class MamTorrentRaw(BaseModel):
    """
    Raw torrent object as returned inside response.data[].

    This model *decodes* JSON-inside-string fields (author_info, narrator_info, 
    series_info, mediainfo, ownership). It also coerces 0/1 flags into booleans.
    """
    model_config = ConfigDict(extra="allow")

    id: int
    title: str

    # Category / language
    main_cat: int = 0
    category: int = 0
    catname: str = ""
    cat: Optional[str] = None
    language: int = 0
    lang_code: str = ""

    # Basics
    size: str = ""
    numfiles: int = 0
    filetype: str = ""
    mediatype: int = 0

    # Flags (coerced to bool)
    vip: bool = False
    free: bool = False
    fl_vip: bool = False
    personal_freeleech: bool = False

    vip_expire: int = 0
    browseflags: int = 0
    w: int = 0

    # Stats
    seeders: int = 0
    leechers: int = 0
    times_completed: int = 0
    comments: int = 0

    # User-related
    bookmarked: Optional[str] = None
    my_snatched: bool = False

    # Metadata
    tags: str = ""
    isbn: Optional[str] = None
    poster_type: Optional[str] = None
    
    # Added timestamp (UTC)
    added: Optional[str] = None

    # Optional bulk HTML / download token
    description: Optional[str] = None
    dl: Optional[str] = None

    # JSON-inside-string fields (decoded)
    author_info: Dict[int, str] = Field(default_factory=dict)
    narrator_info: Dict[int, str] = Field(default_factory=dict)
    series_info: Dict[int, List[Any]] = Field(default_factory=dict)
    mediainfo: Optional[MamMediaInfo] = None
    ownership: Optional[Tuple[int, str]] = None

    # --- Validators / coercions ---

    @field_validator(
        "main_cat", "category", "language", "numfiles", "mediatype", "vip_expire",
        "browseflags", "w", "seeders", "leechers", "times_completed", "comments",
        mode="before",
    )
    @classmethod
    def _coerce_ints(cls, v: Any) -> int:
        return _to_int(v, default=0)

    @field_validator("vip", "free", "fl_vip", "personal_freeleech", "my_snatched", mode="before")
    @classmethod
    def _coerce_bools(cls, v: Any) -> bool:
        return _to_bool(v)

    @field_validator("author_info", "narrator_info", mode="before")
    @classmethod
    def _parse_id_name_map(cls, v: Any) -> Dict[int, str]:
        data = _safe_json_loads(v, default={})
        if not isinstance(data, dict):
            return {}
        out: Dict[int, str] = {}
        for k, name in data.items():
            key = _to_int(k, default=0)
            if key != 0:
                out[key] = str(name)
        return out

    @field_validator("series_info", mode="before")
    @classmethod
    def _parse_series_info(cls, v: Any) -> Dict[int, List[Any]]:
        data = _safe_json_loads(v, default={})
        if not isinstance(data, dict):
            return {}
        out: Dict[int, List[Any]] = {}
        for k, val in data.items():
            key = _to_int(k, default=0)
            if key == 0:
                continue
            if isinstance(val, list):
                out[key] = val
            else:
                out[key] = [val]
        return out

    @field_validator("mediainfo", mode="before")
    @classmethod
    def _parse_mediainfo(cls, v: Any) -> Optional[MamMediaInfo]:
        data = _safe_json_loads(v, default=None)
        if data is None:
            return None
        if isinstance(data, MamMediaInfo):
            return data
        if isinstance(data, dict):
            return MamMediaInfo.model_validate(data)
        return None

    @field_validator("ownership", mode="before")
    @classmethod
    def _parse_ownership(cls, v: Any) -> Optional[Tuple[int, str]]:
        data = _safe_json_loads(v, default=None)
        if data is None:
            return None
        # Observed form: [227510,"annbland"]
        if isinstance(data, list) and len(data) >= 2:
            return (_to_int(data[0], default=0), str(data[1]))
        return None

    # --- Convenience properties ---

    @property
    def tid(self) -> int:
        """Alias for torrent ID."""
        return self.id

    @property
    def asin(self) -> str:
        """Extract ASIN from isbn field (often 'ASIN:B0...')."""
        if not self.isbn:
            return ""
        # Handle "ASIN:B0123456789" format
        if self.isbn.upper().startswith("ASIN:"):
            return self.isbn[5:].strip()
        return self.isbn

    @property
    def added_utc(self) -> Optional[datetime]:
        """Parse added timestamp to UTC datetime."""
        return _parse_added_datetime(self.added)

    @property
    def author_names(self) -> List[str]:
        """Get sorted list of author names."""
        return [name for _, name in sorted(self.author_info.items(), key=lambda kv: kv[0])]

    @property
    def narrator_names(self) -> List[str]:
        """Get sorted list of narrator names."""
        return [name for _, name in sorted(self.narrator_info.items(), key=lambda kv: kv[0])]

    @property
    def series_display(self) -> str:
        """
        Build "Series Name #5" style display from series entries.
        If multiple series, join them with commas.
        """
        if not self.series_info:
            return ""
        parts: List[str] = []
        for _, entry in sorted(self.series_info.items(), key=lambda kv: kv[0]):
            if not entry:
                continue
            # entry is usually [seriesName, "5", 5.0]
            name = str(entry[0]) if len(entry) >= 1 else ""
            num = str(entry[1]) if len(entry) >= 2 else ""
            if name and num:
                parts.append(f"{name} #{num}")
            elif name:
                parts.append(name)
        return ", ".join(parts)

    def to_normalized(self) -> "MamTorrentNormalized":
        """Convert to normalized internal format."""
        mi = self.mediainfo
        return MamTorrentNormalized(
            tid=self.id,
            title=self.title,
            category=self.catname,
            filetype=self.filetype,
            size=self.size,
            added=self.added_utc,
            vip=self.vip,
            free=self.free,
            fl_vip=self.fl_vip,
            seeders=self.seeders,
            leechers=self.leechers,
            asin=self.asin,
            author=", ".join(self.author_names),
            narrator=", ".join(self.narrator_names),
            series=self.series_display or None,
            duration=(mi.General.Duration if mi and mi.General else None),
            bitrate=(mi.Audio1.BitRate if mi and mi.Audio1 else None),
            codec=(mi.Audio1.Format if mi and mi.Audio1 else None),
            tags=self.tags,
            dl_token=self.dl,
        )


class MamSearchResponseRaw(BaseModel):
    """
    Top-level response from loadSearchJSONbasic.php.
    """
    model_config = ConfigDict(extra="allow")

    perpage: int = 0
    start: int = 0
    data: List[MamTorrentRaw] = Field(default_factory=list)
    total: int = 0
    found: int = 0

    @field_validator("perpage", "start", "total", "found", mode="before")
    @classmethod
    def _coerce_ints(cls, v: Any) -> int:
        return _to_int(v, default=0)


class MamTorrentNormalized(BaseModel):
    """
    Internal normalized torrent record.
    
    Clean, typed fields for internal use after parsing MAM's raw response.
    """
    model_config = ConfigDict(extra="forbid")

    tid: int
    title: str
    category: str
    filetype: str
    size: str

    # Parsed UTC datetime (or None if unavailable)
    added: Optional[datetime] = None

    # Freeleech flags
    vip: bool
    free: bool
    fl_vip: bool
    
    # Stats
    seeders: int
    leechers: int

    # Metadata
    asin: str = ""
    author: str = ""
    narrator: str = ""
    series: Optional[str] = None
    tags: str = ""

    # Audio info (from mediainfo)
    duration: Optional[str] = None
    bitrate: Optional[str] = None
    codec: Optional[str] = None
    
    # Download token (if dlLink was requested)
    dl_token: Optional[str] = None
