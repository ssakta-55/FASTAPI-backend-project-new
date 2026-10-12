from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from .. import crud, models, schemas
from ..auth import ensure_owner_or_admin, get_current_user
from ..database import get_db

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
def leaderboard(db: Session = Depends(get_db)):
    return crud.get_leaderboard(db)


# Protected: login required.
@router.post("/matches", response_model=schemas.MatchResponse, status_code=201)
def create_match(
    match: schemas.MatchCreate,
    db: Session = Depends(get_db),
    user: models.UserDB = Depends(get_current_user),
):
    return crud.create_match(db, match.home_team, match.away_team, created_by=user.id)


@router.patch("/matches/{match_id}/score", response_model=schemas.MatchResponse)
def update_score(
    match_id: int,
    data: schemas.MatchScoreUpdate,
    db: Session = Depends(get_db),
    user: models.UserDB = Depends(get_current_user),
):
    match = get_match_or_404(db, match_id)
    ensure_owner_or_admin(match.created_by, user)
    return crud.update_match_score(db, match, data.home_score, data.away_score, data.status)


@router.delete("/matches/{match_id}", status_code=204)
def delete_match(
    match_id: int,
    db: Session = Depends(get_db),
    user: models.UserDB = Depends(get_current_user),
):
    match = get_match_or_404(db, match_id)
    ensure_owner_or_admin(match.created_by, user)
    crud.delete_match(db, match)
