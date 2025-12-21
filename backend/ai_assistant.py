"""
AI Assistant Module - Sprint 9
KI-Assistenz mit strikten Regeln:
- NUR Vorschläge, KEINE autonomen Aktionen
- Logging aller Vorschläge
- Jederzeit abschaltbar
- Keine sensiblen Daten
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone, timedelta
from enum import Enum
import uuid
import os
import logging
import json
from dotenv import load_dotenv

load_dotenv()

from emergentintegrations.llm.chat import LlmChat, UserMessage
from core.database import db
from core.auth import get_current_user, require_roles, require_admin, require_manager

logger = logging.getLogger(__name__)

# Router
ai_router = APIRouter(prefix="/api/ai", tags=["AI Assistant"])

# ============== ENUMS ==============
class AIFeature(str, Enum):
    SCHEDULE = "schedule"
    RESERVATION = "reservation"
    MARKETING = "marketing"

class SuggestionStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    MODIFIED = "modified"

# ============== PYDANTIC MODELS ==============
class ScheduleSuggestionRequest(BaseModel):
    week_start: str = Field(..., description="Start of week (YYYY-MM-DD)")
    staff_ids: Optional[List[str]] = None

class ReservationSuggestionRequest(BaseModel):
    date: str
    time: str
    party_size: int
    occasion: Optional[str] = None
    is_regular: bool = False

class MarketingSuggestionRequest(BaseModel):
    content_type: str = Field(..., pattern="^(newsletter|social)$")
    event_id: Optional[str] = None
    reward_id: Optional[str] = None
    target_audience: str = "newsletter_optin"
    language: str = "de"

class SuggestionDecision(BaseModel):
    accepted: bool
    modified_data: Optional[Dict[str, Any]] = None
    notes: Optional[str] = None

# ============== HELPER FUNCTIONS ==============
def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def get_llm_key() -> str:
    return os.environ.get("EMERGENT_LLM_KEY", "")

def is_ai_configured() -> bool:
    return bool(get_llm_key())

async def get_ai_settings() -> dict:
    """Get AI feature settings from database"""
    settings = await db.settings.find_one({"type": "ai_settings"}, {"_id": 0})
    if not settings:
        # Default: all disabled until explicitly enabled
        settings = {
            "type": "ai_settings",
            "enabled_global": False,
            "features": {
                "schedule": False,
                "reservation": False,
                "marketing": False
            },
            "updated_at": now_iso()
        }
        await db.settings.insert_one(settings)
    return settings

async def is_feature_enabled(feature: str) -> bool:
    """Check if specific AI feature is enabled"""
    settings = await get_ai_settings()
    if not settings.get("enabled_global", False):
        return False
    return settings.get("features", {}).get(feature, False)

async def log_ai_suggestion(
    feature: str,
    input_snapshot: dict,
    output_suggestion: dict,
    confidence_score: float,
    user_id: str
) -> str:
    """Log AI suggestion to ai_logs collection"""
    log_entry = {
        "id": str(uuid.uuid4()),
        "feature": feature,
        "input_snapshot": input_snapshot,  # Already sanitized
        "output_suggestion": output_suggestion,
        "confidence_score": confidence_score,
        "created_at": now_iso(),
        "accepted": None,  # Pending decision
        "decided_by": None,
        "decided_at": None,
        "requested_by": user_id
    }
    await db.ai_logs.insert_one(log_entry)
    return log_entry["id"]

async def update_ai_decision(
    log_id: str,
    accepted: bool,
    user_id: str,
    modified: bool = False
):
    """Update AI log with user decision"""
    status = "accepted" if accepted else "rejected"
    if modified:
        status = "modified"
    
    await db.ai_logs.update_one(
        {"id": log_id},
        {"$set": {
            "accepted": accepted,
            "status": status,
            "decided_by": user_id,
            "decided_at": now_iso()
        }}
    )

def sanitize_input(data: dict, exclude_fields: list = None) -> dict:
    """Remove sensitive fields from input data"""
    exclude_fields = exclude_fields or [
        "password", "password_hash", "token", "secret",
        "iban", "steuer_id", "sv_nummer", "bank_",
        "salary", "gehalt", "lohn"
    ]
    sanitized = {}
    for key, value in data.items():
        # Skip sensitive fields
        skip = False
        for exclude in exclude_fields:
            if exclude.lower() in key.lower():
                skip = True
                break
        if skip:
            continue
        
        # Recursively sanitize nested dicts
        if isinstance(value, dict):
            sanitized[key] = sanitize_input(value, exclude_fields)
        elif isinstance(value, list) and value and isinstance(value[0], dict):
            sanitized[key] = [sanitize_input(v, exclude_fields) for v in value]
        else:
            sanitized[key] = value
    
    return sanitized

# ============== LLM INTEGRATION ==============
async def generate_ai_suggestion(
    system_prompt: str,
    user_prompt: str,
    feature: str
) -> tuple[dict, float]:
    """Generate AI suggestion using Gemini"""
    if not is_ai_configured():
        raise HTTPException(
            status_code=503,
            detail="KI nicht konfiguriert (EMERGENT_LLM_KEY fehlt)"
        )
    
    try:
        chat = LlmChat(
            api_key=get_llm_key(),
            session_id=f"ai_assistant_{feature}_{uuid.uuid4().hex[:8]}",
            system_message=system_prompt
        ).with_model("gemini", "gemini-2.5-flash")
        
        user_message = UserMessage(text=user_prompt)
        response = await chat.send_message(user_message)
        
        # Parse JSON response
        # Try to extract JSON from response
        response_text = str(response)
        
        # Find JSON in response
        json_start = response_text.find("{")
        json_end = response_text.rfind("}") + 1
        
        if json_start != -1 and json_end > json_start:
            json_str = response_text[json_start:json_end]
            result = json.loads(json_str)
        else:
            # Fallback: create structured response
            result = {
                "suggestion": response_text,
                "reasoning": "KI-generierter Vorschlag",
                "confidence": 0.7
            }
        
        confidence = result.get("confidence", 0.7)
        return result, confidence
        
    except json.JSONDecodeError:
        logger.warning("Could not parse AI response as JSON")
        return {
            "suggestion": response_text,
            "reasoning": "Antwort konnte nicht strukturiert werden",
            "confidence": 0.5
        }, 0.5
    except Exception as e:
        logger.error(f"AI generation error: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"KI-Fehler: {str(e)}"
        )

# ============== SCHEDULE SUGGESTIONS ==============
SCHEDULE_SYSTEM_PROMPT = """Du bist ein Dienstplan-Assistent für ein Restaurant.
Deine Aufgabe ist es, VORSCHLÄGE für Schichtverteilungen zu machen.
Du darfst KEINE Entscheidungen treffen, nur Vorschläge mit Begründung liefern.

Antworte IMMER im folgenden JSON-Format:
{
    "suggestion": {
        "shifts": [
            {"staff_id": "...", "staff_name": "...", "day": "...", "shift_type": "...", "hours": ...}
        ],
        "summary": "Kurze Zusammenfassung"
    },
    "reasoning": "Ausführliche Begründung warum diese Verteilung sinnvoll ist",
    "considerations": ["Punkt 1", "Punkt 2"],
    "confidence": 0.8
}

Beachte:
- Gleichmäßige Verteilung der Stunden
- Sollstunden beachten
- Überstunden vermeiden
- Pausen einplanen"""

@ai_router.post("/schedule/suggest")
async def suggest_schedule(
    request: ScheduleSuggestionRequest,
    user: dict = Depends(require_manager)
):
    """Generate schedule suggestion (read-only, no data changes)"""
    if not await is_feature_enabled("schedule"):
        raise HTTPException(status_code=403, detail="Dienstplan-KI ist deaktiviert")
    
    # Gather READ-ONLY data
    staff_query = {"archived": {"$ne": True}}
    if request.staff_ids:
        staff_query["id"] = {"$in": request.staff_ids}
    
    staff_members = await db.staff_members.find(
        staff_query,
        {"_id": 0, "id": 1, "name": 1, "role": 1, "soll_hours_week": 1}
    ).to_list(100)
    
    # Get existing schedules for context
    existing_schedules = await db.schedules.find(
        {"week_start": request.week_start},
        {"_id": 0}
    ).to_list(100)
    
    # Sanitize input for logging
    input_snapshot = sanitize_input({
        "week_start": request.week_start,
        "staff_count": len(staff_members),
        "existing_shifts": len(existing_schedules)
    })
    
    # Build prompt
    user_prompt = f"""Erstelle einen Dienstplan-VORSCHLAG für die Woche ab {request.week_start}.

Verfügbare Mitarbeiter:
{json.dumps([{"id": s["id"], "name": s["name"], "soll_hours": s.get("soll_hours_week", 40)} for s in staff_members], indent=2, ensure_ascii=False)}

Bereits geplante Schichten: {len(existing_schedules)}

Erstelle einen ausgewogenen Vorschlag mit Begründung."""
    
    # Generate suggestion
    result, confidence = await generate_ai_suggestion(
        SCHEDULE_SYSTEM_PROMPT,
        user_prompt,
        "schedule"
    )
    
    # Log suggestion
    log_id = await log_ai_suggestion(
        "schedule",
        input_snapshot,
        result,
        confidence,
        user["id"]
    )
    
    return {
        "log_id": log_id,
        "suggestion": result.get("suggestion", {}),
        "reasoning": result.get("reasoning", ""),
        "considerations": result.get("considerations", []),
        "confidence_score": confidence,
        "disclaimer": "Dies ist nur ein VORSCHLAG. Änderungen werden erst nach Ihrer Bestätigung gespeichert."
    }

# ============== RESERVATION SUGGESTIONS ==============
RESERVATION_SYSTEM_PROMPT = """Du bist ein Reservierungs-Assistent für ein Restaurant.
Deine Aufgabe ist es, VORSCHLÄGE für Tisch- und Bereichszuweisungen zu machen.
Du darfst KEINE Buchungen vornehmen, nur Vorschläge mit Begründung liefern.

Antworte IMMER im folgenden JSON-Format:
{
    "suggestion": {
        "recommended_area": "Bereichsname",
        "alternative_areas": ["Alternative 1", "Alternative 2"],
        "recommended_time_slot": "18:00",
        "table_notes": "Empfehlung für Tischgröße"
    },
    "reasoning": "Ausführliche Begründung",
    "service_tips": ["Tipp 1", "Tipp 2"],
    "confidence": 0.8
}

Beachte:
- Gruppengröße passend zum Bereich
- Auslastung optimieren
- Service-Flow bedenken
- Stammgäste bevorzugen"""

@ai_router.post("/reservation/suggest")
async def suggest_reservation(
    request: ReservationSuggestionRequest,
    user: dict = Depends(require_manager)
):
    """Generate reservation suggestion (read-only, no data changes)"""
    if not await is_feature_enabled("reservation"):
        raise HTTPException(status_code=403, detail="Reservierungs-KI ist deaktiviert")
    
    # Gather READ-ONLY data
    areas = await db.areas.find(
        {"archived": {"$ne": True}},
        {"_id": 0, "id": 1, "name": 1, "min_capacity": 1, "max_capacity": 1}
    ).to_list(50)
    
    # Get existing reservations for the date
    existing = await db.reservations.find(
        {"date": request.date, "status": {"$nin": ["cancelled", "no_show"]}},
        {"_id": 0, "time": 1, "area_id": 1, "party_size": 1}
    ).to_list(200)
    
    # Calculate utilization per area
    area_utilization = {}
    for area in areas:
        area_reservations = [r for r in existing if r.get("area_id") == area["id"]]
        area_utilization[area["name"]] = len(area_reservations)
    
    # Sanitize input
    input_snapshot = sanitize_input({
        "date": request.date,
        "time": request.time,
        "party_size": request.party_size,
        "occasion": request.occasion,
        "is_regular": request.is_regular,
        "areas_available": len(areas),
        "existing_reservations": len(existing)
    })
    
    # Build prompt
    user_prompt = f"""Erstelle einen Reservierungs-VORSCHLAG.

Anfrage:
- Datum: {request.date}
- Uhrzeit: {request.time}
- Personenzahl: {request.party_size}
- Anlass: {request.occasion or "Nicht angegeben"}
- Stammgast: {"Ja" if request.is_regular else "Nein"}

Verfügbare Bereiche:
{json.dumps([{"name": a["name"], "kapazität": f"{a.get('min_capacity', 1)}-{a.get('max_capacity', 10)}"} for a in areas], indent=2, ensure_ascii=False)}

Aktuelle Auslastung:
{json.dumps(area_utilization, indent=2)}

Erstelle einen Vorschlag mit Begründung."""
    
    # Generate suggestion
    result, confidence = await generate_ai_suggestion(
        RESERVATION_SYSTEM_PROMPT,
        user_prompt,
        "reservation"
    )
    
    # Log suggestion
    log_id = await log_ai_suggestion(
        "reservation",
        input_snapshot,
        result,
        confidence,
        user["id"]
    )
    
    return {
        "log_id": log_id,
        "suggestion": result.get("suggestion", {}),
        "reasoning": result.get("reasoning", ""),
        "service_tips": result.get("service_tips", []),
        "confidence_score": confidence,
        "disclaimer": "Dies ist nur ein VORSCHLAG. Die Reservierung wird nicht automatisch geändert."
    }

# ============== MARKETING SUGGESTIONS ==============
MARKETING_SYSTEM_PROMPT = """Du bist ein Marketing-Texter für ein historisches Restaurant namens "Carlsburg".
Deine Aufgabe ist es, VORSCHLÄGE für Newsletter und Social Media Posts zu erstellen.
Der Ton ist: elegant, einladend, historisch angehaucht aber modern.

Antworte IMMER im folgenden JSON-Format:
{
    "suggestion": {
        "title": "Betreffzeile / Überschrift",
        "short_text": "Text für Social Media (max 280 Zeichen)",
        "html_body": "<h1>Newsletter HTML</h1><p>Inhalt...</p>",
        "hashtags": ["#carlsburg", "#restaurant"]
    },
    "reasoning": "Warum dieser Text gut funktioniert",
    "alternatives": ["Alternative Überschrift 1", "Alternative 2"],
    "confidence": 0.85
}

Sprachen: DE (Deutsch), EN (English), PL (Polski)
Beachte DSGVO: Keine persönlichen Daten im Text."""

@ai_router.post("/marketing/suggest")
async def suggest_marketing_text(
    request: MarketingSuggestionRequest,
    user: dict = Depends(require_manager)
):
    """Generate marketing text suggestion (read-only, no data changes)"""
    if not await is_feature_enabled("marketing"):
        raise HTTPException(status_code=403, detail="Marketing-KI ist deaktiviert")
    
    # Gather context (READ-ONLY)
    context = {"content_type": request.content_type, "language": request.language}
    
    if request.event_id:
        event = await db.events.find_one(
            {"id": request.event_id},
            {"_id": 0, "title": 1, "description": 1, "date": 1, "price_per_person": 1}
        )
        if event:
            context["event"] = sanitize_input(event)
    
    if request.reward_id:
        reward = await db.loyalty_rewards.find_one(
            {"id": request.reward_id},
            {"_id": 0, "title": 1, "description": 1, "points_cost": 1}
        )
        if reward:
            context["reward"] = sanitize_input(reward)
    
    # Sanitize input
    input_snapshot = sanitize_input(context)
    
    # Language mapping
    lang_map = {"de": "Deutsch", "en": "Englisch", "pl": "Polnisch"}
    
    # Build prompt
    event_text = ""
    if context.get("event"):
        e = context["event"]
        event_text = f"\nEvent: {e.get('title', '')} am {e.get('date', '')}. {e.get('description', '')}"
    
    reward_text = ""
    if context.get("reward"):
        r = context["reward"]
        reward_text = f"\nReward: {r.get('title', '')} für {r.get('points_cost', 0)} Punkte. {r.get('description', '')}"
    
    user_prompt = f"""Erstelle einen Marketing-Text-VORSCHLAG.

Typ: {request.content_type}
Sprache: {lang_map.get(request.language, 'Deutsch')}
Zielgruppe: {request.target_audience}
{event_text}
{reward_text}

Erstelle einen ansprechenden Text mit Begründung."""
    
    # Generate suggestion
    result, confidence = await generate_ai_suggestion(
        MARKETING_SYSTEM_PROMPT,
        user_prompt,
        "marketing"
    )
    
    # Log suggestion
    log_id = await log_ai_suggestion(
        "marketing",
        input_snapshot,
        result,
        confidence,
        user["id"]
    )
    
    return {
        "log_id": log_id,
        "suggestion": result.get("suggestion", {}),
        "reasoning": result.get("reasoning", ""),
        "alternatives": result.get("alternatives", []),
        "confidence_score": confidence,
        "disclaimer": "Dies ist nur ein VORSCHLAG. Der Text wird nicht automatisch veröffentlicht."
    }

# ============== DECISION ENDPOINTS ==============
@ai_router.post("/decision/{log_id}")
async def record_decision(
    log_id: str,
    decision: SuggestionDecision,
    user: dict = Depends(require_manager)
):
    """Record user decision on AI suggestion"""
    log_entry = await db.ai_logs.find_one({"id": log_id}, {"_id": 0})
    if not log_entry:
        raise HTTPException(status_code=404, detail="Vorschlag nicht gefunden")
    
    if log_entry.get("decided_at"):
        raise HTTPException(status_code=400, detail="Entscheidung bereits getroffen")
    
    modified = decision.modified_data is not None
    await update_ai_decision(log_id, decision.accepted, user["id"], modified)
    
    return {
        "success": True,
        "status": "modified" if modified else ("accepted" if decision.accepted else "rejected"),
        "message": "Entscheidung wurde protokolliert. KEINE automatischen Änderungen vorgenommen."
    }

# ============== ADMIN SETTINGS ==============
@ai_router.get("/settings")
async def get_ai_settings_endpoint(user: dict = Depends(require_manager)):
    """Get AI assistant settings"""
    settings = await get_ai_settings()
    return {
        **settings,
        "ai_configured": is_ai_configured()
    }

@ai_router.patch("/settings")
async def update_ai_settings(
    enabled_global: Optional[bool] = None,
    feature_schedule: Optional[bool] = None,
    feature_reservation: Optional[bool] = None,
    feature_marketing: Optional[bool] = None,
    user: dict = Depends(require_admin)
):
    """Update AI assistant settings (Admin only)"""
    settings = await get_ai_settings()
    
    updates = {"updated_at": now_iso(), "updated_by": user["id"]}
    
    if enabled_global is not None:
        updates["enabled_global"] = enabled_global
    
    if feature_schedule is not None:
        updates["features.schedule"] = feature_schedule
    if feature_reservation is not None:
        updates["features.reservation"] = feature_reservation
    if feature_marketing is not None:
        updates["features.marketing"] = feature_marketing
    
    await db.settings.update_one(
        {"type": "ai_settings"},
        {"$set": updates}
    )
    
    return await get_ai_settings()

# ============== LOGS ==============
@ai_router.get("/logs")
async def get_ai_logs(
    feature: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = Query(default=50, le=200),
    user: dict = Depends(require_manager)
):
    """Get AI suggestion logs"""
    query = {}
    if feature:
        query["feature"] = feature
    if status:
        if status == "pending":
            query["accepted"] = None
        elif status == "accepted":
            query["accepted"] = True
        elif status == "rejected":
            query["accepted"] = False
    
    logs = await db.ai_logs.find(query, {"_id": 0}).sort("created_at", -1).limit(limit).to_list(limit)
    return logs

# ============== STATUS ==============
@ai_router.get("/status")
async def get_ai_status(user: dict = Depends(require_manager)):
    """Get AI assistant status and statistics"""
    settings = await get_ai_settings()
    
    # Get statistics
    total_suggestions = await db.ai_logs.count_documents({})
    accepted = await db.ai_logs.count_documents({"accepted": True})
    rejected = await db.ai_logs.count_documents({"accepted": False})
    pending = await db.ai_logs.count_documents({"accepted": None})
    
    return {
        "ai_configured": is_ai_configured(),
        "enabled_global": settings.get("enabled_global", False),
        "features": settings.get("features", {}),
        "statistics": {
            "total_suggestions": total_suggestions,
            "accepted": accepted,
            "rejected": rejected,
            "pending": pending,
            "acceptance_rate": round(accepted / total_suggestions * 100, 1) if total_suggestions > 0 else 0
        },
        "model": "gemini-2.5-flash",
        "disclaimer": "KI macht NUR Vorschläge. Alle Änderungen erfordern menschliche Bestätigung."
    }
