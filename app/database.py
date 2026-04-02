# 📌 DATABASE CONFIGURATION

# DATABASE_URL:
# SQLite DB use kar rahe hain (local testing ke liye)
# File: test.db

# SessionLocal:
# Ye DB session banata hai (connection handler)

# Base:
# Iska use models banane ke liye hota hai (tables define karne ke liye)


# 🔥 Auto-managed DB session (FastAPI Dependency)

# Why?
# - Manual DB handling mein (db = SessionLocal())
#   connection close hone ka risk hota hai
# - Memory leak aur scaling issues ho sakte hain

# Solution:
# - FastAPI ka Depends use karke DB ko auto open/close karte hain

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# DB URL
DATABASE_URL = "sqlite:///./test.db"

# 🔥 MUST: engine defined hona chahiye
engine = create_engine(DATABASE_URL)

# Session
SessionLocal = sessionmaker(bind=engine)

# Base (models ke liye)
Base = declarative_base()


# 🔥 Auto-managed DB session
# I think this func was initially written on router/player.py file but we moved this here in database.py
# It was local before but now it is global.
def get_db():
  db = SessionLocal()
  try:
    yield db
  finally:
    db.close()
