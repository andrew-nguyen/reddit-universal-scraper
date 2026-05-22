import subprocess
import sys

import pytest

import main


def run_cli(monkeypatch, argv):
    calls = []

    def fake_run_full_history(*args, **kwargs):
        calls.append(("full_history", args, kwargs))
        return {"posts": 0}

    monkeypatch.setattr(sys, "argv", ["main.py", *argv])
    monkeypatch.setattr(main, "run_full_history", fake_run_full_history)

    main.main()
    return calls


def test_history_mode_maps_to_posts_only(monkeypatch):
    calls = run_cli(monkeypatch, ["delhi", "--mode", "history", "--limit", "500"])

    assert calls == [
        (
            "full_history",
            ("delhi", 500, False),
            {
                "download_media_flag": False,
                "scrape_comments_flag": False,
                "dry_run": False,
                "use_plugins": False,
            },
        )
    ]


def test_full_mode_defaults_to_media_and_comments(monkeypatch):
    calls = run_cli(monkeypatch, ["delhi", "--mode", "full", "--limit", "100"])

    assert calls[0][1] == ("delhi", 100, False)
    assert calls[0][2]["download_media_flag"] is True
    assert calls[0][2]["scrape_comments_flag"] is True


def test_full_mode_no_media_and_no_comments_override_independently(monkeypatch):
    no_media = run_cli(monkeypatch, ["delhi", "--mode", "full", "--no-media", "--limit", "200"])
    assert no_media[0][2]["download_media_flag"] is False
    assert no_media[0][2]["scrape_comments_flag"] is True

    no_comments = run_cli(monkeypatch, ["delhi", "--mode", "full", "--no-comments", "--limit", "200"])
    assert no_comments[0][2]["download_media_flag"] is True
    assert no_comments[0][2]["scrape_comments_flag"] is False


def test_user_flag_maps_to_user_target(monkeypatch):
    calls = run_cli(monkeypatch, ["spez", "--user", "--mode", "full", "--limit", "50"])

    assert calls[0][1] == ("spez", 50, True)


def test_monitor_mode_uses_300_second_interval(monkeypatch):
    monitor_calls = []

    class FakeScraper:
        def monitor(self, target, is_user=False, interval_seconds=300, max_iterations=None, stop_event=None):
            monitor_calls.append((target, is_user, interval_seconds, max_iterations, stop_event))
            return iter(())

    monkeypatch.setattr(sys, "argv", ["main.py", "delhi", "--mode", "monitor"])
    monkeypatch.setattr(main._service, "RedditScraper", lambda: FakeScraper())

    main.main()

    assert monitor_calls == [("delhi", False, 300, None, None)]


@pytest.mark.parametrize(
    ("argv", "expected_args", "expected_kwargs"),
    [
        (
            ["delhi", "--mode", "full", "--limit", "100"],
            ("delhi", 100, False),
            {"download_media_flag": True, "scrape_comments_flag": True},
        ),
        (
            ["delhi", "--mode", "history", "--limit", "500"],
            ("delhi", 500, False),
            {"download_media_flag": False, "scrape_comments_flag": False},
        ),
        (
            ["spez", "--user", "--mode", "full", "--limit", "50"],
            ("spez", 50, True),
            {"download_media_flag": True, "scrape_comments_flag": True},
        ),
        (
            ["delhi", "--mode", "full", "--no-media", "--limit", "200"],
            ("delhi", 200, False),
            {"download_media_flag": False, "scrape_comments_flag": True},
        ),
        (
            ["delhi", "--mode", "full", "--no-comments", "--limit", "200"],
            ("delhi", 200, False),
            {"download_media_flag": True, "scrape_comments_flag": False},
        ),
    ],
)
def test_documented_examples(monkeypatch, argv, expected_args, expected_kwargs):
    calls = run_cli(monkeypatch, argv)

    assert calls[0][1] == expected_args
    for key, value in expected_kwargs.items():
        assert calls[0][2][key] is value


def test_help_flags():
    result = subprocess.run(
        [sys.executable, "main.py", "--help"],
        check=True,
        capture_output=True,
        text=True,
    )

    for flag in ["--mode", "--user", "--limit", "--no-media", "--no-comments"]:
        assert flag in result.stdout


def test_main_compatibility_wrappers_delegate_to_package(monkeypatch):
    calls = []

    monkeypatch.setattr(
        "reddit_universal_scraper.extractors.extract_post_data",
        lambda post: calls.append(("extract_post_data", post)) or {"id": "wrapped"},
    )
    monkeypatch.setattr(
        "reddit_universal_scraper.extractors.extract_media_urls",
        lambda post: calls.append(("extract_media_urls", post)) or {"images": [], "videos": [], "galleries": []},
    )
    monkeypatch.setattr(
        "reddit_universal_scraper.extractors.parse_comments",
        lambda comments, permalink, depth=0, max_depth=3: calls.append(
            ("parse_comments", comments, permalink, depth, max_depth)
        )
        or [],
    )
    monkeypatch.setattr(
        "reddit_universal_scraper.storage.setup_directories",
        lambda target, prefix, data_dir="data": calls.append(("setup_directories", target, prefix, data_dir))
        or {"base": "wrapped"},
    )

    assert main.extract_post_data({"id": "post"}) == {"id": "wrapped"}
    assert main.get_media_urls({"id": "post"}) == {"images": [], "videos": [], "galleries": []}
    assert main.parse_comments([], "/p") == []
    assert main.setup_directories("delhi", "r") == {"base": "wrapped"}
    assert [call[0] for call in calls] == [
        "extract_post_data",
        "extract_media_urls",
        "parse_comments",
        "setup_directories",
    ]
