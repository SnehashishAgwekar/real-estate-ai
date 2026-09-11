import os

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from typing import Optional
from email_validator import validate_email, EmailNotValidError, EmailUndeliverableError
from app.database.connection import get_db
from app.database.models import UserModel
from app.core.security import get_password_hash, verify_password, create_access_token, get_current_user

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


class ProfileOut(BaseModel):
    id: int
    name: str
    email: str
    phone_number: Optional[str] = None
    role: str

    class Config:
        from_attributes = True


@router.get("/me", response_model=ProfileOut)
def get_me(current_user: UserModel = Depends(get_current_user)):
    """The signed-in user's own profile — backs the 'Profile Details' tab
    and fills in what /login doesn't return (name, phone)."""
    return current_user


class UpdateLoginDetailsRequest(BaseModel):
    name: Optional[str] = None
    phone_number: Optional[str] = None


@router.put("/me", response_model=ProfileOut)
def update_me(
    payload: UpdateLoginDetailsRequest,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """'Edit Login Details': name and phone number. Email is intentionally
    not editable here (it's the login identity)."""
    if payload.name is not None:
        name = payload.name.strip()
        if not name:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Name cannot be empty")
        current_user.name = name
    if payload.phone_number is not None:
        current_user.phone_number = payload.phone_number.strip() or None
    db.commit()
    db.refresh(current_user)
    return current_user


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


@router.post("/change-password")
def change_password(
    payload: ChangePasswordRequest,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not verify_password(payload.current_password, current_user.hashed_password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect")
    if len(payload.new_password) < 6:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="New password must be at least 6 characters")
    current_user.hashed_password = get_password_hash(payload.new_password)
    db.commit()
    return {"detail": "Password updated successfully"}
