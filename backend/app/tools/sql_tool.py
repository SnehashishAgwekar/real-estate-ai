from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from app.database.models import PropertyModel

def query_structured_properties(
    db: Session,
    city: Optional[str] = None,
    min_price: Optional[float] = None, # <-- Added min_price argument
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
    if min_price:
        query = query.filter(PropertyModel.price_in_inr >= min_price) # <-- Added min_price filter
    if max_price:
        query = query.filter(PropertyModel.price_in_inr <= max_price)
    if min_bhk:
        query = query.filter(PropertyModel.bhk >= min_bhk)
    if property_type:
        query = query.filter(PropertyModel.property_type.ilike(f"%{property_type.strip()}%"))

    results = query.limit(limit).all()

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
            "property_type": p.property_type,
            "builder_name": p.builder_name,
            "amenities": p.amenities,
            "source": p.source
        })

    return properties_list