"""
GastroCore Payment Module - Sprint 4
Zahlungen für Reservierungen & Events
Provider: Stripe (abstrahiert für Wechsel)

ADDITIV - Keine Breaking Changes
"""

from fastapi import APIRouter, HTTPException, Depends, Request, BackgroundTasks
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from enum import Enum
import uuid
import os
import logging

from dotenv import load_dotenv
load_dotenv()

# Import from emergentintegrations
from emergentintegrations.payments.stripe.checkout import (
    StripeCheckout, 
    CheckoutSessionResponse, 
    CheckoutStatusResponse, 
    CheckoutSessionRequest
)

# Import from main server module
from core.database import db
from core.auth import require_admin, require_manager, get_current_user
from core.audit import create_audit_log, safe_dict_for_audit, SYSTEM_ACTOR
from core.exceptions import NotFoundException, ValidationException, ConflictException

logger = logging.getLogger(__name__)


# ============== ENUMS ==============
class PaymentStatus(str, Enum):
    UNPAID = "unpaid"
    PAYMENT_PENDING = "payment_pending"
    PAID = "paid"
    PARTIALLY_PAID = "partially_paid"
    REFUNDED = "refunded"
    FAILED = "failed"


class PaymentType(str, Enum):
    DEPOSIT_PER_PERSON = "deposit_per_person"  # Anzahlung pro Person
    FIXED_DEPOSIT = "fixed_deposit"  # Fixe Anzahlung
    FULL_PAYMENT = "full_payment"  # Komplettzahlung


class PaymentTrigger(str, Enum):
    EVENT = "event"
    HOLIDAY = "holiday"
    GROUP_SIZE = "group_size"
    GREYLIST = "greylist"


# ============== PYDANTIC MODELS ==============

class PaymentRuleCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    trigger: PaymentTrigger
    trigger_value: Optional[int] = None  # z.B. Gruppengröße X
    payment_type: PaymentType
    amount: float = Field(..., ge=0)  # Betrag in EUR
    deadline_hours: int = Field(default=0, ge=0)  # Stunden vor Reservierung
    is_active: bool = True
    description: Optional[str] = None


class PaymentRuleUpdate(BaseModel):
    name: Optional[str] = None
    trigger: Optional[PaymentTrigger] = None
    trigger_value: Optional[int] = None
    payment_type: Optional[PaymentType] = None
    amount: Optional[float] = None
    deadline_hours: Optional[int] = None
    is_active: Optional[bool] = None
    description: Optional[str] = None


class CreatePaymentRequest(BaseModel):
    entity_type: str = Field(..., pattern="^(reservation|event_booking)$")
    entity_id: str
    origin_url: str  # Frontend origin for redirect URLs


class ManualPaymentRequest(BaseModel):
    reason: str = Field(..., min_length=5, max_length=500)


class RefundRequest(BaseModel):
    reason: str = Field(..., min_length=5, max_length=500)


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


async def get_applicable_payment_rule(
    party_size: int = 0,
    is_event: bool = False,
    is_holiday: bool = False,
    is_greylist: bool = False
) -> Optional[dict]:
    """Find the most appropriate payment rule based on conditions"""
    
    rules = await db.payment_rules.find({
        "is_active": True, 
        "archived": False
    }).to_list(100)
    
    applicable_rules = []
    
    for rule in rules:
        trigger = rule.get("trigger")
        
        if trigger == "event" and is_event:
            applicable_rules.append(rule)
        elif trigger == "holiday" and is_holiday:
            applicable_rules.append(rule)
        elif trigger == "group_size" and party_size >= rule.get("trigger_value", 999):
            applicable_rules.append(rule)
        elif trigger == "greylist" and is_greylist:
            applicable_rules.append(rule)
    
    # Return the rule with highest amount (most restrictive)
    if applicable_rules:
        return max(applicable_rules, key=lambda r: r.get("amount", 0))
    
    return None


async def calculate_payment_amount(
    rule: dict,
    party_size: int,
    total_price: float = 0
) -> float:
    """Calculate payment amount based on rule type"""
    payment_type = rule.get("payment_type")
    amount = float(rule.get("amount", 0))
    
    if payment_type == "deposit_per_person":
        return float(amount * party_size)
    elif payment_type == "fixed_deposit":
        return float(amount)
    elif payment_type == "full_payment":
        return float(total_price) if total_price > 0 else float(amount * party_size)
    
    return 0.0


async def check_guest_greylist(phone: str) -> bool:
    """Check if guest is on greylist"""
    if not phone:
        return False
    guest = await db.guests.find_one({"phone": phone, "archived": False})
    return guest.get("flag") == "greylist" if guest else False


# ============== PAYMENT LOG ==============
async def create_payment_log(
    transaction_id: str,
    action: str,
    status: str,
    amount: float = None,
    provider_response: dict = None,
    actor: dict = None
):
    """Create payment audit log entry"""
    log_entry = {
        "id": str(uuid.uuid4()),
        "transaction_id": transaction_id,
        "action": action,
        "status": status,
        "amount": amount,
        "provider_response": provider_response,
        "actor": actor.get("email") if actor else "system",
        "timestamp": now_iso()
    }
    await db.payment_logs.insert_one(log_entry)
    return log_entry


# ============== ROUTER ==============
payment_router = APIRouter(prefix="/api/payments", tags=["Payments"])
payment_webhook_router = APIRouter(tags=["Payment Webhooks"])


# ============== PAYMENT RULES ENDPOINTS ==============
@payment_router.get("/rules")
async def list_payment_rules(user: dict = Depends(require_admin)):
    """List all payment rules"""
    rules = await db.payment_rules.find({"archived": False}, {"_id": 0}).to_list(100)
    return rules


@payment_router.post("/rules")
async def create_payment_rule(data: PaymentRuleCreate, user: dict = Depends(require_admin)):
    """Create a new payment rule"""
    rule = create_entity(data.model_dump())
    await db.payment_rules.insert_one(rule)
    await create_audit_log(user, "payment_rule", rule["id"], "create", None, safe_dict_for_audit(rule))
    return {k: v for k, v in rule.items() if k != "_id"}


@payment_router.patch("/rules/{rule_id}")
async def update_payment_rule(rule_id: str, data: PaymentRuleUpdate, user: dict = Depends(require_admin)):
    """Update a payment rule"""
    existing = await db.payment_rules.find_one({"id": rule_id, "archived": False}, {"_id": 0})
    if not existing:
        raise NotFoundException("Zahlungsregel")
    
    before = safe_dict_for_audit(existing)
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    update_data["updated_at"] = now_iso()
    
    await db.payment_rules.update_one({"id": rule_id}, {"$set": update_data})
    
    updated = await db.payment_rules.find_one({"id": rule_id}, {"_id": 0})
    await create_audit_log(user, "payment_rule", rule_id, "update", before, safe_dict_for_audit(updated))
    return updated


@payment_router.delete("/rules/{rule_id}")
async def archive_payment_rule(rule_id: str, user: dict = Depends(require_admin)):
    """Archive a payment rule"""
    existing = await db.payment_rules.find_one({"id": rule_id, "archived": False}, {"_id": 0})
    if not existing:
        raise NotFoundException("Zahlungsregel")
    
    await db.payment_rules.update_one({"id": rule_id}, {"$set": {"archived": True, "updated_at": now_iso()}})
    await create_audit_log(user, "payment_rule", rule_id, "archive", safe_dict_for_audit(existing), {**existing, "archived": True})
    return {"message": "Zahlungsregel archiviert", "success": True}


# ============== CHECK PAYMENT REQUIRED ==============
@payment_router.get("/check-required")
async def check_payment_required(
    entity_type: str,
    entity_id: str,
    party_size: int = 0,
    user: dict = Depends(require_manager)
):
    """Check if payment is required for a reservation/event"""
    
    is_event = entity_type == "event_booking"
    is_greylist = False
    total_price = 0.0
    
    if entity_type == "reservation":
        reservation = await db.reservations.find_one({"id": entity_id, "archived": False})
        if reservation:
            party_size = reservation.get("party_size", party_size)
            is_greylist = await check_guest_greylist(reservation.get("guest_phone"))
    elif entity_type == "event_booking":
        booking = await db.event_bookings.find_one({"id": entity_id, "archived": False})
        if booking:
            party_size = booking.get("party_size", party_size)
            total_price = float(booking.get("total_price", 0))
            # Get event to check if requires_payment
            event = await db.events.find_one({"id": booking.get("event_id")})
            if event and event.get("requires_payment"):
                is_event = True
    
    rule = await get_applicable_payment_rule(
        party_size=party_size,
        is_event=is_event,
        is_greylist=is_greylist
    )
    
    if not rule:
        return {
            "payment_required": False,
            "reason": None
        }
    
    amount = await calculate_payment_amount(rule, party_size, total_price)
    
    return {
        "payment_required": True,
        "rule_id": rule.get("id"),
        "rule_name": rule.get("name"),
        "payment_type": rule.get("payment_type"),
        "amount": amount,
        "currency": "EUR",
        "deadline_hours": rule.get("deadline_hours", 0),
        "reason": f"{rule.get('trigger')}: {rule.get('description', rule.get('name'))}"
    }


# ============== CREATE CHECKOUT SESSION ==============
@payment_router.post("/checkout/create")
async def create_checkout_session(
    request: Request,
    data: CreatePaymentRequest,
    user: dict = Depends(require_manager)
):
    """Create a Stripe checkout session for payment"""
    
    api_key = os.environ.get("STRIPE_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="Stripe nicht konfiguriert")
    
    # Get entity details
    entity = None
    entity_name = ""
    party_size = 0
    total_price = 0.0
    guest_email = None
    is_event = data.entity_type == "event_booking"
    is_greylist = False
    
    if data.entity_type == "reservation":
        entity = await db.reservations.find_one({"id": data.entity_id, "archived": False})
        if not entity:
            raise NotFoundException("Reservierung")
        entity_name = f"Reservierung {entity.get('date')} {entity.get('time')}"
        party_size = entity.get("party_size", 1)
        guest_email = entity.get("guest_email")
        is_greylist = await check_guest_greylist(entity.get("guest_phone"))
        
    elif data.entity_type == "event_booking":
        entity = await db.event_bookings.find_one({"id": data.entity_id, "archived": False})
        if not entity:
            raise NotFoundException("Event-Buchung")
        event = await db.events.find_one({"id": entity.get("event_id")})
        entity_name = f"Event: {event.get('title') if event else 'Event'}"
        party_size = entity.get("party_size", 1)
        total_price = float(entity.get("total_price", 0))
        guest_email = entity.get("guest_email")
    
    # Get applicable payment rule
    rule = await get_applicable_payment_rule(
        party_size=party_size,
        is_event=is_event,
        is_greylist=is_greylist
    )
    
    if not rule:
        raise ValidationException("Keine Zahlungsregel zutreffend")
    
    # Calculate amount
    amount = await calculate_payment_amount(rule, party_size, total_price)
    if amount <= 0:
        raise ValidationException("Ungültiger Zahlungsbetrag")
    
    # Create webhook URL
    host_url = str(request.base_url).rstrip('/')
    webhook_url = f"{host_url}/api/webhook/stripe"
    
    # Initialize Stripe
    stripe_checkout = StripeCheckout(api_key=api_key, webhook_url=webhook_url)
    
    # Build URLs from frontend origin
    origin_url = data.origin_url.rstrip('/')
    success_url = f"{origin_url}/payment/success?session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = f"{origin_url}/payment/cancel"
    
    # Metadata for tracking
    metadata = {
        "entity_type": data.entity_type,
        "entity_id": data.entity_id,
        "rule_id": rule.get("id"),
        "party_size": str(party_size),
        "source": "gastrocore"
    }
    
    # Create checkout session
    checkout_request = CheckoutSessionRequest(
        amount=float(amount),  # Must be float, not int
        currency="eur",
        success_url=success_url,
        cancel_url=cancel_url,
        metadata=metadata,
        payment_methods=["card"]  # Card, Apple Pay, Google Pay
    )
    
    try:
        session: CheckoutSessionResponse = await stripe_checkout.create_checkout_session(checkout_request)
    except Exception as e:
        logger.error(f"Stripe error: {e}")
        raise HTTPException(status_code=500, detail=f"Zahlungsfehler: {str(e)}")
    
    # Create payment transaction record
    transaction = {
        "id": str(uuid.uuid4()),
        "session_id": session.session_id,
        "entity_type": data.entity_type,
        "entity_id": data.entity_id,
        "amount": amount,
        "currency": "EUR",
        "payment_status": PaymentStatus.PAYMENT_PENDING.value,
        "payment_type": rule.get("payment_type"),
        "rule_id": rule.get("id"),
        "checkout_url": session.url,
        "metadata": metadata,
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "archived": False
    }
    
    await db.payment_transactions.insert_one(transaction)
    
    # Update entity payment status
    if data.entity_type == "reservation":
        await db.reservations.update_one(
            {"id": data.entity_id},
            {"$set": {
                "payment_status": PaymentStatus.PAYMENT_PENDING.value,
                "payment_amount": amount,
                "payment_transaction_id": transaction["id"],
                "updated_at": now_iso()
            }}
        )
    elif data.entity_type == "event_booking":
        await db.event_bookings.update_one(
            {"id": data.entity_id},
            {"$set": {
                "payment_status": PaymentStatus.PAYMENT_PENDING.value,
                "payment_amount": amount,
                "payment_transaction_id": transaction["id"],
                "updated_at": now_iso()
            }}
        )
    
    # Create payment log
    await create_payment_log(
        transaction_id=transaction["id"],
        action="checkout_created",
        status="pending",
        amount=amount,
        actor=user
    )
    
    return {
        "checkout_url": session.url,
        "session_id": session.session_id,
        "transaction_id": transaction["id"],
        "amount": amount,
        "currency": "EUR",
        "success": True
    }


# ============== CHECK PAYMENT STATUS ==============
@payment_router.get("/checkout/status/{session_id}")
async def get_checkout_status(session_id: str):
    """Get status of a checkout session (public for redirect handling)"""
    
    api_key = os.environ.get("STRIPE_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="Stripe nicht konfiguriert")
    
    # Find transaction
    transaction = await db.payment_transactions.find_one({"session_id": session_id})
    if not transaction:
        raise NotFoundException("Transaktion")
    
    # If already processed, return cached status
    if transaction.get("payment_status") in [PaymentStatus.PAID.value, PaymentStatus.FAILED.value, PaymentStatus.REFUNDED.value]:
        return {
            "status": transaction.get("payment_status"),
            "payment_status": transaction.get("payment_status"),
            "amount": transaction.get("amount"),
            "currency": transaction.get("currency"),
            "already_processed": True
        }
    
    # Check with Stripe
    stripe_checkout = StripeCheckout(api_key=api_key, webhook_url="")
    
    try:
        status: CheckoutStatusResponse = await stripe_checkout.get_checkout_status(session_id)
    except Exception as e:
        logger.error(f"Stripe status error: {e}")
        raise HTTPException(status_code=500, detail=f"Status-Fehler: {str(e)}")
    
    # Update transaction if payment completed
    new_status = None
    if status.payment_status == "paid":
        new_status = PaymentStatus.PAID.value
    elif status.status == "expired":
        new_status = PaymentStatus.FAILED.value
    
    if new_status and new_status != transaction.get("payment_status"):
        # ATOMIC UPDATE: Only update if status hasn't changed (prevents race conditions)
        result = await db.payment_transactions.update_one(
            {
                "session_id": session_id,
                "payment_status": {"$nin": [PaymentStatus.PAID.value, PaymentStatus.REFUNDED.value]}
            },
            {"$set": {
                "payment_status": new_status,
                "provider_status": status.status,
                "updated_at": now_iso()
            }}
        )
        
        # Only update entity if transaction was actually updated (idempotent)
        if result.modified_count > 0:
            entity_type = transaction.get("entity_type")
            entity_id = transaction.get("entity_id")
            
            if entity_type == "reservation":
                update_data = {"payment_status": new_status, "updated_at": now_iso()}
                if new_status == PaymentStatus.PAID.value:
                    update_data["status"] = "bestaetigt"  # Auto-confirm on payment
                await db.reservations.update_one({"id": entity_id}, {"$set": update_data})
                
            elif entity_type == "event_booking":
                update_data = {"payment_status": new_status, "updated_at": now_iso()}
                if new_status == PaymentStatus.PAID.value:
                    update_data["status"] = "confirmed"
                await db.event_bookings.update_one({"id": entity_id}, {"$set": update_data})
            
            # Create payment log
            await create_payment_log(
                transaction_id=transaction["id"],
                action="status_updated",
                status=new_status,
                amount=transaction.get("amount"),
                provider_response={"stripe_status": status.status, "payment_status": status.payment_status}
            )
            
            # Create audit log
            await create_audit_log(
                SYSTEM_ACTOR, 
                "payment_transaction", 
                transaction["id"], 
                "payment_completed" if new_status == PaymentStatus.PAID.value else "payment_failed",
                {"payment_status": transaction.get("payment_status")},
                {"payment_status": new_status}
            )
        else:
            # Already processed by webhook or another request
            new_status = None
    
    return {
        "status": status.status,
        "payment_status": new_status or transaction.get("payment_status"),
        "amount": status.amount_total / 100 if status.amount_total else transaction.get("amount"),
        "currency": status.currency or transaction.get("currency"),
        "already_processed": new_status is None and transaction.get("payment_status") == PaymentStatus.PAID.value
    }


# ============== STRIPE WEBHOOK ==============
@payment_webhook_router.post("/api/webhook/stripe")
async def handle_stripe_webhook(request: Request):
    """Handle Stripe webhook events"""
    
    api_key = os.environ.get("STRIPE_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="Stripe nicht konfiguriert")
    
    body = await request.body()
    signature = request.headers.get("Stripe-Signature")
    
    stripe_checkout = StripeCheckout(api_key=api_key, webhook_url="")
    
    try:
        webhook_response = await stripe_checkout.handle_webhook(body, signature)
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return {"status": "error", "message": str(e)}
    
    # Process webhook event
    event_type = webhook_response.event_type
    session_id = webhook_response.session_id
    payment_status = webhook_response.payment_status
    
    logger.info(f"Webhook: {event_type}, session: {session_id}, status: {payment_status}")
    
    # Find and update transaction
    transaction = await db.payment_transactions.find_one({"session_id": session_id})
    if transaction:
        new_status = None
        if payment_status == "paid":
            new_status = PaymentStatus.PAID.value
        elif event_type == "checkout.session.expired":
            new_status = PaymentStatus.FAILED.value
        
        if new_status:
            # ATOMIC UPDATE: Only update if not already in final state (idempotent webhook handling)
            result = await db.payment_transactions.update_one(
                {
                    "session_id": session_id,
                    "payment_status": {"$nin": [PaymentStatus.PAID.value, PaymentStatus.REFUNDED.value]}
                },
                {"$set": {"payment_status": new_status, "updated_at": now_iso()}}
            )
            
            # Only update entity if transaction was actually updated
            if result.modified_count > 0:
                entity_type = transaction.get("entity_type")
                entity_id = transaction.get("entity_id")
                
                if entity_type == "reservation":
                    update_data = {"payment_status": new_status, "updated_at": now_iso()}
                    if new_status == PaymentStatus.PAID.value:
                        update_data["status"] = "bestaetigt"
                    await db.reservations.update_one({"id": entity_id}, {"$set": update_data})
                    
                elif entity_type == "event_booking":
                    update_data = {"payment_status": new_status, "updated_at": now_iso()}
                    if new_status == PaymentStatus.PAID.value:
                        update_data["status"] = "confirmed"
                    await db.event_bookings.update_one({"id": entity_id}, {"$set": update_data})
                
                await create_payment_log(
                    transaction_id=transaction["id"],
                    action=f"webhook_{event_type}",
                    status=new_status,
                    provider_response={"event_type": event_type}
                )
                
                # Audit log for webhook
                await create_audit_log(
                    SYSTEM_ACTOR,
                    "payment_transaction",
                    transaction["id"],
                    f"webhook_{event_type}",
                    {"payment_status": transaction.get("payment_status")},
                    {"payment_status": new_status}
                )
            else:
                logger.info(f"Webhook {event_type} ignored - transaction already processed")
    
    return {"status": "ok"}


# ============== MANUAL PAYMENT (ADMIN) ==============
@payment_router.post("/manual/{transaction_id}")
async def mark_payment_manual(
    transaction_id: str,
    data: ManualPaymentRequest,
    user: dict = Depends(require_admin)
):
    """Manually mark a payment as received (Admin only, with reason)"""
    
    transaction = await db.payment_transactions.find_one({"id": transaction_id, "archived": False})
    if not transaction:
        raise NotFoundException("Transaktion")
    
    if transaction.get("payment_status") == PaymentStatus.PAID.value:
        raise ValidationException("Zahlung bereits als bezahlt markiert")
    
    before = safe_dict_for_audit(transaction)
    
    # Update transaction
    await db.payment_transactions.update_one(
        {"id": transaction_id},
        {"$set": {
            "payment_status": PaymentStatus.PAID.value,
            "manual_payment": True,
            "manual_reason": data.reason,
            "manual_by": user.get("email"),
            "updated_at": now_iso()
        }}
    )
    
    # Update entity
    entity_type = transaction.get("entity_type")
    entity_id = transaction.get("entity_id")
    
    if entity_type == "reservation":
        await db.reservations.update_one(
            {"id": entity_id},
            {"$set": {"payment_status": PaymentStatus.PAID.value, "status": "bestaetigt", "updated_at": now_iso()}}
        )
    elif entity_type == "event_booking":
        await db.event_bookings.update_one(
            {"id": entity_id},
            {"$set": {"payment_status": PaymentStatus.PAID.value, "status": "confirmed", "updated_at": now_iso()}}
        )
    
    # Create logs
    await create_payment_log(
        transaction_id=transaction_id,
        action="manual_payment",
        status=PaymentStatus.PAID.value,
        amount=transaction.get("amount"),
        actor=user
    )
    
    await create_audit_log(
        user, "payment_transaction", transaction_id, "manual_payment",
        before, {**before, "payment_status": PaymentStatus.PAID.value, "manual_reason": data.reason}
    )
    
    return {"message": "Zahlung manuell als erhalten markiert", "success": True}


# ============== RESEND PAYMENT LINK ==============
@payment_router.post("/resend/{transaction_id}")
async def resend_payment_link(transaction_id: str, user: dict = Depends(require_manager)):
    """Resend payment link (via email/WhatsApp)"""
    
    transaction = await db.payment_transactions.find_one({"id": transaction_id, "archived": False})
    if not transaction:
        raise NotFoundException("Transaktion")
    
    if transaction.get("payment_status") == PaymentStatus.PAID.value:
        raise ValidationException("Zahlung bereits abgeschlossen")
    
    checkout_url = transaction.get("checkout_url")
    if not checkout_url:
        raise ValidationException("Kein Zahlungslink vorhanden")
    
    await create_payment_log(
        transaction_id=transaction_id,
        action="link_resent",
        status=transaction.get("payment_status"),
        actor=user,
        provider_response={"checkout_url": checkout_url}
    )
    
    return {
        "checkout_url": checkout_url,
        "message": "Zahlungslink bereit zum Versenden",
        "success": True
    }


# ============== CANCEL PAYMENT (PUBLIC) ==============
@payment_router.post("/cancel/{session_id}")
async def cancel_payment(session_id: str):
    """Handle payment cancellation (called from cancel page)"""
    
    transaction = await db.payment_transactions.find_one({"session_id": session_id})
    if not transaction:
        raise NotFoundException("Transaktion")
    
    # Only update if still pending (idempotent)
    if transaction.get("payment_status") == PaymentStatus.PAYMENT_PENDING.value:
        result = await db.payment_transactions.update_one(
            {
                "session_id": session_id,
                "payment_status": PaymentStatus.PAYMENT_PENDING.value
            },
            {"$set": {
                "payment_status": PaymentStatus.FAILED.value,
                "cancel_reason": "user_cancelled",
                "updated_at": now_iso()
            }}
        )
        
        if result.modified_count > 0:
            # Update entity status
            entity_type = transaction.get("entity_type")
            entity_id = transaction.get("entity_id")
            
            if entity_type == "reservation":
                await db.reservations.update_one(
                    {"id": entity_id},
                    {"$set": {"payment_status": PaymentStatus.FAILED.value, "updated_at": now_iso()}}
                )
            elif entity_type == "event_booking":
                await db.event_bookings.update_one(
                    {"id": entity_id},
                    {"$set": {"payment_status": PaymentStatus.FAILED.value, "updated_at": now_iso()}}
                )
            
            await create_payment_log(
                transaction_id=transaction["id"],
                action="user_cancelled",
                status=PaymentStatus.FAILED.value,
                provider_response={"reason": "user_cancelled"}
            )
    
    return {
        "message": "Zahlung abgebrochen",
        "status": PaymentStatus.FAILED.value,
        "success": True
    }


# ============== REFUND ==============
@payment_router.post("/refund/{transaction_id}")
async def request_refund(
    transaction_id: str,
    data: RefundRequest,
    user: dict = Depends(require_admin)
):
    """Request a refund for a payment"""
    
    transaction = await db.payment_transactions.find_one({"id": transaction_id, "archived": False})
    if not transaction:
        raise NotFoundException("Transaktion")
    
    if transaction.get("payment_status") != PaymentStatus.PAID.value:
        raise ValidationException("Nur bezahlte Transaktionen können erstattet werden")
    
    # Note: In production, you would call Stripe refund API here
    # For now, we just update the status
    
    before = safe_dict_for_audit(transaction)
    
    await db.payment_transactions.update_one(
        {"id": transaction_id},
        {"$set": {
            "payment_status": PaymentStatus.REFUNDED.value,
            "refund_reason": data.reason,
            "refunded_by": user.get("email"),
            "refunded_at": now_iso(),
            "updated_at": now_iso()
        }}
    )
    
    # Update entity - also set status to cancelled/storniert on refund
    entity_type = transaction.get("entity_type")
    entity_id = transaction.get("entity_id")
    
    if entity_type == "reservation":
        await db.reservations.update_one(
            {"id": entity_id},
            {"$set": {
                "payment_status": PaymentStatus.REFUNDED.value,
                "status": "storniert",  # Also cancel the reservation
                "updated_at": now_iso()
            }}
        )
    elif entity_type == "event_booking":
        await db.event_bookings.update_one(
            {"id": entity_id},
            {"$set": {
                "payment_status": PaymentStatus.REFUNDED.value,
                "status": "cancelled",  # Also cancel the booking
                "updated_at": now_iso()
            }}
        )
        # Check if event can be reopened for bookings
        booking = await db.event_bookings.find_one({"id": entity_id})
        if booking:
            from events_module import update_event_status_if_needed, get_event_booked_count
            event = await db.events.find_one({"id": booking.get("event_id")})
            if event and event.get("status") == "sold_out":
                booked = await get_event_booked_count(booking.get("event_id"), include_pending=False)
                if booked < event.get("capacity_total", 0):
                    await db.events.update_one(
                        {"id": booking.get("event_id")},
                        {"$set": {"status": "published", "updated_at": now_iso()}}
                    )
    
    await create_payment_log(
        transaction_id=transaction_id,
        action="refund",
        status=PaymentStatus.REFUNDED.value,
        amount=transaction.get("amount"),
        actor=user,
        provider_response={"reason": data.reason}  # Log reason in provider_response
    )
    
    await create_audit_log(
        user, "payment_transaction", transaction_id, "refund",
        before, {**before, "payment_status": PaymentStatus.REFUNDED.value, "refund_reason": data.reason}
    )
    
    return {"message": "Erstattung durchgeführt", "success": True}


# ============== PAYMENT TRANSACTIONS LIST ==============
@payment_router.get("/transactions")
async def list_transactions(
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 100,
    user: dict = Depends(require_manager)
):
    """List payment transactions"""
    
    query = {"archived": False}
    if entity_type:
        query["entity_type"] = entity_type
    if entity_id:
        query["entity_id"] = entity_id
    if status:
        query["payment_status"] = status
    
    transactions = await db.payment_transactions.find(query, {"_id": 0}).sort("created_at", -1).limit(limit).to_list(limit)
    return transactions


# ============== PAYMENT LOGS ==============
@payment_router.get("/logs")
async def list_payment_logs(
    transaction_id: Optional[str] = None,
    limit: int = 100,
    user: dict = Depends(require_admin)
):
    """List payment logs"""
    
    query = {}
    if transaction_id:
        query["transaction_id"] = transaction_id
    
    logs = await db.payment_logs.find(query, {"_id": 0}).sort("timestamp", -1).limit(limit).to_list(limit)
    return logs


# ============== SEED DEFAULT RULES ==============
async def seed_payment_rules():
    """Seed default payment rules"""
    existing = await db.payment_rules.count_documents({"archived": False})
    if existing > 0:
        return {"message": "Zahlungsregeln bereits vorhanden", "seeded": False}
    
    defaults = [
        {
            "name": "Event-Zahlung",
            "trigger": "event",
            "trigger_value": None,
            "payment_type": "full_payment",
            "amount": 0,  # Uses event price
            "deadline_hours": 48,
            "is_active": True,
            "description": "Volle Zahlung für Event-Buchungen"
        },
        {
            "name": "Großgruppen-Anzahlung",
            "trigger": "group_size",
            "trigger_value": 8,
            "payment_type": "deposit_per_person",
            "amount": 10.0,
            "deadline_hours": 24,
            "is_active": True,
            "description": "10€ Anzahlung pro Person ab 8 Gästen"
        },
        {
            "name": "Greylist-Anzahlung",
            "trigger": "greylist",
            "trigger_value": None,
            "payment_type": "fixed_deposit",
            "amount": 25.0,
            "deadline_hours": 24,
            "is_active": True,
            "description": "25€ Anzahlung für Gäste auf der Greylist"
        }
    ]
    
    for rule_data in defaults:
        rule = create_entity(rule_data)
        await db.payment_rules.insert_one(rule)
    
    return {"message": "Standard-Zahlungsregeln erstellt", "seeded": True, "count": len(defaults)}
