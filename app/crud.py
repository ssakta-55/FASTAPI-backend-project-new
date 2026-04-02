from .models import PlayerDB
# for including Error handling add below import as well
from fastapi import HTTPException

def create_player(db, player):
  new_player = PlayerDB(name=player.name, team=player.team)
  db.add(new_player)
  db.commit()
  db.refresh(new_player)
  return new_player

#def get_players(db):
#  return db.query(PlayerDB).all()
# commenting above line because there is no erorr handling.

def get_players(db):
  players = db.query(PlayerDB).all()
  if not players:
    raise HTTPException(status_code=404, detail="No players found")
  return players

#def update_player(db, player_id, player):
#  db_player = db.query(PlayerDB).filter(PlayerDB.id == player_id).first()
  
#  if not db_player:
#    return None

#  db_player.name = player.name
#  db_player.team = player.team

#  db.commit()
#  db.refresh(db_player)
#  return db_player

def update_player(db, player_id, player):
  db_player = db.query(PlayerDB).filter(PlayerDB.id == player_id).first()

  if not db_player:
    raise HTTPException(status_code=404, detail="Player not found")

  db_player.name = player.name
  db_player.team = player.team

  db.commit()
  db.refresh(db_player)
  return db_player

#def delete_player(db, player_id):
#  player = db.query(PlayerDB).filter(PlayerDB.id == player_id).first()

#  if not player:
#    return None

#  db.delete(player)
#  db.commit()
#  return {"message": "Deleted successfully"}

def delete_player(db, player_id):
  db_player = db.query(PlayerDB).filter(PlayerDB.id == player_id).first()

  if not db_player:
    raise HTTPException(status_code=404, detail="Player not found")

  db.delete(db_player)
  db.commit()

  return {"message": "Player deleted successfully"}


# This below lines are added newly to implenent JWT concept please remember.

from .models import UserDB
from .auth import hash_password

def create_user(db, user):
  hashed = hash_password(user.password)
  db_user = UserDB(username=user.username, password=hashed)
  db.add(db_user)
  db.commit()
  db.refresh(db_user)
  return db_user


def authenticate_user(db, username, password):
  user = db.query(UserDB).filter(UserDB.username == username).first()
  if not user:
    return None
  from .auth import verify_password
  if not verify_password(password, user.password):
    return None
  return user
