"""
Database connection management
"""
from motor.motor_asyncio import AsyncIOMotorClient
from .config import settings

# MongoDB connection - singleton
client = AsyncIOMotorClient(settings.MONGO_URL)
db = client[settings.DB_NAME]

async def close_db_connection():
    """Close database connection"""
    client.close()

async def check_db_connection() -> bool:
    """Check if database is accessible"""
    try:
        await client.admin.command('ping')
        return True
    except Exception:
        return False
