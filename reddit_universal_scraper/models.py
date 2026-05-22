"""Typed public models for scraper callers."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ScrapeMode(str, Enum):
    """Supported scrape modes."""

    FULL = "full"
    HISTORY = "history"
    MONITOR = "monitor"

    @classmethod
    def coerce(cls, value: "ScrapeMode | str") -> "ScrapeMode":
        if isinstance(value, cls):
            return value
        return cls(str(value))


@dataclass(slots=True)
class MediaCounts:
    """Downloaded media counts."""

    images: int = 0
    videos: int = 0

    @property
    def total(self) -> int:
        return self.images + self.videos


@dataclass(slots=True)
class OutputPaths:
    """Filesystem paths used for one scrape target."""

    base: str
    posts: str
    comments: str
    media: str
    images: str
    videos: str


@dataclass(slots=True)
class ScrapeOptions:
    """Options accepted by the sync scraper API."""

    target: str | None = None
    mode: ScrapeMode | str = ScrapeMode.FULL
    limit: int = 100
    is_user: bool = False
    download_media: bool | None = None
    scrape_comments: bool | None = None
    dry_run: bool = False
    use_plugins: bool = False
    collect_records: bool = True

    def __post_init__(self) -> None:
        self.mode = ScrapeMode.coerce(self.mode)


@dataclass(slots=True)
class ScrapeResult:
    """Structured result returned by scraper operations."""

    target: str
    mode: ScrapeMode | str
    output_paths: OutputPaths
    posts_count: int = 0
    comments_count: int = 0
    media_counts: MediaCounts = field(default_factory=MediaCounts)
    duration_seconds: float = 0.0
    is_user: bool = False
    dry_run: bool = False
    job_id: str | None = None
    posts: list[dict[str, Any]] = field(default_factory=list)
    comments: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.mode = ScrapeMode.coerce(self.mode)

    @property
    def media_count(self) -> int:
        return self.media_counts.total
