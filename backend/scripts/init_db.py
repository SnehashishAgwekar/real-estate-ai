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
        "listing_type": "ALTER TABLE properties ADD COLUMN listing_type VARCHAR(20) NOT NULL DEFAULT 'Sale'",
        "security_deposit": "ALTER TABLE properties ADD COLUMN security_deposit DOUBLE PRECISION",
    },
}

# Columns whose NOT NULL was later dropped in the model; create_all() does not
# ALTER existing tables, so relax them for databases created before the change.
_RELAXED_NOT_NULL = {
    "properties": ["bhk"],  # plots/land have no bedrooms
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


def _relax_not_null():
    insp = inspect(engine)
    for table, names in _RELAXED_NOT_NULL.items():
        if not insp.has_table(table):
            continue
        by_name = {c["name"]: c for c in insp.get_columns(table)}
        for name in names:
            col = by_name.get(name)
            if col is not None and not col["nullable"]:
                print(f"Dropping NOT NULL on {table}.{name}...")
                with engine.begin() as conn:
                    conn.execute(text(f"ALTER TABLE {table} ALTER COLUMN {name} DROP NOT NULL"))


def init_db():
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    _apply_added_columns()
    _relax_not_null()
    print("Database tables created successfully!")

if __name__ == "__main__":
    init_db()