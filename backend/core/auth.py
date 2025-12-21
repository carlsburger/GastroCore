"""
Authentication and Authorization
"""
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from datetime import datetime, timezone, timedelta
from typing import List
import jwt
import bcrypt

from .config import settings
from .database import db
from .models import UserRole
from .exceptions import UnauthorizedException, ForbiddenException

security = HTTPBearer()


def hash_password(password: str) -> str:
    """Hash a password using bcrypt"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def verify_password(password: str, hashed: str) -> bool:
    """Verify a password against its hash"""
    try:
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    except Exception:
        return False


def create_token(user_id: str, email: str, role: str) -> str:
    """Create a JWT token for a user"""
    payload = {
        "sub": user_id,
        "email": email,
        "role": role,
        "exp": datetime.now(timezone.utc) + timedelta(hours=settings.JWT_EXPIRATION_HOURS),
        "iat": datetime.now(timezone.utc)
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    """Decode and validate a JWT token"""
    try:
        return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise UnauthorizedException("Token abgelaufen")
    except jwt.InvalidTokenError:
        raise UnauthorizedException("Ungültiges Token")


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """
    Get the current authenticated user from the JWT token.
    This is the primary authentication dependency.
    """
    payload = decode_token(credentials.credentials)
    
    user = await db.users.find_one(
        {"id": payload["sub"], "archived": False},
        {"_id": 0}
    )
    
    if not user:
        raise UnauthorizedException("Benutzer nicht gefunden")
    
    if not user.get("is_active", True):
        raise UnauthorizedException("Konto deaktiviert")
    
    return user


def require_roles(*roles: UserRole):
    """
    Dependency factory for role-based access control.
    Returns a dependency that checks if the user has one of the required roles.
    
    Usage:
        @router.get("/admin-only")
        async def admin_endpoint(user = Depends(require_roles(UserRole.ADMIN))):
            ...
    """
    async def role_checker(user: dict = Depends(get_current_user)):
        user_role = user.get("role")
        allowed_roles = [r.value for r in roles]
        
        if user_role not in allowed_roles:
            raise ForbiddenException(
                f"Diese Aktion erfordert eine der folgenden Rollen: {', '.join(allowed_roles)}"
            )
        
        return user
    
    return role_checker


# Convenience dependencies for common role checks
require_admin = require_roles(UserRole.ADMIN)
require_manager = require_roles(UserRole.ADMIN, UserRole.SCHICHTLEITER)


def can_user_access_resource(user: dict, resource_owner_id: str = None) -> bool:
    """
    Check if a user can access a specific resource.
    Admins can access everything, others can only access their own resources.
    """
    if user.get("role") == UserRole.ADMIN.value:
        return True
    
    if resource_owner_id and user.get("id") == resource_owner_id:
        return True
    
    return False
