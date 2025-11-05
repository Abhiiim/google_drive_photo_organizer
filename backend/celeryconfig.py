"""Celery configuration module loaded by `backend.celery_app`."""

from __future__ import annotations

from kombu import Exchange, Queue

from core.config import get_settings


settings = get_settings()

_exchange_name = "face_organizer"
_default_routing_key = f"{_exchange_name}.default"
_high_priority_routing_key = f"{_exchange_name}.high_priority"
_low_priority_routing_key = f"{_exchange_name}.low_priority"
_maintenance_routing_key = f"{_exchange_name}.maintenance"
_exchange = Exchange(_exchange_name, type="direct")

task_default_queue = settings.celery_task_default_queue
task_default_exchange = _exchange_name
task_default_exchange_type = "direct"
task_default_routing_key = _default_routing_key

task_queues = (
    Queue(
        settings.celery_high_priority_queue,
        _exchange,
        routing_key=_high_priority_routing_key,
    ),
    Queue(
        settings.celery_task_default_queue,
        _exchange,
        routing_key=_default_routing_key,
    ),
    Queue(
        settings.celery_low_priority_queue,
        _exchange,
        routing_key=_low_priority_routing_key,
    ),
    Queue(
        settings.celery_maintenance_queue,
        _exchange,
        routing_key=_maintenance_routing_key,
    ),
)

task_routes = {
    "backend.tasks.photo_tasks.organize_photos_task": {
        "queue": settings.celery_task_default_queue,
        "routing_key": _default_routing_key,
    },
    "backend.tasks.photo_tasks.process_single_photo_task": {
        "queue": settings.celery_high_priority_queue,
        "routing_key": _high_priority_routing_key,
    },
    "backend.tasks.drive_tasks.download_photo_task": {
        "queue": settings.celery_high_priority_queue,
        "routing_key": _high_priority_routing_key,
    },
    "backend.tasks.face_tasks.detect_faces_task": {
        "queue": settings.celery_high_priority_queue,
        "routing_key": _high_priority_routing_key,
    },
    "backend.tasks.face_tasks.cluster_faces_task": {
        "queue": settings.celery_task_default_queue,
        "routing_key": _default_routing_key,
    },
    "backend.tasks.cleanup_tasks.cleanup_temp_files_task": {
        "queue": settings.celery_maintenance_queue,
        "routing_key": _maintenance_routing_key,
    },
    "backend.tasks.cleanup_tasks.cleanup_old_jobs_task": {
        "queue": settings.celery_maintenance_queue,
        "routing_key": _maintenance_routing_key,
    },
    "backend.tasks.cleanup_tasks.update_statistics_task": {
        "queue": settings.celery_low_priority_queue,
        "routing_key": _low_priority_routing_key,
    },
}

imports = (
    "backend.tasks.photo_tasks",
    "backend.tasks.face_tasks",
    "backend.tasks.drive_tasks",
    "backend.tasks.cleanup_tasks",
)

timezone = "UTC"
enable_utc = True
task_track_started = settings.celery_task_track_started
task_soft_time_limit = settings.celery_task_soft_time_limit
task_time_limit = settings.celery_task_time_limit
result_expires = settings.celery_result_expires
worker_disable_rate_limits = False
worker_hijack_root_logger = False
broker_transport_options = {"visibility_timeout": settings.celery_task_time_limit * 2}
task_acks_late = True
task_reject_on_worker_lost = True

