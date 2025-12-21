"""
Audit Logging - Ensures every mutation is tracked
"""
from datetime import datetime, timezone
from typing import Dict, Any, Optional
import uuid

from .database import db
from .models import AuditAction


async def create_audit_log(
    actor: dict,
    entity: str,
    entity_id: str,
    action: str,
    before: Optional[Dict[str, Any]] = None,
    after: Optional[Dict[str, Any]] = None,
    metadata: Optional[Dict[str, Any]] = None
):
    """
    Create an audit log entry for any mutation.
    
    Args:
        actor: The user performing the action (must have 'id' and 'email')
        entity: The type of entity being modified (e.g., 'reservation', 'user')
        entity_id: The ID of the entity being modified
        action: The action being performed (see AuditAction enum)
        before: The state before the change (optional)
        after: The state after the change (optional)
        metadata: Additional metadata to include (optional)
    """
    audit_doc = {
        "id": str(uuid.uuid4()),
        "actor_id": actor.get("id", "unknown"),
        "actor_email": actor.get("email", "unknown"),
        "entity": entity,
        "entity_id": entity_id,
        "action": action,
        "before": safe_dict_for_audit(before),
        "after": safe_dict_for_audit(after),
        "metadata": metadata,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "ip_address": actor.get("ip_address"),  # Can be added from request
    }
    
    await db.audit_logs.insert_one(audit_doc)
    return audit_doc


def safe_dict_for_audit(obj: Optional[dict]) -> Optional[dict]:
    """
    Create a safe dictionary for audit logging.
    Removes sensitive fields and converts non-serializable types.
    """
    if obj is None:
        return None
    
    # Fields to exclude from audit logs
    sensitive_fields = {'password_hash', 'password', '_id', 'token'}
    
    result = {}
    for key, value in obj.items():
        if key in sensitive_fields:
            continue
        
        # Convert datetime to ISO string
        if isinstance(value, datetime):
            result[key] = value.isoformat()
        # Handle nested dicts recursively
        elif isinstance(value, dict):
            result[key] = safe_dict_for_audit(value)
        else:
            result[key] = value
    
    return result


def compute_diff(before: Optional[dict], after: Optional[dict]) -> dict:
    """
    Compute the difference between before and after states.
    Useful for displaying what changed in the UI.
    """
    if before is None:
        return {"added": after, "removed": None, "changed": {}}
    
    if after is None:
        return {"added": None, "removed": before, "changed": {}}
    
    changed = {}
    added = {}
    removed = {}
    
    all_keys = set(before.keys()) | set(after.keys())
    
    for key in all_keys:
        before_val = before.get(key)
        after_val = after.get(key)
        
        if key not in before:
            added[key] = after_val
        elif key not in after:
            removed[key] = before_val
        elif before_val != after_val:
            changed[key] = {"from": before_val, "to": after_val}
    
    return {"added": added, "removed": removed, "changed": changed}


# System actor for automated actions
SYSTEM_ACTOR = {
    "id": "system",
    "email": "system@gastrocore.local"
}
