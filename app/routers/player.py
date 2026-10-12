from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from .. import crud, models, schemas
from ..auth import ensure_owner_or_admin, get_current_user
from ..database import get_db

router = APIRouter(tags=["players"])


def get_player_or_404(db: Session, player_id: int) -> models.PlayerDB:
    player = crud.get_player(db, player_id)
    if player is None:
        raise HTTPException(status_code=404, detail="Player not found")
    return player


# Public: anyone can read.
@router.get("/players", response_model=schemas.PlayerPage)
def list_players(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    return {
        "items": crud.get_players(db, limit, offset),
        "total": crud.count_players(db),
        "limit": limit,
        "offset": offset,
    }


@router.get("/player/{player_id}", response_model=schemas.PlayerResponse)
def read_player(player_id: int, db: Session = Depends(get_db)):
    return get_player_or_404(db, player_id)


# Protected: login required.
@router.post("/player", response_model=schemas.PlayerResponse, status_code=201)
def create_player(
    player: schemas.PlayerCreate,
    db: Session = Depends(get_db),
    user: models.UserDB = Depends(get_current_user),
):
    return crud.create_player(db, player.name, player.team, owner_id=user.id)


@router.put("/player/{player_id}", response_model=schemas.PlayerResponse)
def update_player(
    player_id: int,
    data: schemas.PlayerCreate,
    db: Session = Depends(get_db),
    user: models.UserDB = Depends(get_current_user),
):
    player = get_player_or_404(db, player_id)
    ensure_owner_or_admin(player.owner_id, user)
    return crud.update_player(db, player, data.name, data.team)


@router.delete("/player/{player_id}", status_code=204)
def delete_player(
    player_id: int,
    db: Session = Depends(get_db),
    user: models.UserDB = Depends(get_current_user),
):
    player = get_player_or_404(db, player_id)
    ensure_owner_or_admin(player.owner_id, user)
    crud.delete_player(db, player)
