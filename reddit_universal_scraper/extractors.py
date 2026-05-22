"""Pure Reddit JSON extraction helpers."""

from __future__ import annotations

import datetime
from typing import Any


def extract_media_urls(post_data: dict[str, Any], *, include_youtube: bool = True) -> dict[str, list[str]]:
    """Extract image, video, and gallery URLs from a Reddit post JSON object."""
    media = {"images": [], "videos": [], "galleries": []}

    url = post_data.get("url", "")
    if any(ext in url.lower() for ext in [".jpg", ".jpeg", ".png", ".gif", ".webp"]):
        media["images"].append(url)

    if "i.redd.it" in url:
        media["images"].append(url)

    if post_data.get("is_video"):
        reddit_video = post_data.get("media", {})
        if reddit_video and "reddit_video" in reddit_video:
            video_url = reddit_video["reddit_video"].get("fallback_url", "")
            if video_url:
                media["videos"].append(video_url.split("?")[0])

    preview = post_data.get("preview", {})
    if preview and "images" in preview:
        for img in preview["images"]:
            source = img.get("source", {})
            if source.get("url"):
                clean_url = source["url"].replace("&amp;", "&")
                media["images"].append(clean_url)

    if post_data.get("is_gallery"):
        gallery_data = post_data.get("gallery_data", {})
        media_metadata = post_data.get("media_metadata", {})

        if gallery_data and media_metadata:
            for item in gallery_data.get("items", []):
                media_id = item.get("media_id")
                if media_id and media_id in media_metadata:
                    meta = media_metadata[media_id]
                    if meta.get("s", {}).get("u"):
                        clean_url = meta["s"]["u"].replace("&amp;", "&")
                        media["galleries"].append(clean_url)

    if include_youtube and ("youtube.com" in url or "youtu.be" in url):
        media["videos"].append(url)

    return media


def parse_comments(
    comment_list: list[dict[str, Any]],
    post_permalink: str,
    depth: int = 0,
    max_depth: int = 3,
) -> list[dict[str, Any]]:
    """Recursively parse Reddit comments into CSV-compatible records."""
    comments = []

    if depth > max_depth:
        return comments

    for item in comment_list:
        if item["kind"] != "t1":
            continue

        c = item["data"]

        comment = {
            "post_permalink": post_permalink,
            "comment_id": c.get("id"),
            "parent_id": c.get("parent_id"),
            "author": c.get("author"),
            "body": c.get("body", ""),
            "score": c.get("score", 0),
            "created_utc": datetime.datetime.fromtimestamp(c.get("created_utc", 0)).isoformat(),
            "depth": depth,
            "is_submitter": c.get("is_submitter", False),
        }
        comments.append(comment)

        replies = c.get("replies")
        if replies and isinstance(replies, dict):
            reply_children = replies.get("data", {}).get("children", [])
            comments.extend(parse_comments(reply_children, post_permalink, depth + 1, max_depth))

    return comments


def extract_post_data(post_json: dict[str, Any], *, source: str = "History-Full") -> dict[str, Any]:
    """Extract CSV-compatible post metadata from a Reddit post JSON object."""
    p = post_json

    post_type = "text"
    if p.get("is_video"):
        post_type = "video"
    elif p.get("is_gallery"):
        post_type = "gallery"
    elif any(ext in p.get("url", "").lower() for ext in [".jpg", ".jpeg", ".png", ".gif", ".webp"]) or "i.redd.it" in p.get(
        "url", ""
    ):
        post_type = "image"
    elif p.get("is_self"):
        post_type = "text"
    else:
        post_type = "link"

    return {
        "id": p.get("id"),
        "title": p.get("title"),
        "author": p.get("author"),
        "created_utc": datetime.datetime.fromtimestamp(p.get("created_utc", 0)).isoformat(),
        "permalink": p.get("permalink"),
        "url": p.get("url_overridden_by_dest", p.get("url")),
        "score": p.get("score", 0),
        "upvote_ratio": p.get("upvote_ratio", 0),
        "num_comments": p.get("num_comments", 0),
        "num_crossposts": p.get("num_crossposts", 0),
        "selftext": p.get("selftext", ""),
        "post_type": post_type,
        "is_nsfw": p.get("over_18", False),
        "is_spoiler": p.get("spoiler", False),
        "flair": p.get("link_flair_text", ""),
        "total_awards": p.get("total_awards_received", 0),
        "has_media": p.get("is_video", False) or p.get("is_gallery", False) or "i.redd.it" in p.get("url", ""),
        "media_downloaded": False,
        "source": source,
    }


get_media_urls = extract_media_urls
