"""Celery setup: the background job runner.

The broker is the 'inbox' where the API drops jobs and the worker picks them up.
Choose it with CELERY_BROKER_URL, else REDIS_URL, else a plain local folder (.celery/)
so the project works with nothing to install. The folder broker is for development only.
"""
import os

from celery import Celery

from .config import settings


def _with_ssl(url: str) -> str:
    # Celery refuses rediss:// (TLS) URLs without this option.
    if url.startswith("rediss://") and "ssl_cert_reqs" not in url:
        url += ("&" if "?" in url else "?") + "ssl_cert_reqs=required"
    return url


broker_url = _with_ssl(settings.celery_broker_url or settings.redis_url or "filesystem://")

celery_app = Celery("matchapp", broker=broker_url, include=["app.tasks"])

celery_app.conf.update(
    task_ignore_result=True,  # we never read task results
    task_acks_late=True,  # if a worker dies mid-task, the job is handed out again
    task_serializer="json",
    accept_content=["json"],
    broker_connection_timeout=2,  # a dead broker must not hang the API
    broker_connection_retry_on_startup=True,
    task_publish_retry_policy={
        "max_retries": 1,
        "interval_start": 0,
        "interval_step": 0.2,
        "interval_max": 0.5,
    },
    task_always_eager=settings.celery_always_eager,
)

if broker_url.startswith("filesystem://") and not settings.celery_always_eager:
    base = os.path.join(os.getcwd(), ".celery")
    data_folder = os.path.join(base, "data")
    control_folder = os.path.join(base, "control")
    os.makedirs(data_folder, exist_ok=True)
    os.makedirs(control_folder, exist_ok=True)
    celery_app.conf.broker_transport_options = {
        "data_folder_in": data_folder,
        "data_folder_out": data_folder,
        "control_folder": control_folder,
    }
