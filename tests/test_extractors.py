import datetime

import main
from reddit_universal_scraper import extractors


def make_post(**overrides):
    post = {
        "id": "abc123",
        "title": "Example title",
        "author": "alice",
        "created_utc": 1_700_000_000,
        "permalink": "/r/test/comments/abc123/example/",
        "url": "https://www.reddit.com/r/test/comments/abc123/example/",
        "score": 42,
        "upvote_ratio": 0.91,
        "num_comments": 3,
        "num_crossposts": 1,
        "selftext": "body",
        "is_self": True,
        "over_18": False,
        "spoiler": False,
        "link_flair_text": "News",
        "total_awards_received": 2,
    }
    post.update(overrides)
    return post


def test_extract_post_data_detects_supported_post_types():
    assert main.extract_post_data(make_post(is_self=True))["post_type"] == "text"
    assert main.extract_post_data(make_post(url="https://example.com/image.jpg", is_self=False))["post_type"] == "image"
    assert main.extract_post_data(make_post(url="https://i.redd.it/image", is_self=False))["post_type"] == "image"
    assert main.extract_post_data(make_post(is_gallery=True, is_self=False))["post_type"] == "gallery"
    assert main.extract_post_data(make_post(is_video=True, is_self=False))["post_type"] == "video"
    assert main.extract_post_data(make_post(url="https://example.com/article", is_self=False))["post_type"] == "link"


def test_package_extract_post_data_matches_legacy_defaults():
    assert extractors.extract_post_data(make_post(url="https://example.com/image.jpg", is_self=False)) == main.extract_post_data(
        make_post(url="https://example.com/image.jpg", is_self=False)
    )


def test_extract_post_data_preserves_current_fields_and_source():
    post = main.extract_post_data(make_post(url_overridden_by_dest="https://example.com/final"))

    assert list(post) == [
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
    assert post["created_utc"] == datetime.datetime.fromtimestamp(1_700_000_000).isoformat()
    assert post["url"] == "https://example.com/final"
    assert post["source"] == "History-Full"


def test_get_media_urls_extracts_current_media_sources():
    post = make_post(
        url="https://i.redd.it/photo.jpg",
        is_video=True,
        media={"reddit_video": {"fallback_url": "https://v.redd.it/abc/DASH_720.mp4?source=fallback"}},
        preview={"images": [{"source": {"url": "https://preview.redd.it/photo.jpg?width=640&amp;format=pjpg"}}]},
        is_gallery=True,
        gallery_data={"items": [{"media_id": "gallery1"}]},
        media_metadata={"gallery1": {"s": {"u": "https://i.redd.it/gallery.jpg?width=640&amp;format=pjpg"}}},
    )

    media = main.get_media_urls(post)

    assert media["images"] == [
        "https://i.redd.it/photo.jpg",
        "https://i.redd.it/photo.jpg",
        "https://preview.redd.it/photo.jpg?width=640&format=pjpg",
    ]
    assert media["galleries"] == ["https://i.redd.it/gallery.jpg?width=640&format=pjpg"]
    assert media["videos"] == ["https://v.redd.it/abc/DASH_720.mp4"]


def test_package_extract_media_urls_matches_legacy_defaults():
    post = make_post(url="https://youtu.be/example", is_self=False)

    assert extractors.extract_media_urls(post) == main.get_media_urls(post)


def test_get_media_urls_includes_youtube_urls_as_videos():
    media = main.get_media_urls(make_post(url="https://youtu.be/example", is_self=False))

    assert media["videos"] == ["https://youtu.be/example"]


def test_parse_comments_preserves_recursive_depth_and_fields():
    comments = [
        {
            "kind": "t1",
            "data": {
                "id": "c1",
                "parent_id": "t3_post",
                "author": "bob",
                "body": "top",
                "score": 5,
                "created_utc": 1_700_000_001,
                "is_submitter": False,
                "replies": {
                    "data": {
                        "children": [
                            {
                                "kind": "t1",
                                "data": {
                                    "id": "c2",
                                    "parent_id": "t1_c1",
                                    "author": "alice",
                                    "body": "reply",
                                    "score": 2,
                                    "created_utc": 1_700_000_002,
                                    "is_submitter": True,
                                    "replies": "",
                                },
                            }
                        ]
                    }
                },
            },
        },
        {"kind": "more", "data": {}},
    ]

    parsed = main.parse_comments(comments, "/r/test/comments/post/", max_depth=1)

    assert [comment["comment_id"] for comment in parsed] == ["c1", "c2"]
    assert [comment["depth"] for comment in parsed] == [0, 1]
    assert parsed[0]["post_permalink"] == "/r/test/comments/post/"
    assert parsed[1]["is_submitter"] is True
    assert parsed[0]["created_utc"] == datetime.datetime.fromtimestamp(1_700_000_001).isoformat()


def test_package_parse_comments_matches_legacy_parser():
    comments = [
        {
            "kind": "t1",
            "data": {
                "id": "c1",
                "parent_id": "t3_post",
                "author": "bob",
                "body": "top",
                "score": 5,
                "created_utc": 1_700_000_001,
                "is_submitter": False,
                "replies": "",
            },
        }
    ]

    assert extractors.parse_comments(comments, "/r/test/comments/post/") == main.parse_comments(
        comments, "/r/test/comments/post/"
    )
