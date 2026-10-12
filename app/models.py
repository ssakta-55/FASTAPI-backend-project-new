from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, func

from .database import Base


class UserDB(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    password = Column(String, nullable=False)  # stores the bcrypt hash, never plain text
    role = Column(String, nullable=False, default="user")  # "user" or "admin"


class PlayerDB(Base):
    __tablename__ = "players"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    team = Column(String, nullable=False)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)


class MatchDB(Base):
    __tablename__ = "matches"

    id = Column(Integer, primary_key=True, index=True)
    home_team = Column(String, nullable=False)
    away_team = Column(String, nullable=False)
    home_score = Column(Integer, nullable=False, default=0, server_default="0")
    away_score = Column(Integer, nullable=False, default=0, server_default="0")
    # "scheduled", "live" or "finished"
    status = Column(
        String, nullable=False, default="scheduled", server_default="scheduled", index=True
    )
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
