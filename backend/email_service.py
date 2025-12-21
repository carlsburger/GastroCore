import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timezone
import os
import logging
import hashlib
import hmac

logger = logging.getLogger(__name__)

# SMTP Configuration
SMTP_HOST = os.environ.get('SMTP_HOST', 'smtp.ionos.de')
SMTP_PORT = int(os.environ.get('SMTP_PORT', 465))
SMTP_USER = os.environ.get('SMTP_USER', '')
SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD', '')
SMTP_FROM_EMAIL = os.environ.get('SMTP_FROM_EMAIL', 'reservierung@carlsburg.de')
SMTP_FROM_NAME = os.environ.get('SMTP_FROM_NAME', 'Carlsburg Restaurant')
APP_URL = os.environ.get('APP_URL', 'http://localhost:3000')
CANCEL_SECRET = os.environ.get('JWT_SECRET', 'secret-key')

def generate_cancel_token(reservation_id: str) -> str:
    """Generate a secure cancellation token"""
    message = f"{reservation_id}:{CANCEL_SECRET}"
    return hashlib.sha256(message.encode()).hexdigest()[:32]

def verify_cancel_token(reservation_id: str, token: str) -> bool:
    """Verify a cancellation token"""
    expected = generate_cancel_token(reservation_id)
    return hmac.compare_digest(expected, token)

def get_cancel_url(reservation_id: str) -> str:
    """Generate cancellation URL"""
    token = generate_cancel_token(reservation_id)
    return f"{APP_URL}/cancel/{reservation_id}?token={token}"

def format_date_german(date_str: str) -> str:
    """Format date string to German format"""
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        weekdays = ['Montag', 'Dienstag', 'Mittwoch', 'Donnerstag', 'Freitag', 'Samstag', 'Sonntag']
        months = ['Januar', 'Februar', 'März', 'April', 'Mai', 'Juni', 
                  'Juli', 'August', 'September', 'Oktober', 'November', 'Dezember']
        return f"{weekdays[dt.weekday()]}, {dt.day}. {months[dt.month-1]} {dt.year}"
    except:
        return date_str

# Email Templates
def get_confirmation_email(reservation: dict, area_name: str = None) -> tuple:
    """Generate confirmation email subject and body"""
    cancel_url = get_cancel_url(reservation['id'])
    date_formatted = format_date_german(reservation['date'])
    
    subject = f"Ihre Reservierung bei Carlsburg - {reservation['date']} um {reservation['time']} Uhr"
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: 'Lato', Arial, sans-serif; line-height: 1.6; color: #00280b; background-color: #fafbed; margin: 0; padding: 0; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 40px 20px; }}
            .header {{ text-align: center; margin-bottom: 30px; }}
            .logo {{ width: 60px; height: 60px; background-color: #00280b; border-radius: 50%; display: inline-flex; align-items: center; justify-content: center; }}
            .logo span {{ color: #fafbed; font-family: 'Playfair Display', Georgia, serif; font-size: 28px; font-weight: bold; }}
            h1 {{ font-family: 'Playfair Display', Georgia, serif; color: #00280b; margin: 20px 0 10px; font-size: 28px; }}
            .card {{ background-color: #f3f6de; border-radius: 12px; padding: 30px; margin: 20px 0; }}
            .detail-row {{ display: flex; justify-content: space-between; padding: 12px 0; border-bottom: 1px solid #dce0c5; }}
            .detail-row:last-child {{ border-bottom: none; }}
            .detail-label {{ color: #4a5d4e; font-size: 14px; }}
            .detail-value {{ font-weight: 600; color: #00280b; }}
            .status-badge {{ display: inline-block; background-color: #ffed00; color: #00280b; padding: 6px 16px; border-radius: 20px; font-weight: 600; font-size: 14px; }}
            .btn {{ display: inline-block; background-color: #00280b; color: #fafbed !important; text-decoration: none; padding: 14px 32px; border-radius: 30px; font-weight: 600; margin: 10px 5px; }}
            .btn-outline {{ background-color: transparent; border: 2px solid #00280b; color: #00280b !important; }}
            .footer {{ text-align: center; margin-top: 40px; padding-top: 20px; border-top: 1px solid #dce0c5; color: #4a5d4e; font-size: 14px; }}
            .highlight {{ background-color: #ffed00; padding: 2px 8px; border-radius: 4px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <div class="logo"><span>C</span></div>
                <h1>Reservierung bestätigt</h1>
                <p>Vielen Dank für Ihre Reservierung, {reservation['guest_name']}!</p>
            </div>
            
            <div class="card">
                <div style="text-align: center; margin-bottom: 20px;">
                    <span class="status-badge">Bestätigt</span>
                </div>
                
                <div class="detail-row">
                    <span class="detail-label">Datum</span>
                    <span class="detail-value">{date_formatted}</span>
                </div>
                <div class="detail-row">
                    <span class="detail-label">Uhrzeit</span>
                    <span class="detail-value">{reservation['time']} Uhr</span>
                </div>
                <div class="detail-row">
                    <span class="detail-label">Personen</span>
                    <span class="detail-value">{reservation['party_size']} Personen</span>
                </div>
                {f'''<div class="detail-row">
                    <span class="detail-label">Bereich</span>
                    <span class="detail-value">{area_name}</span>
                </div>''' if area_name else ''}
                {f'''<div class="detail-row">
                    <span class="detail-label">Notizen</span>
                    <span class="detail-value">{reservation.get("notes", "")}</span>
                </div>''' if reservation.get("notes") else ''}
            </div>
            
            <div style="text-align: center; margin: 30px 0;">
                <p>Müssen Sie Ihre Pläne ändern?</p>
                <a href="{cancel_url}" class="btn btn-outline">Reservierung stornieren</a>
            </div>
            
            <div class="footer">
                <p><strong>Carlsburg Restaurant</strong></p>
                <p>Wir freuen uns auf Ihren Besuch!</p>
                <p style="font-size: 12px; margin-top: 20px;">
                    Bei Fragen erreichen Sie uns unter reservierung@carlsburg.de
                </p>
            </div>
        </div>
    </body>
    </html>
    """
    
    text = f"""
Reservierung bestätigt

Vielen Dank für Ihre Reservierung, {reservation['guest_name']}!

Details:
- Datum: {date_formatted}
- Uhrzeit: {reservation['time']} Uhr
- Personen: {reservation['party_size']}
{f"- Bereich: {area_name}" if area_name else ""}
{f"- Notizen: {reservation.get('notes', '')}" if reservation.get('notes') else ""}

Müssen Sie Ihre Pläne ändern?
Stornierungslink: {cancel_url}

Carlsburg Restaurant
Wir freuen uns auf Ihren Besuch!
    """
    
    return subject, html, text


def get_reminder_email(reservation: dict, area_name: str = None) -> tuple:
    """Generate reminder email (24h before)"""
    cancel_url = get_cancel_url(reservation['id'])
    date_formatted = format_date_german(reservation['date'])
    
    subject = f"Erinnerung: Ihre Reservierung morgen um {reservation['time']} Uhr"
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: 'Lato', Arial, sans-serif; line-height: 1.6; color: #00280b; background-color: #fafbed; margin: 0; padding: 0; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 40px 20px; }}
            .header {{ text-align: center; margin-bottom: 30px; }}
            .logo {{ width: 60px; height: 60px; background-color: #00280b; border-radius: 50%; display: inline-flex; align-items: center; justify-content: center; }}
            .logo span {{ color: #fafbed; font-family: 'Playfair Display', Georgia, serif; font-size: 28px; font-weight: bold; }}
            h1 {{ font-family: 'Playfair Display', Georgia, serif; color: #00280b; margin: 20px 0 10px; font-size: 28px; }}
            .card {{ background-color: #f3f6de; border-radius: 12px; padding: 30px; margin: 20px 0; }}
            .detail-row {{ display: flex; justify-content: space-between; padding: 12px 0; border-bottom: 1px solid #dce0c5; }}
            .detail-row:last-child {{ border-bottom: none; }}
            .detail-label {{ color: #4a5d4e; font-size: 14px; }}
            .detail-value {{ font-weight: 600; color: #00280b; }}
            .reminder-badge {{ display: inline-block; background-color: #a2d2ff; color: #00280b; padding: 6px 16px; border-radius: 20px; font-weight: 600; font-size: 14px; }}
            .btn {{ display: inline-block; background-color: #00280b; color: #fafbed !important; text-decoration: none; padding: 14px 32px; border-radius: 30px; font-weight: 600; margin: 10px 5px; }}
            .btn-outline {{ background-color: transparent; border: 2px solid #00280b; color: #00280b !important; }}
            .footer {{ text-align: center; margin-top: 40px; padding-top: 20px; border-top: 1px solid #dce0c5; color: #4a5d4e; font-size: 14px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <div class="logo"><span>C</span></div>
                <h1>Bis morgen!</h1>
                <p>Wir möchten Sie an Ihre Reservierung erinnern, {reservation['guest_name']}.</p>
            </div>
            
            <div class="card">
                <div style="text-align: center; margin-bottom: 20px;">
                    <span class="reminder-badge">Morgen</span>
                </div>
                
                <div class="detail-row">
                    <span class="detail-label">Datum</span>
                    <span class="detail-value">{date_formatted}</span>
                </div>
                <div class="detail-row">
                    <span class="detail-label">Uhrzeit</span>
                    <span class="detail-value">{reservation['time']} Uhr</span>
                </div>
                <div class="detail-row">
                    <span class="detail-label">Personen</span>
                    <span class="detail-value">{reservation['party_size']} Personen</span>
                </div>
                {f'''<div class="detail-row">
                    <span class="detail-label">Bereich</span>
                    <span class="detail-value">{area_name}</span>
                </div>''' if area_name else ''}
            </div>
            
            <div style="text-align: center; margin: 30px 0;">
                <p>Können Sie nicht kommen?</p>
                <a href="{cancel_url}" class="btn btn-outline">Reservierung stornieren</a>
            </div>
            
            <div class="footer">
                <p><strong>Carlsburg Restaurant</strong></p>
                <p>Wir freuen uns auf Ihren Besuch!</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    text = f"""
Erinnerung: Ihre Reservierung morgen

Hallo {reservation['guest_name']},

wir möchten Sie an Ihre Reservierung erinnern:

- Datum: {date_formatted}
- Uhrzeit: {reservation['time']} Uhr
- Personen: {reservation['party_size']}
{f"- Bereich: {area_name}" if area_name else ""}

Können Sie nicht kommen?
Stornierungslink: {cancel_url}

Carlsburg Restaurant
Wir freuen uns auf Ihren Besuch!
    """
    
    return subject, html, text


def get_cancellation_email(reservation: dict) -> tuple:
    """Generate cancellation confirmation email"""
    date_formatted = format_date_german(reservation['date'])
    
    subject = f"Stornierung bestätigt - {reservation['date']}"
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: 'Lato', Arial, sans-serif; line-height: 1.6; color: #00280b; background-color: #fafbed; margin: 0; padding: 0; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 40px 20px; }}
            .header {{ text-align: center; margin-bottom: 30px; }}
            .logo {{ width: 60px; height: 60px; background-color: #00280b; border-radius: 50%; display: inline-flex; align-items: center; justify-content: center; }}
            .logo span {{ color: #fafbed; font-family: 'Playfair Display', Georgia, serif; font-size: 28px; font-weight: bold; }}
            h1 {{ font-family: 'Playfair Display', Georgia, serif; color: #00280b; margin: 20px 0 10px; font-size: 28px; }}
            .card {{ background-color: #f3f6de; border-radius: 12px; padding: 30px; margin: 20px 0; }}
            .cancelled-badge {{ display: inline-block; background-color: #e3e6d0; color: #4a5d4e; padding: 6px 16px; border-radius: 20px; font-weight: 600; font-size: 14px; text-decoration: line-through; }}
            .footer {{ text-align: center; margin-top: 40px; padding-top: 20px; border-top: 1px solid #dce0c5; color: #4a5d4e; font-size: 14px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <div class="logo"><span>C</span></div>
                <h1>Stornierung bestätigt</h1>
                <p>Ihre Reservierung wurde erfolgreich storniert.</p>
            </div>
            
            <div class="card">
                <div style="text-align: center; margin-bottom: 20px;">
                    <span class="cancelled-badge">Storniert</span>
                </div>
                
                <p style="text-align: center; color: #4a5d4e;">
                    <strong>{date_formatted}</strong> um <strong>{reservation['time']} Uhr</strong><br>
                    für {reservation['party_size']} Personen
                </p>
            </div>
            
            <div style="text-align: center; margin: 30px 0;">
                <p>Wir würden uns freuen, Sie ein anderes Mal begrüßen zu dürfen!</p>
            </div>
            
            <div class="footer">
                <p><strong>Carlsburg Restaurant</strong></p>
                <p>reservierung@carlsburg.de</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    text = f"""
Stornierung bestätigt

Ihre Reservierung wurde erfolgreich storniert:

- Datum: {date_formatted}
- Uhrzeit: {reservation['time']} Uhr
- Personen: {reservation['party_size']}

Wir würden uns freuen, Sie ein anderes Mal begrüßen zu dürfen!

Carlsburg Restaurant
reservierung@carlsburg.de
    """
    
    return subject, html, text


async def send_email(to_email: str, subject: str, html_body: str, text_body: str) -> bool:
    """Send email via SMTP"""
    if not SMTP_USER or not SMTP_PASSWORD:
        logger.warning("SMTP credentials not configured, skipping email")
        return False
    
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = f"{SMTP_FROM_NAME} <{SMTP_FROM_EMAIL}>"
        msg['To'] = to_email
        
        # Attach both plain text and HTML versions
        part1 = MIMEText(text_body, 'plain', 'utf-8')
        part2 = MIMEText(html_body, 'html', 'utf-8')
        msg.attach(part1)
        msg.attach(part2)
        
        # Create SSL context
        context = ssl.create_default_context()
        
        # Connect and send
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, context=context) as server:
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_FROM_EMAIL, to_email, msg.as_string())
        
        logger.info(f"Email sent successfully to {to_email}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {str(e)}")
        return False


async def send_confirmation_email(reservation: dict, area_name: str = None) -> bool:
    """Send reservation confirmation email"""
    if not reservation.get('guest_email'):
        logger.info(f"No email for reservation {reservation['id']}, skipping")
        return False
    
    subject, html, text = get_confirmation_email(reservation, area_name)
    return await send_email(reservation['guest_email'], subject, html, text)


async def send_reminder_email(reservation: dict, area_name: str = None) -> bool:
    """Send reminder email"""
    if not reservation.get('guest_email'):
        return False
    
    subject, html, text = get_reminder_email(reservation, area_name)
    return await send_email(reservation['guest_email'], subject, html, text)


async def send_cancellation_email(reservation: dict) -> bool:
    """Send cancellation confirmation email"""
    if not reservation.get('guest_email'):
        return False
    
    subject, html, text = get_cancellation_email(reservation)
    return await send_email(reservation['guest_email'], subject, html, text)
