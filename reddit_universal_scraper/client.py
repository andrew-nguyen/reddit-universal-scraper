"""HTTP client helpers for Reddit and mirror endpoints."""

from __future__ import annotations

import time
from typing import Any

import requests

from .settings import MIRRORS, PROXY_AUTO_ROTATE, PROXY_URL, USER_AGENT, get_formatted_proxy_url, is_proxy_disabled


class RedditClient:
    """Small wrapper around a requests-compatible session."""

    def __init__(
        self,
        session: Any | None = None,
        *,
        user_agent: str = USER_AGENT,
        mirrors: list[str] | None = None,
        timeout: int = 15,
        proxy_url: str | None = PROXY_URL,
        proxy_country: str | None = None,
        proxy_session_id: str | None = None,
        proxy_auto_rotate: bool = PROXY_AUTO_ROTATE,
        retries: int = 3,
        retry_backoff: int = 2,
        sleep: Any = time.sleep,
    ):
        self.session = session or requests.Session()
        self.session.headers.update({"User-Agent": user_agent})
        self.mirrors = list(mirrors or MIRRORS)
        self.timeout = timeout
        self.proxy_url = proxy_url
        self.proxy_country = proxy_country
        self.proxy_session_id = proxy_session_id
        self.proxy_auto_rotate = proxy_auto_rotate
        self.retries = retries
        self.retry_backoff = retry_backoff
        self.sleep = sleep
        self._configure_proxy(force_rotate=False)

    def _current_proxy_url(self, *, force_rotate: bool = False) -> str | None:
        if is_proxy_disabled(self.proxy_url):
            return None
        return get_formatted_proxy_url(
            str(self.proxy_url),
            country=self.proxy_country,
            session_id=self.proxy_session_id,
            force_rotate=force_rotate,
            auto_rotate=self.proxy_auto_rotate,
        )

    def _configure_proxy(self, *, force_rotate: bool = False) -> str | None:
        proxy_url = self._current_proxy_url(force_rotate=force_rotate)
        if proxy_url:
            self.session.proxies = {"http": proxy_url, "https": proxy_url}
        else:
            self.session.proxies = {}
        return proxy_url

    def _get(self, url: str, **kwargs):
        for attempt in range(self.retries):
            try:
                self._configure_proxy(force_rotate=True)
                response = self.session.get(url, **kwargs)
                if response.status_code == 429 and attempt < self.retries - 1:
                    self.sleep(self.retry_backoff * (attempt + 1))
                    continue

                content_type = getattr(response, "headers", {}).get("Content-Type", "")
                body = getattr(response, "text", "")
                if (
                    response.status_code == 200
                    and ".json" in url
                    and "text/html" in content_type
                    and ("Making sure you're not a bot" in body or "bot check" in body.lower())
                ):
                    raise requests.exceptions.RequestException("Bot challenge detected on mirror")

                return response
            except Exception:
                if attempt >= self.retries - 1:
                    raise
                self.sleep(self.retry_backoff)

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
        return self._get(
            self.build_posts_url(target, after=after, is_user=is_user, batch_size=batch_size, base_url=base_url),
            timeout=self.timeout,
        )

    def fetch_comments(self, permalink: str):
        if not permalink.startswith("http"):
            url = f"https://old.reddit.com{permalink}.json?limit=100"
        else:
            url = f"{permalink}.json?limit=100"
        return self._get(url, timeout=self.timeout)

    def fetch_monitor_rss(self, target: str, is_user: bool = False):
        if is_user:
            rss_url = f"https://www.reddit.com/user/{target}/submitted.rss?limit=100"
        else:
            rss_url = f"https://www.reddit.com/r/{target}/new.rss?limit=100"
        return self._get(rss_url, timeout=self.timeout)
