from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Text, ForeignKey, JSON, UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database.connection import Base

class UserModel(Base):
    """
    Database table representation for a user or broker.
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    phone_number = Column(String(20), nullable=True)
    role = Column(String(20), nullable=False, default="user") # "user" or "broker"
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    properties = relationship("PropertyModel", back_populates="broker")


class PropertyModel(Base):
    __tablename__ = "properties"

    id = Column(Integer, primary_key=True, index=True)
    property_name = Column(String(255), nullable=False, index=True)
    city = Column(String(100), nullable=False, index=True)
    location = Column(String(255), nullable=False)
    # For a "Sale" listing this is the sale price; for a "Rent" listing it's
    # the monthly rent amount.
    price_in_inr = Column(Float, nullable=False, index=True)

    # "Sale" or "Rent"
    listing_type = Column(String(20), nullable=False, default="Sale", index=True)
    # Only meaningful when listing_type == "Rent"
    security_deposit = Column(Float, nullable=True)

    # Modified: nullable=True since plots/land don't have bedrooms
    bhk = Column(Integer, nullable=True, index=True)

    area_sqft = Column(Float, nullable=False)
    # New: To display the original unit (e.g., "acre", "sqft", "sq_yard")
    area_unit = Column(String(20), default="sqft")

    # property_type handles "Apartment", "Villa", "Plot", "Commercial"
    property_type = Column(String(50), nullable=False)
    builder_name = Column(String(150), nullable=True)
    amenities = Column(Text, nullable=True)
    availability_status = Column(String(50), default="Ready to Move")
    source = Column(String(100), nullable=False)
    source_url = Column(String(500), nullable=True, unique=True, index=True)

    # List of server-relative image paths, e.g. ["/static/uploads/ab12.jpg", ...]
    image_urls = Column(JSON, nullable=True)

    broker_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    broker = relationship("UserModel", back_populates="properties")


class PropertyInterest(Base):
    """
    A user tapping "Interested" on a broker's listing. One row is the record of
    the mutual contact exchange: the broker sees it as an enquiry (with the
    user's contact), the user is handed the broker's contact in response.
    """
    __tablename__ = "property_interests"
    __table_args__ = (
        UniqueConstraint("property_id", "user_id", name="uq_interest_property_user"),
    )

    id = Column(Integer, primary_key=True, index=True)
    property_id = Column(Integer, ForeignKey("properties.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    broker_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    property = relationship("PropertyModel")
    user = relationship("UserModel", foreign_keys=[user_id])
    broker = relationship("UserModel", foreign_keys=[broker_id])

# class PushSubscriptionModel(Base):
#     __tablename__ = "push_subscriptions"

#     id = Column(Integer, primary_key=True, index=True)
#     user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
#     subscription_data = Column(JSON, nullable=False)