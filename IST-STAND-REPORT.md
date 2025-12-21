# ============================================================
# CARLSBURG COCKPIT - IST-STAND-REPORT
# Stand: 21. Dezember 2025
# ============================================================

## ⚠️ VOR TAB SCHLIEßEN – BACKUP ERSTELLEN

```bash
cd /app && bash scripts/make_backup.sh
```

Dann **ZIP-Datei aus `/app/backups/` lokal herunterladen** und sicher aufbewahren!

---

## 1) VERSION / ARCHITEKTUR

### Modulstruktur
| Modul | Status | Beschreibung |
|-------|--------|--------------|
| Core (Auth/RBAC) | ✅ FERTIG | JWT, 3 Rollen (admin, schichtleiter, mitarbeiter) |
| Reservations | ✅ FERTIG | Online-Buchung, Walk-ins, Statusmaschine |
| Service-Terminal | ✅ FERTIG | Tagesliste, Statuswechsel |
| Events | ✅ FERTIG | Event-Verwaltung mit Buchungen & Produkten |
| Payments | ✅ FERTIG | Stripe-Integration, Regeln, Manuelle Freigabe |
| Staff | ✅ FERTIG | Mitarbeiterverwaltung mit HR-Feldern |
| Schedules | ✅ FERTIG | Dienstplanung mit Schichten |
| Tax Office Exports | ✅ FERTIG | CSV/PDF Exporte für Steuerbüro |
| Customer/Loyalty | ✅ FERTIG | OTP-Login, Punkte-Ledger, Rewards |
| Marketing | ❌ NICHT IMPLEMENTIERT | |
| AI/KI-Module | ❌ NICHT IMPLEMENTIERT | |

### Tech-Stack
- **Backend**: FastAPI (Python 3.11)
- **Frontend**: React 18 + Tailwind CSS + shadcn/ui
- **Datenbank**: MongoDB
- **Auth**: JWT (HS256, 24h Ablauf)
- **Storage**: Lokales Dateisystem (/app/uploads)
- **Email**: SMTP (konfigurierbar via ENV, aktuell nur geloggt)
- **Encryption**: Fernet (AES-256) für HR-Sensitivdaten

---

## 2) DATENMODELLE (Collections)

### users (3 Dokumente)
| Feld | Typ | Beschreibung |
|------|-----|--------------|
| id | UUID | Primärschlüssel |
| email | string | Login-Email |
| password_hash | string | bcrypt Hash |
| name | string | Anzeigename |
| role | enum | admin/schichtleiter/mitarbeiter |
| archived | bool | Soft Delete |
| must_change_password | bool | Erzwingt Passwortänderung |
| created_at | datetime | |
**Status: ✅ FERTIG**

### audit_logs (202 Dokumente)
| Feld | Typ | Beschreibung |
|------|-----|--------------|
| id | UUID | |
| actor | object | {id, name, email, role} |
| entity | string | Entitätstyp |
| entity_id | string | |
| action | string | create/update/delete/etc. |
| before/after | object | Zustand vor/nach |
| metadata | object | Zusätzliche Infos |
| timestamp | datetime | |
**Status: ✅ FERTIG**

### reservations (33 Dokumente)
| Feld | Typ | Beschreibung |
|------|-----|--------------|
| id | UUID | |
| guest_name | string | |
| guest_phone | string | |
| guest_email | string | optional |
| party_size | int | |
| date | string | YYYY-MM-DD |
| time | string | HH:MM |
| status | enum | neu/bestaetigt/angekommen/abgeschlossen/no_show/storniert |
| area_id | UUID | Bereichszuordnung |
| source | enum | online/phone/walk_in |
| notes | string | optional |
| cancel_token | string | Für Storno-Links |
| reminder_sent | bool | |
| payment_status | string | unpaid/pending/paid/failed |
| payment_required | bool | |
**Status: ✅ FERTIG**

### guests (4 Dokumente)
| Feld | Typ | Beschreibung |
|------|-----|--------------|
| id | UUID | |
| phone | string | Primärer Identifier |
| name | string | |
| email | string | optional |
| no_show_count | int | |
| visit_count | int | |
| flag | enum | null/greylist/blacklist |
| notes | string | Admin-Notizen |
| vip | bool | |
**Status: ✅ FERTIG**

### waitlist (8 Dokumente)
| Feld | Typ | Beschreibung |
|------|-----|--------------|
| id | UUID | |
| guest_name | string | |
| guest_phone | string | |
| party_size | int | |
| date | string | |
| status | enum | offen/informiert/eingeloest/erledigt |
| converted_reservation_id | UUID | Nach Umwandlung |
**Status: ✅ FERTIG**

### areas (4 Dokumente)
| Feld | Typ | Beschreibung |
|------|-----|--------------|
| id | UUID | |
| name | string | |
| capacity | int | |
| color | string | Hex-Farbe |
| sort_order | int | |
**Status: ✅ FERTIG**

### opening_hours (7 Dokumente)
| Feld | Typ | Beschreibung |
|------|-----|--------------|
| day_of_week | int | 0-6 (Mo-So) |
| is_closed | bool | |
| slots | array | [{start, end}] |
**Status: ✅ FERTIG**

### payment_rules (3 Dokumente)
| Feld | Typ | Beschreibung |
|------|-----|--------------|
| id | UUID | |
| name | string | |
| trigger | enum | group_size/greylist/event |
| trigger_value | int | z.B. 8 für Gruppengröße |
| payment_type | enum | fixed_deposit/deposit_per_person/full_prepayment |
| amount | float | |
| is_active | bool | |
**Status: ✅ FERTIG**

### staff_members (5 Dokumente)
| Feld | Typ | Beschreibung |
|------|-----|--------------|
| id | UUID | |
| first_name, last_name | string | |
| email | string | |
| phone, mobile_phone | string | |
| role | enum | service/kitchen/bar/management |
| employment_type | enum | vollzeit/teilzeit/minijob |
| weekly_hours | float | |
| entry_date | string | |
| status | enum | aktiv/inaktiv/urlaub |
| work_area_ids | array | |
| user_id | UUID | Optional: Verknüpfung zu users |
| **HR-Felder (verschlüsselt):** | | |
| tax_id | string | ENC:... (11 Ziffern) |
| social_security_number | string | ENC:... |
| bank_iban | string | ENC:... |
| health_insurance | string | |
| street, zip_code, city | string | |
| emergency_contact_name/phone | string | |
**Status: ✅ FERTIG**

### schedules (2 Dokumente)
| Feld | Typ | Beschreibung |
|------|-----|--------------|
| id | UUID | |
| year | int | |
| week | int | |
| status | enum | entwurf/veroeffentlicht/archiviert |
| notes | string | |
**Status: ✅ FERTIG**

### work_areas (4 Dokumente)
| Feld | Typ | Beschreibung |
|------|-----|--------------|
| id | UUID | |
| name | string | Service/Küche/Bar/Event |
| description | string | |
| color | string | |
| sort_order | int | |
**Status: ✅ FERTIG**

### export_jobs (8 Dokumente)
| Feld | Typ | Beschreibung |
|------|-----|--------------|
| id | UUID | |
| export_type | enum | monthly_hours/shift_list/staff_registration |
| status | enum | pending/generating/ready/sent/failed |
| year, month | int | |
| files | array | [{filename, size, content_type}] |
| error | string | Bei Fehlern |
**Status: ✅ FERTIG**

### taxoffice_settings (1 Dokument)
| Feld | Typ | Beschreibung |
|------|-----|--------------|
| recipient_emails | array | |
| sender_name | string | |
| auto_send | bool | |
| include_documents | array | |
**Status: ✅ FERTIG**

### customers (3 Dokumente)
| Feld | Typ | Beschreibung |
|------|-----|--------------|
| id | UUID | |
| email | string | |
| phone | string | |
| name | string | |
| points_balance | int | Aktueller Punktestand |
| total_spent | float | Gesamtumsatz |
| total_points_earned | int | |
| created_at | datetime | |
**Status: ✅ FERTIG**

### loyalty_settings (1 Dokument)
| Feld | Typ | Beschreibung |
|------|-----|--------------|
| points_per_euro | float | 0.2 (= 20 Punkte pro 100€) |
| max_points_per_transaction | int | 200 |
| qr_validity_seconds | int | 90 |
| rounding | string | floor |
**Status: ✅ FERTIG**

### rewards (1 Dokument)
| Feld | Typ | Beschreibung |
|------|-----|--------------|
| id | UUID | |
| name | string | |
| description | string | |
| reward_type | string | |
| points_cost | int | |
| is_active | bool | |
**Status: ✅ FERTIG**

### reminder_rules (2 Dokumente)
| Feld | Typ | Beschreibung |
|------|-----|--------------|
| id | UUID | |
| name | string | |
| hours_before | int | |
| channel | enum | email/sms/whatsapp |
| template | string | |
| is_active | bool | |
**Status: ✅ FERTIG**

### NICHT VORHANDENE Collections:
- marketing_content: ❌ NICHT IMPLEMENTIERT
- ai_log: ❌ NICHT IMPLEMENTIERT
- payment_transactions: ❌ NICHT IMPLEMENTIERT (nur payment_logs)
- shifts (inline in schedules via API)

---

## 3) API-ENDPOINTS (mit RBAC)

### Auth
| Methode | Pfad | Rollen | Zweck |
|---------|------|--------|-------|
| POST | /api/auth/login | Public | Login |
| GET | /api/auth/me | Alle Auth | Aktueller Benutzer |
| POST | /api/auth/change-password | Alle Auth | Passwort ändern |

### Reservierungen
| Methode | Pfad | Rollen | Zweck |
|---------|------|--------|-------|
| GET | /api/reservations | Admin, Schichtleiter | Liste (mit Filter) |
| POST | /api/reservations | Admin, Schichtleiter | Neue Reservierung |
| PATCH | /api/reservations/{id} | Admin, Schichtleiter | Update |
| DELETE | /api/reservations/{id} | Admin, Schichtleiter | Stornieren |
| PATCH | /api/reservations/{id}/status | Admin, Schichtleiter | Statuswechsel |
| POST | /api/walk-ins | Admin, Schichtleiter | Walk-in erstellen |

### Public (Widget)
| Methode | Pfad | Rollen | Zweck |
|---------|------|--------|-------|
| GET | /api/public/availability | Public | Verfügbare Slots |
| POST | /api/public/book | Public | Online-Buchung |
| GET | /api/public/reservations/{id}/cancel-info | Public | Storno-Info |
| POST | /api/public/reservations/{id}/cancel | Public (+Token) | Stornierung |
| POST | /api/public/reservations/{id}/confirm | Public (+Token) | Bestätigung |

### Events
| Methode | Pfad | Rollen | Zweck |
|---------|------|--------|-------|
| GET | /api/events | Admin, Schichtleiter | Event-Liste |
| POST | /api/events | Admin | Neues Event |
| GET/PATCH/DELETE | /api/events/{id} | Admin | Event verwalten |
| POST | /api/events/{id}/publish | Admin | Veröffentlichen |
| GET/POST/PATCH/DELETE | /api/events/{id}/products | Admin | Produkte |
| GET | /api/events/{id}/bookings | Admin, Schichtleiter | Buchungsliste |
| GET | /api/public/events | Public | Öffentliche Events |
| POST | /api/public/events/{id}/book | Public | Event buchen |

### Payments
| Methode | Pfad | Rollen | Zweck |
|---------|------|--------|-------|
| GET | /api/payments/rules | Admin | Regeln anzeigen |
| POST | /api/payments/rules | Admin | Neue Regel |
| PATCH/DELETE | /api/payments/rules/{id} | Admin | Regel verwalten |
| GET | /api/payments/check-required | Admin, Schichtleiter | Prüfen ob Zahlung nötig |
| POST | /api/payments/checkout/create | Admin, Schichtleiter | Stripe Checkout |
| GET | /api/payments/checkout/status/{id} | Admin, Schichtleiter | Status |
| POST | /api/payments/manual/{id} | Admin | Manuelle Freigabe |
| POST | /api/payments/refund/{id} | Admin | Rückerstattung |
| GET | /api/payments/transactions | Admin | Transaktionen |
| GET | /api/payments/logs | Admin | Logs |
| POST | /api/webhook/stripe | Public (Stripe) | Webhook |

### Staff & Schedule
| Methode | Pfad | Rollen | Zweck |
|---------|------|--------|-------|
| GET | /api/staff/members | Admin, Schichtleiter | Mitarbeiter (RBAC-gefiltert) |
| POST | /api/staff/members | Admin | Neuer Mitarbeiter |
| GET/PATCH/DELETE | /api/staff/members/{id} | Admin (Patch/Del), Manager (Get) | Verwaltung |
| PATCH | /api/staff/members/{id}/hr-fields | Admin | HR-Felder (verschlüsselt) |
| POST | /api/staff/members/{id}/reveal-field | Admin | Klartext anzeigen |
| GET | /api/staff/completeness-overview | Admin | Vollständigkeits-Übersicht |
| GET/POST | /api/staff/schedules | Admin | Dienstpläne |
| POST | /api/staff/schedules/{id}/publish | Admin | Veröffentlichen |
| POST | /api/staff/schedules/{id}/archive | Admin | Archivieren |
| GET/POST/PATCH/DELETE | /api/staff/shifts | Admin | Schichten |
| GET | /api/staff/hours-overview | Admin | Stundenübersicht |
| GET | /api/staff/export/staff/csv | Admin | Staff CSV |
| GET | /api/staff/export/shifts/csv | Admin | Shifts CSV |
| GET/POST/PATCH/DELETE | /api/staff/work-areas | Admin, Schichtleiter | Arbeitsbereiche |

### Tax Office (Steuerbüro)
| Methode | Pfad | Rollen | Zweck |
|---------|------|--------|-------|
| GET/PATCH | /api/taxoffice/settings | Admin | Einstellungen |
| GET/POST | /api/taxoffice/jobs | Admin | Export-Jobs |
| GET | /api/taxoffice/jobs/{id}/download/{idx} | Admin | Download |
| POST | /api/taxoffice/jobs/{id}/send | Admin | Per Email senden |
| POST | /api/taxoffice/staff-registration/{id} | Admin | Personalmeldepaket |
| PATCH | /api/taxoffice/staff/{id}/tax-fields | Admin | Steuerfelder |

### Customer/Loyalty (Kunden-App)
| Methode | Pfad | Rollen | Zweck |
|---------|------|--------|-------|
| POST | /api/customer/request-otp | Public | OTP anfordern |
| POST | /api/customer/verify-otp | Public | OTP prüfen |
| POST | /api/customer/request-magic-link | Public | Magic Link |
| POST | /api/customer/verify-magic-link | Public | Magic Link prüfen |
| GET | /api/customer/profile | Customer | Eigenes Profil |
| GET | /api/customer/rewards | Customer | Verfügbare Prämien |
| POST | /api/customer/redeem | Customer | Einlösen |
| GET | /api/customer/points-history | Customer | Punktehistorie |
| GET | /api/loyalty/settings | Admin | Loyalty-Einstellungen |
| PATCH | /api/loyalty/settings | Admin | Einstellungen ändern |
| GET/POST/PATCH/DELETE | /api/loyalty/rewards | Admin | Prämien verwalten |
| POST | /api/loyalty/manual-points | Admin | Manuelle Punkte |
| POST | /api/loyalty/generate-qr | Admin, Schichtleiter | QR generieren |
| GET | /api/loyalty/customer-lookup | Admin | Kunden suchen |
| GET | /api/loyalty/analytics | Admin | Statistiken |

### Sonstige
| Methode | Pfad | Rollen | Zweck |
|---------|------|--------|-------|
| GET | /api/users | Admin | Benutzerliste |
| POST/DELETE | /api/users | Admin | Benutzer verwalten |
| GET | /api/areas | Admin, Schichtleiter | Bereiche |
| GET/POST | /api/opening-hours | Admin | Öffnungszeiten |
| GET | /api/guests | Admin, Schichtleiter | Gästeliste |
| PATCH | /api/guests/{id} | Admin, Schichtleiter | Gast-Flags setzen |
| GET | /api/waitlist | Admin, Schichtleiter | Warteliste |
| POST | /api/waitlist/{id}/convert | Admin, Schichtleiter | In Reservierung umwandeln |
| GET | /api/audit-logs | Admin | Audit-Log |
| GET | /api/message-logs | Admin | Email/SMS Logs |
| GET | /api/settings | Admin | App-Einstellungen |
| POST | /api/settings | Admin | Einstellungen speichern |
| GET | /api/export/table-plan | Admin, Schichtleiter | Tischplan PDF |

---

## 4) UI-SEITEN / ROUTEN

| Route | Seite | Rollen | Status |
|-------|-------|--------|--------|
| /login | Login | Public | ✅ FERTIG |
| /change-password | Passwort ändern | Auth | ✅ FERTIG |
| / | Dashboard | Admin, Schichtleiter | ✅ FERTIG |
| /areas | Bereiche | Admin | ✅ FERTIG |
| /guests | Gästeverwaltung | Admin, Schichtleiter | ✅ FERTIG |
| /waitlist | Warteliste | Admin, Schichtleiter | ✅ FERTIG |
| /events-admin | Events (Admin) | Admin, Schichtleiter | ✅ FERTIG |
| /events/:id | Event-Detail | Admin | ✅ FERTIG |
| /events/:id/products | Event-Produkte | Admin | ✅ FERTIG |
| /events/:id/bookings | Event-Buchungen | Admin, Schichtleiter | ✅ FERTIG |
| /events-public | Events (Public) | Public | ✅ FERTIG |
| /events/:id/book | Event buchen | Public | ✅ FERTIG |
| /payments | Payment-Regeln | Admin | ✅ FERTIG |
| /payments/transactions | Transaktionen | Admin | ✅ FERTIG |
| /payment/success | Zahlung erfolgreich | Public | ✅ FERTIG |
| /payment/cancel | Zahlung abgebrochen | Public | ✅ FERTIG |
| /staff | Mitarbeiter-Liste | Admin, Schichtleiter | ✅ FERTIG |
| /staff/:memberId | Mitarbeiter-Detail | Admin, Schichtleiter | ✅ FERTIG |
| /schedule | Dienstplan | Admin, Schichtleiter | ✅ FERTIG |
| /taxoffice | Steuerbüro-Exporte | Admin | ✅ FERTIG |
| /users | Benutzerverwaltung | Admin | ✅ FERTIG |
| /audit | Audit-Log | Admin | ✅ FERTIG |
| /message-logs | Nachrichten-Log | Admin | ✅ FERTIG |
| /settings | Einstellungen | Admin | ✅ FERTIG |
| /book | Reservierungs-Widget | Public | ✅ FERTIG |
| /confirm/:id | Reservierung bestätigen | Public | ✅ FERTIG |
| /cancel/:id | Reservierung stornieren | Public | ✅ FERTIG |
| /no-access | Kein Zugriff | Mitarbeiter | ✅ FERTIG |

### NICHT IMPLEMENTIERTE UI-Seiten:
- /customer-app (Kunden-App Frontend): ❌ NICHT IMPLEMENTIERT (nur API)
- /marketing: ❌ NICHT IMPLEMENTIERT
- /widget (standalone Widget): ❌ NICHT IMPLEMENTIERT (nur /book)
- Service-Terminal (eigene View): ❌ NICHT IMPLEMENTIERT (Dashboard dient als Terminal)

---

## 5) BUSINESS-REGELN (TATSÄCHLICH IMPLEMENTIERT)

### Reservierungs-Statusmaschine
| Von | Nach | Erlaubt |
|-----|------|---------|
| neu | bestaetigt, storniert, no_show | ✅ |
| bestaetigt | angekommen, storniert, no_show | ✅ |
| angekommen | abgeschlossen, no_show | ✅ |
| abgeschlossen | (Terminal) | ✅ |
| no_show | (Terminal) | ✅ |
| storniert | (Terminal) | ✅ |
**Status: ✅ IMPLEMENTIERT**

### Warteliste-Statusmaschine
| Von | Nach |
|-----|------|
| offen | informiert, erledigt |
| informiert | eingeloest, erledigt |
| eingeloest | erledigt |
**Status: ✅ IMPLEMENTIERT**

### Walk-ins
- Erstellt Reservierung mit status="angekommen" und source="walk_in"
**Status: ✅ IMPLEMENTIERT**

### No-show Grey-/Blacklist Regeln
- Greylist-Schwellenwert: **2 No-Shows**
- Blacklist-Schwellenwert: **4 No-Shows**
- Automatische Flag-Setzung bei No-Show
- Blacklisted Gäste können nicht online buchen
- Greylist erfordert Bestätigung (konfigurierbar)
**Status: ✅ IMPLEMENTIERT**

### Reminder-Regeln
- Konfigurierbare Reminder-Templates
- Channels: email, sms, whatsapp
- Deep-Link-Generierung für WhatsApp
- Reminder-Versand über Cron/Background-Job
**Status: ✅ IMPLEMENTIERT** (Backend), Email-Versand nur geloggt (kein SMTP konfiguriert)

### Storno-Links
- Eindeutiger cancel_token pro Reservierung
- Validierung des Tokens bei Storno
- Storno-Deadline konfigurierbar (24h Standard)
**Status: ✅ IMPLEMENTIERT**

### Payment-Regeln
- Trigger: group_size, greylist, event
- Payment-Types: fixed_deposit, deposit_per_person, full_prepayment
- Status: unpaid → pending → paid / failed / refunded
- Manuelle Zahlungsfreigabe: Nur Admin, Begründung Pflicht
- Stripe-Integration (Checkout Session)
**Status: ✅ IMPLEMENTIERT** (Stripe erfordert API-Key)

### Dienstplan Status
| Status | Sichtbarkeit |
|--------|--------------|
| entwurf | Nur Admin |
| veroeffentlicht | Admin, Schichtleiter |
| archiviert | Nur Admin |
**Status: ✅ IMPLEMENTIERT**

### Soll-/Plan-/Ist-Berechnung
- Soll: weekly_hours aus staff_member
- Plan: Summe geplanter Schichten
- Ist: Aus Zeiterfassung (placeholder)
**Status: ✅ TEILWEISE** (Ist-Berechnung ohne echte Zeiterfassung)

### Steuerbüro Export Jobs
| Status | Beschreibung |
|--------|--------------|
| pending | Job erstellt |
| generating | Wird generiert |
| ready | Bereit zum Download |
| sent | Per Email versandt |
| failed | Fehler |
**Status: ✅ IMPLEMENTIERT**

### Loyalty Regeln
- **points_per_euro: 0.2** (= 20 Punkte pro 100€)
- **max_points_per_transaction: 200**
- **QR-Gültigkeit: 90 Sekunden**
- Keine direkten Saldoänderungen (nur über Ledger)
- Manuelle Punktebuchung: Begründung Pflicht
- Reward-Einlösung mit pending/confirmed Status
**Status: ✅ IMPLEMENTIERT**

### Marketing Freigabe/Auto-posting
**Status: ❌ NICHT IMPLEMENTIERT**

---

## 6) LOGS / AUDIT / SICHERHEIT

### Audit-Log
Aktiv für:
- ✅ Reservierungen (create, update, status_change, delete)
- ✅ Benutzer (create, delete)
- ✅ Gäste (flag_change)
- ✅ Staff Members (create, update, archive, HR-fields)
- ✅ Schedules (create, publish, archive)
- ✅ Payment Rules (create, update, delete)
- ✅ Export Jobs (create, status_change)
- ✅ Loyalty (manual_points, redemption)
- ✅ Sensitive HR Field Reveal (reveal_sensitive_field)

### Message/Email Log
- ✅ Email-Versuche werden geloggt
- ✅ Reminder-Versand wird geloggt
- SMTP nicht konfiguriert (nur Logging)

### RBAC serverseitig
- ✅ Alle Endpoints mit Depends(require_admin/require_manager)
- ✅ Mitarbeiter hat keinen Zugriff auf Backoffice
- ✅ Schichtleiter eingeschränkter Zugriff

### HR-Sensitivfelder Absicherung
- ✅ **Verschlüsselung at rest**: Fernet (AES-256)
- ✅ **RBAC**: Nur Admin sieht sensitive Felder
- ✅ **Maskierung**: tax_id, social_security_number, bank_iban
- ✅ **Reveal-Endpoint**: Mit Audit-Logging
- ✅ **Export**: Nur Admin kann Exporte erstellen

### Public Endpoints
| Endpoint | Liefert |
|----------|---------|
| /api/public/availability | Verfügbare Slots (keine Kundendaten) |
| /api/public/book | Bestätigung (keine sensitiven Daten) |
| /api/public/events | Öffentliche Event-Infos |
| /api/public/events/{id}/book | Buchungsbestätigung |
| /api/customer/request-otp | "Code gesendet" (keine Details) |

---

## 7) KNOWN ISSUES / TODO

### Bekannte Probleme
1. **Email-Versand**: SMTP nicht konfiguriert, Emails werden nur geloggt
2. **Stripe**: Erfordert API-Key Konfiguration
3. **Kunden-App Frontend**: API vorhanden, aber kein separates Frontend
4. **Service-Terminal**: Kein dediziertes Terminal-UI (Dashboard wird verwendet)
5. **Zeiterfassung**: "Ist"-Stunden werden nicht erfasst (nur Plan/Soll)

### TODO nach Priorität

**HOCH:**
1. SMTP konfigurieren für echten Email-Versand
2. Stripe API-Key einrichten für Payments
3. Kunden-App Frontend erstellen

**MITTEL:**
4. Service-Terminal als eigene Seite
5. Zeiterfassung für Mitarbeiter
6. Widget als standalone iFrame
7. Tischplan-Grafik (aktuell nur PDF-Liste)

**NIEDRIG:**
8. Marketing-Modul
9. AI/KI-Integrationen
10. SMS-Versand (Twilio etc.)
11. Push-Notifications

---

## ABSCHLUSS

### Was ist wirklich nutzbar im Betrieb heute?
1. ✅ **Reservierungsverwaltung**: Online-Buchung, Walk-ins, Statusmaschine vollständig
2. ✅ **Gästeverwaltung**: Grey-/Blacklist, No-Show Tracking, Gästehistorie
3. ✅ **Warteliste**: Kompletter Workflow inkl. Umwandlung
4. ✅ **Event-Management**: Events erstellen, Produkte, Buchungen
5. ✅ **Mitarbeiterverwaltung**: Stammdaten, HR-Felder (verschlüsselt), Dokumente
6. ✅ **Dienstplanung**: Wochenpläne, Schichten, Veröffentlichung
7. ✅ **Steuerbüro-Exporte**: CSV/PDF generieren, Download
8. ✅ **Loyalty-System**: Punkte, Prämien, QR-Code (Backend vollständig)
9. ✅ **Payment-Regeln**: Konfiguration, Check (Stripe benötigt Key)
10. ✅ **Audit-Trail**: Lückenlose Protokollierung aller Aktionen

### Was fehlt noch für Sprint 9 / Reservierung Feinschliff?
1. ❌ **Tischplan-Visualisierung**: Grafische Tischanordnung statt Liste
2. ❌ **Drag & Drop**: Reservierungen auf Tische ziehen
3. ❌ **Kapazitätsanzeige**: Echtzeit-Auslastung pro Bereich
4. ❌ **SMS-Integration**: Für Reminder (aktuell nur Email/WhatsApp-Link)
5. ❌ **Kunden-App Frontend**: Mobile App für Loyalty
6. ❌ **Service-Terminal**: Dedizierte Touch-optimierte Ansicht
7. ❌ **Wartezeit-Schätzung**: Automatische Berechnung
8. ❌ **Google Reservierungen**: Integration
9. ❌ **Online-Zahlung bei Buchung**: Stripe im Widget
10. ❌ **Multi-Restaurant**: Mandantenfähigkeit
