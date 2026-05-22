"""Job-history adapter used by the scraper service."""

from __future__ import annotations

from typing import Callable


class JobTracker:
    """Adapter around export.database job-history helpers."""

    def __init__(self, printer: Callable[[str], None] = print):
        self.printer = printer

    def start(self, target: str, mode: str, is_user: bool = False, dry_run: bool = False) -> str | None:
        try:
            from export.database import start_job_record

            return start_job_record(target, mode, is_user, dry_run)
        except Exception as exc:
            self.printer(f"⚠️ Job tracking unavailable: {exc}")
            return None

    def complete(
        self,
        job_id: str | None,
        status: str,
        posts: int = 0,
        comments: int = 0,
        media: int = 0,
        errors: str | None = None,
    ) -> None:
        if not job_id:
            return
        try:
            from export.database import complete_job_record

            complete_job_record(job_id, status, posts, comments, media, errors)
        except Exception as exc:
            self.printer(f"⚠️ Failed to complete job record: {exc}")
