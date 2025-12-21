# Core Module - Shared configurations and utilities
from .config import settings, get_settings
from .database import db, client
from .auth import (
    get_current_user, 
    require_roles, 
    hash_password, 
    verify_password,
    create_token,
    decode_token
)
from .audit import create_audit_log, safe_dict_for_audit
from .models import UserRole, ReservationStatus
from .validators import validate_status_transition, validate_reservation_data
from .exceptions import (
    GastroCoreException,
    UnauthorizedException,
    ForbiddenException,
    NotFoundException,
    ValidationException,
    ConflictException
)

__all__ = [
    'settings', 'get_settings', 'db', 'client',
    'get_current_user', 'require_roles', 'hash_password', 'verify_password',
    'create_token', 'decode_token',
    'create_audit_log', 'safe_dict_for_audit',
    'UserRole', 'ReservationStatus',
    'validate_status_transition', 'validate_reservation_data',
    'GastroCoreException', 'UnauthorizedException', 'ForbiddenException',
    'NotFoundException', 'ValidationException', 'ConflictException'
]
