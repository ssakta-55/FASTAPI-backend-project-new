from sqlalchemy import Column, Integer, String   # This import also used for JWT concept.
from .database import Base

class PlayerDB(Base):
  __tablename__ = "players"

  id = Column(Integer, primary_key=True, index=True)
  name = Column(String)
  team = Column(String)

# Below updating file for using JWT concepts.

class UserDB(Base):
  __tablename__ = "users"

  id = Column(Integer, primary_key=True, index=True)
  username = Column(String, unique=True, index=True)
  password = Column(String)
