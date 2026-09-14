"""
Populate a freshly created database with sample data so a new clone of this
repo has something to look at immediately, instead of an empty catalog.

Git never carries the actual Postgres data (it lives in a local Docker
volume), so every collaborator who clones this repo starts with zero users
and zero properties even after running init_db.py. This script fixes that
for local development.

Idempotent: safe to run more than once. Rows are matched by email (users)
and by (property_name, broker) (properties), so re-running just fills in
anything missing instead of creating duplicates.

Usage (from backend/):
    python scripts/seed.py
"""
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database.connection import SessionLocal
from app.database.models import PropertyModel, UserModel
from app.core.security import get_password_hash

# Every seeded account uses this password — shown at the end of the run too.
DEMO_PASSWORD = "Demo@1234"

USERS = [
    {"name": "Asha Mehta", "email": "asha.buyer@example.com", "role": "user", "phone_number": "9800000001"},
    {"name": "Rohan Verma", "email": "rohan.buyer@example.com", "role": "user", "phone_number": "9800000002"},
    {"name": "Priya Kapoor", "email": "priya.broker@example.com", "role": "broker", "phone_number": "9800000003"},
    {"name": "Sanjay Oberoi", "email": "sanjay.broker@example.com", "role": "broker", "phone_number": "9800000004"},
]

# broker_email is resolved to an id after the brokers above are created.
PROPERTIES = [
    {
        "property_name": "Skyline Residences", "city": "Indore", "location": "Vijay Nagar",
        "price_in_inr": 9500000, "listing_type": "Sale", "bhk": 3, "area_sqft": 1650,
        "area_unit": "sqft", "property_type": "Apartment", "builder_name": "ABC Group",
        "amenities": "Pool, Gym, Clubhouse", "availability_status": "Ready to Move",
        "broker_email": "priya.broker@example.com",
    },
    {
        "property_name": "Greenfield Homes", "city": "Indore", "location": "Rau",
        "price_in_inr": 4200000, "listing_type": "Sale", "bhk": 2, "area_sqft": 980,
        "area_unit": "sqft", "property_type": "Apartment", "builder_name": "Greenfield Developers",
        "amenities": "Garden, Parking", "availability_status": "Under Construction",
        "broker_email": "priya.broker@example.com",
    },
    {
        "property_name": "Oceanview Villa", "city": "Pune", "location": "Baner",
        "price_in_inr": 25000000, "listing_type": "Sale", "bhk": 4, "area_sqft": 3200,
        "area_unit": "sqft", "property_type": "Villa", "builder_name": None,
        "amenities": "Private Pool, Garden", "availability_status": "Ready to Move",
        "broker_email": "sanjay.broker@example.com",
    },
    {
        "property_name": "Riverside Plot 12", "city": "Indore", "location": "Super Corridor",
        "price_in_inr": 3500000, "listing_type": "Sale", "bhk": None, "area_sqft": 0.15,
        "area_unit": "acre", "property_type": "Plot", "builder_name": None,
        "amenities": None, "availability_status": "Ready to Move",
        "broker_email": "sanjay.broker@example.com",
    },
    {
        "property_name": "Metro Business Hub", "city": "Pune", "location": "Hinjewadi",
        "price_in_inr": 18000000, "listing_type": "Sale", "bhk": None, "area_sqft": 2200,
        "area_unit": "sqft", "property_type": "Commercial", "builder_name": "Metro Realty",
        "amenities": "Elevator, Power Backup", "availability_status": "Ready to Move",
        "broker_email": "priya.broker@example.com",
    },
    {
        "property_name": "Sunrise Apartments 2B", "city": "Indore", "location": "Vijay Nagar",
        "price_in_inr": 18000, "listing_type": "Rent", "bhk": 2, "area_sqft": 950,
        "area_unit": "sqft", "property_type": "Apartment", "builder_name": None,
        "amenities": "Lift, Security", "availability_status": "Ready to Move",
        "broker_email": "priya.broker@example.com", "security_deposit": 50000,
    },
    {
        "property_name": "Hilltop Independent House", "city": "Bhopal", "location": "Arera Colony",
        "price_in_inr": 32000, "listing_type": "Rent", "bhk": 3, "area_sqft": 1800,
        "area_unit": "sqft", "property_type": "Independent House", "builder_name": None,
        "amenities": "Terrace, Parking", "availability_status": "Ready to Move",
        "broker_email": "sanjay.broker@example.com", "security_deposit": 100000,
    },
    {
        "property_name": "Lakeview 1BHK Studio", "city": "Pune", "location": "Kharadi",
        "price_in_inr": 15000, "listing_type": "Rent", "bhk": 1, "area_sqft": 550,
        "area_unit": "sqft", "property_type": "Apartment", "builder_name": None,
        "amenities": "Furnished, Wifi", "availability_status": "Ready to Move",
        "broker_email": "sanjay.broker@example.com", "security_deposit": 30000,
    },
]


def seed_users(db) -> dict:
    """Returns {email: UserModel} for every user in USERS, creating any that don't exist."""
    by_email = {}
    for u in USERS:
        existing = db.query(UserModel).filter(UserModel.email == u["email"]).first()
        if existing:
            by_email[u["email"]] = existing
            continue
        new_user = UserModel(
            name=u["name"],
            email=u["email"],
            hashed_password=get_password_hash(DEMO_PASSWORD),
            role=u["role"],
            phone_number=u["phone_number"],
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        by_email[u["email"]] = new_user
        print(f"  + created {u['role']} {u['name']} <{u['email']}>")
    return by_email


def seed_properties(db, users_by_email: dict) -> None:
    for p in PROPERTIES:
        broker = users_by_email[p["broker_email"]]
        existing = (
            db.query(PropertyModel)
            .filter(PropertyModel.property_name == p["property_name"], PropertyModel.broker_id == broker.id)
            .first()
        )
        if existing:
            continue
        db.add(PropertyModel(
            property_name=p["property_name"],
            city=p["city"],
            location=p["location"],
            price_in_inr=p["price_in_inr"],
            listing_type=p["listing_type"],
            security_deposit=p.get("security_deposit"),
            bhk=p["bhk"],
            area_sqft=p["area_sqft"],
            area_unit=p["area_unit"],
            property_type=p["property_type"],
            builder_name=p["builder_name"],
            amenities=p["amenities"],
            availability_status=p["availability_status"],
            source="seed_script",
            broker_id=broker.id,
        ))
        print(f"  + created listing \"{p['property_name']}\" ({p['city']})")
    db.commit()


def seed():
    db = SessionLocal()
    try:
        print("Seeding users...")
        users_by_email = seed_users(db)
        print("Seeding properties...")
        seed_properties(db, users_by_email)
        print("\nDone. Demo accounts (all use the same password):")
        for u in USERS:
            print(f"  {u['role']:<7} {u['email']}")
        print(f"  password: {DEMO_PASSWORD}")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
