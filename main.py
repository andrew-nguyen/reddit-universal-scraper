"""
Universal Reddit Scraper Suite CLI.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import requests

from reddit_universal_scraper import client as _client
from reddit_universal_scraper import comments as _comments
from reddit_universal_scraper import extractors as _extractors
from reddit_universal_scraper import media as _media
from reddit_universal_scraper import service as _service
from reddit_universal_scraper import storage as _storage
from reddit_universal_scraper.settings import MIRRORS, USER_AGENT


_LEGACY_STORAGE = _storage.ScraperStorage()
SEEN_URLS = _LEGACY_STORAGE.seen_urls
SESSION = requests.Session()
SESSION.headers.update({"User-Agent": USER_AGENT})
_LEGACY_CLIENT = _client.RedditClient(session=SESSION, mirrors=MIRRORS)
_LEGACY_MEDIA = _media.MediaDownloader(session=SESSION)
_LEGACY_COMMENTS = _comments.CommentFetcher(_LEGACY_CLIENT)


def setup_directories(target, prefix):
    """Creates organized folder structure for scraped data."""
    return _storage.setup_directories(target, prefix)


def get_file_path(target, type_prefix):
    """Legacy function for backward compatibility."""
    return _storage.get_file_path(target, type_prefix)


def load_history(filepath):
    """Loads existing CSV history to prevent duplicates."""
    _LEGACY_STORAGE.load_history(filepath)


def save_posts_csv(posts, filepath):
    """Saves posts to CSV with all metadata."""
    return _LEGACY_STORAGE.save_posts_csv(posts, filepath)


def save_comments_csv(comments, filepath):
    """Saves comments to CSV."""
    return _LEGACY_STORAGE.save_comments_csv(comments, filepath)


def get_media_urls(post_data):
    """Extracts all media URLs from a post."""
    return _extractors.extract_media_urls(post_data)


def download_media(url, save_path, media_type="image"):
    """Downloads a single media file."""
    return _LEGACY_MEDIA.download(url, save_path, media_type)


def download_reddit_video_with_audio(video_url, save_path):
    """Downloads Reddit video with audio by fetching both streams and merging."""
    return _LEGACY_MEDIA.download_reddit_video_with_audio(video_url, save_path)


def download_post_media(post_data, dirs, post_id):
    """Downloads all media from a post."""
    downloaded = _LEGACY_MEDIA.download_post_media(post_data, dirs, post_id)
    return {"images": downloaded.images, "videos": downloaded.videos}


def scrape_comments(permalink, max_depth=3):
    """Scrapes comments from a post."""
    comments = _LEGACY_COMMENTS.fetch(permalink, max_depth)
    if len(comments) > 0:
        print(f"   + Scraped {len(comments)} comments")
    return comments


def parse_comments(comment_list, post_permalink, depth=0, max_depth=3):
    """Recursively parses comments."""
    return _extractors.parse_comments(comment_list, post_permalink, depth, max_depth)


def extract_post_data(post_json):
    """Extracts comprehensive post data."""
    return _extractors.extract_post_data(post_json)


def run_monitor(target, is_user=False):
    """Compatibility wrapper for one monitor check."""
    return _service.RedditScraper().check_monitor_once(target, is_user=is_user)


def run_full_history(target, limit, is_user=False, download_media_flag=True,
                     scrape_comments_flag=True, dry_run=False, use_plugins=False):
    """Compatibility wrapper for the importable scraper service."""
    mode = "history" if not download_media_flag and not scrape_comments_flag else "full"
    result = _service.RedditScraper().scrape(
        target,
        mode=mode,
        limit=limit,
        is_user=is_user,
        download_media=download_media_flag,
        scrape_comments=scrape_comments_flag,
        dry_run=dry_run,
        use_plugins=use_plugins,
    )
    return {
        "posts": result.posts_count,
        "images": result.media_counts.images,
        "videos": result.media_counts.videos,
        "comments": result.comments_count,
        "duration": f"{result.duration_seconds:.1f}s",
        "dry_run": result.dry_run,
        "job_id": result.job_id,
    }


def build_parser():
    parser = argparse.ArgumentParser(
        description="🤖 Universal Reddit Scraper Suite",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Commands:
  SCRAPING:
    uv run python main.py <target> --mode full --limit 100
    uv run python main.py <target> --mode history --limit 500
    uv run python main.py <target> --mode monitor
    uv run python main.py <target> --dry-run           # Test without saving
    uv run python main.py <target> --plugins           # Enable post-processing

  SEARCH:
    uv run python main.py --search "keyword" --subreddit delhi
    uv run python main.py --search "keyword" --min-score 100

  DASHBOARD:
    uv run python main.py --dashboard

  SCHEDULE:
    uv run python main.py --schedule delhi --every 60

  ANALYTICS:
    uv run python main.py --analyze delhi --sentiment
    uv run python main.py --analyze delhi --keywords

  MAINTENANCE:
    uv run python main.py --job-history                # View job history
    uv run python main.py --backup                     # Backup database
    uv run python main.py --vacuum                     # Optimize database
    uv run python main.py --export-parquet python      # Export to Parquet
    uv run python main.py --list-plugins               # List available plugins

  REST API:
    uv run python main.py --api                        # Start REST API server
        """,
    )

    parser.add_argument("target", nargs="?", help="Subreddit or username to scrape")
    parser.add_argument("--mode", choices=["monitor", "history", "full"], default="full")
    parser.add_argument("--user", action="store_true", help="Target is a user")
    parser.add_argument("--limit", type=int, default=100, help="Max posts to scrape")
    parser.add_argument("--no-media", action="store_true", help="Skip media download")
    parser.add_argument("--no-comments", action="store_true", help="Skip comments")

    parser.add_argument("--dashboard", action="store_true", help="Launch web dashboard")

    parser.add_argument("--search", type=str, help="Search scraped data")
    parser.add_argument("--subreddit", type=str, help="Filter by subreddit")
    parser.add_argument("--min-score", type=int, help="Filter by minimum score")
    parser.add_argument("--author", type=str, help="Filter by author")

    parser.add_argument("--analyze", type=str, help="Run analytics on subreddit")
    parser.add_argument("--sentiment", action="store_true", help="Run sentiment analysis")
    parser.add_argument("--keywords", action="store_true", help="Extract keywords")

    parser.add_argument("--schedule", type=str, help="Schedule scraping for target")
    parser.add_argument("--every", type=int, help="Interval in minutes")

    parser.add_argument("--alert", type=str, help="Set keyword alert")
    parser.add_argument("--discord-webhook", type=str, help="Discord webhook URL")
    parser.add_argument("--telegram-token", type=str, help="Telegram bot token")
    parser.add_argument("--telegram-chat", type=str, help="Telegram chat ID")

    parser.add_argument("--dry-run", action="store_true", help="Simulate scrape without saving data")
    parser.add_argument("--plugins", action="store_true", help="Enable post-processing plugins")
    parser.add_argument("--list-plugins", action="store_true", help="List available plugins")
    parser.add_argument("--job-history", action="store_true", help="View job history")
    parser.add_argument("--backup", action="store_true", help="Backup SQLite database")
    parser.add_argument("--vacuum", action="store_true", help="Optimize SQLite database")
    parser.add_argument("--export-parquet", type=str, help="Export subreddit to Parquet format")
    parser.add_argument("--api", action="store_true", help="Start REST API server (port 8000)")
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)

    print("=" * 50)
    print("🤖 UNIVERSAL REDDIT SCRAPER SUITE")
    print("=" * 50)

    if args.dashboard:
        print("\n🌐 Launching Dashboard...")
        print("   Open: http://localhost:8501")
        os.system("streamlit run dashboard/app.py")
        return

    if args.api:
        print("\n🚀 Starting REST API server...")
        print("   📖 Docs: http://localhost:8000/docs")
        print("   📊 Connect Metabase/Grafana to http://localhost:8000")
        try:
            import uvicorn
            from api.server import app

            uvicorn.run(app, host="0.0.0.0", port=8000)
        except ImportError:
            print("❌ Install dependencies: uv sync")
        return

    if args.job_history:
        from export.database import print_job_history

        print_job_history()
        return

    if args.backup:
        from export.database import backup_database

        backup_database()
        return

    if args.vacuum:
        from export.database import vacuum_database

        vacuum_database()
        return

    if args.export_parquet:
        from export.parquet import export_to_parquet

        prefix = "u" if args.user else "r"
        export_to_parquet(args.export_parquet, prefix=prefix)
        return

    if args.list_plugins:
        from plugins import list_plugins

        list_plugins()
        return

    if args.search:
        print(f"\n🔍 Searching for: {args.search}")
        from search.query import print_search_results, search_all_data

        results = search_all_data(
            query=args.search,
            min_score=args.min_score,
            author=args.author,
        )
        print_search_results(results)
        return

    if args.analyze:
        print(f"\n📊 Analyzing: {args.analyze}")

        data_dir = Path(f"data/r_{args.analyze}")
        if not data_dir.exists():
            print(f"❌ No data found for r/{args.analyze}")
            return

        posts_file = data_dir / "posts.csv"
        if not posts_file.exists():
            print("❌ No posts data found")
            return

        import pandas as pd

        df = pd.read_csv(posts_file)
        posts = df.to_dict("records")

        if args.sentiment:
            from analytics.sentiment import analyze_posts_sentiment

            analyzed, counts = analyze_posts_sentiment(posts)
            print("\n😀 Sentiment Analysis:")
            print(f"   Positive: {counts['positive']}")
            print(f"   Neutral:  {counts['neutral']}")
            print(f"   Negative: {counts['negative']}")

        if args.keywords:
            from analytics.sentiment import extract_keywords

            texts = [str(p.get("title", "") or "") + " " + str(p.get("selftext", "") or "") for p in posts]
            keywords = extract_keywords(texts, top_n=20)
            print("\n☁️ Top Keywords:")
            for word, count in keywords:
                print(f"   {word}: {count}")
        return

    if args.schedule:
        if not args.every:
            print("❌ Please specify --every <minutes>")
            return

        from scheduler.cron import run_scheduled

        run_scheduled(args.schedule, args.every, args.mode, args.limit, args.user)
        return

    if not args.target:
        parser.print_help()
        return

    if args.mode == "monitor":
        prefix = "u" if args.user else "r"
        print(f"🔄 Monitoring {prefix}/{args.target} every 5 mins...")
        try:
            for _result in _service.RedditScraper().monitor(args.target, args.user, interval_seconds=300):
                pass
        except KeyboardInterrupt:
            print("\n🛑 Monitor stopped")
    elif args.mode == "history":
        run_full_history(
            args.target,
            args.limit,
            args.user,
            download_media_flag=False,
            scrape_comments_flag=False,
            dry_run=args.dry_run,
            use_plugins=args.plugins,
        )
    else:
        run_full_history(
            args.target,
            args.limit,
            args.user,
            download_media_flag=not args.no_media,
            scrape_comments_flag=not args.no_comments,
            dry_run=args.dry_run,
            use_plugins=args.plugins,
        )


if __name__ == "__main__":
    main()
