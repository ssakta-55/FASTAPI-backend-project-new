from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import crud, models, schemas
from ..auth import get_current_user
from ..database import get_db

router = APIRouter(tags=["players"])


def get_player_or_404(db: Session, player_id: int) -> models.PlayerDB:
    player = crud.get_player(db, player_id)
    if player is None:
        raise HTTPException(status_code=404, detail="Player not found")
    return player


def check_can_modify(player: models.PlayerDB, user: models.UserDB) -> None:
    """Only the owner or an admin may change or delete a player."""
    if player.owner_id != user.id and user.role != "admin":
        raise HTTPException(status_code=403, detail="You do not own this player")


# Public: anyone can read.
@router.get("/players", response_model=list[schemas.PlayerResponse])
def list_players(db: Session = Depends(get_db)):
    return crud.get_players(db)  # an empty list is a valid answer (200), not an error


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
    check_can_modify(player, user)
    return crud.update_player(db, player, data.name, data.team)


@router.delete("/player/{player_id}", status_code=204)
def delete_player(
    player_id: int,
    db: Session = Depends(get_db),
    user: models.UserDB = Depends(get_current_user),
):
    player = get_player_or_404(db, player_id)
    check_can_modify(player, user)
    crud.delete_player(db, player)
