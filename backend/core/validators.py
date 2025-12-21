"""
Extended Validators for Sprint 2
"""
from datetime import datetime, timezone, timedelta
from typing import Optional

from .config import settings
from .models import ReservationStatus, WaitlistStatus
from .exceptions import ValidationException, InvalidStatusTransitionException


def validate_status_transition(current_status: str, new_status: str) -> bool:
    """Validate reservation status transition"""
    allowed_transitions = settings.STATUS_TRANSITIONS.get(current_status, [])
    
    if new_status not in allowed_transitions:
        raise InvalidStatusTransitionException(current_status, new_status)
    
    return True


def validate_waitlist_status_transition(current: str, new: str) -> bool:
    """Validate waitlist status transition"""
    allowed = {
        "offen": ["informiert", "erledigt"],
        "informiert": ["eingeloest", "erledigt"],
        "eingeloest": ["erledigt"],
        "erledigt": []
    }
    
    if new not in allowed.get(current, []):
        raise InvalidStatusTransitionException(current, new)
    
    return True


def validate_reservation_data(data: dict, is_update: bool = False) -> dict:
    """Validate reservation data"""
    errors = []
    
    # Party size validation
    party_size = data.get("party_size")
    if party_size is not None:
        if party_size < settings.MIN_PARTY_SIZE:
            errors.append(f"Personenzahl muss mindestens {settings.MIN_PARTY_SIZE} sein")
        if party_size > settings.MAX_PARTY_SIZE:
            errors.append(f"Personenzahl darf maximal {settings.MAX_PARTY_SIZE} sein")
    elif not is_update:
        errors.append("Personenzahl ist erforderlich")
    
    # Date validation
    date_str = data.get("date")
    if date_str:
        try:
            reservation_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            today = datetime.now(timezone.utc).date()
            
            if reservation_date < today:
                errors.append("Reservierungsdatum kann nicht in der Vergangenheit liegen")
            
            max_date = today + timedelta(days=settings.RESERVATION_ADVANCE_DAYS)
            if reservation_date > max_date:
                errors.append(f"Reservierung kann maximal {settings.RESERVATION_ADVANCE_DAYS} Tage im Voraus erfolgen")
        except ValueError:
            errors.append("Ungültiges Datumsformat (erwartet: YYYY-MM-DD)")
    elif not is_update:
        errors.append("Datum ist erforderlich")
    
    # Time validation
    time_str = data.get("time")
    if time_str:
        try:
            datetime.strptime(time_str, "%H:%M")
        except ValueError:
            errors.append("Ungültiges Zeitformat (erwartet: HH:MM)")
    elif not is_update:
        errors.append("Uhrzeit ist erforderlich")
    
    # Guest name validation
    guest_name = data.get("guest_name")
    if guest_name:
        if len(guest_name.strip()) < 2:
            errors.append("Gastname muss mindestens 2 Zeichen lang sein")
    elif not is_update:
        errors.append("Gastname ist erforderlich")
    
    # Phone validation
    guest_phone = data.get("guest_phone")
    if guest_phone:
        cleaned_phone = guest_phone.replace(" ", "").replace("-", "").replace("/", "")
        if len(cleaned_phone) < 6:
            errors.append("Telefonnummer ist zu kurz")
    elif not is_update:
        errors.append("Telefonnummer ist erforderlich")
    
    # Email validation
    guest_email = data.get("guest_email")
    if guest_email and "@" not in guest_email:
        errors.append("Ungültige E-Mail-Adresse")
    
    if errors:
        raise ValidationException("; ".join(errors))
    
    return data


def validate_opening_hours(date_str: str, time_str: str, opening_hours: dict) -> dict:
    """Validate against opening hours"""
    if not opening_hours:
        return {"valid": True}
    
    if opening_hours.get("is_closed"):
        return {"valid": False, "message": "Geschlossen an diesem Tag"}
    
    open_time = opening_hours.get("open_time", "00:00")
    close_time = opening_hours.get("close_time", "23:59")
    
    if not (open_time <= time_str <= close_time):
        return {"valid": False, "message": f"Öffnungszeiten: {open_time} - {close_time}"}
    
    return {"valid": True}


def validate_capacity(current_guests: int, party_size: int, max_capacity: int) -> dict:
    """Validate capacity"""
    available = max_capacity - current_guests
    
    if party_size > available:
        return {
            "valid": False,
            "available": available,
            "message": f"Nur {available} Plätze verfügbar"
        }
    
    return {"valid": True, "available": available}


def validate_area_data(data: dict, is_update: bool = False) -> dict:
    """Validate area data"""
    errors = []
    
    name = data.get("name")
    if name:
        if len(name.strip()) < 2:
            errors.append("Bereichsname muss mindestens 2 Zeichen lang sein")
    elif not is_update:
        errors.append("Bereichsname ist erforderlich")
    
    capacity = data.get("capacity")
    if capacity is not None and capacity < 1:
        errors.append("Kapazität muss mindestens 1 sein")
    
    if errors:
        raise ValidationException("; ".join(errors))
    
    return data


def validate_user_data(data: dict, is_update: bool = False) -> dict:
    """Validate user data"""
    errors = []
    
    name = data.get("name")
    if name:
        if len(name.strip()) < 2:
            errors.append("Name muss mindestens 2 Zeichen lang sein")
    elif not is_update:
        errors.append("Name ist erforderlich")
    
    email = data.get("email")
    if email:
        if "@" not in email or "." not in email:
            errors.append("Ungültige E-Mail-Adresse")
    elif not is_update:
        errors.append("E-Mail ist erforderlich")
    
    password = data.get("password")
    if password:
        if len(password) < 8:
            errors.append("Passwort muss mindestens 8 Zeichen lang sein")
    elif not is_update:
        errors.append("Passwort ist erforderlich")
    
    if errors:
        raise ValidationException("; ".join(errors))
    
    return data


def validate_password_strength(password: str) -> bool:
    """Validate password strength"""
    if len(password) < 8:
        raise ValidationException("Passwort muss mindestens 8 Zeichen lang sein")
    return True
