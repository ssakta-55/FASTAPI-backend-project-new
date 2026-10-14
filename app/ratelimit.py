"""Rate limiting with a fixed window counter.

Each caller gets a counter that lives for one window (default 60 seconds).
When the counter goes over the limit, we answer 429 Too Many Requests.
"""
from fastapi import Depends, HTTPException, Request

from . import models
from .auth import get_current_user
from .cache import cache
from .config import settings


def _check(bucket: str, identity: str, limit: int) -> None:
    count, seconds_left = cache.incr_window(
        f"rl:{bucket}:{identity}", settings.rate_limit_window_seconds
    )
    if count > limit:
        raise HTTPException(
            status_code=429,
            detail="Too many requests. Please try again later.",
            headers={"Retry-After": str(seconds_left)},
        )


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def login_limit(request: Request) -> None:
    _check("login", _client_ip(request), settings.login_rate_limit)


def register_limit(request: Request) -> None:
    _check("register", _client_ip(request), settings.register_rate_limit)


def write_limit(user: models.UserDB = Depends(get_current_user)) -> None:
    # Limited per user (not per IP), because writes always need a login.
    _check("write", str(user.id), settings.write_rate_limit)
