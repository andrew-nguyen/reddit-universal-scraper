"""CSV storage and output path helpers."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Callable

import pandas as pd

from .models import OutputPaths

Printer = Callable[[str], None]


def _target_dir(data_dir: str | os.PathLike[str], target: str, prefix: str) -> Path:
    return Path(data_dir) / f"{prefix}_{target}"


def build_output_paths(target: str, prefix: str, data_dir: str | os.PathLike[str] = "data") -> OutputPaths:
    base_dir = _target_dir(data_dir, target, prefix)
    return OutputPaths(
        base=str(base_dir),
        posts=str(base_dir / "posts.csv"),
        comments=str(base_dir / "comments.csv"),
        media=str(base_dir / "media"),
        images=str(base_dir / "media" / "images"),
        videos=str(base_dir / "media" / "videos"),
    )


def setup_directories(
    target: str,
    prefix: str,
    data_dir: str | os.PathLike[str] = "data",
) -> dict[str, str]:
    """Create the current output directory layout and return legacy path keys."""
    paths = build_output_paths(target, prefix, data_dir)
    for path in [paths.base, paths.media, paths.images, paths.videos]:
        Path(path).mkdir(parents=True, exist_ok=True)
    return {
        "base": paths.base,
        "posts": paths.posts,
        "comments": paths.comments,
        "media": paths.media,
        "images": paths.images,
        "videos": paths.videos,
    }


def get_file_path(target: str, type_prefix: str, data_dir: str | os.PathLike[str] = "data") -> str:
    """Legacy flat CSV path helper."""
    Path(data_dir).mkdir(parents=True, exist_ok=True)
    sanitized_target = target.replace("/", "_")
    return str(Path(data_dir) / f"{type_prefix}_{sanitized_target}.csv")


def load_history(filepath: str | os.PathLike[str], seen_urls: set[str] | None = None, printer: Printer = print) -> set[str]:
    """Load existing post permalinks into a seen-url set."""
    urls = seen_urls if seen_urls is not None else set()
    urls.clear()
    if os.path.exists(filepath):
        try:
            df = pd.read_csv(filepath)
            for url in df["permalink"]:
                urls.add(str(url))
            printer(f"📚 Loaded {len(urls)} existing items from {filepath}")
        except Exception:
            pass
    return urls


def save_posts_csv(
    posts: list[dict[str, Any]],
    filepath: str | os.PathLike[str],
    seen_urls: set[str] | None = None,
    printer: Printer = print,
) -> int:
    """Append new post rows to CSV, filtering by permalink."""
    if not posts:
        return 0

    urls = seen_urls if seen_urls is not None else set()
    new_posts = [p for p in posts if p["permalink"] not in urls]

    if new_posts:
        df = pd.DataFrame(new_posts)
        if os.path.exists(filepath):
            df.to_csv(filepath, mode="a", header=False, index=False)
        else:
            df.to_csv(filepath, index=False)

        for post in new_posts:
            urls.add(post["permalink"])

        printer(f"✅ Saved {len(new_posts)} new posts")
        return len(new_posts)

    printer("💤 No new unique posts found.")
    return 0


def save_comments_csv(comments: list[dict[str, Any]], filepath: str | os.PathLike[str], printer: Printer = print) -> None:
    """Append comment rows to CSV."""
    if not comments:
        return

    df = pd.DataFrame(comments)
    if os.path.exists(filepath):
        df.to_csv(filepath, mode="a", header=False, index=False)
    else:
        df.to_csv(filepath, index=False)

    printer(f"💬 Saved {len(comments)} comments")


class ScraperStorage:
    """Instance-scoped CSV storage state for one scraper caller."""

    def __init__(self, data_dir: str | os.PathLike[str] = "data", printer: Printer = print):
        self.data_dir = data_dir
        self.printer = printer
        self.seen_urls: set[str] = set()

    def setup_directories(self, target: str, prefix: str) -> OutputPaths:
        setup_directories(target, prefix, self.data_dir)
        return build_output_paths(target, prefix, self.data_dir)

    def get_file_path(self, target: str, type_prefix: str) -> str:
        return get_file_path(target, type_prefix, self.data_dir)

    def load_history(self, filepath: str | os.PathLike[str]) -> set[str]:
        return load_history(filepath, self.seen_urls, self.printer)

    def save_posts_csv(self, posts: list[dict[str, Any]], filepath: str | os.PathLike[str]) -> int:
        return save_posts_csv(posts, filepath, self.seen_urls, self.printer)

    def save_comments_csv(self, comments: list[dict[str, Any]], filepath: str | os.PathLike[str]) -> None:
        save_comments_csv(comments, filepath, self.printer)
