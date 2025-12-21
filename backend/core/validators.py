"""
Validators - Centralized validation logic
"""
from datetime import datetime, timezone, timedelta
from typing import Optional

from .config import settings
from .models import ReservationStatus
from .exceptions import ValidationException, InvalidStatusTransitionException


def validate_status_transition(current_status: str, new_status: str) -> bool:
    """
    Validate that a status transition is allowed.
    Raises InvalidStatusTransitionException if not allowed.
    
    Status workflow:
        neu → bestaetigt, storniert, no_show
        bestaetigt → angekommen, storniert, no_show
        angekommen → abgeschlossen, no_show
        abgeschlossen → (terminal)
        no_show → (terminal)
        storniert → (terminal)
    """
    allowed_transitions = settings.STATUS_TRANSITIONS.get(current_status, [])
    
    if new_status not in allowed_transitions:
        raise InvalidStatusTransitionException(current_status, new_status)
    
    return True


def validate_reservation_data(data: dict, is_update: bool = False) -> dict:
    """
    Validate reservation data.
    Returns cleaned/validated data or raises ValidationException.
    """
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
        # Remove spaces and common separators for validation
        cleaned_phone = guest_phone.replace(" ", "").replace("-", "").replace("/", "")
        if len(cleaned_phone) < 6:
            errors.append("Telefonnummer ist zu kurz")
    elif not is_update:
        errors.append("Telefonnummer ist erforderlich")
    
    # Email validation (optional field)
    guest_email = data.get("guest_email")
    if guest_email and "@" not in guest_email:
        errors.append("Ungültige E-Mail-Adresse")
    
    if errors:
        raise ValidationException("; ".join(errors))
    
    return data


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
    """
    Validate password strength.
    Requirements: At least 8 characters.
    """
    if len(password) < 8:
        raise ValidationException("Passwort muss mindestens 8 Zeichen lang sein")
    
    return True
