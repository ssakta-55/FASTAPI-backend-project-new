from sqlalchemy import Column, ForeignKey, Integer, String

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
