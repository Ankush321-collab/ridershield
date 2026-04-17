"""
JWT Authentication middleware — imported by ALL services.

Usage:
    from shared.auth import get_current_rider, require_admin

    # Protect rider endpoints
    @router.get("/api/riders/me")
    async def get_me(rider = Depends(get_current_rider)):
        return rider

    # Protect admin endpoints
    @router.get("/api/admin/claims")
    async def admin_claims(admin = Depends(require_admin)):
        ...
"""

from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.config import settings
from shared.database import get_db

security = HTTPBearer()


# ─── Token Creation ─────────────────────────────────

def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """
    Create a JWT token.
    
    Args:
        data: payload — must include "sub" (rider_id) and "role" ("rider" or "admin")
        expires_delta: optional custom expiry
    
    Returns:
        Encoded JWT string
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_temp_token(phone: str) -> str:
    """Short-lived token for registration flow (10 min)."""
    return create_access_token(
        data={"sub": phone, "role": "temp"},
        expires_delta=timedelta(minutes=10),
    )


# ─── Token Verification ─────────────────────────────

def verify_token(token: str) -> dict:
    """Decode and verify a JWT token. Returns the payload."""
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "TOKEN_INVALID", "message": "Invalid or expired token"},
        )


# ─── FastAPI Dependencies ───────────────────────────

async def get_current_rider(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
):
    """
    Dependency: extracts rider from JWT token.
    Returns the rider ORM object.
    Raises 401 if token is invalid or rider not found.
    """
    payload = verify_token(credentials.credentials)
    rider_id = payload.get("sub")
    role = payload.get("role")

    if not rider_id or role not in ("rider", "admin"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "TOKEN_INVALID", "message": "Invalid token payload"},
        )

    try:
        rider_uuid = UUID(rider_id) if isinstance(rider_id, str) else rider_id
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "TOKEN_INVALID", "message": "Invalid rider ID format"},
        )

    # Lazy import to avoid circular dependency
    from rider_service.models import Rider

    result = await db.execute(select(Rider).where(Rider.id == rider_uuid))
    rider = result.scalar_one_or_none()

    if not rider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "RIDER_NOT_FOUND", "message": "Rider not found"},
        )

    return rider


async def require_admin(
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    """
    Dependency: verifies the caller is an admin.
    Returns the admin payload dict.
    Raises 403 if not admin.
    """
    payload = verify_token(credentials.credentials)
    role = payload.get("role")

    if role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "ADMIN_UNAUTHORIZED", "message": "Admin access required"},
        )

    return payload
