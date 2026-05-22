"""Media download helpers."""

from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse

import requests

from .extractors import extract_media_urls
from .models import MediaCounts


class MediaDownloader:
    """Downloads post media with instance-scoped dependencies."""

    def __init__(
        self,
        session: Any | None = None,
        *,
        runner: Callable[..., Any] = subprocess.run,
        printer: Callable[[str], None] = print,
    ):
        self.session = session or requests.Session()
        self.runner = runner
        self.printer = printer

    def download(self, url: str, save_path: str | os.PathLike[str], media_type: str = "image") -> bool:
        """Download a single media file."""
        try:
            if os.path.exists(save_path):
                return True

            response = self.session.get(url, timeout=30, stream=True)
            if response.status_code == 200:
                with open(save_path, "wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                return True
        except Exception:
            pass
        return False

    def download_reddit_video_with_audio(self, video_url: str, save_path: str | os.PathLike[str]) -> bool:
        """Download Reddit video and merge an available audio stream with ffmpeg."""
        try:
            if os.path.exists(save_path):
                return True

            base_url = video_url.rsplit("/", 1)[0]
            audio_urls = [
                f"{base_url}/DASH_audio.mp4",
                f"{base_url}/DASH_AUDIO_128.mp4",
                f"{base_url}/DASH_AUDIO_64.mp4",
                f"{base_url}/audio.mp4",
                f"{base_url}/audio",
            ]

            with tempfile.NamedTemporaryFile(suffix="_video.mp4", delete=False) as video_temp:
                video_temp_path = video_temp.name
                response = self.session.get(video_url, timeout=60, stream=True)
                if response.status_code != 200:
                    return False
                for chunk in response.iter_content(chunk_size=8192):
                    video_temp.write(chunk)

            audio_temp_path = None
            for audio_url in audio_urls:
                try:
                    response = self.session.get(audio_url, timeout=30, stream=True)
                    if response.status_code == 200:
                        with tempfile.NamedTemporaryFile(suffix="_audio.mp4", delete=False) as audio_temp:
                            audio_temp_path = audio_temp.name
                            for chunk in response.iter_content(chunk_size=8192):
                                audio_temp.write(chunk)
                        break
                except Exception:
                    continue

            if audio_temp_path:
                try:
                    cmd = [
                        "ffmpeg",
                        "-y",
                        "-hide_banner",
                        "-loglevel",
                        "error",
                        "-i",
                        video_temp_path,
                        "-i",
                        audio_temp_path,
                        "-c:v",
                        "copy",
                        "-c:a",
                        "aac",
                        "-shortest",
                        str(save_path),
                    ]
                    result = self.runner(cmd, capture_output=True, timeout=120)

                    if result.returncode == 0:
                        os.unlink(video_temp_path)
                        os.unlink(audio_temp_path)
                        return True

                    self.printer("   ⚠️ ffmpeg merge failed, saving video without audio")
                    os.rename(video_temp_path, save_path)
                    os.unlink(audio_temp_path)
                    return True
                except FileNotFoundError:
                    self.printer("   ⚠️ ffmpeg not found, saving video without audio")
                    os.rename(video_temp_path, save_path)
                    if audio_temp_path:
                        os.unlink(audio_temp_path)
                    return True
                except Exception:
                    os.rename(video_temp_path, save_path)
                    if audio_temp_path and os.path.exists(audio_temp_path):
                        os.unlink(audio_temp_path)
                    return True

            os.rename(video_temp_path, save_path)
            return True
        except Exception:
            pass
        return False

    def download_post_media(
        self,
        post_data: dict,
        dirs: dict[str, str],
        post_id: str,
        *,
        dry_run: bool = False,
    ) -> MediaCounts:
        """Download all media from a post."""
        downloaded = MediaCounts()
        if dry_run:
            return downloaded

        media = extract_media_urls(post_data)

        for i, img_url in enumerate(media["images"][:5]):
            ext = os.path.splitext(urlparse(img_url).path)[1] or ".jpg"
            save_path = Path(dirs["images"]) / f"{post_id}_{i}{ext}"
            if self.download(img_url, save_path, "image"):
                downloaded.images += 1

        for i, img_url in enumerate(media["galleries"][:10]):
            save_path = Path(dirs["images"]) / f"{post_id}_gallery_{i}.jpg"
            if self.download(img_url, save_path, "gallery"):
                downloaded.images += 1

        for i, vid_url in enumerate(media["videos"][:2]):
            if "youtube" not in vid_url:
                save_path = Path(dirs["videos"]) / f"{post_id}_{i}.mp4"
                if "v.redd.it" in vid_url or "reddit.com" in vid_url:
                    if self.download_reddit_video_with_audio(vid_url, save_path):
                        downloaded.videos += 1
                elif self.download(vid_url, save_path, "video"):
                    downloaded.videos += 1

        return downloaded
