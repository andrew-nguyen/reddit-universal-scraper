"""Comment fetching helpers."""

from __future__ import annotations

from .client import RedditClient
from .extractors import parse_comments


class CommentFetcher:
    """Fetch and parse comments using a RedditClient."""

    def __init__(self, client: RedditClient):
        self.client = client

    def fetch(self, permalink: str, max_depth: int = 3) -> list[dict]:
        comments: list[dict] = []
        try:
            response = self.client.fetch_comments(permalink)
            if response.status_code != 200:
                return comments

            data = response.json()
            if len(data) > 1:
                comment_data = data[1]["data"]["children"]
                comments = parse_comments(comment_data, permalink, depth=0, max_depth=max_depth)
        except Exception:
            pass
        return comments
