"""
Email Service with Multi-Language Templates (DE/EN/PL)
"""
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timezone
import os
import logging
import hashlib
import hmac
from pathlib import Path
from dotenv import load_dotenv
from typing import Dict, Optional

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

logger = logging.getLogger(__name__)

# SMTP Configuration - ALL values from ENV, NO defaults for sensitive data
SMTP_HOST = os.environ.get('SMTP_HOST', '')
SMTP_PORT = int(os.environ.get('SMTP_PORT', '465'))
SMTP_USER = os.environ.get('SMTP_USER', '')
SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD', '')  # NEVER log or expose
SMTP_FROM_EMAIL = os.environ.get('SMTP_FROM', os.environ.get('SMTP_FROM_EMAIL', 'reservierungen@carlsburg.de'))
SMTP_FROM_NAME = os.environ.get('SMTP_FROM_NAME', 'Carlsburg Restaurant')
SMTP_USE_TLS = os.environ.get('SMTP_USE_TLS', 'false').lower() == 'true'
APP_URL = os.environ.get('APP_URL', 'http://localhost:3000')
CANCEL_SECRET = os.environ.get('JWT_SECRET', 'secret-key')


def is_smtp_configured() -> bool:
    """Check if SMTP is fully configured"""
    return bool(SMTP_HOST and SMTP_USER and SMTP_PASSWORD)


def get_smtp_status() -> dict:
    """Get SMTP configuration status (without exposing secrets)"""
    return {
        "configured": is_smtp_configured(),
        "host": SMTP_HOST if SMTP_HOST else "NOT SET",
        "port": SMTP_PORT,
        "user": SMTP_USER[:3] + "***" if SMTP_USER else "NOT SET",
        "from_email": SMTP_FROM_EMAIL,
        "from_name": SMTP_FROM_NAME,
        "use_tls": SMTP_USE_TLS,
        "message": "SMTP bereit" if is_smtp_configured() else "SMTP nicht konfiguriert - E-Mails werden nur geloggt"
    }


def generate_cancel_token(reservation_id: str) -> str:
    """Generate secure cancellation token"""
    message = f"{reservation_id}:{CANCEL_SECRET}"
    return hashlib.sha256(message.encode()).hexdigest()[:32]


def verify_cancel_token(reservation_id: str, token: str) -> bool:
    """Verify cancellation token"""
    expected = generate_cancel_token(reservation_id)
    return hmac.compare_digest(expected, token)


def get_cancel_url(reservation_id: str) -> str:
    """Generate cancellation URL"""
    token = generate_cancel_token(reservation_id)
    return f"{APP_URL}/cancel/{reservation_id}?token={token}"


# ============== MULTI-LANGUAGE TEMPLATES ==============
TEMPLATES = {
    "confirmation": {
        "de": {
            "subject": "Ihre Reservierung bei {restaurant} - {date} um {time} Uhr",
            "greeting": "Vielen Dank für Ihre Reservierung",
            "details_title": "Reservierungsdetails",
            "date_label": "Datum",
            "time_label": "Uhrzeit",
            "guests_label": "Personen",
            "area_label": "Bereich",
            "occasion_label": "Anlass",
            "cancel_text": "Müssen Sie Ihre Pläne ändern?",
            "cancel_button": "Reservierung stornieren",
            "footer": "Wir freuen uns auf Ihren Besuch!"
        },
        "en": {
            "subject": "Your reservation at {restaurant} - {date} at {time}",
            "greeting": "Thank you for your reservation",
            "details_title": "Reservation Details",
            "date_label": "Date",
            "time_label": "Time",
            "guests_label": "Guests",
            "area_label": "Area",
            "occasion_label": "Occasion",
            "cancel_text": "Need to change your plans?",
            "cancel_button": "Cancel Reservation",
            "footer": "We look forward to your visit!"
        },
        "pl": {
            "subject": "Twoja rezerwacja w {restaurant} - {date} o {time}",
            "greeting": "Dziękujemy za rezerwację",
            "details_title": "Szczegóły rezerwacji",
            "date_label": "Data",
            "time_label": "Godzina",
            "guests_label": "Osoby",
            "area_label": "Strefa",
            "occasion_label": "Okazja",
            "cancel_text": "Chcesz zmienić plany?",
            "cancel_button": "Anuluj rezerwację",
            "footer": "Czekamy na Twoją wizytę!"
        }
    },
    "reminder": {
        "de": {
            "subject": "Erinnerung: Ihre Reservierung morgen um {time} Uhr",
            "greeting": "Bis morgen!",
            "text": "Wir möchten Sie an Ihre Reservierung erinnern.",
            "footer": "Wir freuen uns auf Ihren Besuch!"
        },
        "en": {
            "subject": "Reminder: Your reservation tomorrow at {time}",
            "greeting": "See you tomorrow!",
            "text": "We would like to remind you of your reservation.",
            "footer": "We look forward to your visit!"
        },
        "pl": {
            "subject": "Przypomnienie: Twoja rezerwacja jutro o {time}",
            "greeting": "Do zobaczenia jutro!",
            "text": "Chcielibyśmy przypomnieć o Twojej rezerwacji.",
            "footer": "Czekamy na Twoją wizytę!"
        }
    },
    "cancellation": {
        "de": {
            "subject": "Stornierung bestätigt - {date}",
            "greeting": "Stornierung bestätigt",
            "text": "Ihre Reservierung wurde erfolgreich storniert.",
            "footer": "Wir würden uns freuen, Sie ein anderes Mal begrüßen zu dürfen!"
        },
        "en": {
            "subject": "Cancellation confirmed - {date}",
            "greeting": "Cancellation confirmed",
            "text": "Your reservation has been successfully cancelled.",
            "footer": "We would be happy to welcome you another time!"
        },
        "pl": {
            "subject": "Potwierdzenie anulowania - {date}",
            "greeting": "Anulowanie potwierdzone",
            "text": "Twoja rezerwacja została pomyślnie anulowana.",
            "footer": "Będziemy szczęśliwi, mogąc powitać Cię innym razem!"
        }
    },
    "waitlist": {
        "de": {
            "subject": "Ein Platz ist frei geworden! - {date}",
            "greeting": "Gute Nachrichten!",
            "text": "Ein Platz für Ihre gewünschte Reservierung ist frei geworden. Bitte kontaktieren Sie uns, um Ihre Reservierung zu bestätigen.",
            "footer": "Wir freuen uns auf Ihre Rückmeldung!"
        },
        "en": {
            "subject": "A spot has opened up! - {date}",
            "greeting": "Good news!",
            "text": "A spot for your desired reservation has become available. Please contact us to confirm your reservation.",
            "footer": "We look forward to hearing from you!"
        },
        "pl": {
            "subject": "Miejsce się zwolniło! - {date}",
            "greeting": "Dobre wieści!",
            "text": "Miejsce na Twoją rezerwację jest dostępne. Prosimy o kontakt w celu potwierdzenia.",
            "footer": "Czekamy na Twoją odpowiedź!"
        }
    }
}


def get_email_templates() -> list:
    """Get all email templates for admin editing"""
    templates = []
    for template_type, languages in TEMPLATES.items():
        for lang, content in languages.items():
            templates.append({
                "key": f"{template_type}_{lang}",
                "template_type": template_type,
                "language": lang,
                **content
            })
    return templates


def format_date_localized(date_str: str, lang: str) -> str:
    """Format date for different languages"""
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        
        weekdays = {
            "de": ['Montag', 'Dienstag', 'Mittwoch', 'Donnerstag', 'Freitag', 'Samstag', 'Sonntag'],
            "en": ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'],
            "pl": ['Poniedziałek', 'Wtorek', 'Środa', 'Czwartek', 'Piątek', 'Sobota', 'Niedziela']
        }
        
        months = {
            "de": ['Januar', 'Februar', 'März', 'April', 'Mai', 'Juni', 'Juli', 'August', 'September', 'Oktober', 'November', 'Dezember'],
            "en": ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'],
            "pl": ['Stycznia', 'Lutego', 'Marca', 'Kwietnia', 'Maja', 'Czerwca', 'Lipca', 'Sierpnia', 'Września', 'Października', 'Listopada', 'Grudnia']
        }
        
        wd = weekdays.get(lang, weekdays["de"])[dt.weekday()]
        m = months.get(lang, months["de"])[dt.month - 1]
        
        return f"{wd}, {dt.day}. {m} {dt.year}"
    except:
        return date_str


def get_html_template(template_type: str, lang: str, data: dict) -> str:
    """Generate HTML email from template"""
    t = TEMPLATES.get(template_type, {}).get(lang, TEMPLATES.get(template_type, {}).get("de", {}))
    
    cancel_url = data.get("cancel_url", "")
    restaurant = data.get("restaurant", SMTP_FROM_NAME)
    
    base_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: 'Lato', Arial, sans-serif; line-height: 1.6; color: #00280b; background-color: #fafbed; margin: 0; padding: 0; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 40px 20px; }}
            .header {{ text-align: center; margin-bottom: 30px; }}
            .logo {{ width: 60px; height: 60px; background-color: #00280b; border-radius: 50%; display: inline-block; line-height: 60px; }}
            .logo span {{ color: #fafbed; font-family: Georgia, serif; font-size: 28px; font-weight: bold; }}
            h1 {{ font-family: Georgia, serif; color: #00280b; margin: 20px 0 10px; font-size: 28px; }}
            .card {{ background-color: #f3f6de; border-radius: 12px; padding: 30px; margin: 20px 0; }}
            .detail-row {{ display: flex; justify-content: space-between; padding: 12px 0; border-bottom: 1px solid #dce0c5; }}
            .detail-row:last-child {{ border-bottom: none; }}
            .detail-label {{ color: #4a5d4e; font-size: 14px; }}
            .detail-value {{ font-weight: 600; color: #00280b; }}
            .status-badge {{ display: inline-block; background-color: #ffed00; color: #00280b; padding: 6px 16px; border-radius: 20px; font-weight: 600; font-size: 14px; }}
            .btn {{ display: inline-block; background-color: #00280b; color: #fafbed !important; text-decoration: none; padding: 14px 32px; border-radius: 30px; font-weight: 600; margin: 10px 5px; }}
            .btn-outline {{ background-color: transparent; border: 2px solid #00280b; color: #00280b !important; }}
            .footer {{ text-align: center; margin-top: 40px; padding-top: 20px; border-top: 1px solid #dce0c5; color: #4a5d4e; font-size: 14px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <div class="logo"><span>C</span></div>
                <h1>{t.get('greeting', 'Hello')}</h1>
                <p>{data.get('guest_name', '')}</p>
            </div>
    """
    
    if template_type == "confirmation" or template_type == "reminder":
        base_html += f"""
            <div class="card">
                <div style="text-align: center; margin-bottom: 20px;">
                    <span class="status-badge">{"Bestätigt" if template_type == "confirmation" else "Morgen"}</span>
                </div>
                
                <div class="detail-row">
                    <span class="detail-label">{t.get('date_label', 'Date')}</span>
                    <span class="detail-value">{data.get('date_formatted', data.get('date', ''))}</span>
                </div>
                <div class="detail-row">
                    <span class="detail-label">{t.get('time_label', 'Time')}</span>
                    <span class="detail-value">{data.get('time', '')} Uhr</span>
                </div>
                <div class="detail-row">
                    <span class="detail-label">{t.get('guests_label', 'Guests')}</span>
                    <span class="detail-value">{data.get('party_size', '')} {t.get('guests_label', 'Guests')}</span>
                </div>
                {'<div class="detail-row"><span class="detail-label">' + t.get('area_label', 'Area') + '</span><span class="detail-value">' + data.get('area_name', '') + '</span></div>' if data.get('area_name') else ''}
                {'<div class="detail-row"><span class="detail-label">' + t.get('occasion_label', 'Occasion') + '</span><span class="detail-value">' + data.get('occasion', '') + '</span></div>' if data.get('occasion') else ''}
            </div>
            
            <div style="text-align: center; margin: 30px 0;">
                <p>{t.get('cancel_text', 'Need to change plans?')}</p>
                <a href="{cancel_url}" class="btn btn-outline">{t.get('cancel_button', 'Cancel')}</a>
            </div>
        """
    elif template_type == "cancellation":
        base_html += f"""
            <div class="card">
                <p style="text-align: center; color: #4a5d4e;">
                    {t.get('text', '')}
                </p>
                <p style="text-align: center; color: #4a5d4e;">
                    <strong>{data.get('date_formatted', data.get('date', ''))}</strong> - {data.get('time', '')} Uhr<br>
                    {data.get('party_size', '')} {t.get('guests_label', 'Guests')}
                </p>
            </div>
        """
    elif template_type == "waitlist":
        base_html += f"""
            <div class="card">
                <p style="text-align: center;">
                    {t.get('text', '')}
                </p>
                <p style="text-align: center; font-weight: 600;">
                    {data.get('date_formatted', data.get('date', ''))}
                </p>
            </div>
        """
    
    base_html += f"""
            <div class="footer">
                <p><strong>{restaurant}</strong></p>
                <p>{t.get('footer', '')}</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    return base_html


async def log_email(to_email: str, subject: str, template_type: str, status: str, error: str = None):
    """Log email send attempt"""
    from core.database import db
    
    log = {
        "id": hashlib.sha256(f"{to_email}{datetime.now().isoformat()}".encode()).hexdigest()[:16],
        "to_email": to_email,
        "subject": subject,
        "template_type": template_type,
        "status": status,
        "error": error,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    try:
        await db.email_logs.insert_one(log)
    except Exception as e:
        logger.error(f"Failed to log email: {e}")


async def send_email(to_email: str, subject: str, html_body: str, text_body: str, template_type: str = "other") -> bool:
    """Send email via SMTP with TLS/SSL support"""
    if not is_smtp_configured():
        logger.warning("SMTP nicht konfiguriert - E-Mail wird nur geloggt")
        await log_email(to_email, subject, template_type, "skipped", "SMTP nicht konfiguriert")
        return False
    
    logger.info(f"SMTP Send attempt: host={SMTP_HOST}, port={SMTP_PORT}, user={SMTP_USER[:3]}***, to={to_email}")
    
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = f"{SMTP_FROM_NAME} <{SMTP_FROM_EMAIL}>"
        msg['To'] = to_email
        
        msg.attach(MIMEText(text_body, 'plain', 'utf-8'))
        msg.attach(MIMEText(html_body, 'html', 'utf-8'))
        
        context = ssl.create_default_context()
        
        if SMTP_USE_TLS:
            # STARTTLS (Port 587)
            logger.debug(f"Using STARTTLS mode (port {SMTP_PORT})")
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
                server.starttls(context=context)
                server.login(SMTP_USER, SMTP_PASSWORD)
                server.sendmail(SMTP_FROM_EMAIL, to_email, msg.as_string())
        else:
            # SSL (Port 465)
            logger.debug(f"Using SSL mode (port {SMTP_PORT})")
            with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, context=context) as server:
                server.login(SMTP_USER, SMTP_PASSWORD)
                server.sendmail(SMTP_FROM_EMAIL, to_email, msg.as_string())
        
        logger.info(f"E-Mail erfolgreich gesendet an {to_email}")
        await log_email(to_email, subject, template_type, "sent")
        return True
        
    except smtplib.SMTPAuthenticationError as e:
        logger.error(f"SMTP Auth Fehler: Falsches Passwort oder Benutzer für {SMTP_USER} auf {SMTP_HOST}:{SMTP_PORT}")
        logger.exception("SMTP Authentication exception stack:")
        await log_email(to_email, subject, template_type, "failed", "Authentifizierung fehlgeschlagen")
        return False
        
    except smtplib.SMTPConnectError as e:
        logger.error(f"SMTP Connect Fehler: Kann {SMTP_HOST}:{SMTP_PORT} nicht erreichen")
        logger.exception("SMTP Connect exception stack:")
        await log_email(to_email, subject, template_type, "failed", f"Verbindung fehlgeschlagen: {e}")
        return False
        
    except Exception as e:
        error_msg = str(e)
        # NEVER log passwords or sensitive data
        if SMTP_PASSWORD and SMTP_PASSWORD in error_msg:
            error_msg = error_msg.replace(SMTP_PASSWORD, "***")
        logger.error(f"E-Mail-Versand fehlgeschlagen an {to_email}: {error_msg}")
        logger.exception(f"SMTP exception stack (host={SMTP_HOST}, port={SMTP_PORT}):")
        await log_email(to_email, subject, template_type, "failed", error_msg)
        return False


async def send_test_email(to_email: str) -> dict:
    """Send a test email to verify SMTP configuration"""
    if not is_smtp_configured():
        return {
            "success": False,
            "error": "SMTP nicht konfiguriert. Bitte SMTP_HOST, SMTP_USER und SMTP_PASSWORD setzen.",
            "smtp_status": get_smtp_status()
        }
    
    subject = "Carlsburg Cockpit - SMTP Testmail"
    html_body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; padding: 20px;">
        <h2 style="color: #005500;">✅ SMTP Konfiguration erfolgreich!</h2>
        <p>Diese Testmail bestätigt, dass die E-Mail-Konfiguration für das Carlsburg Cockpit korrekt funktioniert.</p>
        <hr>
        <p style="color: #666; font-size: 12px;">
            Gesendet am: {datetime.now(timezone.utc).strftime('%d.%m.%Y %H:%M:%S')} UTC<br>
            Von: {SMTP_FROM_NAME} &lt;{SMTP_FROM_EMAIL}&gt;
        </p>
    </body>
    </html>
    """
    text_body = f"SMTP Konfiguration erfolgreich! Gesendet am {datetime.now(timezone.utc).strftime('%d.%m.%Y %H:%M:%S')} UTC"
    
    success = await send_email(to_email, subject, html_body, text_body, "test")
    
    return {
        "success": success,
        "recipient": to_email,
        "smtp_status": get_smtp_status(),
        "message": "Testmail erfolgreich gesendet" if success else "Testmail fehlgeschlagen - siehe Logs"
    }


async def send_confirmation_email(reservation: dict, area_name: str = None, lang: str = "de") -> bool:
    """Send reservation confirmation email"""
    if not reservation.get('guest_email'):
        return False
    
    t = TEMPLATES["confirmation"].get(lang, TEMPLATES["confirmation"]["de"])
    
    data = {
        **reservation,
        "date_formatted": format_date_localized(reservation.get("date", ""), lang),
        "area_name": area_name,
        "cancel_url": get_cancel_url(reservation["id"]),
        "restaurant": SMTP_FROM_NAME
    }
    
    subject = t["subject"].format(
        restaurant=SMTP_FROM_NAME,
        date=reservation.get("date", ""),
        time=reservation.get("time", "")
    )
    
    html = get_html_template("confirmation", lang, data)
    text = f"{t['greeting']}\n\n{t['date_label']}: {data['date_formatted']}\n{t['time_label']}: {reservation.get('time')}\n{t['guests_label']}: {reservation.get('party_size')}\n\n{data['cancel_url']}"
    
    return await send_email(reservation['guest_email'], subject, html, text, "confirmation")


async def send_reminder_email(reservation: dict, area_name: str = None, lang: str = "de") -> bool:
    """Send reminder email"""
    if not reservation.get('guest_email'):
        return False
    
    t = TEMPLATES["reminder"].get(lang, TEMPLATES["reminder"]["de"])
    
    data = {
        **reservation,
        "date_formatted": format_date_localized(reservation.get("date", ""), lang),
        "area_name": area_name,
        "cancel_url": get_cancel_url(reservation["id"]),
        "restaurant": SMTP_FROM_NAME
    }
    
    subject = t["subject"].format(time=reservation.get("time", ""))
    html = get_html_template("reminder", lang, data)
    text = f"{t['greeting']}\n\n{t['text']}\n\n{t['date_label']}: {data['date_formatted']}\n{t['time_label']}: {reservation.get('time')}"
    
    return await send_email(reservation['guest_email'], subject, html, text, "reminder")


async def send_cancellation_email(reservation: dict, lang: str = "de") -> bool:
    """Send cancellation confirmation email"""
    if not reservation.get('guest_email'):
        return False
    
    t = TEMPLATES["cancellation"].get(lang, TEMPLATES["cancellation"]["de"])
    
    data = {
        **reservation,
        "date_formatted": format_date_localized(reservation.get("date", ""), lang),
        "restaurant": SMTP_FROM_NAME
    }
    
    subject = t["subject"].format(date=reservation.get("date", ""))
    html = get_html_template("cancellation", lang, data)
    text = f"{t['greeting']}\n\n{t['text']}\n\n{reservation.get('date')} - {reservation.get('time')}"
    
    return await send_email(reservation['guest_email'], subject, html, text, "cancellation")


async def send_waitlist_notification(entry: dict, lang: str = "de") -> bool:
    """Send waitlist notification email"""
    if not entry.get('guest_email'):
        return False
    
    t = TEMPLATES["waitlist"].get(lang, TEMPLATES["waitlist"]["de"])
    
    data = {
        **entry,
        "date_formatted": format_date_localized(entry.get("date", ""), lang),
        "restaurant": SMTP_FROM_NAME
    }
    
    subject = t["subject"].format(date=entry.get("date", ""))
    html = get_html_template("waitlist", lang, data)
    text = f"{t['greeting']}\n\n{t['text']}\n\n{entry.get('date')}"
    
    return await send_email(entry['guest_email'], subject, html, text, "waitlist")



async def send_email_template(to_email: str, subject: str, body: str) -> bool:
    """Send a simple text email (for welcome emails, etc.)"""
    if not SMTP_USER or not SMTP_PASSWORD:
        logger.warning("SMTP credentials not configured, skipping email")
        return False
    
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = f"{SMTP_FROM_NAME} <{SMTP_FROM_EMAIL}>"
        msg['To'] = to_email
        
        # Simple HTML wrapper
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: 'Lato', Arial, sans-serif; line-height: 1.6; color: #00280b; background-color: #fafbed; margin: 0; padding: 0; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 40px 20px; }}
                .header {{ text-align: center; margin-bottom: 30px; }}
                .logo {{ width: 60px; height: 60px; background-color: #00280b; border-radius: 50%; display: inline-block; line-height: 60px; }}
                .logo span {{ color: #fafbed; font-family: Georgia, serif; font-size: 28px; font-weight: bold; }}
                h1 {{ font-family: Georgia, serif; color: #00280b; margin: 20px 0 10px; font-size: 24px; }}
                .content {{ background-color: #f3f6de; border-radius: 12px; padding: 30px; margin: 20px 0; white-space: pre-line; }}
                .footer {{ text-align: center; margin-top: 40px; padding-top: 20px; border-top: 1px solid #dce0c5; color: #4a5d4e; font-size: 14px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div class="logo"><span>G</span></div>
                    <h1>GastroCore</h1>
                </div>
                <div class="content">{body}</div>
                <div class="footer">
                    <p>&copy; {datetime.now().year} GastroCore. Alle Rechte vorbehalten.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        msg.attach(MIMEText(body, 'plain', 'utf-8'))
        msg.attach(MIMEText(html_body, 'html', 'utf-8'))
        
        context = ssl.create_default_context()
        
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, context=context) as server:
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_FROM_EMAIL, to_email, msg.as_string())
        
        logger.info(f"Template email sent to {to_email}")
        await log_email(to_email, subject, "template", "sent")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send template email to {to_email}: {str(e)}")
        await log_email(to_email, subject, "template", "failed", str(e))
        raise e



async def send_email_with_attachments(
    to_emails: list,
    subject: str,
    body: str,
    attachments: list = None,
    cc_emails: list = None,
    bcc_emails: list = None
) -> bool:
    """Send email with attachments (for tax office exports)
    
    Args:
        to_emails: List of recipient emails
        subject: Email subject
        body: Email body text
        attachments: List of dicts with 'filename', 'content' (bytes), 'content_type'
        cc_emails: List of CC recipients
        bcc_emails: List of BCC recipients
    """
    if not SMTP_USER or not SMTP_PASSWORD:
        logger.warning("SMTP credentials not configured, skipping email")
        return False
    
    try:
        from email.mime.base import MIMEBase
        from email import encoders
        
        msg = MIMEMultipart('mixed')
        msg['Subject'] = subject
        msg['From'] = f"{SMTP_FROM_NAME} <{SMTP_FROM_EMAIL}>"
        msg['To'] = ", ".join(to_emails)
        
        if cc_emails:
            msg['Cc'] = ", ".join(cc_emails)
        
        # Add body
        body_part = MIMEMultipart('alternative')
        
        # Plain text
        body_part.attach(MIMEText(body, 'plain', 'utf-8'))
        
        # HTML wrapper
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head><meta charset="utf-8"></head>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <div style="text-align: center; margin-bottom: 20px;">
                    <h2 style="color: #00280b; margin: 0;">GastroCore</h2>
                </div>
                <div style="background-color: #f5f5f5; border-radius: 8px; padding: 20px;">
                    <p style="white-space: pre-line;">{body}</p>
                </div>
                <div style="text-align: center; margin-top: 20px; color: #666; font-size: 12px;">
                    <p>&copy; {datetime.now().year} GastroCore. Automatisch generierte Nachricht.</p>
                </div>
            </div>
        </body>
        </html>
        """
        body_part.attach(MIMEText(html_body, 'html', 'utf-8'))
        msg.attach(body_part)
        
        # Add attachments
        if attachments:
            for attachment in attachments:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(attachment['content'])
                encoders.encode_base64(part)
                part.add_header(
                    'Content-Disposition',
                    f"attachment; filename=\"{attachment['filename']}\""
                )
                if attachment.get('content_type'):
                    part.replace_header('Content-Type', attachment['content_type'])
                msg.attach(part)
        
        # Collect all recipients
        all_recipients = list(to_emails)
        if cc_emails:
            all_recipients.extend(cc_emails)
        if bcc_emails:
            all_recipients.extend(bcc_emails)
        
        context = ssl.create_default_context()
        
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, context=context) as server:
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_FROM_EMAIL, all_recipients, msg.as_string())
        
        logger.info(f"Email with attachments sent to {', '.join(to_emails)}")
        await log_email(", ".join(to_emails), subject, "taxoffice_export", "sent")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send email with attachments: {str(e)}")
        await log_email(", ".join(to_emails), subject, "taxoffice_export", "failed", str(e))
        raise e
