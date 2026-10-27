import hashlib
import secrets
import hmac
import time
import json
import base64
import re
from fastapi import HTTPException, Security, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from backend.app.database import get_db
from backend.app.models_db import User

SECRET_KEY = "neuroscope_clinical_researcher_secret_key_2026_salt_token"
security = HTTPBearer(auto_error=False)

def hash_password(password: str) -> str:
    """Hash password using PBKDF2-HMAC-SHA256 with cryptographically secure random salt."""
    salt = secrets.token_hex(16)
    pw_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 100000).hex()
    return f"{salt}${pw_hash}"

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against salt and hash using constant-time comparison."""
    try:
        salt, expected_hash = hashed_password.split('$', 1)
        actual_hash = hashlib.pbkdf2_hmac('sha256', plain_password.encode('utf-8'), salt.encode('utf-8'), 100000).hex()
        return hmac.compare_digest(actual_hash, expected_hash)
    except Exception:
        return False

def validate_password_strength(password: str) -> tuple[bool, str]:
    """
    Password requirements:
    - Minimum 9 characters (length greater than 8).
    - At least one uppercase letter.
    - At least one lowercase letter.
    - At least one number.
    - At least one special character.
    """
    if len(password) < 9:
        return False, "Password must be at least 9 characters long."
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter."
    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter."
    if not re.search(r'\d', password):
        return False, "Password must contain at least one numeric digit."
    if not re.search(r'[!@#$%^&*(),.?":{}|<>_\-+=\[\]\\\/`~;]', password):
        return False, "Password must contain at least one special character (e.g. !@#$%^&*)."
    return True, ""

def create_access_token(user_id: int, email: str, name: str) -> str:
    """Create a signed HMAC-SHA256 session token valid for 7 days."""
    payload = {
        "user_id": user_id,
        "email": email,
        "name": name,
        "exp": int(time.time()) + (86400 * 7)
    }
    payload_bytes = json.dumps(payload).encode('utf-8')
    b64_payload = base64.urlsafe_b64encode(payload_bytes).decode('utf-8').rstrip('=')
    sig = hmac.new(SECRET_KEY.encode('utf-8'), b64_payload.encode('utf-8'), hashlib.sha256).hexdigest()
    return f"{b64_payload}.{sig}"

def verify_access_token(token: str) -> dict | None:
    """Validate signed token and return payload if valid and not expired."""
    try:
        if not token or '.' not in token:
            return None
        b64_payload, sig = token.split('.', 1)
        expected_sig = hmac.new(SECRET_KEY.encode('utf-8'), b64_payload.encode('utf-8'), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected_sig):
            return None
        
        # Add base64 padding
        padding = 4 - (len(b64_payload) % 4)
        if padding != 4:
            b64_payload += '=' * padding
        
        payload = json.loads(base64.urlsafe_b64decode(b64_payload.encode('utf-8')).decode('utf-8'))
        if payload.get("exp", 0) < time.time():
            return None
        return payload
    except Exception:
        return None

def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials = Security(security),
    db: Session = Depends(get_db)
) -> User | None:
    """Extract authenticated user if Authorization Bearer header is present."""
    if not credentials or not credentials.credentials:
        return None
    payload = verify_access_token(credentials.credentials)
    if not payload:
        return None
    user = db.query(User).filter(User.id == payload.get("user_id")).first()
    return user

def get_current_user_required(
    credentials: HTTPAuthorizationCredentials = Security(security),
    db: Session = Depends(get_db)
) -> User:
    """Enforce authentication on protected routes."""
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token required to access protected clinical workspace.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = verify_access_token(credentials.credentials)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session has expired or token signature is invalid. Please sign in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = db.query(User).filter(User.id == payload.get("user_id")).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Researcher account associated with this token not found.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user
