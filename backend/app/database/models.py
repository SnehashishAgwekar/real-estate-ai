from sqlalchemy import Column, Integer, String, Float, DateTime, Text
from sqlalchemy.sql import func
from app.database.connection import Base

class PropertyModel(Base):
    """
    Database table representation for a real estate property.
    """
    __tablename__ = "properties"

    id = Column(Integer, primary_key=True, index=True)
    property_name = Column(String(255), nullable=False, index=True)
    city = Column(String(100), nullable=False, index=True)
    location = Column(String(255), nullable=False)
    price_in_inr = Column(Float, nullable=False, index=True)
    bhk = Column(Integer, nullable=False, index=True)
    area_sqft = Column(Float, nullable=False)
    property_type = Column(String(50), nullable=False)  # Apartment, Villa, Plot
    builder_name = Column(String(150), nullable=True)
    amenities = Column(Text, nullable=True)             # Comma-separated or description
    availability_status = Column(String(50), default="Ready to Move")
    source = Column(String(100), nullable=False)        # Housing.com, MagicBricks, etc.
    
    # CRITICAL UPDATE: Added unique=True and index=True to prevent duplicate scraping
    source_url = Column(String(500), nullable=True, unique=True, index=True) 
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())