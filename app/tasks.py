"""Background jobs. These run in the Celery worker, not inside the API process."""
import json
import logging
import urllib.error
import urllib.request

from . import crud
from .celery_app import celery_app
from .config import settings
from .database import SessionLocal

logger = logging.getLogger(__name__)


class NotificationError(Exception):
    """Delivering the notification failed. Worth retrying."""


def deliver_notification(payload: dict) -> None:
    """Send the payload to WEBHOOK_URL. Without a URL we only log it."""
    if not settings.webhook_url:
        logger.info("No WEBHOOK_URL set. Would have sent: %s", payload)
        return
    request = urllib.request.Request(
        settings.webhook_url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=5):
            pass
    except (urllib.error.URLError, OSError) as exc:  # HTTP 4xx/5xx also land here
        raise NotificationError(str(exc)) from exc


@celery_app.task(
    bind=True,
    name="matches.send_finished_notification",
    autoretry_for=(NotificationError,),
    retry_backoff=2,  # wait 2s, 4s, 8s ... between tries
    retry_backoff_max=60,
    retry_jitter=False,  # in production you would add jitter, so many retries do not fire together
    max_retries=3,
)
def send_match_finished_notification(self, match_id: int):
    db = SessionLocal()
    try:
        match = crud.get_match(db, match_id)
        payload = None
        if match is not None:
            payload = {
                "event": "match_finished",
                "match_id": match.id,  # receivers can use this to ignore duplicates
                "home_team": match.home_team,
                "away_team": match.away_team,
                "home_score": match.home_score,
                "away_score": match.away_score,
            }
    finally:
        db.close()

    if payload is None:
        logger.warning("Match %s no longer exists, nothing to send", match_id)
        return "match not found"

    deliver_notification(payload)
    logger.info("Notification sent for match %s", match_id)
    return "sent"


def enqueue_match_finished(match_id: int) -> None:
    """Queue the job. A broken queue must never break the API request."""
    try:
        send_match_finished_notification.delay(match_id)
    except Exception:
        logger.warning("Could not queue notification for match %s", match_id, exc_info=True)
