import shlex
from pathlib import Path


README = Path("README.md")


def test_readme_documents_python_api_workflows():
    text = README.read_text()

    for snippet in [
        "from reddit_universal_scraper import RedditScraper",
        'scraper.scrape("delhi", mode="full", limit=100)',
        'scraper.scrape("delhi", mode="history", limit=500)',
        'scraper.monitor("delhi", interval_seconds=300)',
        'scraper.scrape("spez", is_user=True, mode="full", limit=50)',
        'scraper.scrape("delhi", mode="full", limit=200, download_media=False)',
        'scraper.scrape("delhi", mode="full", limit=200, scrape_comments=False)',
    ]:
        assert snippet in text


def test_readme_cli_examples_use_supported_scrape_flags():
    text = README.read_text()
    supported_flags = {
        "--mode",
        "--limit",
        "--user",
        "--no-media",
        "--no-comments",
        "--dry-run",
        "--plugins",
    }
    section_lines = []
    in_scraping_section = False
    for line in text.splitlines():
        if line.startswith("### ") and "Scraping" in line:
            in_scraping_section = True
            continue
        if in_scraping_section and line.startswith("### ") and "Python API" in line:
            break
        if in_scraping_section:
            section_lines.append(line)
    scraping_section = "\n".join(section_lines)
    scrape_commands = [
        line.strip()
        for line in scraping_section.splitlines()
        if line.strip().startswith("uv run python main.py")
    ]

    assert scrape_commands
    for command in scrape_commands:
        tokens = shlex.split(command)
        flags = {token for token in tokens if token.startswith("--")}
        assert flags <= supported_flags
