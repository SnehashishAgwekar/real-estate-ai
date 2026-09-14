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


def _img(photo_id: str, w: int = 1200) -> str:
    return f"https://images.unsplash.com/photo-{photo_id}?auto=format&fit=crop&w={w}&q=80"


# Stock photos grouped by what they actually show, so each seed listing's
# images match its property_type instead of being random. Every URL below
# was verified to load (200, image/jpeg) before being added.
_APT_BEDROOM_1 = _img("1522708323590-d24dbb6b0267")
_APT_BEDROOM_2 = _img("1512918728675-ed5a9ecdebfd")
_APT_SEATING = _img("1502672260266-1c1ef2d93688")
_APT_LIVING_WINDOW = _img("1583847268964-b28dc8f51f92")
_APT_LIVING_MINIMAL = _img("1585128792020-803d29415281")
_APT_LIVING_NEUTRAL = _img("1560448204-e02f11c3d0e2")
_APT_KITCHEN = _img("1484154218962-a197022b5858")
_VILLA_EXTERIOR = _img("1580587771525-78b9dba3b914")
_VILLA_POOL = _img("1613977257592-4871e5fcd7c4")
_HOUSE_LOW_ANGLE = _img("1574245076380-a66f5bd39ecc")
_HOUSE_FRONT = _img("1621417403732-e564f462e7ec")
_PLOT_FIELD = _img("1599809563132-4b678fb6f611")

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
        "image_urls": [_APT_BEDROOM_1, _APT_LIVING_WINDOW],
    },
    {
        "property_name": "DCNPL Hills", "city": "Indore", "location": "Super Corridor",
        "price_in_inr": 10000000, "listing_type": "Sale", "bhk": 3, "area_sqft": 1660,
        "area_unit": "sqft", "property_type": "Apartment", "builder_name": None,
        "amenities": None, "availability_status": "Ready to Move",
        "broker_email": "priya.broker@example.com",
        "image_urls": [_APT_BEDROOM_2, _APT_KITCHEN],
    },
    {
        "property_name": "Victoria Urban Oasis", "city": "Indore", "location": "Super Corridor",
        "price_in_inr": 3800000, "listing_type": "Sale", "bhk": 2, "area_sqft": 628,
        "area_unit": "sqft", "property_type": "Apartment", "builder_name": None,
        "amenities": None, "availability_status": "Ready to Move",
        "broker_email": "priya.broker@example.com",
        "image_urls": [_APT_SEATING, _APT_LIVING_MINIMAL],
    },
    # -- Sanjay Oberoi's listings --
    {
        "property_name": "3 BHK House / VILLA", "city": "Indore", "location": "Nipania",
        "price_in_inr": 16000000, "listing_type": "Sale", "bhk": 3, "area_sqft": 1000,
        "area_unit": "sqft", "property_type": "Villa", "builder_name": None,
        "amenities": None, "availability_status": "Ready to Move",
        "broker_email": "sanjay.broker@example.com",
        "image_urls": [_VILLA_EXTERIOR, _VILLA_POOL],
    },
    {
        "property_name": "4 BHK House / VILLA", "city": "Indore", "location": "Laxmi Nagar Colony, Nipania, Sector D",
        "price_in_inr": 16500000, "listing_type": "Sale", "bhk": 4, "area_sqft": 2500,
        "area_unit": "sqft", "property_type": "Villa", "builder_name": None,
        "amenities": None, "availability_status": "Ready to Move",
        "broker_email": "sanjay.broker@example.com",
        "image_urls": [_VILLA_POOL, _VILLA_EXTERIOR],
    },
    # -- Meera Nair's listings --
    {
        "property_name": "Apollo DB City", "city": "Indore", "location": "Nipania",
        "price_in_inr": 5500000, "listing_type": "Sale", "bhk": 2, "area_sqft": 1300,
        "area_unit": "sqft", "property_type": "Apartment", "builder_name": None,
        "amenities": None, "availability_status": "Ready to Move",
        "broker_email": "meera.broker@example.com",
        "image_urls": [_APT_LIVING_WINDOW, _APT_LIVING_NEUTRAL],
    },
    {
        "property_name": "Kalindi Kunj Annexe", "city": "Indore", "location": "Sahara City Homes",
        "price_in_inr": 9500000, "listing_type": "Sale", "bhk": 4, "area_sqft": 2800,
        "area_unit": "sqft", "property_type": "Apartment", "builder_name": None,
        "amenities": None, "availability_status": "Ready to Move",
        "broker_email": "meera.broker@example.com",
        "image_urls": [_APT_BEDROOM_1, _APT_KITCHEN],
    },
    {
        "property_name": "HelloWorld Peace", "city": "Indore", "location": "Vijay Nagar",
        "price_in_inr": 3000000, "listing_type": "Sale", "bhk": 1, "area_sqft": 300,
        "area_unit": "sqft", "property_type": "Apartment", "builder_name": None,
        "amenities": None, "availability_status": "Ready to Move",
        "broker_email": "meera.broker@example.com",
        "image_urls": [_APT_LIVING_MINIMAL, _APT_SEATING],
    },
    {
        "property_name": "Shanti Kunj", "city": "Indore", "location": "Navlakha",
        "price_in_inr": 4500000, "listing_type": "Sale", "bhk": 1, "area_sqft": 1500,
        "area_unit": "sqft", "property_type": "Apartment", "builder_name": None,
        "amenities": None, "availability_status": "Ready to Move",
        "broker_email": "meera.broker@example.com",
        "image_urls": [_APT_BEDROOM_2, _APT_LIVING_NEUTRAL],
    },
    # -- Karan Deshmukh's listings --
    {
        "property_name": "Nivas", "city": "Indore", "location": "Kushwah Nagar",
        "price_in_inr": 27000000, "listing_type": "Sale", "bhk": 4, "area_sqft": 3000,
        "area_unit": "sqft", "property_type": "Independent House", "builder_name": None,
        "amenities": None, "availability_status": "Ready to Move",
        "broker_email": "karan.broker@example.com",
        "image_urls": [_HOUSE_LOW_ANGLE, _HOUSE_FRONT],
    },
    {
        "property_name": "Independent House in Mahalaxmi Nagar", "city": "Indore", "location": "Mahalaxmi Nagar",
        "price_in_inr": 13000000, "listing_type": "Sale", "bhk": 3, "area_sqft": 1300,
        "area_unit": "sqft", "property_type": "Independent House", "builder_name": None,
        "amenities": None, "availability_status": "Ready to Move",
        "broker_email": "karan.broker@example.com",
        "image_urls": [_HOUSE_FRONT, _HOUSE_LOW_ANGLE],
    },
    {
        "property_name": "Mahadevi Redwood Platinum", "city": "Indore", "location": "Pigdamber",
        "price_in_inr": 21600000, "listing_type": "Sale", "bhk": None, "area_sqft": 1000,
        "area_unit": "sqft", "property_type": "Apartment", "builder_name": None,
        "amenities": None, "availability_status": "Ready to Move",
        "broker_email": "karan.broker@example.com",
        "image_urls": [_APT_LIVING_WINDOW, _APT_BEDROOM_1],
    },
    {
        "property_name": "Emerald Paradise Cove", "city": "Indore", "location": "Panod",
        "price_in_inr": 16000000, "listing_type": "Sale", "bhk": None, "area_sqft": 4000,
        "area_unit": "sqft", "property_type": "Plot", "builder_name": None,
        "amenities": None, "availability_status": "Ready to Move",
        "broker_email": "karan.broker@example.com",
        "image_urls": [_PLOT_FIELD],
    },
    # -- Rent examples (no real-data equivalent yet) --
    {
        "property_name": "Sunrise Apartments 2B", "city": "Indore", "location": "Vijay Nagar",
        "price_in_inr": 18000, "listing_type": "Rent", "bhk": 2, "area_sqft": 950,
        "area_unit": "sqft", "property_type": "Apartment", "builder_name": None,
        "amenities": "Lift, Security", "availability_status": "Ready to Move",
        "broker_email": "priya.broker@example.com", "security_deposit": 50000,
        "image_urls": [_APT_LIVING_NEUTRAL, _APT_KITCHEN],
    },
    {
        "property_name": "Lakeview 1BHK Studio", "city": "Pune", "location": "Kharadi",
        "price_in_inr": 15000, "listing_type": "Rent", "bhk": 1, "area_sqft": 550,
        "area_unit": "sqft", "property_type": "Apartment", "builder_name": None,
        "amenities": "Furnished, Wifi", "availability_status": "Ready to Move",
        "broker_email": "meera.broker@example.com", "security_deposit": 30000,
        "image_urls": [_APT_LIVING_MINIMAL, _APT_BEDROOM_2],
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
            # Backfill images onto rows seeded before this script had any
            # (harmless no-op once every row has photos).
            if not existing.image_urls and p.get("image_urls"):
                existing.image_urls = p["image_urls"]
                print(f"  + added photos to \"{p['property_name']}\"")
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
            image_urls=p.get("image_urls"),
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
