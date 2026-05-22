import os
import subprocess
import sys
import zipfile


def test_public_model_imports():
    from reddit_universal_scraper import (
        MediaCounts,
        OutputPaths,
        ScrapeMode,
        ScrapeOptions,
        ScrapeResult,
    )

    assert ScrapeMode.FULL.value == "full"
    assert ScrapeMode.HISTORY.value == "history"
    assert ScrapeMode.MONITOR.value == "monitor"
    assert ScrapeOptions(mode="history").mode is ScrapeMode.HISTORY
    assert MediaCounts(images=2, videos=3).total == 5

    paths = OutputPaths(
        base="data/r_delhi",
        posts="data/r_delhi/posts.csv",
        comments="data/r_delhi/comments.csv",
        media="data/r_delhi/media",
        images="data/r_delhi/media/images",
        videos="data/r_delhi/media/videos",
    )
    result = ScrapeResult(
        target="delhi",
        mode=ScrapeMode.FULL,
        output_paths=paths,
        posts_count=4,
        comments_count=5,
        media_counts=MediaCounts(images=1, videos=2),
        duration_seconds=1.25,
    )

    assert result.media_count == 3
    assert result.output_paths.posts == "data/r_delhi/posts.csv"


def test_package_import_smoke():
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "from reddit_universal_scraper import ScrapeOptions, ScrapeResult, ScrapeMode; print(ScrapeMode.FULL.value)",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert result.stdout.strip() == "full"


def test_wheel_contents(tmp_path):
    dist_dir = tmp_path / "dist"
    env = os.environ.copy()
    env["UV_CACHE_DIR"] = str(tmp_path / ".uv-cache")

    subprocess.run(
        ["uv", "build", "--wheel", "--out-dir", str(dist_dir), "--no-build-isolation"],
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )

    wheels = list(dist_dir.glob("*.whl"))
    assert len(wheels) == 1

    with zipfile.ZipFile(wheels[0]) as wheel:
        names = set(wheel.namelist())

    assert "reddit_universal_scraper/__init__.py" in names
    assert "reddit_universal_scraper/models.py" in names
    assert not any(name.startswith("data/") for name in names)
    assert not any(name.startswith("thoughts/") for name in names)
    assert not any(name.startswith("runtime/") for name in names)
