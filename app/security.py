from datetime import datetime, timedelta, timezone
import base64
import hashlib
import uuid

import bcrypt
import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from .config import settings
from .database import get_db
from .models import User


bearer = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    # Pre-hashing avoids bcrypt's 72-byte input truncation while preserving its work factor.
    prepared = base64.b64encode(hashlib.sha256(password.encode()).digest())
    return "bcrypt-sha256$" + bcrypt.hashpw(prepared, bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    if password_hash.startswith("bcrypt-sha256$"):
        prepared = base64.b64encode(hashlib.sha256(password.encode()).digest())
        password_hash = password_hash.removeprefix("bcrypt-sha256$")
    else:
        prepared = password.encode()
    return bcrypt.checkpw(prepared, password_hash.encode())


def create_token(user: User) -> str:
    expires = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_minutes)
    return jwt.encode({"sub": str(user.id), "role": user.role.value, "sv": user.session_version, "exp": expires}, settings.secret_key, algorithm="HS256")


def current_user(request: Request, credentials: HTTPAuthorizationCredentials | None = Depends(bearer), db: Session = Depends(get_db)) -> User:
    token = credentials.credentials if credentials else request.cookies.get("opensurgery_session")
    if not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Authentication required")
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
        user_id = uuid.UUID(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token")
    user = db.get(User, user_id)
    # Tokens issued before session-versioning was deployed implicitly belong to
    # version zero. This preserves existing sessions through the migration while
    # still revoking them as soon as a password reset increments the version.
    if not user or not user.is_active or user.deleted_at or payload.get("sv", 0) != user.session_version:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Account unavailable")
    return user
