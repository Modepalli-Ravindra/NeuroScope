from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.app.database import get_db
from backend.app.models_db import User
from backend.app.schemas import UserRegisterRequest, UserLoginRequest, UserResponse
from backend.app.utils.auth import (
    hash_password,
    verify_password,
    validate_password_strength,
    create_access_token,
    get_current_user_required
)

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register_researcher(req: UserRegisterRequest, db: Session = Depends(get_db)):
    """Register a new clinical researcher account with real password hashing and verification."""
    clean_name = req.name.strip()
    clean_institution = (req.institution or "Independent Research").strip() or "Independent Research"
    clean_email = req.email.strip().lower()

    if not clean_name:
        raise HTTPException(status_code=400, detail="Researcher Name is required.")
    if not clean_email or "@" not in clean_email:
        raise HTTPException(status_code=400, detail="A valid email address is required.")

    # 1. Check passwords match
    if req.password != req.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match. Please re-enter matching passwords.")

    # 2. Check password policy
    is_valid, msg = validate_password_strength(req.password)
    if not is_valid:
        raise HTTPException(status_code=400, detail=msg)

    # 3. Check duplicate email
    existing_user = db.query(User).filter(User.email == clean_email).first()
    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="A researcher account with this email address already exists. Please sign in or use a different address."
        )

    # 4. Hash password and persist
    hashed = hash_password(req.password)
    new_user = User(
        name=clean_name,
        institution=clean_institution,
        email=clean_email,
        hashed_password=hashed
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    token = create_access_token(new_user.id, new_user.email, new_user.name)

    return UserResponse(
        id=new_user.id,
        name=new_user.name,
        institution=new_user.institution,
        email=new_user.email,
        token=token
    )

@router.post("/login", response_model=UserResponse)
def login_researcher(req: UserLoginRequest, db: Session = Depends(get_db)):
    """Authenticate researcher credentials against SQLite hash."""
    clean_email = req.email.strip().lower()
    if not clean_email or not req.password:
        raise HTTPException(status_code=400, detail="Email and password are both required.")

    user = db.query(User).filter(User.email == clean_email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials. No researcher account found with this email."
        )

    if not verify_password(req.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials. Incorrect password."
        )

    token = create_access_token(user.id, user.email, user.name)

    return UserResponse(
        id=user.id,
        name=user.name,
        institution=user.institution,
        email=user.email,
        token=token
    )

@router.get("/me")
def get_authenticated_researcher(current_user: User = Depends(get_current_user_required)):
    """Return currently authenticated researcher profile."""
    return {
        "id": current_user.id,
        "name": current_user.name,
        "institution": current_user.institution,
        "email": current_user.email,
        "created_at": current_user.created_at.strftime("%Y-%m-%d %H:%M:%S") if current_user.created_at else None
    }
