import json
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from .. import crud, models, schemas
from ..auth import ensure_owner_or_admin, get_current_user
from ..cache import LEADERBOARD_KEY, cache
from ..config import settings
from ..database import get_db
from ..ratelimit import write_limit
from ..realtime import publish
from ..tasks import enqueue_match_finished

router = APIRouter(tags=["matches"])


def get_match_or_404(db: Session, match_id: int) -> models.MatchDB:
    match = crud.get_match(db, match_id)
    if match is None:
        raise HTTPException(status_code=404, detail="Match not found")
    return match


# Public: anyone can read.
@router.get("/matches", response_model=schemas.MatchPage)
def list_matches(
    status: Optional[schemas.MatchStatus] = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    return {
        "items": crud.get_matches(db, limit, offset, status),
        "total": crud.count_matches(db, status),
        "limit": limit,
        "offset": offset,
    }


@router.get("/matches/{match_id}", response_model=schemas.MatchResponse)
def read_match(match_id: int, db: Session = Depends(get_db)):
    return get_match_or_404(db, match_id)


@router.get("/leaderboard", response_model=List[schemas.LeaderboardRow])
def leaderboard(response: Response, db: Session = Depends(get_db)):
    """Cache-aside: look in the cache first, ask the database only on a miss."""
    cached = cache.get(LEADERBOARD_KEY)
    if cached is not None:
        response.headers["X-Cache"] = "HIT"
        return json.loads(cached)

    table = crud.get_leaderboard(db)
    cache.set(LEADERBOARD_KEY, json.dumps(table), settings.cache_ttl_seconds)
    response.headers["X-Cache"] = "MISS"
    return table


# Protected: login required.
@router.post(
    "/matches",
    response_model=schemas.MatchResponse,
    status_code=201,
    dependencies=[Depends(write_limit)],
)
def create_match(
    match: schemas.MatchCreate,
    db: Session = Depends(get_db),
    user: models.UserDB = Depends(get_current_user),
):
    return crud.create_match(db, match.home_team, match.away_team, created_by=user.id)


@router.patch(
    "/matches/{match_id}/score",
    response_model=schemas.MatchResponse,
    dependencies=[Depends(write_limit)],
)
def update_score(
    match_id: int,
    data: schemas.MatchScoreUpdate,
    db: Session = Depends(get_db),
    user: models.UserDB = Depends(get_current_user),
):
    match = get_match_or_404(db, match_id)
    ensure_owner_or_admin(match.created_by, user)
    was_finished = match.status == "finished"
    updated = crud.update_match_score(db, match, data.home_score, data.away_score, data.status)
    cache.delete(LEADERBOARD_KEY)  # standings may have changed

    # Tell everyone who is watching, right now.
    publish(
        f"match:{updated.id}",
        {
            "type": "score_update",
            "match": schemas.MatchResponse.model_validate(updated).model_dump(mode="json"),
        },
    )
    publish("leaderboard", {"type": "leaderboard_changed"})

    # Slow work goes to the background worker, and only once per match.
    if updated.status == "finished" and not was_finished:
        enqueue_match_finished(updated.id)
    return updated


@router.delete("/matches/{match_id}", status_code=204, dependencies=[Depends(write_limit)])
def delete_match(
    match_id: int,
    db: Session = Depends(get_db),
    user: models.UserDB = Depends(get_current_user),
):
    match = get_match_or_404(db, match_id)
    ensure_owner_or_admin(match.created_by, user)
    crud.delete_match(db, match)
    cache.delete(LEADERBOARD_KEY)  # standings may have changed
    publish(f"match:{match_id}", {"type": "match_deleted", "match_id": match_id})
    publish("leaderboard", {"type": "leaderboard_changed"})
