from typing import List, Optional

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.database.models import PropertyModel, PropertyInterest, UserModel
from app.core.security import get_current_user
from app.core.storage import ALLOWED_IMAGE_TYPES, save_upload_image

router = APIRouter()


def require_broker(current_user: UserModel = Depends(get_current_user)) -> UserModel:
    """Auth dependency that also enforces the caller is a broker."""
    if current_user.role != "broker":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only registered brokers can access the broker dashboard",
        )
    return current_user


@router.get("/my-listings")
def get_broker_listings(current_user: UserModel = Depends(require_broker), db: Session = Depends(get_db)):
    return (
        db.query(PropertyModel)
        .filter(PropertyModel.broker_id == current_user.id)
        .order_by(PropertyModel.created_at.desc())
        .all()
    )


@router.get("/leads")
def get_broker_leads(current_user: UserModel = Depends(require_broker), db: Session = Depends(get_db)):
    """
    Enquiries: every user who tapped "Interested" on one of this broker's
    listings, with that user's contact details.
    """
    rows = (
        db.query(PropertyInterest, PropertyModel, UserModel)
        .join(PropertyModel, PropertyInterest.property_id == PropertyModel.id)
        .join(UserModel, PropertyInterest.user_id == UserModel.id)
        .filter(PropertyInterest.broker_id == current_user.id)
        .order_by(PropertyInterest.created_at.desc())
        .all()
    )
    return [
        {
            "interest_id": interest.id,
            "created_at": interest.created_at,
            "message": interest.message,
            "property_id": prop.id,
            "property_name": prop.property_name,
            "city": prop.city,
            "location": prop.location,
            "user": {"name": user.name, "email": user.email, "phone": user.phone_number},
        }
        for (interest, prop, user) in rows
    ]


@router.post("/listings", status_code=status.HTTP_201_CREATED)
def create_listing(
    property_name: str = Form(..., min_length=1, max_length=255),
    city: str = Form(..., min_length=1, max_length=100),
    location: str = Form(..., min_length=1, max_length=255),
    price_in_inr: float = Form(..., gt=0),
    area_sqft: float = Form(..., gt=0),
    property_type: str = Form("Apartment", min_length=1, max_length=50),
    bhk: Optional[int] = Form(None, ge=0, le=50),
    area_unit: str = Form("sqft", max_length=20),
    builder_name: Optional[str] = Form(None, max_length=150),
    amenities: Optional[str] = Form(None),
    availability_status: str = Form("Ready to Move", max_length=50),
    source_url: Optional[str] = Form(None, max_length=500),
    images: List[UploadFile] = File(...),
    current_user: UserModel = Depends(require_broker),
    db: Session = Depends(get_db),
):
    # Reject anything that isn't an accepted image type before writing to disk
    for img in images:
        if img.content_type not in ALLOWED_IMAGE_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported image type: {img.content_type or 'unknown'}. "
                       "Allowed: JPEG, PNG, WebP, GIF.",
            )

    # Persist the binaries to backend/static/uploads/ and collect their URLs
    image_urls = [save_upload_image(img) for img in images]

    new_property = PropertyModel(
        property_name=property_name,
        city=city,
        location=location,
        price_in_inr=price_in_inr,
        area_sqft=area_sqft,
        property_type=property_type,
        bhk=bhk,
        area_unit=area_unit,
        builder_name=builder_name,
        amenities=amenities,
        availability_status=availability_status,
        source_url=source_url,
        image_urls=image_urls,
        source="broker_dashboard",
        broker_id=current_user.id,
    )
    db.add(new_property)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A listing with this source URL already exists",
        )
    db.refresh(new_property)
    return new_property
