"""Legacy async scraper package.

Prefer importing the sync public API from ``reddit_universal_scraper``.
"""

from reddit_universal_scraper import RedditScraper, ScrapeMode, ScrapeOptions, ScrapeResult

from .async_scraper import run_async_scraper, scrape_async

__all__ = [
    "RedditScraper",
    "ScrapeMode",
    "ScrapeOptions",
    "ScrapeResult",
    "run_async_scraper",
    "scrape_async",
]
