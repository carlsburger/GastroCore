"""
Configuration Management - All configurable values in one place
Loads from environment and database settings
"""
from pydantic_settings import BaseSettings
from pydantic import Field, field_validator
from typing import Optional, Dict, Any
from functools import lru_cache
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).parent.parent
load_dotenv(ROOT_DIR / '.env')


class Settings(BaseSettings):
    """Application settings loaded from environment"""
    
    # Database - KEIN LOCALHOST FALLBACK!
    # MONGO_URL MUSS in .env gesetzt sein
    MONGO_URL: str = Field(...)  # Required - kein Default!
    DB_NAME: str = Field(default="gastrocore")
    
    # ATLAS-GUARD: Wenn true, nur mongodb+srv:// oder .mongodb.net erlaubt
    REQUIRE_ATLAS: bool = Field(default=False)
    
    # AUTO-RESTORE Control
    AUTO_RESTORE_ENABLED: bool = Field(default=False)
    
    # Security - KRITISCH: MUSS aus .env kommen!
    # KEINE automatische Generierung, KEINE unsicheren Defaults
    JWT_SECRET: str = Field(...)  # Required - kein Default!
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_HOURS: int = 24
    
    # Optional: Encryption Key für sensible Daten
    ENCRYPTION_KEY: str = Field(default="")
    
    # CORS
    CORS_ORIGINS: str = "*"
    
    # SMTP
    SMTP_HOST: str = ""
    SMTP_PORT: int = 465
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = ""
    SMTP_FROM_NAME: str = "Carlsburg Cockpit"
    
    # App
    APP_URL: str = "http://localhost:3000"
    APP_NAME: str = "Carlsburg Cockpit"
    
    # Reservation Limits (configurable)
    MAX_PARTY_SIZE: int = 20
    MIN_PARTY_SIZE: int = 1
    RESERVATION_ADVANCE_DAYS: int = 90  # How far in advance can book
    
    # Status Workflow - Define allowed transitions
    STATUS_TRANSITIONS: Dict[str, list] = {
        "neu": ["bestaetigt", "storniert", "no_show"],
        "bestaetigt": ["angekommen", "storniert", "no_show"],
        "angekommen": ["abgeschlossen", "no_show"],
        "abgeschlossen": [],  # Terminal state
        "no_show": [],  # Terminal state
        "storniert": []  # Terminal state
    }
    
    @field_validator('JWT_SECRET')
    @classmethod
    def validate_jwt_secret(cls, v: str) -> str:
        """Verhindere unsichere JWT_SECRET Werte"""
        unsafe_values = ['change-me', 'change-me-in-production', 'secret', 'jwt-secret', '']
        if v.lower() in unsafe_values or len(v) < 16:
            print("=" * 60, file=sys.stderr)
            print("KRITISCHER FEHLER: JWT_SECRET ist nicht sicher konfiguriert!", file=sys.stderr)
            print("Bitte setzen Sie einen sicheren Wert in /app/backend/.env", file=sys.stderr)
            print("Mindestlänge: 16 Zeichen", file=sys.stderr)
            print("=" * 60, file=sys.stderr)
            sys.exit(1)
        return v
    
    @field_validator('MONGO_URL')
    @classmethod
    def validate_mongo_url(cls, v: str, info) -> str:
        """ATLAS-GUARD: Prüfe MongoDB-URI gegen REQUIRE_ATLAS"""
        # Hinweis: REQUIRE_ATLAS wird separat aus ENV gelesen da Validierung früh läuft
        require_atlas = os.getenv("REQUIRE_ATLAS", "false").lower() == "true"
        
        is_atlas = "mongodb+srv://" in v or ".mongodb.net" in v
        is_localhost = "localhost" in v or "127.0.0.1" in v
        
        if require_atlas:
            if is_localhost:
                print("=" * 60, file=sys.stderr)
                print("ATLAS-GUARD FEHLER: REQUIRE_ATLAS=true aber localhost-URI!", file=sys.stderr)
                print(f"Aktuelle URI beginnt mit: {v[:30]}...", file=sys.stderr)
                print("Bitte Atlas-URI in /app/backend/.env setzen", file=sys.stderr)
                print("=" * 60, file=sys.stderr)
                sys.exit(1)
            
            if not is_atlas:
                print("=" * 60, file=sys.stderr)
                print("ATLAS-GUARD FEHLER: REQUIRE_ATLAS=true aber keine Atlas-URI!", file=sys.stderr)
                print("URI muss 'mongodb+srv://' oder '.mongodb.net' enthalten", file=sys.stderr)
                print("=" * 60, file=sys.stderr)
                sys.exit(1)
        
        return v
    
    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


settings = get_settings()


# Runtime configurable settings (from database)
class RuntimeConfig:
    """Settings that can be changed at runtime via admin UI"""
    _cache: Dict[str, Any] = {}
    
    @classmethod
    async def get(cls, key: str, default: Any = None) -> Any:
        """Get a runtime setting"""
        if key in cls._cache:
            return cls._cache[key]
        return default
    
    @classmethod
    async def set(cls, key: str, value: Any):
        """Set a runtime setting"""
        cls._cache[key] = value
    
    @classmethod
    async def load_from_db(cls, db):
        """Load all settings from database"""
        settings_docs = await db.settings.find({}, {"_id": 0}).to_list(1000)
        for doc in settings_docs:
            cls._cache[doc["key"]] = doc["value"]
    
    @classmethod
    def clear_cache(cls):
        """Clear the settings cache"""
        cls._cache.clear()


runtime_config = RuntimeConfig()
