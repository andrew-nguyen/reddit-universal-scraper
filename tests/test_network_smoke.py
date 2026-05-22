import os

import pytest

from reddit_universal_scraper import RedditScraper
from reddit_universal_scraper.client import RedditClient


@pytest.mark.skipif(os.environ.get("RUN_NETWORK") != "1", reason="set RUN_NETWORK=1 to run live Reddit smoke tests")
def test_history_low_limit(tmp_path):
    scraper = RedditScraper(
        data_dir=tmp_path / "data",
        client=RedditClient(timeout=5),
        job_tracker=None,
        sleep=lambda _seconds: None,
    )

    result = scraper.scrape_history("python", limit=1)
    if result.posts_count == 0:
        pytest.skip("Reddit mirrors unavailable or returned no posts")

    assert result.posts_count == 1
    assert result.output_paths.posts.endswith("data/r_python/posts.csv")
    assert result.comments_count == 0
    assert result.media_count == 0
