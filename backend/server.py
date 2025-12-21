from fastapi import FastAPI, APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import List, Optional, Any, Dict
import uuid
from datetime import datetime, timezone, timedelta
import jwt
import bcrypt
from enum import Enum
import json

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# JWT Config
JWT_SECRET = os.environ.get('JWT_SECRET', 'gastrocore-super-secret-key-2024')
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24

# Create the main app
app = FastAPI(title="GastroCore API", version="1.0.0")

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

security = HTTPBearer()

# ============== ENUMS ==============
class UserRole(str, Enum):
    ADMIN = "admin"
    SCHICHTLEITER = "schichtleiter"
    MITARBEITER = "mitarbeiter"

class ReservationStatus(str, Enum):
    NEU = "neu"
    BESTAETIGT = "bestaetigt"
    ANGEKOMMEN = "angekommen"
    ABGESCHLOSSEN = "abgeschlossen"
    NO_SHOW = "no_show"

# ============== MODELS ==============
class UserBase(BaseModel):
    email: EmailStr
    name: str
    role: UserRole

class UserCreate(BaseModel):
    email: EmailStr
    name: str
    password: str
    role: UserRole

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class PasswordChange(BaseModel):
    current_password: str
    new_password: str

class User(UserBase):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    is_active: bool = True
    must_change_password: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    archived: bool = False

class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    role: UserRole
    is_active: bool
    must_change_password: bool
    created_at: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

class AreaBase(BaseModel):
    name: str
    description: Optional[str] = None
    capacity: Optional[int] = None

class AreaCreate(AreaBase):
    pass

class Area(AreaBase):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    archived: bool = False

class ReservationBase(BaseModel):
    guest_name: str
    guest_phone: str
    guest_email: Optional[str] = None
    party_size: int
    date: str  # ISO date string
    time: str  # HH:MM format
    area_id: Optional[str] = None
    notes: Optional[str] = None

class ReservationCreate(ReservationBase):
    pass

class ReservationUpdate(BaseModel):
    guest_name: Optional[str] = None
    guest_phone: Optional[str] = None
    guest_email: Optional[str] = None
    party_size: Optional[int] = None
    date: Optional[str] = None
    time: Optional[str] = None
    area_id: Optional[str] = None
    notes: Optional[str] = None
    status: Optional[ReservationStatus] = None

class Reservation(ReservationBase):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    status: ReservationStatus = ReservationStatus.NEU
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    archived: bool = False

class SettingBase(BaseModel):
    key: str
    value: str
    description: Optional[str] = None

class SettingCreate(SettingBase):
    pass

class Setting(SettingBase):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class AuditLog(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    actor_id: str
    actor_email: str
    entity: str
    entity_id: str
    action: str
    before: Optional[Dict[str, Any]] = None
    after: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# ============== HELPERS ==============
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def create_token(user_id: str, email: str, role: str) -> str:
    payload = {
        "sub": user_id,
        "email": email,
        "role": role,
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRATION_HOURS)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token abgelaufen")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Ungültiges Token")

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    payload = decode_token(credentials.credentials)
    user = await db.users.find_one({"id": payload["sub"], "archived": False}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=401, detail="Benutzer nicht gefunden")
    return user

def require_roles(*roles: UserRole):
    async def role_checker(user: dict = Depends(get_current_user)):
        if user["role"] not in [r.value for r in roles]:
            raise HTTPException(status_code=403, detail="Keine Berechtigung")
        return user
    return role_checker

async def create_audit_log(actor: dict, entity: str, entity_id: str, action: str, before: dict = None, after: dict = None):
    """Create audit log entry for any mutation"""
    audit = AuditLog(
        actor_id=actor["id"],
        actor_email=actor["email"],
        entity=entity,
        entity_id=entity_id,
        action=action,
        before=before,
        after=after
    )
    doc = audit.model_dump()
    doc['timestamp'] = doc['timestamp'].isoformat()
    await db.audit_logs.insert_one(doc)

def serialize_datetime(obj: dict) -> dict:
    """Convert datetime fields to ISO strings for MongoDB"""
    result = obj.copy()
    for key, value in result.items():
        if isinstance(value, datetime):
            result[key] = value.isoformat()
    return result

def safe_dict_for_audit(obj: dict) -> dict:
    """Create a safe dict for audit logging (remove sensitive fields)"""
    if obj is None:
        return None
    result = {k: v for k, v in obj.items() if k not in ['password_hash', '_id']}
    return result

# ============== AUTH ENDPOINTS ==============
@api_router.post("/auth/login", response_model=TokenResponse)
async def login(data: UserLogin):
    user = await db.users.find_one({"email": data.email, "archived": False}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=401, detail="Ungültige Anmeldedaten")
    if not verify_password(data.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Ungültige Anmeldedaten")
    if not user.get("is_active", True):
        raise HTTPException(status_code=401, detail="Konto deaktiviert")
    
    token = create_token(user["id"], user["email"], user["role"])
    
    return TokenResponse(
        access_token=token,
        user=UserResponse(
            id=user["id"],
            email=user["email"],
            name=user["name"],
            role=user["role"],
            is_active=user["is_active"],
            must_change_password=user.get("must_change_password", False),
            created_at=user["created_at"]
        )
    )

@api_router.get("/auth/me", response_model=UserResponse)
async def get_me(user: dict = Depends(get_current_user)):
    return UserResponse(
        id=user["id"],
        email=user["email"],
        name=user["name"],
        role=user["role"],
        is_active=user["is_active"],
        must_change_password=user.get("must_change_password", False),
        created_at=user["created_at"]
    )

@api_router.post("/auth/change-password")
async def change_password(data: PasswordChange, user: dict = Depends(get_current_user)):
    if not verify_password(data.current_password, user["password_hash"]):
        raise HTTPException(status_code=400, detail="Aktuelles Passwort ist falsch")
    
    before = safe_dict_for_audit(user)
    new_hash = hash_password(data.new_password)
    
    await db.users.update_one(
        {"id": user["id"]},
        {"$set": {"password_hash": new_hash, "must_change_password": False}}
    )
    
    after = {**before, "must_change_password": False}
    await create_audit_log(user, "user", user["id"], "password_change", before, after)
    
    return {"message": "Passwort erfolgreich geändert"}

# ============== USER ENDPOINTS (Admin only) ==============
@api_router.get("/users", response_model=List[UserResponse])
async def get_users(user: dict = Depends(require_roles(UserRole.ADMIN))):
    users = await db.users.find({"archived": False}, {"_id": 0, "password_hash": 0}).to_list(1000)
    return [UserResponse(**u) for u in users]

@api_router.post("/users", response_model=UserResponse)
async def create_user(data: UserCreate, user: dict = Depends(require_roles(UserRole.ADMIN))):
    existing = await db.users.find_one({"email": data.email, "archived": False})
    if existing:
        raise HTTPException(status_code=400, detail="E-Mail bereits registriert")
    
    new_user = User(
        email=data.email,
        name=data.name,
        role=data.role,
        must_change_password=True
    )
    doc = serialize_datetime(new_user.model_dump())
    doc["password_hash"] = hash_password(data.password)
    
    await db.users.insert_one(doc)
    await create_audit_log(user, "user", new_user.id, "create", None, safe_dict_for_audit(doc))
    
    return UserResponse(
        id=new_user.id,
        email=new_user.email,
        name=new_user.name,
        role=new_user.role,
        is_active=new_user.is_active,
        must_change_password=new_user.must_change_password,
        created_at=doc["created_at"]
    )

@api_router.delete("/users/{user_id}")
async def archive_user(user_id: str, user: dict = Depends(require_roles(UserRole.ADMIN))):
    existing = await db.users.find_one({"id": user_id, "archived": False}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Benutzer nicht gefunden")
    
    if existing["id"] == user["id"]:
        raise HTTPException(status_code=400, detail="Eigenes Konto kann nicht archiviert werden")
    
    before = safe_dict_for_audit(existing)
    await db.users.update_one({"id": user_id}, {"$set": {"archived": True}})
    after = {**before, "archived": True}
    
    await create_audit_log(user, "user", user_id, "archive", before, after)
    return {"message": "Benutzer archiviert"}

# ============== AREA ENDPOINTS ==============
@api_router.get("/areas", response_model=List[Area])
async def get_areas(user: dict = Depends(get_current_user)):
    areas = await db.areas.find({"archived": False}, {"_id": 0}).to_list(1000)
    return areas

@api_router.post("/areas", response_model=Area)
async def create_area(data: AreaCreate, user: dict = Depends(require_roles(UserRole.ADMIN))):
    area = Area(**data.model_dump())
    doc = serialize_datetime(area.model_dump())
    
    await db.areas.insert_one(doc)
    await create_audit_log(user, "area", area.id, "create", None, safe_dict_for_audit(doc))
    
    return area

@api_router.put("/areas/{area_id}", response_model=Area)
async def update_area(area_id: str, data: AreaCreate, user: dict = Depends(require_roles(UserRole.ADMIN))):
    existing = await db.areas.find_one({"id": area_id, "archived": False}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Bereich nicht gefunden")
    
    before = safe_dict_for_audit(existing)
    update_data = data.model_dump()
    
    await db.areas.update_one({"id": area_id}, {"$set": update_data})
    
    updated = await db.areas.find_one({"id": area_id}, {"_id": 0})
    await create_audit_log(user, "area", area_id, "update", before, safe_dict_for_audit(updated))
    
    return updated

@api_router.delete("/areas/{area_id}")
async def archive_area(area_id: str, user: dict = Depends(require_roles(UserRole.ADMIN))):
    existing = await db.areas.find_one({"id": area_id, "archived": False}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Bereich nicht gefunden")
    
    before = safe_dict_for_audit(existing)
    await db.areas.update_one({"id": area_id}, {"$set": {"archived": True}})
    after = {**before, "archived": True}
    
    await create_audit_log(user, "area", area_id, "archive", before, after)
    return {"message": "Bereich archiviert"}

# ============== RESERVATION ENDPOINTS ==============
@api_router.get("/reservations")
async def get_reservations(
    date: Optional[str] = None,
    status: Optional[ReservationStatus] = None,
    area_id: Optional[str] = None,
    search: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    query = {"archived": False}
    
    if date:
        query["date"] = date
    if status:
        query["status"] = status.value
    if area_id:
        query["area_id"] = area_id
    if search:
        query["$or"] = [
            {"guest_name": {"$regex": search, "$options": "i"}},
            {"guest_phone": {"$regex": search, "$options": "i"}}
        ]
    
    reservations = await db.reservations.find(query, {"_id": 0}).sort("time", 1).to_list(1000)
    return reservations

@api_router.get("/reservations/{reservation_id}")
async def get_reservation(reservation_id: str, user: dict = Depends(get_current_user)):
    reservation = await db.reservations.find_one({"id": reservation_id, "archived": False}, {"_id": 0})
    if not reservation:
        raise HTTPException(status_code=404, detail="Reservierung nicht gefunden")
    return reservation

@api_router.post("/reservations")
async def create_reservation(data: ReservationCreate, user: dict = Depends(require_roles(UserRole.ADMIN, UserRole.SCHICHTLEITER))):
    reservation = Reservation(**data.model_dump())
    doc = serialize_datetime(reservation.model_dump())
    
    await db.reservations.insert_one(doc)
    await create_audit_log(user, "reservation", reservation.id, "create", None, safe_dict_for_audit(doc))
    
    return reservation

@api_router.put("/reservations/{reservation_id}")
async def update_reservation(
    reservation_id: str,
    data: ReservationUpdate,
    user: dict = Depends(require_roles(UserRole.ADMIN, UserRole.SCHICHTLEITER))
):
    existing = await db.reservations.find_one({"id": reservation_id, "archived": False}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Reservierung nicht gefunden")
    
    before = safe_dict_for_audit(existing)
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    await db.reservations.update_one({"id": reservation_id}, {"$set": update_data})
    
    updated = await db.reservations.find_one({"id": reservation_id}, {"_id": 0})
    await create_audit_log(user, "reservation", reservation_id, "update", before, safe_dict_for_audit(updated))
    
    return updated

@api_router.patch("/reservations/{reservation_id}/status")
async def update_reservation_status(
    reservation_id: str,
    new_status: ReservationStatus,
    user: dict = Depends(require_roles(UserRole.ADMIN, UserRole.SCHICHTLEITER))
):
    existing = await db.reservations.find_one({"id": reservation_id, "archived": False}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Reservierung nicht gefunden")
    
    before = safe_dict_for_audit(existing)
    update_data = {
        "status": new_status.value,
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.reservations.update_one({"id": reservation_id}, {"$set": update_data})
    
    updated = await db.reservations.find_one({"id": reservation_id}, {"_id": 0})
    await create_audit_log(user, "reservation", reservation_id, "status_change", before, safe_dict_for_audit(updated))
    
    return updated

@api_router.delete("/reservations/{reservation_id}")
async def archive_reservation(
    reservation_id: str,
    user: dict = Depends(require_roles(UserRole.ADMIN, UserRole.SCHICHTLEITER))
):
    existing = await db.reservations.find_one({"id": reservation_id, "archived": False}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Reservierung nicht gefunden")
    
    before = safe_dict_for_audit(existing)
    await db.reservations.update_one({"id": reservation_id}, {"$set": {"archived": True}})
    after = {**before, "archived": True}
    
    await create_audit_log(user, "reservation", reservation_id, "archive", before, after)
    return {"message": "Reservierung archiviert"}

# ============== SETTINGS ENDPOINTS ==============
@api_router.get("/settings")
async def get_settings(user: dict = Depends(require_roles(UserRole.ADMIN))):
    settings = await db.settings.find({}, {"_id": 0}).to_list(1000)
    return settings

@api_router.post("/settings")
async def create_or_update_setting(data: SettingCreate, user: dict = Depends(require_roles(UserRole.ADMIN))):
    existing = await db.settings.find_one({"key": data.key}, {"_id": 0})
    
    if existing:
        before = safe_dict_for_audit(existing)
        update_data = {
            "value": data.value,
            "description": data.description,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        await db.settings.update_one({"key": data.key}, {"$set": update_data})
        updated = await db.settings.find_one({"key": data.key}, {"_id": 0})
        await create_audit_log(user, "setting", data.key, "update", before, safe_dict_for_audit(updated))
        return updated
    else:
        setting = Setting(**data.model_dump())
        doc = serialize_datetime(setting.model_dump())
        await db.settings.insert_one(doc)
        await create_audit_log(user, "setting", data.key, "create", None, safe_dict_for_audit(doc))
        return setting

# ============== AUDIT LOG ENDPOINTS ==============
@api_router.get("/audit-logs")
async def get_audit_logs(
    entity: Optional[str] = None,
    entity_id: Optional[str] = None,
    actor_id: Optional[str] = None,
    limit: int = 100,
    user: dict = Depends(require_roles(UserRole.ADMIN))
):
    query = {}
    if entity:
        query["entity"] = entity
    if entity_id:
        query["entity_id"] = entity_id
    if actor_id:
        query["actor_id"] = actor_id
    
    logs = await db.audit_logs.find(query, {"_id": 0}).sort("timestamp", -1).limit(limit).to_list(limit)
    return logs

# ============== SEED DATA ==============
@api_router.post("/seed")
async def seed_data():
    """Seed initial test data - only works if no users exist"""
    existing_users = await db.users.count_documents({"archived": False})
    if existing_users > 0:
        return {"message": "Daten bereits vorhanden", "seeded": False}
    
    # Create test users
    test_users = [
        {"email": "admin@gastrocore.de", "name": "Admin User", "role": "admin", "password": "Admin123!"},
        {"email": "schichtleiter@gastrocore.de", "name": "Schicht Leiter", "role": "schichtleiter", "password": "Schicht123!"},
        {"email": "mitarbeiter@gastrocore.de", "name": "Mit Arbeiter", "role": "mitarbeiter", "password": "Mitarbeiter123!"},
    ]
    
    for u in test_users:
        user = User(email=u["email"], name=u["name"], role=u["role"], must_change_password=True)
        doc = serialize_datetime(user.model_dump())
        doc["password_hash"] = hash_password(u["password"])
        await db.users.insert_one(doc)
    
    # Create test areas
    test_areas = [
        {"name": "Terrasse", "description": "Außenbereich mit Sonnenschirmen", "capacity": 40},
        {"name": "Saal", "description": "Hauptspeiseraum", "capacity": 80},
        {"name": "Wintergarten", "description": "Verglaster Bereich", "capacity": 30},
        {"name": "Bar", "description": "Barhocker und Stehtische", "capacity": 20},
    ]
    
    area_ids = []
    for a in test_areas:
        area = Area(**a)
        doc = serialize_datetime(area.model_dump())
        await db.areas.insert_one(doc)
        area_ids.append(area.id)
    
    # Create test reservations
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    test_reservations = [
        {"guest_name": "Familie Müller", "guest_phone": "+49 170 1234567", "party_size": 4, "date": today, "time": "12:00", "area_id": area_ids[1], "status": "bestaetigt"},
        {"guest_name": "Hans Schmidt", "guest_phone": "+49 171 2345678", "party_size": 2, "date": today, "time": "13:00", "area_id": area_ids[0], "status": "neu"},
        {"guest_name": "Lisa Weber", "guest_phone": "+49 172 3456789", "party_size": 6, "date": today, "time": "18:30", "area_id": area_ids[2], "status": "neu"},
        {"guest_name": "Peter Braun", "guest_phone": "+49 173 4567890", "party_size": 3, "date": today, "time": "19:00", "area_id": area_ids[1], "status": "angekommen"},
        {"guest_name": "Maria Schwarz", "guest_phone": "+49 174 5678901", "party_size": 8, "date": today, "time": "20:00", "area_id": area_ids[1], "status": "neu"},
    ]
    
    for r in test_reservations:
        reservation = Reservation(**r)
        doc = serialize_datetime(reservation.model_dump())
        await db.reservations.insert_one(doc)
    
    return {
        "message": "Testdaten erstellt",
        "seeded": True,
        "users": [{"email": u["email"], "password": u["password"], "role": u["role"]} for u in test_users]
    }

# ============== ROOT ENDPOINT ==============
@api_router.get("/")
async def root():
    return {"message": "GastroCore API v1.0.0", "status": "running"}

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
