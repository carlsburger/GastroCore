"""
Marketing Module - Sprint 8
Newsletter, Social Posting, Auto-Ausspielung
DSGVO-konform: Nur Opt-in, Freigabe erforderlich
"""
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Query
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone, timedelta
from enum import Enum
import uuid
import hashlib
import hmac
import logging
import os

from core.database import db
from core.auth import get_current_user, require_roles, require_admin, require_manager
from core.audit import create_audit_log

logger = logging.getLogger(__name__)

# Router
marketing_router = APIRouter(prefix="/api/marketing", tags=["Marketing"])
marketing_public_router = APIRouter(prefix="/api/public/marketing", tags=["Marketing Public"])

# ============== ENUMS ==============
class ContentType(str, Enum):
    NEWSLETTER = "newsletter"
    SOCIAL = "social"
    PUSH = "push"

class ContentStatus(str, Enum):
    DRAFT = "draft"
    REVIEW = "review"
    APPROVED = "approved"
    SCHEDULED = "scheduled"
    SENT = "sent"
    POSTED = "posted"
    FAILED = "failed"
    ARCHIVED = "archived"

class JobType(str, Enum):
    NEWSLETTER_SEND = "newsletter_send"
    SOCIAL_POST = "social_post"

class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"

class Audience(str, Enum):
    ALL_CUSTOMERS = "all_customers"
    NEWSLETTER_OPTIN = "newsletter_optin"
    LOYALTY_CUSTOMERS = "loyalty_customers"

# ============== PYDANTIC MODELS ==============
class MarketingContentCreate(BaseModel):
    title: str = Field(..., min_length=2, max_length=200)
    content_type: ContentType
    language: str = Field(default="de", pattern="^(de|en|pl)$")
    short_text: Optional[str] = Field(None, max_length=500)
    html_body: Optional[str] = None
    image_url: Optional[str] = None
    link_url: Optional[str] = None
    channels: List[str] = Field(default=["email"])
    audience: Audience = Audience.NEWSLETTER_OPTIN
    scheduled_at: Optional[datetime] = None

class MarketingContentUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=2, max_length=200)
    short_text: Optional[str] = Field(None, max_length=500)
    html_body: Optional[str] = None
    image_url: Optional[str] = None
    link_url: Optional[str] = None
    channels: Optional[List[str]] = None
    audience: Optional[Audience] = None
    scheduled_at: Optional[datetime] = None
    language: Optional[str] = Field(None, pattern="^(de|en|pl)$")

class SubmitForReviewRequest(BaseModel):
    notes: Optional[str] = None

class ApprovalRequest(BaseModel):
    approved: bool = True
    notes: Optional[str] = None

class ScheduleRequest(BaseModel):
    scheduled_at: datetime

class TestSendRequest(BaseModel):
    test_email: EmailStr

# ============== HELPER FUNCTIONS ==============
def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def generate_unsubscribe_token(customer_id: str) -> str:
    """Generate secure unsubscribe token"""
    secret = os.environ.get('JWT_SECRET', 'secret-key')
    message = f"unsubscribe:{customer_id}:{secret}"
    return hashlib.sha256(message.encode()).hexdigest()[:32]

def verify_unsubscribe_token(customer_id: str, token: str) -> bool:
    """Verify unsubscribe token"""
    expected = generate_unsubscribe_token(customer_id)
    return hmac.compare_digest(expected, token)

def get_unsubscribe_url(customer_id: str) -> str:
    """Generate unsubscribe URL"""
    app_url = os.environ.get('APP_URL', 'http://localhost:3000')
    token = generate_unsubscribe_token(customer_id)
    return f"{app_url}/unsubscribe/{customer_id}?token={token}"

def is_smtp_configured() -> bool:
    """Check if SMTP is configured"""
    smtp_user = os.environ.get('SMTP_USER', '')
    smtp_password = os.environ.get('SMTP_PASSWORD', '')
    return bool(smtp_user and smtp_password)

def is_social_configured(platform: str) -> bool:
    """Check if social platform is configured"""
    if platform == "facebook":
        return bool(os.environ.get('FACEBOOK_TOKEN') and os.environ.get('FACEBOOK_PAGE_ID'))
    elif platform == "instagram":
        return bool(os.environ.get('INSTAGRAM_TOKEN') and os.environ.get('INSTAGRAM_ACCOUNT_ID'))
    return False

# ============== SOCIAL CONNECTORS (Stubs) ==============
class SocialConnector:
    """Base class for social media connectors"""
    platform: str = "unknown"
    
    def is_configured(self) -> bool:
        return False
    
    async def post(self, content: dict) -> dict:
        """Post content to platform. Returns {success, post_id, error}"""
        return {"success": False, "error": "Not implemented"}

class FacebookConnector(SocialConnector):
    platform = "facebook"
    
    def is_configured(self) -> bool:
        return is_social_configured("facebook")
    
    async def post(self, content: dict) -> dict:
        if not self.is_configured():
            return {"success": False, "error": "Facebook not configured (FACEBOOK_TOKEN, FACEBOOK_PAGE_ID required)"}
        
        # Stub: Real implementation would use Facebook Graph API
        logger.info(f"[STUB] Would post to Facebook: {content.get('short_text', '')[:50]}...")
        return {
            "success": True, 
            "post_id": f"fb_stub_{uuid.uuid4().hex[:8]}",
            "note": "STUB - Facebook API not implemented"
        }

class InstagramConnector(SocialConnector):
    platform = "instagram"
    
    def is_configured(self) -> bool:
        return is_social_configured("instagram")
    
    async def post(self, content: dict) -> dict:
        if not self.is_configured():
            return {"success": False, "error": "Instagram not configured (INSTAGRAM_TOKEN, INSTAGRAM_ACCOUNT_ID required)"}
        
        # Stub: Real implementation would use Instagram Graph API
        logger.info(f"[STUB] Would post to Instagram: {content.get('short_text', '')[:50]}...")
        return {
            "success": True,
            "post_id": f"ig_stub_{uuid.uuid4().hex[:8]}",
            "note": "STUB - Instagram API not implemented"
        }

# Connector registry
SOCIAL_CONNECTORS = {
    "facebook": FacebookConnector(),
    "instagram": InstagramConnector(),
}

# ============== NEWSLETTER SENDING ==============
async def get_newsletter_recipients(audience: str, language: str = None) -> List[dict]:
    """Get recipients based on audience, respecting opt-in"""
    query = {"newsletter_optin": True, "archived": {"$ne": True}}
    
    if audience == Audience.LOYALTY_CUSTOMERS:
        # Only customers with points balance > 0
        query["points_balance"] = {"$gt": 0}
    
    if language:
        query["$or"] = [{"language": language}, {"language": {"$exists": False}}]
    
    customers = await db.customers.find(query, {"_id": 0}).to_list(10000)
    return customers

async def send_newsletter_to_recipient(content: dict, recipient: dict, job_id: str) -> bool:
    """Send newsletter to single recipient"""
    from email_service import send_email
    
    email = recipient.get("email")
    if not email:
        return False
    
    customer_id = recipient.get("id", "unknown")
    unsubscribe_url = get_unsubscribe_url(customer_id)
    
    # Add unsubscribe link to HTML
    html_body = content.get("html_body", "")
    if html_body and "{unsubscribe_url}" in html_body:
        html_body = html_body.replace("{unsubscribe_url}", unsubscribe_url)
    else:
        html_body += f'<br><br><p style="font-size:12px;color:#666;">Um sich abzumelden, klicken Sie <a href="{unsubscribe_url}">hier</a>.</p>'
    
    # Plain text version
    text_body = content.get("short_text", content.get("title", ""))
    text_body += f"\n\nAbmelden: {unsubscribe_url}"
    
    subject = content.get("title", "Newsletter")
    
    success = await send_email(email, subject, html_body, text_body, "newsletter")
    
    # Log
    await db.marketing_logs.insert_one({
        "id": str(uuid.uuid4()),
        "marketing_content_id": content.get("id"),
        "job_id": job_id,
        "channel": "email",
        "recipient_hash": hashlib.sha256(email.encode()).hexdigest()[:16],
        "status": "sent" if success else "failed",
        "timestamp": now_iso()
    })
    
    return success

async def run_newsletter_job(job_id: str, content_id: str):
    """Background task to send newsletter"""
    # Update job status
    await db.marketing_jobs.update_one(
        {"id": job_id},
        {"$set": {"status": JobStatus.RUNNING, "started_at": now_iso()}}
    )
    
    content = await db.marketing_content.find_one({"id": content_id}, {"_id": 0})
    if not content:
        await db.marketing_jobs.update_one(
            {"id": job_id},
            {"$set": {"status": JobStatus.FAILED, "error": "Content not found", "finished_at": now_iso()}}
        )
        return
    
    # Check SMTP
    if not is_smtp_configured():
        logger.warning("SMTP not configured - newsletter will be logged only")
    
    # Get recipients
    recipients = await get_newsletter_recipients(content.get("audience", Audience.NEWSLETTER_OPTIN), content.get("language"))
    
    stats = {
        "recipients_total": len(recipients),
        "recipients_sent": 0,
        "failures_count": 0
    }
    
    for recipient in recipients:
        try:
            success = await send_newsletter_to_recipient(content, recipient, job_id)
            if success:
                stats["recipients_sent"] += 1
            else:
                stats["failures_count"] += 1
        except Exception as e:
            logger.error(f"Error sending to recipient: {e}")
            stats["failures_count"] += 1
    
    # Update job
    final_status = JobStatus.DONE if stats["failures_count"] == 0 else JobStatus.FAILED
    await db.marketing_jobs.update_one(
        {"id": job_id},
        {"$set": {
            "status": final_status,
            "finished_at": now_iso(),
            "stats": stats
        }}
    )
    
    # Update content status
    await db.marketing_content.update_one(
        {"id": content_id},
        {"$set": {"status": ContentStatus.SENT, "updated_at": now_iso()}}
    )

async def run_social_post_job(job_id: str, content_id: str):
    """Background task to post to social media"""
    await db.marketing_jobs.update_one(
        {"id": job_id},
        {"$set": {"status": JobStatus.RUNNING, "started_at": now_iso()}}
    )
    
    content = await db.marketing_content.find_one({"id": content_id}, {"_id": 0})
    if not content:
        await db.marketing_jobs.update_one(
            {"id": job_id},
            {"$set": {"status": JobStatus.FAILED, "error": "Content not found", "finished_at": now_iso()}}
        )
        return
    
    channels = content.get("channels", [])
    results = {}
    all_success = True
    
    for channel in channels:
        if channel == "email":
            continue  # Email handled separately
        
        connector = SOCIAL_CONNECTORS.get(channel)
        if not connector:
            results[channel] = {"success": False, "error": f"Unknown platform: {channel}"}
            all_success = False
            continue
        
        result = await connector.post(content)
        results[channel] = result
        
        # Log
        await db.marketing_logs.insert_one({
            "id": str(uuid.uuid4()),
            "marketing_content_id": content_id,
            "job_id": job_id,
            "channel": channel,
            "platform_post_id": result.get("post_id"),
            "status": "posted" if result.get("success") else "failed",
            "error": result.get("error"),
            "timestamp": now_iso()
        })
        
        if not result.get("success"):
            all_success = False
    
    # Update job
    final_status = JobStatus.DONE if all_success else JobStatus.FAILED
    await db.marketing_jobs.update_one(
        {"id": job_id},
        {"$set": {
            "status": final_status,
            "finished_at": now_iso(),
            "stats": {"results": results}
        }}
    )
    
    # Update content status
    new_status = ContentStatus.POSTED if all_success else ContentStatus.FAILED
    await db.marketing_content.update_one(
        {"id": content_id},
        {"$set": {"status": new_status, "updated_at": now_iso()}}
    )

# ============== API ENDPOINTS ==============

# --- Content CRUD ---
@marketing_router.get("", response_model=List[dict])
async def list_marketing_content(
    status: Optional[str] = None,
    content_type: Optional[str] = None,
    language: Optional[str] = None,
    limit: int = Query(default=50, le=200),
    user: dict = Depends(require_manager)
):
    """List marketing content (Admin + Schichtleiter)"""
    query = {"archived": {"$ne": True}}
    
    if status:
        query["status"] = status
    if content_type:
        query["content_type"] = content_type
    if language:
        query["language"] = language
    
    items = await db.marketing_content.find(query, {"_id": 0}).sort("created_at", -1).limit(limit).to_list(limit)
    return items

@marketing_router.get("/{content_id}")
async def get_marketing_content(content_id: str, user: dict = Depends(require_manager)):
    """Get single marketing content"""
    content = await db.marketing_content.find_one({"id": content_id}, {"_id": 0})
    if not content:
        raise HTTPException(status_code=404, detail="Content nicht gefunden")
    return content

@marketing_router.post("", status_code=201)
async def create_marketing_content(
    data: MarketingContentCreate,
    user: dict = Depends(require_manager)
):
    """Create marketing content (Admin + Schichtleiter)"""
    content = {
        "id": str(uuid.uuid4()),
        "title": data.title,
        "content_type": data.content_type,
        "language": data.language,
        "short_text": data.short_text,
        "html_body": data.html_body,
        "image_url": data.image_url,
        "link_url": data.link_url,
        "channels": data.channels,
        "audience": data.audience,
        "scheduled_at": data.scheduled_at.isoformat() if data.scheduled_at else None,
        "status": ContentStatus.DRAFT,
        "created_by": {"id": user["id"], "name": user["name"], "email": user["email"]},
        "approved_by": None,
        "approved_at": None,
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "archived": False
    }
    
    await db.marketing_content.insert_one(content)
    
    await create_audit_log(
        user, "marketing_content", content["id"], "create",
        None, {"title": content["title"], "type": content["content_type"]}
    )
    
    # Remove _id before returning (MongoDB adds it)
    content.pop("_id", None)
    return content

@marketing_router.patch("/{content_id}")
async def update_marketing_content(
    content_id: str,
    data: MarketingContentUpdate,
    user: dict = Depends(require_manager)
):
    """Update marketing content (only if draft or review)"""
    content = await db.marketing_content.find_one({"id": content_id}, {"_id": 0})
    if not content:
        raise HTTPException(status_code=404, detail="Content nicht gefunden")
    
    if content["status"] not in [ContentStatus.DRAFT, ContentStatus.REVIEW]:
        raise HTTPException(status_code=400, detail="Nur Entwürfe können bearbeitet werden")
    
    updates = {k: v for k, v in data.model_dump().items() if v is not None}
    updates["updated_at"] = now_iso()
    
    await db.marketing_content.update_one({"id": content_id}, {"$set": updates})
    
    await create_audit_log(
        user, "marketing_content", content_id, "update",
        {"status": content["status"]}, updates
    )
    
    return {**content, **updates}

@marketing_router.delete("/{content_id}")
async def archive_marketing_content(content_id: str, user: dict = Depends(require_admin)):
    """Archive marketing content (Admin only)"""
    content = await db.marketing_content.find_one({"id": content_id}, {"_id": 0})
    if not content:
        raise HTTPException(status_code=404, detail="Content nicht gefunden")
    
    await db.marketing_content.update_one(
        {"id": content_id},
        {"$set": {"status": ContentStatus.ARCHIVED, "archived": True, "updated_at": now_iso()}}
    )
    
    await create_audit_log(user, "marketing_content", content_id, "archive", None, None)
    
    return {"success": True}

# --- Workflow ---
@marketing_router.post("/{content_id}/submit-review")
async def submit_for_review(
    content_id: str,
    data: SubmitForReviewRequest,
    user: dict = Depends(require_manager)
):
    """Submit content for review (Admin + Schichtleiter)"""
    content = await db.marketing_content.find_one({"id": content_id}, {"_id": 0})
    if not content:
        raise HTTPException(status_code=404, detail="Content nicht gefunden")
    
    if content["status"] != ContentStatus.DRAFT:
        raise HTTPException(status_code=400, detail="Nur Entwürfe können eingereicht werden")
    
    await db.marketing_content.update_one(
        {"id": content_id},
        {"$set": {"status": ContentStatus.REVIEW, "review_notes": data.notes, "updated_at": now_iso()}}
    )
    
    await create_audit_log(user, "marketing_content", content_id, "submit_review", None, {"notes": data.notes})
    
    return {"success": True, "status": ContentStatus.REVIEW}

@marketing_router.post("/{content_id}/approve")
async def approve_content(
    content_id: str,
    data: ApprovalRequest,
    user: dict = Depends(require_admin)
):
    """Approve or reject content (Admin only)"""
    content = await db.marketing_content.find_one({"id": content_id}, {"_id": 0})
    if not content:
        raise HTTPException(status_code=404, detail="Content nicht gefunden")
    
    if content["status"] not in [ContentStatus.REVIEW, ContentStatus.DRAFT]:
        raise HTTPException(status_code=400, detail="Content kann nicht freigegeben werden")
    
    if data.approved:
        new_status = ContentStatus.APPROVED
        await db.marketing_content.update_one(
            {"id": content_id},
            {"$set": {
                "status": new_status,
                "approved_by": {"id": user["id"], "name": user["name"]},
                "approved_at": now_iso(),
                "approval_notes": data.notes,
                "updated_at": now_iso()
            }}
        )
    else:
        new_status = ContentStatus.DRAFT
        await db.marketing_content.update_one(
            {"id": content_id},
            {"$set": {"status": new_status, "rejection_notes": data.notes, "updated_at": now_iso()}}
        )
    
    await create_audit_log(
        user, "marketing_content", content_id,
        "approve" if data.approved else "reject",
        None, {"approved": data.approved, "notes": data.notes}
    )
    
    return {"success": True, "status": new_status}

@marketing_router.post("/{content_id}/schedule")
async def schedule_content(
    content_id: str,
    data: ScheduleRequest,
    user: dict = Depends(require_admin)
):
    """Schedule approved content (Admin only)"""
    content = await db.marketing_content.find_one({"id": content_id}, {"_id": 0})
    if not content:
        raise HTTPException(status_code=404, detail="Content nicht gefunden")
    
    if content["status"] != ContentStatus.APPROVED:
        raise HTTPException(status_code=400, detail="Nur freigegebene Inhalte können geplant werden")
    
    if data.scheduled_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Geplanter Zeitpunkt muss in der Zukunft liegen")
    
    await db.marketing_content.update_one(
        {"id": content_id},
        {"$set": {
            "status": ContentStatus.SCHEDULED,
            "scheduled_at": data.scheduled_at.isoformat(),
            "updated_at": now_iso()
        }}
    )
    
    await create_audit_log(user, "marketing_content", content_id, "schedule", None, {"scheduled_at": data.scheduled_at.isoformat()})
    
    return {"success": True, "scheduled_at": data.scheduled_at.isoformat()}

# --- Sending/Posting ---
@marketing_router.post("/{content_id}/send-test")
async def send_test_newsletter(
    content_id: str,
    data: TestSendRequest,
    background_tasks: BackgroundTasks,
    user: dict = Depends(require_admin)
):
    """Send test newsletter to single email (Admin only)"""
    content = await db.marketing_content.find_one({"id": content_id}, {"_id": 0})
    if not content:
        raise HTTPException(status_code=404, detail="Content nicht gefunden")
    
    if content["content_type"] != ContentType.NEWSLETTER:
        raise HTTPException(status_code=400, detail="Nur Newsletter können als Test gesendet werden")
    
    # Create fake recipient for test
    test_recipient = {"id": "test", "email": data.test_email, "name": "Test"}
    
    smtp_configured = is_smtp_configured()
    
    # Send immediately (not as job)
    success = await send_newsletter_to_recipient(content, test_recipient, f"test_{content_id}")
    
    await create_audit_log(user, "marketing_content", content_id, "test_send", None, {"to": data.test_email, "smtp_configured": smtp_configured})
    
    return {
        "success": success or not smtp_configured,
        "smtp_configured": smtp_configured,
        "message": "Test gesendet" if smtp_configured else "SMTP nicht konfiguriert - nur geloggt"
    }

@marketing_router.post("/{content_id}/send-now")
async def send_newsletter_now(
    content_id: str,
    background_tasks: BackgroundTasks,
    user: dict = Depends(require_admin)
):
    """Send newsletter immediately (Admin only, must be approved)"""
    content = await db.marketing_content.find_one({"id": content_id}, {"_id": 0})
    if not content:
        raise HTTPException(status_code=404, detail="Content nicht gefunden")
    
    if content["status"] not in [ContentStatus.APPROVED, ContentStatus.SCHEDULED]:
        raise HTTPException(status_code=400, detail="Nur freigegebene Inhalte können versendet werden")
    
    if content["content_type"] != ContentType.NEWSLETTER:
        raise HTTPException(status_code=400, detail="Nur Newsletter können versendet werden")
    
    # Create job
    job = {
        "id": str(uuid.uuid4()),
        "job_type": JobType.NEWSLETTER_SEND,
        "marketing_content_id": content_id,
        "status": JobStatus.PENDING,
        "started_at": None,
        "finished_at": None,
        "error": None,
        "stats": {},
        "created_at": now_iso()
    }
    await db.marketing_jobs.insert_one(job)
    
    # Start background task
    background_tasks.add_task(run_newsletter_job, job["id"], content_id)
    
    await create_audit_log(user, "marketing_content", content_id, "send_newsletter", None, {"job_id": job["id"]})
    
    return {"success": True, "job_id": job["id"], "smtp_configured": is_smtp_configured()}

@marketing_router.post("/{content_id}/post-now")
async def post_social_now(
    content_id: str,
    background_tasks: BackgroundTasks,
    user: dict = Depends(require_admin)
):
    """Post to social media immediately (Admin only, must be approved)"""
    content = await db.marketing_content.find_one({"id": content_id}, {"_id": 0})
    if not content:
        raise HTTPException(status_code=404, detail="Content nicht gefunden")
    
    if content["status"] not in [ContentStatus.APPROVED, ContentStatus.SCHEDULED]:
        raise HTTPException(status_code=400, detail="Nur freigegebene Inhalte können gepostet werden")
    
    if content["content_type"] != ContentType.SOCIAL:
        raise HTTPException(status_code=400, detail="Nur Social-Inhalte können gepostet werden")
    
    # Create job
    job = {
        "id": str(uuid.uuid4()),
        "job_type": JobType.SOCIAL_POST,
        "marketing_content_id": content_id,
        "status": JobStatus.PENDING,
        "started_at": None,
        "finished_at": None,
        "error": None,
        "stats": {},
        "created_at": now_iso()
    }
    await db.marketing_jobs.insert_one(job)
    
    # Start background task
    background_tasks.add_task(run_social_post_job, job["id"], content_id)
    
    # Check which platforms are configured
    channels = content.get("channels", [])
    config_status = {ch: is_social_configured(ch) for ch in channels if ch != "email"}
    
    await create_audit_log(user, "marketing_content", content_id, "post_social", None, {"job_id": job["id"]})
    
    return {"success": True, "job_id": job["id"], "platform_config": config_status}

@marketing_router.post("/{content_id}/retry")
async def retry_failed_content(
    content_id: str,
    background_tasks: BackgroundTasks,
    user: dict = Depends(require_admin)
):
    """Retry failed content (Admin only)"""
    content = await db.marketing_content.find_one({"id": content_id}, {"_id": 0})
    if not content:
        raise HTTPException(status_code=404, detail="Content nicht gefunden")
    
    if content["status"] != ContentStatus.FAILED:
        raise HTTPException(status_code=400, detail="Nur fehlgeschlagene Inhalte können wiederholt werden")
    
    # Reset to approved
    await db.marketing_content.update_one(
        {"id": content_id},
        {"$set": {"status": ContentStatus.APPROVED, "updated_at": now_iso()}}
    )
    
    # Determine job type and retry
    if content["content_type"] == ContentType.NEWSLETTER:
        job = {
            "id": str(uuid.uuid4()),
            "job_type": JobType.NEWSLETTER_SEND,
            "marketing_content_id": content_id,
            "status": JobStatus.PENDING,
            "created_at": now_iso()
        }
        await db.marketing_jobs.insert_one(job)
        background_tasks.add_task(run_newsletter_job, job["id"], content_id)
    else:
        job = {
            "id": str(uuid.uuid4()),
            "job_type": JobType.SOCIAL_POST,
            "marketing_content_id": content_id,
            "status": JobStatus.PENDING,
            "created_at": now_iso()
        }
        await db.marketing_jobs.insert_one(job)
        background_tasks.add_task(run_social_post_job, job["id"], content_id)
    
    await create_audit_log(user, "marketing_content", content_id, "retry", None, {"job_id": job["id"]})
    
    return {"success": True, "job_id": job["id"]}

# --- Jobs & Logs ---
@marketing_router.get("/jobs/list")
async def list_jobs(
    status: Optional[str] = None,
    limit: int = Query(default=50, le=200),
    user: dict = Depends(require_manager)
):
    """List marketing jobs"""
    query = {}
    if status:
        query["status"] = status
    
    jobs = await db.marketing_jobs.find(query, {"_id": 0}).sort("created_at", -1).limit(limit).to_list(limit)
    return jobs

@marketing_router.get("/logs/{content_id}")
async def get_content_logs(
    content_id: str,
    limit: int = Query(default=100, le=500),
    user: dict = Depends(require_manager)
):
    """Get logs for specific content"""
    logs = await db.marketing_logs.find(
        {"marketing_content_id": content_id},
        {"_id": 0}
    ).sort("timestamp", -1).limit(limit).to_list(limit)
    return logs

# --- Config Status ---
@marketing_router.get("/config/status")
async def get_config_status(user: dict = Depends(require_manager)):
    """Get configuration status for marketing channels"""
    return {
        "smtp_configured": is_smtp_configured(),
        "facebook_configured": is_social_configured("facebook"),
        "instagram_configured": is_social_configured("instagram"),
        "smtp_host": os.environ.get('SMTP_HOST', 'not set'),
        "note": "Social connectors are stubs - real API integration pending"
    }

# ============== PUBLIC ENDPOINTS ==============
@marketing_public_router.post("/unsubscribe")
async def unsubscribe(customer_id: str, token: str):
    """Unsubscribe from newsletter"""
    if not verify_unsubscribe_token(customer_id, token):
        raise HTTPException(status_code=400, detail="Ungültiger Abmelde-Link")
    
    result = await db.customers.update_one(
        {"id": customer_id},
        {"$set": {"newsletter_optin": False, "unsubscribed_at": now_iso()}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Kunde nicht gefunden")
    
    await db.marketing_logs.insert_one({
        "id": str(uuid.uuid4()),
        "marketing_content_id": None,
        "channel": "unsubscribe",
        "recipient_hash": hashlib.sha256(customer_id.encode()).hexdigest()[:16],
        "status": "unsubscribed",
        "timestamp": now_iso()
    })
    
    return {"success": True, "message": "Sie wurden erfolgreich abgemeldet"}

@marketing_public_router.get("/unsubscribe/confirm")
async def unsubscribe_confirm_page(customer_id: str, token: str):
    """Confirmation page data for unsubscribe"""
    if not verify_unsubscribe_token(customer_id, token):
        return {"valid": False, "message": "Ungültiger Abmelde-Link"}
    
    customer = await db.customers.find_one({"id": customer_id}, {"_id": 0, "email": 1, "newsletter_optin": 1})
    if not customer:
        return {"valid": False, "message": "Kunde nicht gefunden"}
    
    return {
        "valid": True,
        "already_unsubscribed": not customer.get("newsletter_optin", True),
        "email_masked": customer.get("email", "")[:3] + "***" if customer.get("email") else None
    }

# ============== SCHEDULER HELPER ==============
async def process_scheduled_content():
    """Process scheduled content (called by scheduler/cron)"""
    now = datetime.now(timezone.utc)
    
    # Find scheduled content that's due
    scheduled = await db.marketing_content.find({
        "status": ContentStatus.SCHEDULED,
        "scheduled_at": {"$lte": now.isoformat()}
    }, {"_id": 0}).to_list(100)
    
    for content in scheduled:
        content_id = content["id"]
        
        if content["content_type"] == ContentType.NEWSLETTER:
            job = {
                "id": str(uuid.uuid4()),
                "job_type": JobType.NEWSLETTER_SEND,
                "marketing_content_id": content_id,
                "status": JobStatus.PENDING,
                "created_at": now_iso()
            }
            await db.marketing_jobs.insert_one(job)
            await run_newsletter_job(job["id"], content_id)
        
        elif content["content_type"] == ContentType.SOCIAL:
            job = {
                "id": str(uuid.uuid4()),
                "job_type": JobType.SOCIAL_POST,
                "marketing_content_id": content_id,
                "status": JobStatus.PENDING,
                "created_at": now_iso()
            }
            await db.marketing_jobs.insert_one(job)
            await run_social_post_job(job["id"], content_id)

# Endpoint to trigger scheduler manually (Admin)
@marketing_router.post("/scheduler/run")
async def run_scheduler(user: dict = Depends(require_admin)):
    """Manually run the scheduler to process due content"""
    await process_scheduled_content()
    return {"success": True, "message": "Scheduler ausgeführt"}

# ============== AUTO-DRAFT SUGGESTIONS ==============
async def create_event_marketing_draft(event: dict, actor: dict):
    """Create draft marketing content when event is published"""
    content = {
        "id": str(uuid.uuid4()),
        "title": f"Neues Event: {event.get('title', 'Veranstaltung')}",
        "content_type": ContentType.SOCIAL,
        "language": "de",
        "short_text": f"🎉 {event.get('title')} am {event.get('date', '')}! Jetzt buchen.",
        "html_body": None,
        "image_url": event.get("image_url"),
        "link_url": event.get("booking_url"),
        "channels": ["facebook", "instagram"],
        "audience": Audience.ALL_CUSTOMERS,
        "status": ContentStatus.DRAFT,
        "created_by": {"id": "system", "name": "Auto-Draft", "email": "system"},
        "auto_generated": True,
        "source_event_id": event.get("id"),
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "archived": False
    }
    
    await db.marketing_content.insert_one(content)
    logger.info(f"Auto-created marketing draft for event {event.get('id')}")
    return content
