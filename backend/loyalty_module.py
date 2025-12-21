"""
GastroCore Loyalty Module - Sprint 7
Kunden-App & Punkte-System

ADDITIV - Keine Breaking Changes
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from enum import Enum
import uuid
import secrets
import hashlib
import qrcode
import io
import base64
import logging

from dotenv import load_dotenv
load_dotenv()

# Core imports
from core.database import db
from core.auth import require_admin, require_manager, get_current_user
from core.audit import create_audit_log, safe_dict_for_audit, SYSTEM_ACTOR
from core.exceptions import NotFoundException, ValidationException, ForbiddenException

logger = logging.getLogger(__name__)


# ============== ENUMS ==============
class LedgerTransactionType(str, Enum):
    EARN = "earn"  # Punkte sammeln
    REDEEM = "redeem"  # Punkte einlösen
    MANUAL_ADD = "manual_add"  # Manuelle Gutschrift
    MANUAL_REMOVE = "manual_remove"  # Manuelle Abbuchung
    EXPIRE = "expire"  # Verfall (vorbereitet)
    CORRECTION = "correction"  # Korrektur


class RewardType(str, Enum):
    PRODUCT = "product"  # Hofladen-Produkt
    DESSERT = "dessert"
    COFFEE = "coffee"
    EVENT_DISCOUNT = "event_discount"
    TWO_FOR_ONE = "two_for_one"


class RedemptionStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"


# ============== HELPER FUNCTIONS ==============
def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_entity(data: dict) -> dict:
    return {
        "id": str(uuid.uuid4()),
        **data,
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "archived": False
    }


def generate_otp() -> str:
    """Generate 6-digit OTP"""
    return ''.join([str(secrets.randbelow(10)) for _ in range(6)])


def generate_magic_link_token() -> str:
    """Generate secure magic link token"""
    return secrets.token_urlsafe(32)


def generate_qr_token() -> str:
    """Generate short-lived QR token"""
    return secrets.token_urlsafe(16)


def calculate_points(amount: float, rate: float = 0.1) -> int:
    """Calculate points from amount (default: 100€ = 10 points)"""
    return int(amount * rate)


# ============== PYDANTIC MODELS ==============

# Customer Models
class CustomerRegister(BaseModel):
    email: EmailStr
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    language: str = Field(default="de", pattern="^(de|en|pl)$")
    newsletter_opt_in: bool = False
    push_opt_in: bool = False


class CustomerUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    language: Optional[str] = None
    newsletter_opt_in: Optional[bool] = None
    push_opt_in: Optional[bool] = None


class OTPRequest(BaseModel):
    email: EmailStr


class OTPVerify(BaseModel):
    email: EmailStr
    otp: str = Field(..., min_length=6, max_length=6)


class MagicLinkVerify(BaseModel):
    token: str


# Loyalty Models
class LoyaltySettings(BaseModel):
    points_per_euro: float = Field(default=0.1, ge=0, le=1)  # 0.1 = 10 points per 100€
    max_points_per_transaction: int = Field(default=100, ge=1, le=1000)
    qr_validity_seconds: int = Field(default=90, ge=30, le=300)
    points_expiry_days: Optional[int] = None  # None = no expiry
    rounding: str = Field(default="floor", pattern="^(floor|ceil|round)$")


class ManualPointsRequest(BaseModel):
    customer_id: str
    amount: float = Field(..., gt=0)
    reason: str = Field(..., min_length=5, max_length=500)
    transaction_type: str = Field(default="manual_add", pattern="^(manual_add|manual_remove|correction)$")


class QRPointsRequest(BaseModel):
    amount: float = Field(..., gt=0)
    table_number: Optional[str] = None
    notes: Optional[str] = None


class QRScanRequest(BaseModel):
    qr_token: str
    confirm_amount: bool = True


# Reward Models
class RewardCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    description: Optional[str] = None
    reward_type: RewardType
    points_cost: int = Field(..., ge=1, le=10000)
    valid_from: Optional[str] = None
    valid_until: Optional[str] = None
    valid_weekdays: List[int] = Field(default=[0, 1, 2, 3, 4, 5, 6])  # 0=Mon, 6=Sun
    valid_time_from: Optional[str] = None  # HH:MM
    valid_time_until: Optional[str] = None  # HH:MM
    not_combinable: bool = False
    max_redemptions: Optional[int] = None
    is_active: bool = True


class RewardUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    points_cost: Optional[int] = None
    valid_from: Optional[str] = None
    valid_until: Optional[str] = None
    valid_weekdays: Optional[List[int]] = None
    valid_time_from: Optional[str] = None
    valid_time_until: Optional[str] = None
    not_combinable: Optional[bool] = None
    max_redemptions: Optional[int] = None
    is_active: Optional[bool] = None


class RedeemRewardRequest(BaseModel):
    reward_id: str


class ConfirmRedemptionRequest(BaseModel):
    redemption_id: str


# ============== ROUTERS ==============
loyalty_router = APIRouter(prefix="/api/loyalty", tags=["Loyalty"])
customer_router = APIRouter(prefix="/api/customer", tags=["Customer App"])


# ============== CUSTOMER AUTH ==============
@customer_router.post("/request-otp")
async def request_otp(data: OTPRequest, background_tasks: BackgroundTasks):
    """Request OTP for customer login"""
    email = data.email.lower()
    
    # Find or create customer
    customer = await db.customers.find_one({"email": email, "archived": False})
    if not customer:
        # Auto-register new customer
        customer = create_entity({
            "email": email,
            "points_balance": 0,
            "language": "de",
            "newsletter_opt_in": False,
            "push_opt_in": False,
            "is_verified": False
        })
        await db.customers.insert_one(customer)
    
    # Generate OTP
    otp = generate_otp()
    otp_hash = hashlib.sha256(otp.encode()).hexdigest()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)
    
    # Store OTP
    await db.customer_otps.delete_many({"email": email})  # Clear old OTPs
    await db.customer_otps.insert_one({
        "email": email,
        "otp_hash": otp_hash,
        "expires_at": expires_at.isoformat(),
        "created_at": now_iso()
    })
    
    # Send OTP via email (background task)
    from email_service import send_email_template
    try:
        await send_email_template(
            to_email=email,
            subject="Ihr Anmeldecode - GastroCore",
            body=f"Ihr Einmalcode lautet:\n\n{otp}\n\nDieser Code ist 10 Minuten gültig."
        )
    except Exception as e:
        logger.error(f"Failed to send OTP: {e}")
    
    return {"message": "Code wurde gesendet", "success": True}


@customer_router.post("/verify-otp")
async def verify_otp(data: OTPVerify):
    """Verify OTP and return customer token"""
    email = data.email.lower()
    otp_hash = hashlib.sha256(data.otp.encode()).hexdigest()
    
    # Find OTP
    otp_record = await db.customer_otps.find_one({
        "email": email,
        "otp_hash": otp_hash
    })
    
    if not otp_record:
        raise ValidationException("Ungültiger Code")
    
    # Check expiry
    expires_at = datetime.fromisoformat(otp_record["expires_at"].replace("Z", "+00:00"))
    if datetime.now(timezone.utc) > expires_at:
        raise ValidationException("Code abgelaufen")
    
    # Delete OTP
    await db.customer_otps.delete_many({"email": email})
    
    # Get customer
    customer = await db.customers.find_one({"email": email, "archived": False})
    if not customer:
        raise NotFoundException("Kunde")
    
    # Mark as verified
    if not customer.get("is_verified"):
        await db.customers.update_one({"id": customer["id"]}, {"$set": {"is_verified": True}})
    
    # Generate session token
    session_token = secrets.token_urlsafe(32)
    expires = datetime.now(timezone.utc) + timedelta(days=30)
    
    await db.customer_sessions.insert_one({
        "token": session_token,
        "customer_id": customer["id"],
        "expires_at": expires.isoformat(),
        "created_at": now_iso()
    })
    
    return {
        "token": session_token,
        "customer_id": customer["id"],
        "expires_at": expires.isoformat()
    }


@customer_router.post("/request-magic-link")
async def request_magic_link(data: OTPRequest, request: Request):
    """Request magic link for customer login"""
    email = data.email.lower()
    
    # Find or create customer
    customer = await db.customers.find_one({"email": email, "archived": False})
    if not customer:
        customer = create_entity({
            "email": email,
            "points_balance": 0,
            "language": "de",
            "newsletter_opt_in": False,
            "push_opt_in": False,
            "is_verified": False
        })
        await db.customers.insert_one(customer)
    
    # Generate magic link token
    token = generate_magic_link_token()
    expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
    
    await db.magic_links.delete_many({"email": email})
    await db.magic_links.insert_one({
        "email": email,
        "token": token,
        "expires_at": expires_at.isoformat(),
        "created_at": now_iso()
    })
    
    # Build magic link URL
    base_url = str(request.base_url).rstrip("/")
    magic_link = f"{base_url}/customer/verify-magic?token={token}"
    
    # Send email
    from email_service import send_email_template
    try:
        await send_email_template(
            to_email=email,
            subject="Ihr Anmeldelink - GastroCore",
            body=f"Klicken Sie hier, um sich anzumelden:\n\n{magic_link}\n\nDieser Link ist 1 Stunde gültig."
        )
    except Exception as e:
        logger.error(f"Failed to send magic link: {e}")
    
    return {"message": "Link wurde gesendet", "success": True}


@customer_router.post("/verify-magic-link")
async def verify_magic_link(data: MagicLinkVerify):
    """Verify magic link and return customer token"""
    
    record = await db.magic_links.find_one({"token": data.token})
    if not record:
        raise ValidationException("Ungültiger Link")
    
    expires_at = datetime.fromisoformat(record["expires_at"].replace("Z", "+00:00"))
    if datetime.now(timezone.utc) > expires_at:
        raise ValidationException("Link abgelaufen")
    
    email = record["email"]
    await db.magic_links.delete_many({"email": email})
    
    customer = await db.customers.find_one({"email": email, "archived": False})
    if not customer:
        raise NotFoundException("Kunde")
    
    if not customer.get("is_verified"):
        await db.customers.update_one({"id": customer["id"]}, {"$set": {"is_verified": True}})
    
    session_token = secrets.token_urlsafe(32)
    expires = datetime.now(timezone.utc) + timedelta(days=30)
    
    await db.customer_sessions.insert_one({
        "token": session_token,
        "customer_id": customer["id"],
        "expires_at": expires.isoformat(),
        "created_at": now_iso()
    })
    
    return {
        "token": session_token,
        "customer_id": customer["id"],
        "expires_at": expires.isoformat()
    }


# ============== CUSTOMER AUTH DEPENDENCY ==============
async def get_current_customer(request: Request) -> dict:
    """Get current customer from session token"""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Nicht authentifiziert")
    
    token = auth_header.split(" ")[1]
    session = await db.customer_sessions.find_one({"token": token})
    
    if not session:
        raise HTTPException(status_code=401, detail="Ungültige Sitzung")
    
    expires_at = datetime.fromisoformat(session["expires_at"].replace("Z", "+00:00"))
    if datetime.now(timezone.utc) > expires_at:
        raise HTTPException(status_code=401, detail="Sitzung abgelaufen")
    
    customer = await db.customers.find_one({"id": session["customer_id"], "archived": False}, {"_id": 0})
    if not customer:
        raise HTTPException(status_code=401, detail="Kunde nicht gefunden")
    
    return customer


# ============== CUSTOMER PROFILE ==============
@customer_router.get("/profile")
async def get_customer_profile(customer: dict = Depends(get_current_customer)):
    """Get customer profile with points balance"""
    # Calculate actual balance from ledger
    balance = await calculate_customer_balance(customer["id"])
    
    return {
        "id": customer["id"],
        "email": customer.get("email"),
        "first_name": customer.get("first_name"),
        "last_name": customer.get("last_name"),
        "phone": customer.get("phone"),
        "language": customer.get("language", "de"),
        "newsletter_opt_in": customer.get("newsletter_opt_in", False),
        "push_opt_in": customer.get("push_opt_in", False),
        "points_balance": balance,
        "created_at": customer.get("created_at")
    }


@customer_router.patch("/profile")
async def update_customer_profile(
    data: CustomerUpdate,
    customer: dict = Depends(get_current_customer)
):
    """Update customer profile"""
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    update_data["updated_at"] = now_iso()
    
    await db.customers.update_one({"id": customer["id"]}, {"$set": update_data})
    return {"message": "Profil aktualisiert", "success": True}


@customer_router.get("/points-history")
async def get_points_history(
    limit: int = 50,
    customer: dict = Depends(get_current_customer)
):
    """Get customer's points transaction history"""
    transactions = await db.points_ledger.find(
        {"customer_id": customer["id"]},
        {"_id": 0}
    ).sort("created_at", -1).limit(limit).to_list(limit)
    
    return transactions


@customer_router.get("/rewards")
async def get_available_rewards(customer: dict = Depends(get_current_customer)):
    """Get rewards available for the customer"""
    now = datetime.now(timezone.utc)
    weekday = now.weekday()
    current_time = now.strftime("%H:%M")
    
    # Get active rewards
    rewards = await db.rewards.find({
        "is_active": True,
        "archived": False
    }, {"_id": 0}).to_list(100)
    
    # Calculate customer balance
    balance = await calculate_customer_balance(customer["id"])
    
    # Filter and enrich rewards
    available = []
    for reward in rewards:
        # Check validity
        if reward.get("valid_from") and reward["valid_from"] > now.isoformat():
            continue
        if reward.get("valid_until") and reward["valid_until"] < now.isoformat():
            continue
        if reward.get("valid_weekdays") and weekday not in reward["valid_weekdays"]:
            reward["available_today"] = False
        else:
            reward["available_today"] = True
        
        # Check time restrictions
        if reward.get("valid_time_from") and current_time < reward["valid_time_from"]:
            reward["available_now"] = False
        elif reward.get("valid_time_until") and current_time > reward["valid_time_until"]:
            reward["available_now"] = False
        else:
            reward["available_now"] = reward["available_today"]
        
        # Check if customer can afford
        reward["can_afford"] = balance >= reward.get("points_cost", 0)
        reward["customer_balance"] = balance
        
        available.append(reward)
    
    return available


@customer_router.post("/redeem")
async def redeem_reward(
    data: RedeemRewardRequest,
    customer: dict = Depends(get_current_customer)
):
    """Redeem a reward (creates pending redemption)"""
    reward = await db.rewards.find_one({"id": data.reward_id, "is_active": True, "archived": False})
    if not reward:
        raise NotFoundException("Prämie")
    
    # Check balance
    balance = await calculate_customer_balance(customer["id"])
    if balance < reward.get("points_cost", 0):
        raise ValidationException("Nicht genügend Punkte")
    
    # Check if already has pending redemption for this reward
    existing = await db.redemptions.find_one({
        "customer_id": customer["id"],
        "reward_id": reward["id"],
        "status": RedemptionStatus.PENDING.value
    })
    if existing:
        raise ValidationException("Sie haben bereits eine offene Einlösung für diese Prämie")
    
    # Create redemption
    redemption = create_entity({
        "customer_id": customer["id"],
        "reward_id": reward["id"],
        "reward_name": reward.get("name"),
        "points_cost": reward.get("points_cost"),
        "status": RedemptionStatus.PENDING.value,
        "redemption_code": secrets.token_urlsafe(8).upper()[:8],
        "expires_at": (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()
    })
    
    await db.redemptions.insert_one(redemption)
    
    return {
        "redemption_id": redemption["id"],
        "redemption_code": redemption["redemption_code"],
        "reward_name": reward.get("name"),
        "points_cost": reward.get("points_cost"),
        "expires_at": redemption["expires_at"],
        "message": "Zeigen Sie diesen Code dem Service"
    }


@customer_router.get("/my-redemptions")
async def get_my_redemptions(
    status: Optional[str] = None,
    customer: dict = Depends(get_current_customer)
):
    """Get customer's redemptions"""
    query = {"customer_id": customer["id"]}
    if status:
        query["status"] = status
    
    redemptions = await db.redemptions.find(query, {"_id": 0}).sort("created_at", -1).to_list(100)
    return redemptions


# ============== QR CODE POINTS ==============
@loyalty_router.post("/generate-qr")
async def generate_points_qr(
    data: QRPointsRequest,
    user: dict = Depends(require_manager)
):
    """Generate QR code for customer to scan and earn points"""
    
    # Get settings
    settings = await get_loyalty_settings()
    validity_seconds = settings.get("qr_validity_seconds", 90)
    
    # Generate token
    qr_token = generate_qr_token()
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=validity_seconds)
    
    # Store QR data
    qr_data = create_entity({
        "token": qr_token,
        "amount": data.amount,
        "table_number": data.table_number,
        "notes": data.notes,
        "generated_by": user.get("email"),
        "expires_at": expires_at.isoformat(),
        "used": False
    })
    await db.qr_tokens.insert_one(qr_data)
    
    # Generate QR code image
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(f"GASTROCORE:{qr_token}")
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Convert to base64
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    qr_base64 = base64.b64encode(buffer.getvalue()).decode()
    
    # Calculate points preview
    points = calculate_points(data.amount, settings.get("points_per_euro", 0.1))
    
    return {
        "qr_token": qr_token,
        "qr_image": f"data:image/png;base64,{qr_base64}",
        "amount": data.amount,
        "points_preview": points,
        "expires_at": expires_at.isoformat(),
        "expires_in_seconds": validity_seconds
    }


@customer_router.post("/scan-qr")
async def scan_qr_code(
    data: QRScanRequest,
    customer: dict = Depends(get_current_customer)
):
    """Scan QR code to earn points"""
    
    # Find QR token
    qr_record = await db.qr_tokens.find_one({"token": data.qr_token, "used": False})
    if not qr_record:
        raise ValidationException("Ungültiger oder bereits verwendeter QR-Code")
    
    # Check expiry
    expires_at = datetime.fromisoformat(qr_record["expires_at"].replace("Z", "+00:00"))
    if datetime.now(timezone.utc) > expires_at:
        raise ValidationException("QR-Code abgelaufen")
    
    # Get settings
    settings = await get_loyalty_settings()
    
    # Calculate points
    amount = qr_record.get("amount", 0)
    points = calculate_points(amount, settings.get("points_per_euro", 0.1))
    max_points = settings.get("max_points_per_transaction", 100)
    points = min(points, max_points)
    
    # Mark QR as used
    await db.qr_tokens.update_one(
        {"token": data.qr_token},
        {"$set": {"used": True, "used_by": customer["id"], "used_at": now_iso()}}
    )
    
    # Create ledger entry
    ledger_entry = create_entity({
        "customer_id": customer["id"],
        "transaction_type": LedgerTransactionType.EARN.value,
        "points": points,
        "amount": amount,
        "reference_type": "qr_scan",
        "reference_id": qr_record["id"],
        "description": f"Punkte für {amount:.2f}€ Umsatz"
    })
    await db.points_ledger.insert_one(ledger_entry)
    
    # Update cached balance
    new_balance = await calculate_customer_balance(customer["id"])
    await db.customers.update_one(
        {"id": customer["id"]},
        {"$set": {"points_balance": new_balance, "updated_at": now_iso()}}
    )
    
    # Audit log
    await create_audit_log(
        {"id": customer["id"], "email": customer.get("email")},
        "points_ledger", ledger_entry["id"], "earn_points",
        None, {"points": points, "amount": amount, "method": "qr_scan"}
    )
    
    return {
        "success": True,
        "points_earned": points,
        "amount": amount,
        "new_balance": new_balance,
        "message": f"Sie haben {points} Punkte gesammelt!"
    }


# ============== MANUAL POINTS (ADMIN) ==============
@loyalty_router.post("/manual-points")
async def add_manual_points(
    data: ManualPointsRequest,
    user: dict = Depends(require_manager)
):
    """Manually add or remove points (requires reason)"""
    
    customer = await db.customers.find_one({"id": data.customer_id, "archived": False})
    if not customer:
        raise NotFoundException("Kunde")
    
    settings = await get_loyalty_settings()
    
    if data.transaction_type == "manual_add":
        points = calculate_points(data.amount, settings.get("points_per_euro", 0.1))
        points = min(points, settings.get("max_points_per_transaction", 100))
        trans_type = LedgerTransactionType.MANUAL_ADD.value
    elif data.transaction_type == "manual_remove":
        points = -calculate_points(data.amount, settings.get("points_per_euro", 0.1))
        trans_type = LedgerTransactionType.MANUAL_REMOVE.value
    else:
        points = calculate_points(data.amount, settings.get("points_per_euro", 0.1))
        trans_type = LedgerTransactionType.CORRECTION.value
    
    # Create ledger entry
    ledger_entry = create_entity({
        "customer_id": data.customer_id,
        "transaction_type": trans_type,
        "points": points,
        "amount": data.amount,
        "reference_type": "manual",
        "reference_id": None,
        "description": data.reason,
        "processed_by": user.get("email")
    })
    await db.points_ledger.insert_one(ledger_entry)
    
    # Update balance
    new_balance = await calculate_customer_balance(data.customer_id)
    await db.customers.update_one(
        {"id": data.customer_id},
        {"$set": {"points_balance": new_balance, "updated_at": now_iso()}}
    )
    
    # Audit log (required for manual actions)
    await create_audit_log(
        user, "points_ledger", ledger_entry["id"], f"manual_{data.transaction_type}",
        None, {
            "customer_id": data.customer_id,
            "points": points,
            "amount": data.amount,
            "reason": data.reason
        }
    )
    
    return {
        "success": True,
        "points": points,
        "new_balance": new_balance,
        "ledger_id": ledger_entry["id"]
    }


# ============== CONFIRM REDEMPTION (SERVICE) ==============
@loyalty_router.post("/confirm-redemption")
async def confirm_redemption(
    data: ConfirmRedemptionRequest,
    user: dict = Depends(require_manager)
):
    """Service confirms reward redemption"""
    
    redemption = await db.redemptions.find_one({
        "id": data.redemption_id,
        "status": RedemptionStatus.PENDING.value
    })
    if not redemption:
        raise NotFoundException("Einlösung nicht gefunden oder bereits verarbeitet")
    
    # Check expiry
    expires_at = datetime.fromisoformat(redemption["expires_at"].replace("Z", "+00:00"))
    if datetime.now(timezone.utc) > expires_at:
        await db.redemptions.update_one(
            {"id": data.redemption_id},
            {"$set": {"status": RedemptionStatus.CANCELLED.value, "cancel_reason": "expired"}}
        )
        raise ValidationException("Einlösung abgelaufen")
    
    customer_id = redemption["customer_id"]
    points_cost = redemption["points_cost"]
    
    # Check balance again
    balance = await calculate_customer_balance(customer_id)
    if balance < points_cost:
        raise ValidationException("Nicht genügend Punkte")
    
    # Create ledger entry (deduct points)
    ledger_entry = create_entity({
        "customer_id": customer_id,
        "transaction_type": LedgerTransactionType.REDEEM.value,
        "points": -points_cost,
        "amount": 0,
        "reference_type": "redemption",
        "reference_id": redemption["id"],
        "description": f"Einlösung: {redemption.get('reward_name')}"
    })
    await db.points_ledger.insert_one(ledger_entry)
    
    # Update redemption status
    await db.redemptions.update_one(
        {"id": data.redemption_id},
        {"$set": {
            "status": RedemptionStatus.CONFIRMED.value,
            "confirmed_by": user.get("email"),
            "confirmed_at": now_iso(),
            "ledger_id": ledger_entry["id"]
        }}
    )
    
    # Update balance
    new_balance = await calculate_customer_balance(customer_id)
    await db.customers.update_one(
        {"id": customer_id},
        {"$set": {"points_balance": new_balance, "updated_at": now_iso()}}
    )
    
    # Audit log
    await create_audit_log(
        user, "redemption", data.redemption_id, "confirm_redemption",
        {"status": "pending"}, {"status": "confirmed", "points_deducted": points_cost}
    )
    
    return {
        "success": True,
        "message": "Prämie erfolgreich eingelöst",
        "points_deducted": points_cost,
        "new_balance": new_balance
    }


@loyalty_router.get("/pending-redemptions")
async def get_pending_redemptions(user: dict = Depends(require_manager)):
    """Get all pending redemptions for service terminal"""
    redemptions = await db.redemptions.find(
        {"status": RedemptionStatus.PENDING.value},
        {"_id": 0}
    ).sort("created_at", -1).to_list(100)
    
    # Enrich with customer info
    for r in redemptions:
        customer = await db.customers.find_one({"id": r["customer_id"]}, {"_id": 0, "email": 1, "first_name": 1, "last_name": 1})
        r["customer"] = customer
    
    return redemptions


# ============== REWARDS MANAGEMENT (ADMIN) ==============
@loyalty_router.get("/rewards")
async def list_rewards(
    include_inactive: bool = False,
    user: dict = Depends(require_manager)
):
    """List all rewards"""
    query = {"archived": False}
    if not include_inactive:
        query["is_active"] = True
    
    rewards = await db.rewards.find(query, {"_id": 0}).sort("points_cost", 1).to_list(100)
    return rewards


@loyalty_router.post("/rewards")
async def create_reward(data: RewardCreate, user: dict = Depends(require_admin)):
    """Create a new reward"""
    reward = create_entity(data.model_dump())
    await db.rewards.insert_one(reward)
    
    await create_audit_log(user, "reward", reward["id"], "create", None, safe_dict_for_audit(reward))
    
    return {k: v for k, v in reward.items() if k != "_id"}


@loyalty_router.patch("/rewards/{reward_id}")
async def update_reward(
    reward_id: str,
    data: RewardUpdate,
    user: dict = Depends(require_admin)
):
    """Update a reward"""
    existing = await db.rewards.find_one({"id": reward_id, "archived": False}, {"_id": 0})
    if not existing:
        raise NotFoundException("Prämie")
    
    before = safe_dict_for_audit(existing)
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    update_data["updated_at"] = now_iso()
    
    await db.rewards.update_one({"id": reward_id}, {"$set": update_data})
    updated = await db.rewards.find_one({"id": reward_id}, {"_id": 0})
    
    await create_audit_log(user, "reward", reward_id, "update", before, safe_dict_for_audit(updated))
    
    return updated


@loyalty_router.delete("/rewards/{reward_id}")
async def archive_reward(reward_id: str, user: dict = Depends(require_admin)):
    """Archive a reward"""
    existing = await db.rewards.find_one({"id": reward_id, "archived": False})
    if not existing:
        raise NotFoundException("Prämie")
    
    await db.rewards.update_one({"id": reward_id}, {"$set": {"archived": True, "is_active": False}})
    await create_audit_log(user, "reward", reward_id, "archive", {"archived": False}, {"archived": True})
    
    return {"message": "Prämie archiviert", "success": True}


# ============== LOYALTY SETTINGS ==============
async def get_loyalty_settings() -> dict:
    """Get loyalty settings"""
    settings = await db.loyalty_settings.find_one({"type": "loyalty"}, {"_id": 0})
    if not settings:
        return LoyaltySettings().model_dump()
    # Remove MongoDB _id if present and return only serializable fields
    return {
        "points_per_euro": settings.get("points_per_euro", 0.1),
        "max_points_per_transaction": settings.get("max_points_per_transaction", 100),
        "qr_validity_seconds": settings.get("qr_validity_seconds", 90),
        "points_expiry_days": settings.get("points_expiry_days"),
        "rounding": settings.get("rounding", "floor")
    }


@loyalty_router.get("/settings")
async def get_loyalty_settings_endpoint(user: dict = Depends(require_admin)):
    """Get loyalty settings"""
    return await get_loyalty_settings()


@loyalty_router.patch("/settings")
async def update_loyalty_settings(
    data: LoyaltySettings,
    user: dict = Depends(require_admin)
):
    """Update loyalty settings"""
    existing = await db.loyalty_settings.find_one({"type": "loyalty"})
    
    update_data = data.model_dump()
    update_data["type"] = "loyalty"
    update_data["updated_at"] = now_iso()
    
    if existing:
        before = safe_dict_for_audit(existing)
        await db.loyalty_settings.update_one({"type": "loyalty"}, {"$set": update_data})
        await create_audit_log(user, "loyalty_settings", "loyalty", "update", before, update_data)
    else:
        update_data["created_at"] = now_iso()
        await db.loyalty_settings.insert_one(update_data)
        await create_audit_log(user, "loyalty_settings", "loyalty", "create", None, update_data)
    
    return await get_loyalty_settings()


# ============== CUSTOMER LOOKUP (SERVICE) ==============
@loyalty_router.get("/customer-lookup")
async def lookup_customer(
    email: Optional[str] = None,
    customer_id: Optional[str] = None,
    user: dict = Depends(require_manager)
):
    """Lookup customer for service terminal"""
    if not email and not customer_id:
        raise ValidationException("E-Mail oder Kunden-ID erforderlich")
    
    query = {"archived": False}
    if email:
        query["email"] = email.lower()
    if customer_id:
        query["id"] = customer_id
    
    customer = await db.customers.find_one(query, {"_id": 0})
    if not customer:
        raise NotFoundException("Kunde")
    
    # Get balance and recent activity
    balance = await calculate_customer_balance(customer["id"])
    recent_transactions = await db.points_ledger.find(
        {"customer_id": customer["id"]},
        {"_id": 0}
    ).sort("created_at", -1).limit(5).to_list(5)
    
    pending_redemptions = await db.redemptions.find(
        {"customer_id": customer["id"], "status": RedemptionStatus.PENDING.value},
        {"_id": 0}
    ).to_list(10)
    
    return {
        "customer": {
            "id": customer["id"],
            "email": customer.get("email"),
            "first_name": customer.get("first_name"),
            "last_name": customer.get("last_name"),
            "points_balance": balance
        },
        "recent_transactions": recent_transactions,
        "pending_redemptions": pending_redemptions
    }


# ============== ANALYTICS (ADMIN) ==============
@loyalty_router.get("/analytics")
async def get_loyalty_analytics(
    days: int = 30,
    user: dict = Depends(require_admin)
):
    """Get loyalty analytics"""
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    
    # Total points issued
    earned_pipeline = [
        {"$match": {"transaction_type": {"$in": ["earn", "manual_add"]}, "created_at": {"$gte": since}}},
        {"$group": {"_id": None, "total": {"$sum": "$points"}}}
    ]
    earned_result = await db.points_ledger.aggregate(earned_pipeline).to_list(1)
    total_earned = earned_result[0]["total"] if earned_result else 0
    
    # Total points redeemed
    redeemed_pipeline = [
        {"$match": {"transaction_type": "redeem", "created_at": {"$gte": since}}},
        {"$group": {"_id": None, "total": {"$sum": {"$abs": "$points"}}}}
    ]
    redeemed_result = await db.points_ledger.aggregate(redeemed_pipeline).to_list(1)
    total_redeemed = redeemed_result[0]["total"] if redeemed_result else 0
    
    # Redemptions by reward
    redemptions_pipeline = [
        {"$match": {"status": "confirmed", "confirmed_at": {"$gte": since}}},
        {"$group": {"_id": "$reward_name", "count": {"$sum": 1}, "points": {"$sum": "$points_cost"}}},
        {"$sort": {"count": -1}}
    ]
    top_rewards = await db.redemptions.aggregate(redemptions_pipeline).to_list(10)
    
    # Manual transactions
    manual_count = await db.points_ledger.count_documents({
        "transaction_type": {"$in": ["manual_add", "manual_remove", "correction"]},
        "created_at": {"$gte": since}
    })
    
    # Active customers
    active_customers = await db.points_ledger.distinct("customer_id", {"created_at": {"$gte": since}})
    
    return {
        "period_days": days,
        "total_points_earned": total_earned,
        "total_points_redeemed": total_redeemed,
        "top_rewards": top_rewards,
        "manual_transactions": manual_count,
        "active_customers": len(active_customers)
    }


# ============== HELPERS ==============
async def calculate_customer_balance(customer_id: str) -> int:
    """Calculate customer's actual balance from ledger"""
    pipeline = [
        {"$match": {"customer_id": customer_id}},
        {"$group": {"_id": None, "total": {"$sum": "$points"}}}
    ]
    result = await db.points_ledger.aggregate(pipeline).to_list(1)
    return result[0]["total"] if result else 0


# ============== SEED DEFAULT REWARDS ==============
async def seed_default_rewards():
    """Seed default rewards"""
    existing = await db.rewards.count_documents({"archived": False})
    if existing > 0:
        return {"message": "Prämien bereits vorhanden", "seeded": False}
    
    defaults = [
        {
            "name": "Kaffee nach Wahl",
            "description": "Cappuccino, Latte oder Espresso",
            "reward_type": "coffee",
            "points_cost": 20,
            "is_active": True
        },
        {
            "name": "Dessert des Tages",
            "description": "Ein Dessert Ihrer Wahl aus der Tageskarte",
            "reward_type": "dessert",
            "points_cost": 35,
            "is_active": True
        },
        {
            "name": "Hofladen-Gutschein 5€",
            "description": "Einzulösen im Hofladen",
            "reward_type": "product",
            "points_cost": 50,
            "is_active": True
        },
        {
            "name": "2-für-1 Hauptgericht",
            "description": "Mo-Do, beim Kauf eines Hauptgerichts das zweite gratis",
            "reward_type": "two_for_one",
            "points_cost": 80,
            "valid_weekdays": [0, 1, 2, 3],
            "not_combinable": True,
            "is_active": True
        },
        {
            "name": "10€ Event-Rabatt",
            "description": "Auf das nächste Event-Ticket",
            "reward_type": "event_discount",
            "points_cost": 100,
            "is_active": True
        }
    ]
    
    for reward_data in defaults:
        reward = create_entity(reward_data)
        await db.rewards.insert_one(reward)
    
    return {"message": "Standard-Prämien erstellt", "seeded": True, "count": len(defaults)}
