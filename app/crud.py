"""Database operations only. HTTP errors are handled in the routers."""
from sqlalchemy.orm import Session

from .models import PlayerDB, UserDB


# ---- users ----
def get_user_by_username(db: Session, username: str):
    return db.query(UserDB).filter(UserDB.username == username).first()


def list_users(db: Session):
    return db.query(UserDB).all()


def create_user(db: Session, username: str, hashed_password: str):
    user = UserDB(username=username, password=hashed_password)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


# ---- players ----
def get_players(db: Session):
    return db.query(PlayerDB).all()


def get_player(db: Session, player_id: int):
    return db.query(PlayerDB).filter(PlayerDB.id == player_id).first()


def create_player(db: Session, name: str, team: str, owner_id: int):
    player = PlayerDB(name=name, team=team, owner_id=owner_id)
    db.add(player)
    db.commit()
    db.refresh(player)
    return player


def update_player(db: Session, player: PlayerDB, name: str, team: str):
    player.name = name
    player.team = team
    db.commit()
    db.refresh(player)
    return player


def delete_player(db: Session, player: PlayerDB):
    db.delete(player)
    db.commit()
