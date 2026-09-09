import os

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from typing import Optional
from email_validator import validate_email, EmailNotValidError, EmailUndeliverableError
from app.database.connection import get_db
from app.database.models import UserModel
from app.core.security import get_password_hash, verify_password, create_access_token

router = APIRouter()

# Set SKIP_EMAIL_DELIVERABILITY_CHECK=1 to bypass the DNS lookup (e.g. offline dev).
_SKIP_DELIVERABILITY = os.getenv("SKIP_EMAIL_DELIVERABILITY_CHECK", "").lower() in ("1", "true", "yes")


def verify_email_deliverable(email: str) -> str:
    """
    Confirm the email's domain can actually receive mail (has MX / A records),
    rejecting made-up domains at signup. Returns the normalized address.
    Does not prove the individual mailbox exists.
    """
    try:
        result = validate_email(email, check_deliverability=not _SKIP_DELIVERABILITY)
        return result.normalized
    except EmailUndeliverableError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This email address doesn't exist. Please use a real, reachable email.",
        )
    except EmailNotValidError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please enter a valid email address.",
        )


class SignupRequest(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: str
    phone_number: Optional[str] = None

@router.post("/signup", status_code=status.HTTP_201_CREATED)
def signup(user_data: SignupRequest, db: Session = Depends(get_db)):
    email = verify_email_deliverable(user_data.email)

    existing_user = db.query(UserModel).filter(UserModel.email == email).first()
    if existing_user:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email is already registered")

    hashed_pw = get_password_hash(user_data.password)
    new_user = UserModel(
        name=user_data.name,
        email=email,
        hashed_password=hashed_pw,
        role=user_data.role,
        phone_number=user_data.phone_number
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    token = create_access_token(data={"sub": str(new_user.id), "role": new_user.role})
    return {"access_token": token, "token_type": "bearer", "role": new_user.role}

@router.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    # OAuth2PasswordRequestForm strictly uses the field name 'username'. We map this to our email column.
    user = db.query(UserModel).filter(UserModel.email == form_data.username).first()

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"}
        )

    token = create_access_token(data={"sub": str(user.id), "role": user.role})
    return {"access_token": token, "token_type": "bearer", "role": user.role}
