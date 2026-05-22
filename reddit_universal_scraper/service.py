"""Synchronous public scraper service."""

from __future__ import annotations

import random
import time
from typing import Callable

from .client import RedditClient
from .comments import CommentFetcher
from .extractors import extract_post_data
from .job_tracking import JobTracker
from .media import MediaDownloader
from .models import MediaCounts, ScrapeMode, ScrapeOptions, ScrapeResult
from .monitor import parse_monitor_rss
from .storage import ScraperStorage

_DEFAULT_JOB_TRACKER = object()


class RedditScraper:
    """Synchronous Reddit scraper API matching the documented CLI behavior."""

    def __init__(
        self,
        data_dir: str = "data",
        *,
        client: RedditClient | None = None,
        storage: ScraperStorage | None = None,
        media_downloader: MediaDownloader | None = None,
        comment_fetcher: CommentFetcher | None = None,
        job_tracker: JobTracker | None | object = _DEFAULT_JOB_TRACKER,
        sleep: Callable[[float], None] = time.sleep,
        printer: Callable[[str], None] = print,
        shuffle: Callable[[list[str]], None] = random.shuffle,
    ):
        self.printer = printer
        self.sleep = sleep
        self.shuffle = shuffle
        self.client = client or RedditClient()
        self.storage = storage or ScraperStorage(data_dir, printer=printer)
        self.media_downloader = media_downloader or MediaDownloader(session=getattr(self.client, "session", None), printer=printer)
        self.comment_fetcher = comment_fetcher or CommentFetcher(self.client)
        self.job_tracker = JobTracker(printer=printer) if job_tracker is _DEFAULT_JOB_TRACKER else job_tracker

    def scrape(
        self,
        target: str,
        mode: ScrapeMode | str = ScrapeMode.FULL,
        limit: int = 100,
        is_user: bool = False,
        download_media: bool | None = None,
        scrape_comments: bool | None = None,
        dry_run: bool = False,
        use_plugins: bool = False,
        collect_records: bool = True,
    ) -> ScrapeResult:
        options = self._resolve_options(
            target=target,
            mode=mode,
            limit=limit,
            is_user=is_user,
            download_media=download_media,
            scrape_comments=scrape_comments,
            dry_run=dry_run,
            use_plugins=use_plugins,
            collect_records=collect_records,
        )
        if options.mode is ScrapeMode.MONITOR:
            return self.check_monitor_once(target, is_user=is_user)
        return self._scrape_listing(options)

    def scrape_full(self, target: str, limit: int = 100, is_user: bool = False, **overrides) -> ScrapeResult:
        return self.scrape(target, mode=ScrapeMode.FULL, limit=limit, is_user=is_user, **overrides)

    def scrape_history(self, target: str, limit: int = 500, is_user: bool = False) -> ScrapeResult:
        return self.scrape(target, mode=ScrapeMode.HISTORY, limit=limit, is_user=is_user)

    def check_monitor_once(self, target: str, is_user: bool = False) -> ScrapeResult:
        prefix = "u" if is_user else "r"
        paths = self.storage.setup_directories(target, prefix)
        self.storage.load_history(paths.posts)
        start_time = time.time()
        warnings = []
        errors = []

        try:
            response = self.client.fetch_monitor_rss(target, is_user=is_user)
            if response.status_code != 200:
                warnings.append(f"RSS blocked (Status {response.status_code}), trying JSON")
                result = self.scrape(
                    target,
                    mode=ScrapeMode.HISTORY,
                    limit=25,
                    is_user=is_user,
                    download_media=False,
                    scrape_comments=False,
                )
                result.warnings.extend(warnings)
                return result

            posts = parse_monitor_rss(response.content)
            new_posts = [post for post in posts if post["permalink"] not in self.storage.seen_urls]
            saved = self.storage.save_posts_csv(posts, paths.posts)
        except Exception as exc:
            errors.append(str(exc))
            new_posts = []
            saved = 0

        return ScrapeResult(
            target=target,
            mode=ScrapeMode.MONITOR,
            output_paths=paths,
            posts_count=saved,
            duration_seconds=time.time() - start_time,
            is_user=is_user,
            posts=new_posts,
            warnings=warnings,
            errors=errors,
        )

    def monitor(
        self,
        target: str,
        is_user: bool = False,
        interval_seconds: int = 300,
        max_iterations: int | None = None,
        stop_event=None,
    ):
        iterations = 0
        while True:
            if stop_event is not None and stop_event.is_set():
                break
            if max_iterations is not None and iterations >= max_iterations:
                break

            yield self.check_monitor_once(target, is_user=is_user)
            iterations += 1

            if max_iterations is not None and iterations >= max_iterations:
                break
            if stop_event is not None and stop_event.is_set():
                break
            self.sleep(interval_seconds)

    def _resolve_options(self, **kwargs) -> ScrapeOptions:
        options = ScrapeOptions(**kwargs)
        if options.mode is ScrapeMode.HISTORY:
            options.download_media = False
            options.scrape_comments = False
        elif options.mode is ScrapeMode.FULL:
            options.download_media = True if options.download_media is None else options.download_media
            options.scrape_comments = True if options.scrape_comments is None else options.scrape_comments
        return options

    def _scrape_listing(self, options: ScrapeOptions) -> ScrapeResult:
        prefix = "u" if options.is_user else "r"
        paths = self.storage.setup_directories(options.target, prefix)
        dirs = {
            "base": paths.base,
            "posts": paths.posts,
            "comments": paths.comments,
            "media": paths.media,
            "images": paths.images,
            "videos": paths.videos,
        }
        self.storage.load_history(paths.posts)

        total_posts = 0
        total_comments = 0
        total_media = MediaCounts()
        all_scraped_posts: list[dict] = []
        all_scraped_comments: list[dict] = []
        warnings: list[str] = []
        errors: list[str] = []
        after = None
        start_time = time.time()
        error_msg = None

        job_mode = "full" if options.download_media and options.scrape_comments else "history"
        job_id = self.job_tracker.start(options.target, job_mode, options.is_user, options.dry_run) if self.job_tracker else None

        try:
            while total_posts < options.limit:
                mirrors = list(self.client.mirrors)
                self.shuffle(mirrors)
                success = False

                for base_url in mirrors:
                    try:
                        batch_size = min(100, options.limit - total_posts)
                        response = self.client.fetch_posts_page(
                            options.target,
                            after=after,
                            is_user=options.is_user,
                            batch_size=batch_size,
                            base_url=base_url,
                        )
                        if response.status_code != 200:
                            continue

                        data = response.json()
                        posts = []
                        batch_comments = []
                        children = data["data"]["children"]

                        for child in children:
                            post_json = child["data"]
                            post = extract_post_data(post_json)

                            if post["permalink"] in self.storage.seen_urls:
                                continue

                            if options.download_media and not options.dry_run:
                                downloaded = self.media_downloader.download_post_media(
                                    post_json,
                                    dirs,
                                    post["id"],
                                    dry_run=options.dry_run,
                                )
                                post["media_downloaded"] = downloaded.images > 0 or downloaded.videos > 0
                                total_media.images += downloaded.images
                                total_media.videos += downloaded.videos

                            posts.append(post)

                            if options.scrape_comments and post["num_comments"] > 0:
                                comments = self.comment_fetcher.fetch(post["permalink"])
                                batch_comments.extend(comments)
                                total_comments += len(comments)
                                self.sleep(1)

                        all_scraped_posts.extend(posts)
                        all_scraped_comments.extend(batch_comments)

                        if not options.dry_run:
                            saved = self.storage.save_posts_csv(posts, paths.posts)
                            total_posts += saved

                            if batch_comments:
                                self.storage.save_comments_csv(batch_comments, paths.comments)
                        else:
                            total_posts += len(posts)

                        after = data["data"].get("after")
                        if not after:
                            break

                        success = True
                        break
                    except Exception as exc:
                        warnings.append(f"Error with {base_url}: {exc}")
                        continue

                if not after:
                    break

                if not success:
                    self.sleep(30)
                else:
                    self.sleep(3)

            if options.use_plugins and (all_scraped_posts or all_scraped_comments):
                try:
                    from plugins import load_plugins, run_plugins

                    plugins = load_plugins()
                    if plugins:
                        all_scraped_posts, all_scraped_comments = run_plugins(
                            all_scraped_posts,
                            all_scraped_comments,
                            plugins,
                        )
                except Exception as exc:
                    warnings.append(f"Plugin error: {exc}")
        except Exception as exc:
            error_msg = str(exc)
            errors.append(error_msg)

        duration = time.time() - start_time
        status = "failed" if error_msg else "completed"
        if self.job_tracker:
            self.job_tracker.complete(
                job_id,
                status,
                total_posts,
                total_comments,
                total_media.total,
                error_msg,
            )

        return ScrapeResult(
            target=options.target,
            mode=options.mode,
            output_paths=paths,
            posts_count=total_posts,
            comments_count=total_comments,
            media_counts=total_media,
            duration_seconds=duration,
            is_user=options.is_user,
            dry_run=options.dry_run,
            job_id=job_id,
            posts=all_scraped_posts if options.collect_records else [],
            comments=all_scraped_comments if options.collect_records else [],
            warnings=warnings,
            errors=errors,
        )
