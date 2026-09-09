from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from app.database.models import PropertyModel

def query_structured_properties(
    db: Session,
    city: Optional[str] = None,
    location: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    min_bhk: Optional[int] = None,
    property_type: Optional[str] = None,
    limit: int = 5
) -> List[Dict[str, Any]]:
    """
    Executes a structured SQL query against PostgreSQL filtering properties.
    """
    query = db.query(PropertyModel)

    if city:
        query = query.filter(PropertyModel.city.ilike(f"%{city.strip()}%"))
    if location:
        # locality / area / sector match, e.g. "Super Corridor", "Vijay Nagar"
        query = query.filter(PropertyModel.location.ilike(f"%{location.strip()}%"))
    if min_price:
        query = query.filter(PropertyModel.price_in_inr >= min_price)
    if max_price:
        query = query.filter(PropertyModel.price_in_inr <= max_price)
    if min_bhk:
        query = query.filter(PropertyModel.bhk >= min_bhk)
    if property_type:
        query = query.filter(PropertyModel.property_type.ilike(f"%{property_type.strip()}%"))

    results = query.order_by(PropertyModel.created_at.desc()).limit(limit).all()

    properties_list = []
    for p in results:
        properties_list.append({
            "id": p.id,
            "property_name": p.property_name,
            "city": p.city,
            "location": p.location,
            "price_in_inr": p.price_in_inr,
            "bhk": p.bhk,
            "area_sqft": p.area_sqft,
            "area_unit": p.area_unit or "sqft",
            "property_type": p.property_type,
            "builder_name": p.builder_name,
            "amenities": p.amenities,
            "availability_status": p.availability_status,
            "image_urls": p.image_urls or [],
            "source_url": p.source_url,
            "source": p.source,
            "broker_id": p.broker_id,
            # True when this is one of our own broker-uploaded listings
            "on_platform": p.broker_id is not None,
        })

    return properties_list