"""Monitor-mode helpers."""

from __future__ import annotations

import xml.etree.ElementTree as ET


def parse_monitor_rss(content: bytes) -> list[dict]:
    """Parse Reddit Atom RSS entries into post records compatible with posts.csv."""
    root = ET.fromstring(content)
    namespace = {"atom": "http://www.w3.org/2005/Atom"}
    posts = []

    for entry in root.findall("atom:entry", namespace):
        title = entry.find("atom:title", namespace)
        published = entry.find("atom:published", namespace)
        link = entry.find("atom:link", namespace)
        href = link.attrib["href"] if link is not None else ""
        posts.append(
            {
                "id": "",
                "title": title.text if title is not None else "",
                "author": "",
                "created_utc": published.text if published is not None else "",
                "permalink": href,
                "url": href,
                "score": 0,
                "upvote_ratio": 0,
                "num_comments": 0,
                "num_crossposts": 0,
                "selftext": "",
                "post_type": "unknown",
                "is_nsfw": False,
                "is_spoiler": False,
                "flair": "",
                "total_awards": 0,
                "has_media": False,
                "media_downloaded": False,
                "source": "Monitor-RSS",
            }
        )

    return posts
