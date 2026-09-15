import json
import re
from difflib import SequenceMatcher
from typing import Dict, List, Optional, Tuple

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.database.models import PropertyModel, PropertyInterest, UserModel
from app.core.security import get_current_user
from app.core.storage import ALLOWED_IMAGE_TYPES, delete_uploaded_image, save_upload_image

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
    listing_type: str = Form("Sale", pattern="^(Sale|Rent)$"),
    security_deposit: Optional[float] = Form(None, ge=0),
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
        listing_type=listing_type,
        # Deposit only makes sense for a rental; ignore it on a sale listing
        # even if the form sent one.
        security_deposit=security_deposit if listing_type == "Rent" else None,
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
    except IntegrityError as exc:
        db.rollback()
        message = str(getattr(exc, "orig", exc)).lower()
        if "source_url" in message:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A listing with this source URL already exists",
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not save the listing: the data violates a database constraint.",
        )
    db.refresh(new_property)
    return new_property


def _get_own_listing(property_id: int, current_user: UserModel, db: Session) -> PropertyModel:
    prop = db.query(PropertyModel).filter(PropertyModel.id == property_id).first()
    if prop is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Listing not found")
    if prop.broker_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only manage your own listings",
        )
    return prop


@router.put("/listings/{property_id}")
def update_listing(
    property_id: int,
    property_name: str = Form(..., min_length=1, max_length=255),
    city: str = Form(..., min_length=1, max_length=100),
    location: str = Form(..., min_length=1, max_length=255),
    price_in_inr: float = Form(..., gt=0),
    area_sqft: float = Form(..., gt=0),
    property_type: str = Form("Apartment", min_length=1, max_length=50),
    listing_type: str = Form("Sale", pattern="^(Sale|Rent)$"),
    security_deposit: Optional[float] = Form(None, ge=0),
    bhk: Optional[int] = Form(None, ge=0, le=50),
    area_unit: str = Form("sqft", max_length=20),
    builder_name: Optional[str] = Form(None, max_length=150),
    amenities: Optional[str] = Form(None),
    availability_status: str = Form("Ready to Move", max_length=50),
    source_url: Optional[str] = Form(None, max_length=500),
    # JSON-encoded array of existing image_urls entries to drop, e.g. '["https://.../a.png"]'
    remove_image_urls: Optional[str] = Form(None),
    # New photos to append alongside whatever wasn't removed
    images: List[UploadFile] = File(default=[]),
    current_user: UserModel = Depends(require_broker),
    db: Session = Depends(get_db),
):
    prop = _get_own_listing(property_id, current_user, db)

    for img in images:
        if img.content_type not in ALLOWED_IMAGE_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported image type: {img.content_type or 'unknown'}. "
                       "Allowed: JPEG, PNG, WebP, GIF.",
            )

    to_remove = set()
    if remove_image_urls:
        try:
            parsed = json.loads(remove_image_urls)
            if not isinstance(parsed, list):
                raise ValueError
            to_remove = set(parsed)
        except (ValueError, TypeError):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="remove_image_urls must be a JSON array of URLs",
            )

    current_images = list(prop.image_urls or [])
    kept_images = [u for u in current_images if u not in to_remove]
    new_image_urls = [save_upload_image(img) for img in images]
    final_images = kept_images + new_image_urls

    if not final_images:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A listing must have at least one photo — add a replacement before removing the last one.",
        )

    prop.property_name = property_name
    prop.city = city
    prop.location = location
    prop.price_in_inr = price_in_inr
    prop.area_sqft = area_sqft
    prop.property_type = property_type
    prop.listing_type = listing_type
    prop.security_deposit = security_deposit if listing_type == "Rent" else None
    prop.bhk = bhk
    prop.area_unit = area_unit
    prop.builder_name = builder_name
    prop.amenities = amenities
    prop.availability_status = availability_status
    prop.source_url = source_url
    prop.image_urls = final_images

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        message = str(getattr(exc, "orig", exc)).lower()
        if "source_url" in message:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A listing with this source URL already exists",
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not save changes: the data violates a database constraint.",
        )
    db.refresh(prop)

    # Only actually delete the removed images' files once the DB write that
    # drops their references has committed successfully.
    for url in current_images:
        if url in to_remove:
            delete_uploaded_image(url)

    return prop


@router.delete("/listings/{property_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_listing(
    property_id: int,
    current_user: UserModel = Depends(require_broker),
    db: Session = Depends(get_db),
):
    """Removes a listing entirely — e.g. once it's sold or rented out.
    Also clears any buyer 'Interested' records against it (their whole
    purpose was pointing at this listing) and cleans up its photos."""
    prop = _get_own_listing(property_id, current_user, db)

    db.query(PropertyInterest).filter(PropertyInterest.property_id == property_id).delete(synchronize_session=False)
    image_urls = list(prop.image_urls or [])
    db.delete(prop)
    db.commit()

    for url in image_urls:
        delete_uploaded_image(url)


# ---------------------------------------------------------------------------
# Buyer-interest assistant: a small, deterministic Q&A helper over the
# broker's own leads data. Deliberately NOT LLM-backed — buyer counts and
# names are read straight out of the DB and templated into the reply, so a
# broker can trust the numbers instead of risking a hallucinated count.
# ---------------------------------------------------------------------------

class AssistantRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=500)


class AssistantResponse(BaseModel):
    reply: str
    property_name: Optional[str] = None
    buyers: List[dict] = []


def _normalize(text: str) -> str:
    return re.sub(r"[^a-z0-9 ]", " ", text.lower()).strip()


# Words that don't help identify a specific listing, so they're ignored on
# both sides when scoring a token-overlap match.
_STOPWORDS = {
    "the", "in", "on", "at", "for", "of", "a", "an", "my", "is", "are", "was",
    "who", "what", "how", "many", "much", "which", "with", "about", "to",
    "interested", "interest", "buyer", "buyers", "want", "wants", "wanted",
    "show", "tell", "me", "please", "there", "any", "and", "property",
}


def _best_property_match(question: str, properties: List[PropertyModel]) -> Optional[PropertyModel]:
    """Fuzzy-match a property the broker mentioned against their own
    listings. Returns None rather than guessing when nothing scores highly
    enough to be a confident match."""
    q = _normalize(question)
    if not q:
        return None
    q_tokens = {t for t in q.split() if len(t) >= 3 and t not in _STOPWORDS}
    best, best_score = None, 0.0
    for p in properties:
        name = _normalize(p.property_name)
        if not name:
            continue
        if name in q:
            # Exact substring containment ("...interested in Skyline
            # Residences") is treated as a near-certain match.
            score = 0.95
        else:
            name_tokens = {t for t in name.split() if len(t) >= 3}
            # How much of the property's own name shows up in the question
            # (handles a partial mention like "Skyline" for "Skyline
            # Residences"), combined with a general fuzzy-typo ratio.
            overlap = (len(name_tokens & q_tokens) / len(name_tokens)) if name_tokens else 0.0
            score = max(overlap, SequenceMatcher(None, name, q).ratio())
        if score > best_score:
            best, best_score = p, score
    return best if best_score >= 0.5 else None


def _buyer_payload(pairs: List[Tuple[PropertyInterest, UserModel]]) -> List[dict]:
    return [
        {
            "name": u.name,
            "email": u.email,
            "phone": u.phone_number,
            "message": i.message,
            "created_at": i.created_at,
        }
        for (i, u) in pairs
    ]


@router.post("/assistant", response_model=AssistantResponse)
def broker_assistant(
    payload: AssistantRequest,
    current_user: UserModel = Depends(require_broker),
    db: Session = Depends(get_db),
):
    """
    Answers a broker's question about buyer interest in their own listings —
    "how many buyers are interested in Skyline Residences?", "who wants my
    Vijay Nagar plot?", "which listing has the most interest?", or a general
    "how many enquiries do I have?".
    """
    properties = (
        db.query(PropertyModel)
        .filter(PropertyModel.broker_id == current_user.id)
        .all()
    )
    if not properties:
        return AssistantResponse(
            reply="You don't have any listings yet, so there's no buyer interest to report."
        )

    rows = (
        db.query(PropertyInterest, UserModel)
        .join(UserModel, PropertyInterest.user_id == UserModel.id)
        .filter(PropertyInterest.broker_id == current_user.id)
        .order_by(PropertyInterest.created_at.desc())
        .all()
    )
    by_property: Dict[int, List[Tuple[PropertyInterest, UserModel]]] = {}
    for interest, user in rows:
        by_property.setdefault(interest.property_id, []).append((interest, user))

    matched = _best_property_match(payload.message, properties)

    if matched is not None:
        pairs = by_property.get(matched.id, [])
        if not pairs:
            reply = f'No one has shown interest in "{matched.property_name}" yet.'
        else:
            names = ", ".join(u.name for _, u in pairs[:5])
            more = f" and {len(pairs) - 5} more" if len(pairs) > 5 else ""
            verb = "is" if len(pairs) == 1 else "are"
            plural = "" if len(pairs) == 1 else "s"
            reply = (
                f'{len(pairs)} buyer{plural} {verb} interested in '
                f'"{matched.property_name}": {names}{more}.'
            )
        return AssistantResponse(reply=reply, property_name=matched.property_name, buyers=_buyer_payload(pairs))

    q_lower = payload.message.lower()
    total = len(rows)

    if any(w in q_lower for w in ("most", "top", "highest", "popular")):
        if total == 0:
            return AssistantResponse(reply="None of your listings have any buyer interest yet.")
        top_id, top_pairs = max(by_property.items(), key=lambda kv: len(kv[1]))
        top_prop = next(p for p in properties if p.id == top_id)
        return AssistantResponse(
            reply=f'"{top_prop.property_name}" has the most interest — {len(top_pairs)} buyer(s).',
            property_name=top_prop.property_name,
            buyers=_buyer_payload(top_pairs),
        )

    # No specific property recognized and no "top listing" question — give a
    # per-listing breakdown so the broker can see what to ask about next.
    if total == 0:
        return AssistantResponse(reply="No one has shown interest in any of your listings yet.")

    lines = [f"{p.property_name} — {len(by_property[p.id])}" for p in properties if by_property.get(p.id)]
    summary = "; ".join(lines) if lines else "no interest yet on any listing"
    plural = "" if total == 1 else "s"
    return AssistantResponse(
        reply=(
            f"You have {total} buyer{plural} interested across your listings: {summary}. "
            "Ask me about a specific property by name for buyer details."
        ),
    )
