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
    {"name": "Meera Nair", "email": "meera.broker@example.com", "role": "broker", "phone_number": "9800000005"},
    {"name": "Karan Deshmukh", "email": "karan.broker@example.com", "role": "broker", "phone_number": "9800000006"},
]

# The 13 listings below are real Indore-market listings this project's own
# dev database has accumulated (grouped under 4 brokers, same as the real
# data) — only the broker identities are fictional; property names/prices/
# locations are real and not personal data, so it's safe to ship them here.
# Two Rent examples are added on top so the Sale/Rent filter has coverage.
#
# broker_email is resolved to an id after the brokers above are created.
PROPERTIES = [
    # -- Priya Kapoor's listings --
    {
        "property_name": "DCNPL Hills", "city": "Indore", "location": "Super Corridor",
        "price_in_inr": 7000000, "listing_type": "Sale", "bhk": 2, "area_sqft": 1207,
        "area_unit": "sqft", "property_type": "Apartment", "builder_name": None,
        "amenities": None, "availability_status": "Ready to Move",
        "broker_email": "priya.broker@example.com",
    },
    {
        "property_name": "DCNPL Hills", "city": "Indore", "location": "Super Corridor",
        "price_in_inr": 10000000, "listing_type": "Sale", "bhk": 3, "area_sqft": 1660,
        "area_unit": "sqft", "property_type": "Apartment", "builder_name": None,
        "amenities": None, "availability_status": "Ready to Move",
        "broker_email": "priya.broker@example.com",
    },
    {
        "property_name": "Victoria Urban Oasis", "city": "Indore", "location": "Super Corridor",
        "price_in_inr": 3800000, "listing_type": "Sale", "bhk": 2, "area_sqft": 628,
        "area_unit": "sqft", "property_type": "Apartment", "builder_name": None,
        "amenities": None, "availability_status": "Ready to Move",
        "broker_email": "priya.broker@example.com",
    },
    # -- Sanjay Oberoi's listings --
    {
        "property_name": "3 BHK House / VILLA", "city": "Indore", "location": "Nipania",
        "price_in_inr": 16000000, "listing_type": "Sale", "bhk": 3, "area_sqft": 1000,
        "area_unit": "sqft", "property_type": "Villa", "builder_name": None,
        "amenities": None, "availability_status": "Ready to Move",
        "broker_email": "sanjay.broker@example.com",
    },
    {
        "property_name": "4 BHK House / VILLA", "city": "Indore", "location": "Laxmi Nagar Colony, Nipania, Sector D",
        "price_in_inr": 16500000, "listing_type": "Sale", "bhk": 4, "area_sqft": 2500,
        "area_unit": "sqft", "property_type": "Villa", "builder_name": None,
        "amenities": None, "availability_status": "Ready to Move",
        "broker_email": "sanjay.broker@example.com",
    },
    # -- Meera Nair's listings --
    {
        "property_name": "Apollo DB City", "city": "Indore", "location": "Nipania",
        "price_in_inr": 5500000, "listing_type": "Sale", "bhk": 2, "area_sqft": 1300,
        "area_unit": "sqft", "property_type": "Apartment", "builder_name": None,
        "amenities": None, "availability_status": "Ready to Move",
        "broker_email": "meera.broker@example.com",
    },
    {
        "property_name": "Kalindi Kunj Annexe", "city": "Indore", "location": "Sahara City Homes",
        "price_in_inr": 9500000, "listing_type": "Sale", "bhk": 4, "area_sqft": 2800,
        "area_unit": "sqft", "property_type": "Apartment", "builder_name": None,
        "amenities": None, "availability_status": "Ready to Move",
        "broker_email": "meera.broker@example.com",
    },
    {
        "property_name": "HelloWorld Peace", "city": "Indore", "location": "Vijay Nagar",
        "price_in_inr": 3000000, "listing_type": "Sale", "bhk": 1, "area_sqft": 300,
        "area_unit": "sqft", "property_type": "Apartment", "builder_name": None,
        "amenities": None, "availability_status": "Ready to Move",
        "broker_email": "meera.broker@example.com",
    },
    {
        "property_name": "Shanti Kunj", "city": "Indore", "location": "Navlakha",
        "price_in_inr": 4500000, "listing_type": "Sale", "bhk": 1, "area_sqft": 1500,
        "area_unit": "sqft", "property_type": "Apartment", "builder_name": None,
        "amenities": None, "availability_status": "Ready to Move",
        "broker_email": "meera.broker@example.com",
    },
    # -- Karan Deshmukh's listings --
    {
        "property_name": "Nivas", "city": "Indore", "location": "Kushwah Nagar",
        "price_in_inr": 27000000, "listing_type": "Sale", "bhk": 4, "area_sqft": 3000,
        "area_unit": "sqft", "property_type": "Independent House", "builder_name": None,
        "amenities": None, "availability_status": "Ready to Move",
        "broker_email": "karan.broker@example.com",
    },
    {
        "property_name": "Independent House in Mahalaxmi Nagar", "city": "Indore", "location": "Mahalaxmi Nagar",
        "price_in_inr": 13000000, "listing_type": "Sale", "bhk": 3, "area_sqft": 1300,
        "area_unit": "sqft", "property_type": "Independent House", "builder_name": None,
        "amenities": None, "availability_status": "Ready to Move",
        "broker_email": "karan.broker@example.com",
    },
    {
        "property_name": "Mahadevi Redwood Platinum", "city": "Indore", "location": "Pigdamber",
        "price_in_inr": 21600000, "listing_type": "Sale", "bhk": None, "area_sqft": 1000,
        "area_unit": "sqft", "property_type": "Apartment", "builder_name": None,
        "amenities": None, "availability_status": "Ready to Move",
        "broker_email": "karan.broker@example.com",
    },
    {
        "property_name": "Emerald Paradise Cove", "city": "Indore", "location": "Panod",
        "price_in_inr": 16000000, "listing_type": "Sale", "bhk": None, "area_sqft": 4000,
        "area_unit": "sqft", "property_type": "Plot", "builder_name": None,
        "amenities": None, "availability_status": "Ready to Move",
        "broker_email": "karan.broker@example.com",
    },
    # -- Rent examples (no real-data equivalent yet) --
    {
        "property_name": "Sunrise Apartments 2B", "city": "Indore", "location": "Vijay Nagar",
        "price_in_inr": 18000, "listing_type": "Rent", "bhk": 2, "area_sqft": 950,
        "area_unit": "sqft", "property_type": "Apartment", "builder_name": None,
        "amenities": "Lift, Security", "availability_status": "Ready to Move",
        "broker_email": "priya.broker@example.com", "security_deposit": 50000,
    },
    {
        "property_name": "Lakeview 1BHK Studio", "city": "Pune", "location": "Kharadi",
        "price_in_inr": 15000, "listing_type": "Rent", "bhk": 1, "area_sqft": 550,
        "area_unit": "sqft", "property_type": "Apartment", "builder_name": None,
        "amenities": "Furnished, Wifi", "availability_status": "Ready to Move",
        "broker_email": "meera.broker@example.com", "security_deposit": 30000,
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
        # Include bhk in the match key: a broker can legitimately list two
        # differently-configured units under the same project name (e.g. a
        # 2 BHK and a 3 BHK both called "DCNPL Hills").
        existing = (
            db.query(PropertyModel)
            .filter(
                PropertyModel.property_name == p["property_name"],
                PropertyModel.broker_id == broker.id,
                PropertyModel.bhk == p["bhk"],
            )
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
