import sys
import os

# Add parent directory to python path so scripts can import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import inspect, text

from app.database.connection import engine, Base
from app.database.models import PropertyModel, UserModel

# Columns added after the initial schema; create_all() does not ALTER existing
# tables, so patch them in for databases created before the column existed.
_ADDED_COLUMNS = {
    "properties": {
        "area_unit": "ALTER TABLE properties ADD COLUMN area_unit VARCHAR(20) DEFAULT 'sqft'",
        "image_urls": "ALTER TABLE properties ADD COLUMN image_urls JSONB",
    },
}


def _apply_added_columns():
    insp = inspect(engine)
    for table, columns in _ADDED_COLUMNS.items():
        if not insp.has_table(table):
            continue
        existing = {c["name"] for c in insp.get_columns(table)}
        for name, ddl in columns.items():
            if name not in existing:
                print(f"Adding missing column {table}.{name}...")
                with engine.begin() as conn:
                    conn.execute(text(ddl))


def init_db():
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    _apply_added_columns()
    print("Database tables created successfully!")

if __name__ == "__main__":
    init_db()