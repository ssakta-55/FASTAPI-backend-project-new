# 📌 FILE: player.py

# 🧠 NOTE:

# Is project mein FastAPI ka best practice use kiya gaya hai:
# db: Session = Depends(get_db)

# 👉 Iska matlab:
# - Har API ke liye DB session automatically create hota hai
# - Request ke baad automatically close ho jata hai

# 👉 Benefit:
# ✔ clean code
# ✔ no connection leak
# ✔ production-ready
# ✔ scalable approach

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..database import get_db
from .. import crud, schemas
from ..auth import get_current_user # this import added for Protected route concept.

router = APIRouter()


# CREATE → new player add karna
# But need to comment this as we are now loking to add Response Model control and validate the output data returned to the client.
# Or we can saw no extra and optional data will be returned only limited ones.
#@router.post("/player")
#def create(player: schemas.PlayerCreate, db: Session = Depends(get_db)):
#  return crud.create_player(db, player)


# READ → sab players fetch karna
#@router.get("/players")
#def read(db: Session = Depends(get_db)):
#  return crud.get_players(db)


# UPDATE → existing player update karna
#@router.put("/player/{player_id}")
#def update(player_id: int, player: schemas.PlayerCreate, db: Session = Depends(get_db)):
#  return crud.update_player(db, player_id, player)


# DELETE → player remove karna
#@router.delete("/player/{player_id}")
#def delete(player_id: int, db: Session = Depends(get_db)):
#  return crud.delete_player(db, player_id)

# CREATE → new player add karna with having response model
@router.post("/player", response_model=schemas.PlayerResponse)
def create(player: schemas.PlayerCreate, db: Session = Depends(get_db)):
  return crud.create_player(db, player)


# READ → sab players fetch karna using response model
from typing import List

@router.get("/players", response_model=List[schemas.PlayerResponse])
#This below read function I'll comment and modify it so that it will supoort protected routes concept in JWT.
#def read(db: Session = Depends(get_db)):
#  return crud.get_players(db
# Now modifying this to support protected routes.
def read(
  db: Session = Depends(get_db),
  user: str = Depends(get_current_user)   # 👈 add this
):
  return crud.get_players(db)

# UPDATE → existing player update karna using response model..
@router.put("/player/{player_id}", response_model=schemas.PlayerResponse)
def update(player_id: int, player: schemas.PlayerCreate, db: Session = Depends(get_db)):
  return crud.update_player(db, player_id, player)


# DELETE → player remove karna using response model
@router.delete("/player/{player_id}")
def delete(player_id: int, db: Session = Depends(get_db)):
  return crud.delete_player(db, player_id)
