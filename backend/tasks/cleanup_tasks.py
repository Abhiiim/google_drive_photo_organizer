"""Background maintenance Celery tasks."""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List

from celery import shared_task

from core.config import get_settings
from core.logger import get_logger


settings = get_settings()
logger = get_logger(__name__)


@shared_task(bind=True, name="backend.tasks.cleanup_tasks.cleanup_temp_files_task")
def cleanup_temp_files_task(self, max_age_minutes: int = 60) -> Dict[str, int]:
    """Remove temporary files older than the configured age threshold."""

    temp_dir: Path = settings.temp_dir
    if not temp_dir.exists():
        logger.info("tasks.cleanup_temp_files.skipped", reason="missing_temp_dir")
        return {"deleted_files": 0}

    deleted_files = 0
    threshold = datetime.utcnow() - timedelta(minutes=max_age_minutes)

    for entry in temp_dir.iterdir():
        try:
            if entry.is_file() and datetime.utcfromtimestamp(entry.stat().st_mtime) < threshold:
                entry.unlink()
                deleted_files += 1
        except Exception as exc:  # pragma: no cover - best effort cleanup
            logger.warning(
                "tasks.cleanup_temp_files.error",
                path=str(entry),
                error=str(exc),
            )

    logger.info("tasks.cleanup_temp_files.completed", deleted_files=deleted_files)
    return {"deleted_files": deleted_files}


@shared_task(bind=True, name="backend.tasks.cleanup_tasks.cleanup_old_jobs_task")
def cleanup_old_jobs_task(self) -> Dict[str, int]:
    """Placeholder task for cleaning up stale job metadata."""

    logger.info("tasks.cleanup_old_jobs.start")
    # TODO: Integrate with persistent job store in future iterations.
    logger.info("tasks.cleanup_old_jobs.completed", removed_jobs=0)
    return {"removed_jobs": 0}


@shared_task(bind=True, name="backend.tasks.cleanup_tasks.update_statistics_task")
def update_statistics_task(self) -> Dict[str, List[str]]:
    """Placeholder statistics updater; returns tracked metrics when implemented."""

    logger.info("tasks.update_statistics.start")
    # TODO: Aggregate processing statistics for monitoring dashboard.
    metrics: List[str] = []
    logger.info("tasks.update_statistics.completed", metrics=len(metrics))
    return {"metrics": metrics}

