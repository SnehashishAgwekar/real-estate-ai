import sys
import os

# Add parent directory to python path so scripts can import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database.connection import SessionLocal, engine
from app.database.models import UserModel

# connection.py builds the engine with echo=True; silence the SQL log so this
# report isn't buried in statements.
engine.echo = False


def list_users():
    db = SessionLocal()
    try:
        rows = db.query(UserModel).order_by(UserModel.created_at).all()
    finally:
        db.close()

    print(f"\n{len(rows)} registered user(s):\n")
    header = f"{'ID':<5} {'ROLE':<8} {'NAME':<24} {'EMAIL':<34} {'PHONE':<16} CREATED"
    print(header)
    print("-" * len(header))
    for u in rows:
        print(
            f"{u.id:<5} {u.role:<8} {(u.name or ''):<24} {u.email:<34} "
            f"{(u.phone_number or ''):<16} {u.created_at}"
        )
    print()


if __name__ == "__main__":
    list_users()
