"""HTTP client helpers for Reddit and mirror endpoints."""

from __future__ import annotations

from typing import Any

import requests

from .settings import MIRRORS, USER_AGENT


class RedditClient:
    """Small wrapper around a requests-compatible session."""

    def __init__(
        self,
        session: Any | None = None,
        *,
        user_agent: str = USER_AGENT,
        mirrors: list[str] | None = None,
        timeout: int = 15,
    ):
        self.session = session or requests.Session()
        self.session.headers.update({"User-Agent": user_agent})
        self.mirrors = list(mirrors or MIRRORS)
        self.timeout = timeout

    def build_posts_url(
        self,
        target: str,
        *,
        after: str | None = None,
        is_user: bool = False,
        batch_size: int = 100,
        base_url: str | None = None,
    ) -> str:
        base = base_url or self.mirrors[0]
        path = f"/user/{target}/submitted.json" if is_user else f"/r/{target}/new.json"
        url = f"{base}{path}?limit={batch_size}&raw_json=1"
        if after:
            url += f"&after={after}"
        return url

    def fetch_posts_page(
        self,
        target: str,
        after: str | None = None,
        is_user: bool = False,
        batch_size: int = 100,
        base_url: str | None = None,
    ):
        return self.session.get(
            self.build_posts_url(target, after=after, is_user=is_user, batch_size=batch_size, base_url=base_url),
            timeout=self.timeout,
        )

    def fetch_comments(self, permalink: str):
        if not permalink.startswith("http"):
            url = f"https://old.reddit.com{permalink}.json?limit=100"
        else:
            url = f"{permalink}.json?limit=100"
        return self.session.get(url, timeout=self.timeout)

    def fetch_monitor_rss(self, target: str, is_user: bool = False):
        if is_user:
            rss_url = f"https://www.reddit.com/user/{target}/submitted.rss?limit=100"
        else:
            rss_url = f"https://www.reddit.com/r/{target}/new.rss?limit=100"
        return self.session.get(rss_url, timeout=self.timeout)
