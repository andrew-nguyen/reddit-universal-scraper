import pandas as pd

import main
from reddit_universal_scraper.storage import ScraperStorage, setup_directories as package_setup_directories


POST_COLUMNS = [
    "id",
    "title",
    "author",
    "created_utc",
    "permalink",
    "url",
    "score",
    "upvote_ratio",
    "num_comments",
    "num_crossposts",
    "selftext",
    "post_type",
    "is_nsfw",
    "is_spoiler",
    "flair",
    "total_awards",
    "has_media",
    "media_downloaded",
    "source",
]

COMMENT_COLUMNS = [
    "post_permalink",
    "comment_id",
    "parent_id",
    "author",
    "body",
    "score",
    "created_utc",
    "depth",
    "is_submitter",
]


def make_post(permalink="/r/test/comments/post/"):
    return {column: f"value-{column}" for column in POST_COLUMNS} | {
        "permalink": permalink,
        "score": 1,
        "upvote_ratio": 0.5,
        "num_comments": 0,
        "num_crossposts": 0,
        "is_nsfw": False,
        "is_spoiler": False,
        "total_awards": 0,
        "has_media": False,
        "media_downloaded": False,
    }


def make_comment(comment_id="c1"):
    return {column: f"value-{column}" for column in COMMENT_COLUMNS} | {
        "comment_id": comment_id,
        "score": 1,
        "depth": 0,
        "is_submitter": False,
    }


def test_setup_directories_matches_current_layout(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    dirs = main.setup_directories("delhi", "r")

    assert dirs == {
        "base": "data/r_delhi",
        "posts": "data/r_delhi/posts.csv",
        "comments": "data/r_delhi/comments.csv",
        "media": "data/r_delhi/media",
        "images": "data/r_delhi/media/images",
        "videos": "data/r_delhi/media/videos",
    }
    for key in ["base", "media", "images", "videos"]:
        assert (tmp_path / dirs[key]).is_dir()


def test_package_setup_directories_matches_current_layout(tmp_path):
    dirs = package_setup_directories("delhi", "r", data_dir=tmp_path / "data")

    assert dirs["base"] == str(tmp_path / "data/r_delhi")
    assert dirs["posts"] == str(tmp_path / "data/r_delhi/posts.csv")
    assert dirs["comments"] == str(tmp_path / "data/r_delhi/comments.csv")
    assert dirs["images"] == str(tmp_path / "data/r_delhi/media/images")


def test_save_posts_csv_appends_only_new_permalinks(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    main.SEEN_URLS.clear()
    posts_path = tmp_path / "posts.csv"

    assert main.save_posts_csv([make_post("/p/1"), make_post("/p/2")], posts_path) == 2
    assert main.save_posts_csv([make_post("/p/2"), make_post("/p/3")], posts_path) == 1

    df = pd.read_csv(posts_path)
    assert df["permalink"].tolist() == ["/p/1", "/p/2", "/p/3"]


def test_load_history_populates_seen_urls(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    posts_path = tmp_path / "posts.csv"
    pd.DataFrame([make_post("/existing/1"), make_post("/existing/2")]).to_csv(posts_path, index=False)
    main.SEEN_URLS.clear()

    main.load_history(posts_path)

    assert main.SEEN_URLS == {"/existing/1", "/existing/2"}


def test_save_comments_csv_preserves_schema(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    comments_path = tmp_path / "comments.csv"

    main.save_comments_csv([make_comment("c1")], comments_path)
    main.save_comments_csv([make_comment("c2")], comments_path)

    df = pd.read_csv(comments_path)
    assert list(df.columns) == COMMENT_COLUMNS
    assert df["comment_id"].tolist() == ["c1", "c2"]


def test_csv_schema_compatibility(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    posts_path = tmp_path / "posts.csv"
    comments_path = tmp_path / "comments.csv"
    main.SEEN_URLS.clear()

    main.save_posts_csv([make_post()], posts_path)
    main.save_comments_csv([make_comment()], comments_path)

    assert list(pd.read_csv(posts_path).columns) == POST_COLUMNS
    assert list(pd.read_csv(comments_path).columns) == COMMENT_COLUMNS


def test_storage_instances_keep_seen_urls_isolated(tmp_path):
    first = ScraperStorage(tmp_path / "first")
    second = ScraperStorage(tmp_path / "second")
    first_paths = first.setup_directories("delhi", "r")
    second_paths = second.setup_directories("delhi", "r")

    assert first.save_posts_csv([make_post("/same")], first_paths.posts) == 1
    assert first.save_posts_csv([make_post("/same")], first_paths.posts) == 0
    assert second.save_posts_csv([make_post("/same")], second_paths.posts) == 1
