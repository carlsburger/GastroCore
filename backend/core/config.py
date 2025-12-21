"""
Configuration Management - All configurable values in one place
Loads from environment and database settings
"""
from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional, Dict, Any
from functools import lru_cache
import os
from pathlib import Path
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).parent.parent
load_dotenv(ROOT_DIR / '.env')


class Settings(BaseSettings):
    """Application settings loaded from environment"""
    
    # Database
    MONGO_URL: str = Field(default="mongodb://localhost:27017")
    DB_NAME: str = Field(default="gastrocore")
    
    # Security
    JWT_SECRET: str = Field(default="change-me-in-production")
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_HOURS: int = 24
    
    # CORS
    CORS_ORIGINS: str = "*"
    
    # SMTP
    SMTP_HOST: str = ""
    SMTP_PORT: int = 465
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = ""
    SMTP_FROM_NAME: str = "GastroCore"
    
    # App
    APP_URL: str = "http://localhost:3000"
    APP_NAME: str = "GastroCore"
    
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
