from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest

import main
from reddit_universal_scraper import RedditScraper, ScrapeMode
from reddit_universal_scraper.models import MediaCounts
from reddit_universal_scraper.media import MediaDownloader
from reddit_universal_scraper.storage import setup_directories


class FakeResponse:
    def __init__(self, status_code=200, body=b"data", json_data=None):
        self.status_code = status_code
        self.body = body
        self._json_data = json_data
        self.content = body

    def iter_content(self, chunk_size=8192):
        yield self.body

    def json(self):
        return self._json_data


class FakeSession:
    def __init__(self, responses=None):
        self.responses = responses or {}
        self.calls = []
        self.headers = {}

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        response = self.responses.get(url)
        if isinstance(response, Exception):
            raise response
        if response is None:
            raise AssertionError(f"unexpected URL: {url}")
        return response


class FakeClient:
    def __init__(self, pages):
        self.pages = list(pages)
        self.mirrors = ["https://mirror.example"]
        self.calls = []

    def fetch_posts_page(self, target, after=None, is_user=False, batch_size=100, base_url=None):
        self.calls.append(
            {
                "target": target,
                "after": after,
                "is_user": is_user,
                "batch_size": batch_size,
                "base_url": base_url,
            }
        )
        return FakeResponse(json_data=self.pages.pop(0))


class FakeCommentFetcher:
    def __init__(self, comments=None):
        self.comments = comments or []
        self.calls = []

    def fetch(self, permalink, max_depth=3):
        self.calls.append((permalink, max_depth))
        return list(self.comments)


class FakeMediaDownloader:
    def __init__(self, counts=None):
        self.counts = counts or MediaCounts()
        self.calls = []

    def download_post_media(self, post_data, dirs, post_id, dry_run=False):
        self.calls.append((post_data, dirs, post_id, dry_run))
        return self.counts


class FakeJobTracker:
    def __init__(self):
        self.started = []
        self.completed = []

    def start(self, target, mode, is_user=False, dry_run=False):
        self.started.append((target, mode, is_user, dry_run))
        return "job-1"

    def complete(self, job_id, status, posts=0, comments=0, media=0, errors=None):
        self.completed.append((job_id, status, posts, comments, media, errors))


def make_page(after=None, post_id="p1", num_comments=0):
    return {
        "data": {
            "after": after,
            "children": [
                {
                    "data": {
                        "id": post_id,
                        "title": f"Post {post_id}",
                        "author": "alice",
                        "created_utc": 1_700_000_000,
                        "permalink": f"/r/delhi/comments/{post_id}/post/",
                        "url": f"https://www.reddit.com/r/delhi/comments/{post_id}/post/",
                        "score": 10,
                        "upvote_ratio": 0.9,
                        "num_comments": num_comments,
                        "num_crossposts": 0,
                        "selftext": "",
                        "is_self": True,
                    }
                }
            ],
        }
    }


def test_dry_run_writes_no_media(tmp_path):
    dirs = setup_directories("delhi", "r", data_dir=tmp_path / "data")
    downloader = MediaDownloader(session=FakeSession())
    post = {
        "id": "post1",
        "url": "https://example.com/image.jpg",
        "is_video": False,
        "is_gallery": False,
    }

    counts = downloader.download_post_media(post, dirs, "post1", dry_run=True)

    assert counts.images == 0
    assert counts.videos == 0
    assert list(Path(dirs["images"]).iterdir()) == []
    assert list(Path(dirs["videos"]).iterdir()) == []
    assert downloader.session.calls == []


def test_reddit_scraper_history_uses_posts_only_and_returns_result(tmp_path):
    media = FakeMediaDownloader(MediaCounts(images=3, videos=4))
    comments = FakeCommentFetcher([{"comment_id": "c1"}])
    tracker = FakeJobTracker()
    scraper = RedditScraper(
        data_dir=tmp_path / "data",
        client=FakeClient([make_page()]),
        media_downloader=media,
        comment_fetcher=comments,
        job_tracker=tracker,
        sleep=lambda seconds: None,
    )

    result = scraper.scrape_history("delhi", limit=25)

    assert result.mode is ScrapeMode.HISTORY
    assert result.posts_count == 1
    assert result.comments_count == 0
    assert result.media_count == 0
    assert result.job_id == "job-1"
    assert result.output_paths.posts.endswith("data/r_delhi/posts.csv")
    assert media.calls == []
    assert comments.calls == []
    assert tracker.completed == [("job-1", "completed", 1, 0, 0, None)]
    assert pd.read_csv(result.output_paths.posts)["permalink"].tolist() == ["/r/delhi/comments/p1/post/"]


def test_reddit_scraper_full_counts_media_comments_and_records(tmp_path):
    comment = {
        "post_permalink": "/r/delhi/comments/p1/post/",
        "comment_id": "c1",
        "parent_id": "t3_p1",
        "author": "bob",
        "body": "hello",
        "score": 1,
        "created_utc": "2023-11-14T22:13:20",
        "depth": 0,
        "is_submitter": False,
    }
    scraper = RedditScraper(
        data_dir=tmp_path / "data",
        client=FakeClient([make_page(num_comments=1)]),
        media_downloader=FakeMediaDownloader(MediaCounts(images=2, videos=1)),
        comment_fetcher=FakeCommentFetcher([comment]),
        job_tracker=None,
        sleep=lambda seconds: None,
    )

    result = scraper.scrape("delhi", mode="full", limit=10)

    assert result.mode is ScrapeMode.FULL
    assert result.posts_count == 1
    assert result.comments_count == 1
    assert result.media_counts == MediaCounts(images=2, videos=1)
    assert result.posts[0]["id"] == "p1"
    assert result.comments == [comment]
    assert pd.read_csv(result.output_paths.comments)["comment_id"].tolist() == ["c1"]


def test_cli_api_history_equivalence(tmp_path, monkeypatch):
    api_scraper = RedditScraper(
        data_dir=tmp_path / "api",
        client=FakeClient([make_page()]),
        media_downloader=FakeMediaDownloader(),
        comment_fetcher=FakeCommentFetcher(),
        job_tracker=None,
        sleep=lambda seconds: None,
    )
    api_result = api_scraper.scrape_history("delhi", limit=1)

    def scraper_factory(data_dir="data"):
        return RedditScraper(
            data_dir=tmp_path / "cli",
            client=FakeClient([make_page()]),
            media_downloader=FakeMediaDownloader(),
            comment_fetcher=FakeCommentFetcher(),
            job_tracker=None,
            sleep=lambda seconds: None,
        )

    monkeypatch.setattr(main._service, "RedditScraper", scraper_factory)
    legacy_result = main.run_full_history(
        "delhi",
        1,
        False,
        download_media_flag=False,
        scrape_comments_flag=False,
    )

    api_posts = pd.read_csv(api_result.output_paths.posts)
    cli_posts = pd.read_csv(tmp_path / "cli/r_delhi/posts.csv")
    assert legacy_result["posts"] == api_result.posts_count == 1
    assert list(cli_posts.columns) == list(api_posts.columns)


@pytest.mark.parametrize(
    ("runner", "expected"),
    [
        ("success", b"merged"),
        ("missing", b"video"),
        ("failure", b"video"),
    ],
)
def test_reddit_video_audio_fallback(tmp_path, runner, expected):
    video_url = "https://v.redd.it/post/DASH_720.mp4"
    audio_url = "https://v.redd.it/post/DASH_audio.mp4"
    save_path = tmp_path / f"{runner}.mp4"
    session = FakeSession(
        {
            video_url: FakeResponse(body=b"video"),
            audio_url: FakeResponse(body=b"audio"),
        }
    )

    def fake_runner(cmd, capture_output=True, timeout=120):
        if runner == "missing":
            raise FileNotFoundError
        if runner == "success":
            Path(cmd[-1]).write_bytes(b"merged")
            return SimpleNamespace(returncode=0)
        return SimpleNamespace(returncode=1)

    downloader = MediaDownloader(session=session, runner=fake_runner)

    assert downloader.download_reddit_video_with_audio(video_url, save_path) is True
    assert save_path.read_bytes() == expected
