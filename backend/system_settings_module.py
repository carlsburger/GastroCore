"""
GastroCore System Settings Module
================================================================================
Company Profile & System-Stammdaten

Features:
- Zentrale Konfiguration für Geschäftsdaten
- Legal Name, Adresse, Kontakt, Timezone
- Admin-only Access

ADDITIV - Keine Breaking Changes
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field, EmailStr, field_validator
from typing import Optional
from datetime import datetime, timezone
import uuid
import re

# Core imports
from core.database import db
from core.auth import require_admin, get_current_user
from core.audit import create_audit_log, safe_dict_for_audit
from core.exceptions import NotFoundException, ValidationException

import logging
logger = logging.getLogger(__name__)


# ============== ROUTER ==============
system_settings_router = APIRouter(tags=["System Settings"])


# ============== CONSTANTS ==============
DEFAULT_TIMEZONE = "Europe/Berlin"
VALID_TIMEZONES = [
    "Europe/Berlin", "Europe/Vienna", "Europe/Zurich",
    "Europe/Amsterdam", "Europe/Paris", "Europe/London",
    "UTC"
]


# ============== PYDANTIC MODELS ==============

class SystemSettingsCreate(BaseModel):
    """Initial System Settings"""
    legal_name: str = Field(..., min_length=2, max_length=200)
    address_street: Optional[str] = Field(None, max_length=200)
    address_zip: Optional[str] = Field(None, max_length=20)
    address_city: Optional[str] = Field(None, max_length=100)
    address_country: str = Field(default="Deutschland", max_length=100)
    phone: Optional[str] = Field(None, max_length=50)
    email: Optional[EmailStr] = None
    website: Optional[str] = Field(None, max_length=200)
    timezone: str = Field(default=DEFAULT_TIMEZONE)
    
    @field_validator('phone')
    @classmethod
    def validate_phone(cls, v):
        if v:
            # Erlaubt: +49 123 456789, 0123-456789, etc.
            cleaned = re.sub(r'[\s\-\/\(\)]', '', v)
            if not re.match(r'^\+?[0-9]{6,20}$', cleaned):
                raise ValueError('Ungültiges Telefonnummer-Format')
        return v
    
    @field_validator('timezone')
    @classmethod
    def validate_timezone(cls, v):
        if v not in VALID_TIMEZONES:
            raise ValueError(f'Ungültige Zeitzone. Erlaubt: {VALID_TIMEZONES}')
        return v
    
    @field_validator('website')
    @classmethod
    def validate_website(cls, v):
        if v:
            if not v.startswith(('http://', 'https://')):
                v = 'https://' + v
        return v


class SystemSettingsUpdate(BaseModel):
    """Update System Settings"""
    legal_name: Optional[str] = Field(None, min_length=2, max_length=200)
    address_street: Optional[str] = Field(None, max_length=200)
    address_zip: Optional[str] = Field(None, max_length=20)
    address_city: Optional[str] = Field(None, max_length=100)
    address_country: Optional[str] = Field(None, max_length=100)
    phone: Optional[str] = Field(None, max_length=50)
    email: Optional[EmailStr] = None
    website: Optional[str] = Field(None, max_length=200)
    timezone: Optional[str] = None
    
    @field_validator('phone')
    @classmethod
    def validate_phone(cls, v):
        if v:
            cleaned = re.sub(r'[\s\-\/\(\)]', '', v)
            if not re.match(r'^\+?[0-9]{6,20}$', cleaned):
                raise ValueError('Ungültiges Telefonnummer-Format')
        return v
    
    @field_validator('timezone')
    @classmethod
    def validate_timezone(cls, v):
        if v and v not in VALID_TIMEZONES:
            raise ValueError(f'Ungültige Zeitzone. Erlaubt: {VALID_TIMEZONES}')
        return v


class SystemSettingsResponse(BaseModel):
    """Response Model"""
    id: str
    legal_name: str
    address_street: Optional[str] = None
    address_zip: Optional[str] = None
    address_city: Optional[str] = None
    address_country: str
    phone: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    timezone: str
    created_at: str
    updated_at: str


# ============== HELPER FUNCTIONS ==============

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def get_or_create_system_settings() -> dict:
    """
    Hole System Settings oder erstelle Default-Eintrag.
    Es gibt immer nur EINEN Eintrag (Singleton).
    """
    settings = await db.system_settings.find_one({}, {"_id": 0})
    
    if not settings:
        # Erstelle Default-Eintrag
        settings = {
            "id": str(uuid.uuid4()),
            "legal_name": "Carlsburg Restaurant",
            "address_street": "",
            "address_zip": "",
            "address_city": "",
            "address_country": "Deutschland",
            "phone": "",
            "email": "",
            "website": "",
            "timezone": DEFAULT_TIMEZONE,
            "created_at": now_iso(),
            "updated_at": now_iso()
        }
        await db.system_settings.insert_one(settings)
        logger.info("System Settings: Default-Eintrag erstellt")
    
    return settings


# ============== API ENDPOINTS ==============

@system_settings_router.get(
    "/system/settings",
    response_model=SystemSettingsResponse,
    summary="System-Einstellungen abrufen",
    description="Ruft die zentralen Geschäftsdaten ab. Admin only."
)
async def get_system_settings(current_user: dict = Depends(require_admin)):
    """GET /api/system/settings - Company Profile abrufen"""
    settings = await get_or_create_system_settings()
    return settings


@system_settings_router.put(
    "/system/settings",
    response_model=SystemSettingsResponse,
    summary="System-Einstellungen aktualisieren",
    description="Aktualisiert die zentralen Geschäftsdaten. Admin only."
)
async def update_system_settings(
    data: SystemSettingsUpdate,
    current_user: dict = Depends(require_admin)
):
    """PUT /api/system/settings - Company Profile aktualisieren"""
    
    # Hole aktuellen Stand
    settings = await get_or_create_system_settings()
    old_settings = settings.copy()
    
    # Update nur übergebene Felder
    update_data = data.model_dump(exclude_unset=True)
    if not update_data:
        raise ValidationException("Keine Änderungen übergeben")
    
    update_data["updated_at"] = now_iso()
    
    # Update in DB
    await db.system_settings.update_one(
        {"id": settings["id"]},
        {"$set": update_data}
    )
    
    # Audit Log
    await create_audit_log(
        actor=current_user,
        action="update",
        entity="system_settings",
        entity_id=settings["id"],
        before=safe_dict_for_audit(old_settings),
        after=safe_dict_for_audit(update_data)
    )
    
    # Hole aktualisierten Stand
    updated = await db.system_settings.find_one(
        {"id": settings["id"]},
        {"_id": 0}
    )
    
    logger.info(f"System Settings aktualisiert von {current_user.get('email')}")
    return updated


# ============== PUBLIC HELPER (für andere Module) ==============

async def get_system_timezone() -> str:
    """Hole konfigurierte Zeitzone für andere Module"""
    settings = await get_or_create_system_settings()
    return settings.get("timezone", DEFAULT_TIMEZONE)


async def get_company_info() -> dict:
    """Hole Firmendaten für Dokumente/Emails"""
    settings = await get_or_create_system_settings()
    return {
        "name": settings.get("legal_name", ""),
        "address": f"{settings.get('address_street', '')}, {settings.get('address_zip', '')} {settings.get('address_city', '')}".strip(", "),
        "phone": settings.get("phone", ""),
        "email": settings.get("email", ""),
        "website": settings.get("website", "")
    }
