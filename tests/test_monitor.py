import pandas as pd

import main
from reddit_universal_scraper import RedditScraper
from reddit_universal_scraper.client import RedditClient
from reddit_universal_scraper.comments import CommentFetcher


class FakeResponse:
    def __init__(self, status_code=200, json_data=None):
        self.status_code = status_code
        self._json_data = json_data
        self.content = b""

    def json(self):
        return self._json_data


class FakeSession:
    def __init__(self):
        self.headers = {}
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return FakeResponse(
            json_data=[
                {},
                {
                    "data": {
                        "children": [
                            {
                                "kind": "t1",
                                "data": {
                                    "id": "c1",
                                    "parent_id": "t3_post",
                                    "author": "alice",
                                    "body": "hello",
                                    "score": 1,
                                    "created_utc": 1_700_000_000,
                                    "is_submitter": False,
                                    "replies": "",
                                },
                            }
                        ]
                    }
                },
            ]
        )


class FakeRSSResponse:
    status_code = 200
    content = b"""<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <title>Monitor title</title>
    <published>2026-05-21T12:00:00Z</published>
    <link href="https://www.reddit.com/r/delhi/comments/p1/post/" />
  </entry>
</feed>
"""


class FakeMonitorClient:
    def __init__(self, rss_response=None, pages=None):
        self.rss_response = rss_response or FakeRSSResponse()
        self.pages = list(pages or [])
        self.mirrors = ["https://mirror.example"]
        self.rss_calls = []
        self.page_calls = []

    def fetch_monitor_rss(self, target, is_user=False):
        self.rss_calls.append((target, is_user))
        return self.rss_response

    def fetch_posts_page(self, target, after=None, is_user=False, batch_size=100, base_url=None):
        self.page_calls.append((target, after, is_user, batch_size, base_url))
        return FakeResponse(json_data=self.pages.pop(0))


def test_reddit_client_builds_posts_comments_and_rss_urls():
    session = FakeSession()
    client = RedditClient(session=session, mirrors=["https://mirror.example"], timeout=7)

    client.fetch_posts_page("delhi", after="token", is_user=False, batch_size=25)
    client.fetch_posts_page("spez", is_user=True, batch_size=10)
    client.fetch_comments("/r/test/comments/post/")
    client.fetch_monitor_rss("delhi", is_user=False)
    client.fetch_monitor_rss("spez", is_user=True)

    assert session.headers["User-Agent"]
    assert session.calls[0] == (
        "https://mirror.example/r/delhi/new.json?limit=25&raw_json=1&after=token",
        {"timeout": 7},
    )
    assert session.calls[1][0] == "https://mirror.example/user/spez/submitted.json?limit=10&raw_json=1"
    assert session.calls[2][0] == "https://old.reddit.com/r/test/comments/post/.json?limit=100"
    assert session.calls[3][0] == "https://www.reddit.com/r/delhi/new.rss?limit=100"
    assert session.calls[4][0] == "https://www.reddit.com/user/spez/submitted.rss?limit=100"


def test_comment_fetcher_uses_shared_parser():
    session = FakeSession()
    client = RedditClient(session=session, mirrors=["https://mirror.example"])
    fetcher = CommentFetcher(client)

    comments = fetcher.fetch("/r/test/comments/post/")

    assert [comment["comment_id"] for comment in comments] == ["c1"]
    assert comments[0]["post_permalink"] == "/r/test/comments/post/"


def test_bounded_monitor(tmp_path):
    scraper = RedditScraper(
        data_dir=tmp_path / "data",
        client=FakeMonitorClient(),
        job_tracker=None,
        sleep=lambda seconds: None,
    )

    results = list(scraper.monitor("delhi", interval_seconds=300, max_iterations=1))

    assert len(results) == 1
    assert results[0].posts_count == 1
    assert results[0].posts[0]["source"] == "Monitor-RSS"
    assert pd.read_csv(results[0].output_paths.posts)["title"].tolist() == ["Monitor title"]


def test_monitor_fallback_runs_history_when_rss_blocked(tmp_path):
    blocked = type("Blocked", (), {"status_code": 403, "content": b""})()
    client = FakeMonitorClient(
        rss_response=blocked,
        pages=[
            {
                "data": {
                    "after": None,
                    "children": [
                        {
                            "data": {
                                "id": "p1",
                                "title": "History fallback",
                                "author": "alice",
                                "created_utc": 1_700_000_000,
                                "permalink": "/r/delhi/comments/p1/post/",
                                "url": "https://www.reddit.com/r/delhi/comments/p1/post/",
                                "score": 1,
                                "num_comments": 0,
                                "is_self": True,
                            }
                        }
                    ],
                }
            }
        ],
    )
    scraper = RedditScraper(data_dir=tmp_path / "data", client=client, job_tracker=None, sleep=lambda seconds: None)

    result = scraper.check_monitor_once("delhi")

    assert result.posts_count == 1
    assert client.page_calls[0][3] == 25


def test_cli_monitor_interrupt(monkeypatch):
    calls = []

    class FakeScraper:
        def monitor(self, target, is_user=False, interval_seconds=300, max_iterations=None, stop_event=None):
            calls.append((target, is_user, interval_seconds, max_iterations, stop_event))
            raise KeyboardInterrupt

    monkeypatch.setattr(main.sys, "argv", ["main.py", "delhi", "--mode", "monitor"])
    monkeypatch.setattr(main._service, "RedditScraper", lambda: FakeScraper())

    main.main()

    assert calls == [("delhi", False, 300, None, None)]
