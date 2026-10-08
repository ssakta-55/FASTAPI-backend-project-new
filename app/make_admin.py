"""Usage: python -m app.make_admin <username>"""
import sys

from .database import SessionLocal
from .models import UserDB

if len(sys.argv) != 2:
    sys.exit("Usage: python -m app.make_admin <username>")

db = SessionLocal()
user = db.query(UserDB).filter(UserDB.username == sys.argv[1]).first()
if user is None:
    sys.exit(f"No such user: {sys.argv[1]}")
user.role = "admin"
db.commit()
print(f"{user.username} is now an admin")
