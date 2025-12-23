"""
Extended Enums and Models for Sprint 2
"""
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Dict, Any
from datetime import datetime, timezone
import uuid


class UserRole(str, Enum):
    """User roles with hierarchical permissions"""
    ADMIN = "admin"
    SCHICHTLEITER = "schichtleiter"
    SERVICE = "service"  # Kellner - nur Service-Terminal Zugang
    MITARBEITER = "mitarbeiter"
    
    @classmethod
    def can_manage_reservations(cls, role: str) -> bool:
        """Wer darf Reservierungen verwalten (Status ändern, Walk-ins, etc.)"""
        return role in [cls.ADMIN.value, cls.SCHICHTLEITER.value, cls.SERVICE.value]
    
    @classmethod
    def can_access_backoffice(cls, role: str) -> bool:
        """Wer darf ins Admin-Cockpit (Einstellungen, Mitarbeiter, etc.)"""
        return role in [cls.ADMIN.value, cls.SCHICHTLEITER.value]
    
    @classmethod
    def can_access_terminal(cls, role: str) -> bool:
        """Wer darf das Service-Terminal nutzen"""
        return role in [cls.ADMIN.value, cls.SCHICHTLEITER.value, cls.SERVICE.value]
    
    @classmethod
    def can_access_admin(cls, role: str) -> bool:
        """Wer darf Admin-Bereiche (Einstellungen, System) nutzen"""
        return role == cls.ADMIN.value
    
    @classmethod
    def is_service_only(cls, role: str) -> bool:
        """Ist der Benutzer nur Service (kein Admin/Backoffice Zugang)"""
        return role == cls.SERVICE.value


class ReservationStatus(str, Enum):
    """Reservation status with strict workflow"""
    NEU = "neu"
    BESTAETIGT = "bestaetigt"
    ANGEKOMMEN = "angekommen"
    ABGESCHLOSSEN = "abgeschlossen"
    NO_SHOW = "no_show"
    STORNIERT = "storniert"
    
    @classmethod
    def is_terminal(cls, status: str) -> bool:
        return status in [cls.ABGESCHLOSSEN.value, cls.NO_SHOW.value, cls.STORNIERT.value]
    
    @classmethod
    def is_active(cls, status: str) -> bool:
        return status in [cls.NEU.value, cls.BESTAETIGT.value, cls.ANGEKOMMEN.value]
    
    @classmethod
    def can_cancel(cls, status: str) -> bool:
        return status in [cls.NEU.value, cls.BESTAETIGT.value]


class WaitlistStatus(str, Enum):
    """Waitlist entry status"""
    OFFEN = "offen"
    INFORMIERT = "informiert"
    EINGELOEST = "eingeloest"
    ERLEDIGT = "erledigt"


class GuestFlag(str, Enum):
    """Guest flag for no-show management"""
    NONE = "none"
    GREYLIST = "greylist"
    BLACKLIST = "blacklist"


class ReservationSource(str, Enum):
    """Source of reservation"""
    WIDGET = "widget"
    INTERN = "intern"
    WALK_IN = "walk-in"
    WAITLIST = "waitlist"
    PHONE = "phone"


class AuditAction(str, Enum):
    """Audit log action types"""
    CREATE = "create"
    UPDATE = "update"
    ARCHIVE = "archive"
    STATUS_CHANGE = "status_change"
    PASSWORD_CHANGE = "password_change"
    LOGIN = "login"
    CANCEL_BY_GUEST = "cancel_by_guest"


def serialize_for_db(obj: dict) -> dict:
    """Convert datetime fields to ISO strings for MongoDB storage"""
    result = obj.copy()
    for key, value in result.items():
        if isinstance(value, datetime):
            result[key] = value.isoformat()
    return result
