#====================================================================================================
# Event-Preise + Varianten + Zahlung/Anzahlung Session (26.12.2025)
#====================================================================================================

user_problem_statement: |
  SESSION TASK – Event-Preise + Varianten + Zahlung/Anzahlung im Reservierungssystem
  
  ZIELE:
  1. Event-Preise mit Single-Price oder Varianten-Modus
  2. Payment-Policy: none/deposit/full je nach Event-Kategorie
  3. Preisberechnung: seats × price_per_person, Anzahlung nach Typ
  4. WP-Sync Schutz: Manuell gepflegte Felder nicht überschreiben
  5. Admin-UI für Preis- und Zahlungs-Konfiguration

frontend:
  - task: "EventPricing Dialog Komponente"
    implemented: true
    working: true
    file: "components/EventPricing.jsx"
    stuck_count: 0
    priority: "critical"
    needs_retesting: true
    status_history:
      - working: true
        agent: "main"
        comment: "✅ Neue Komponente: EventPricingDialog mit Tabs für Preise und Zahlung. Varianten-Editor, Deposit-Konfiguration."

  - task: "Events.jsx Integration"
    implemented: true
    working: true
    file: "pages/Events.jsx"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: true
        agent: "main"
        comment: "✅ Pricing-Button und EventPriceBadge in Event-Liste. Dialog-Integration."

backend:
  - task: "Event Pricing Enums + Models"
    implemented: true
    working: true
    file: "events_module.py"
    stuck_count: 0
    priority: "critical"
    needs_retesting: false
    status_history:
      - working: true
        agent: "main"
        comment: "✅ EventPricingMode, PaymentPolicyMode, DepositType Enums. EventPricing, PaymentPolicy Pydantic Models."

  - task: "Pricing API Endpoints"
    implemented: true
    working: true
    file: "events_module.py"
    stuck_count: 0
    priority: "critical"
    needs_retesting: false
    status_history:
      - working: true
        agent: "main"
        comment: "✅ PATCH /events/{id}/pricing, PATCH /events/{id}/payment-policy, GET /events/{id}/pricing-info, POST /events/{id}/calculate-price"

  - task: "WP-Sync Schutz"
    implemented: true
    working: true
    file: "events_module.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: true
        agent: "main"
        comment: "✅ event_pricing und payment_policy sind NICHT in WP-Sync update_fields. Marker-Felder *_modified_at."

metadata:
  created_by: "main_agent"
  version: "11.0"
  session_date: "2025-12-26"
  test_sequence: 1
  run_ui: true

#====================================================================================================
# TEST-ERGEBNISSE
#====================================================================================================

test_results:
  test_a_schnitzel_ohne_anzahlung:
    seats: 4
    price_per_person: 29.90
    total_price: 119.60
    payment_mode: "none"
    payment_required: false
    amount_due: 0
    status: "✅ PASS"

  test_a2_schnitzel_mit_anzahlung:
    seats: 4
    price_per_person: 29.90
    total_price: 119.60
    payment_mode: "deposit"
    payment_required: true
    deposit_per_person: 10.00
    amount_due: 40.00
    status: "✅ PASS"

  test_b_gaensemenue:
    seats: 2
    variant_hauptgang:
      price_per_person: 34.90
      total_price: 69.80
    variant_3gaenge:
      price_per_person: 49.90
      total_price: 99.80
    payment_mode: "deposit"
    deposit_per_person: 20.00
    amount_due: 40.00
    status: "✅ PASS"

  test_c_valentinstag:
    seats: 2
    variant_classic:
      price_per_person: 59.90
      total_price: 119.80
    variant_veg:
      price_per_person: 49.90
      total_price: 99.80
    payment_mode: "deposit"
    deposit_per_person: 25.00
    amount_due: 50.00
    status: "✅ PASS"

  test_d_wp_sync_schutz:
    event_pricing_protected: true
    payment_policy_protected: true
    status: "✅ PASS"

#====================================================================================================
# VORHERIGE SESSION (Schichtmodelle)
#====================================================================================================

previous_session:

  - task: "Seed Default Templates (Normal + Kulturabend)"
    implemented: true
    working: true
    file: "staff_module.py"
    stuck_count: 0
    priority: "critical"
    needs_retesting: false
    status_history:
      - working: true
        agent: "main"
        comment: "✅ 9 Templates erstellt: 6 Normal (Service Früh/Spät, Küche Früh/Spät, Schichtleiter, Reinigung) + 3 Kulturabend (Service Spät Kultur, Küche Spät Kultur, Schichtleiter Kultur - alle bis 00:00)"

  - task: "Apply Templates Idempotent"
    implemented: true
    working: true
    file: "staff_module.py"
    stuck_count: 0
    priority: "critical"
    needs_retesting: false
    status_history:
      - working: true
        agent: "testing"
        comment: "✅ SMOKE TEST PASS: Idempotenz funktioniert. Apply #1: 42 Schichten erstellt. Apply #2: 0 erstellt, 35 übersprungen (skipped_existing). Keine Duplikate."

  - task: "ApplyTemplatesBody Model Fix"
    implemented: true
    working: true
    file: "staff_module.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: true
        agent: "main"
        comment: "✅ Separates ApplyTemplatesBody Model erstellt (ohne schedule_id im Body, da aus URL-Path). Endpoint /schedules/{schedule_id}/apply-templates funktioniert."

metadata:
  created_by: "main_agent"
  version: "10.0"
  session_date: "2025-12-24"
  test_sequence: 1
  run_ui: false

#====================================================================================================
# ABSCHLUSSREPORT
#====================================================================================================

abschlussreport:
  templates:
    total: 9
    normalbetrieb:
      - name: "Service Früh"
        times: "10:00 - 15:00"
        end_time_mode: "fixed"
        department: "service"
      - name: "Service Spät"
        times: "17:00 - Close + 30 min"
        end_time_mode: "close_plus_minutes"
        department: "service"
      - name: "Küche Früh"
        times: "09:00 - 15:00"
        end_time_mode: "fixed"
        department: "kitchen"
      - name: "Küche Spät"
        times: "16:00 - Close + 30 min"
        end_time_mode: "close_plus_minutes"
        department: "kitchen"
      - name: "Schichtleiter"
        times: "11:00 - Close"
        end_time_mode: "close_plus_minutes (offset=0)"
        department: "service"
      - name: "Reinigung"
        times: "06:00 - 10:00"
        end_time_mode: "fixed"
        department: "reinigung"
    kulturabend:
      - name: "Service Spät Kultur"
        times: "17:00 - 00:00"
        end_time_mode: "fixed"
        department: "service"
        headcount: 3
      - name: "Küche Spät Kultur"
        times: "16:00 - 00:00"
        end_time_mode: "fixed"
        department: "kitchen"
        headcount: 2
      - name: "Schichtleiter Kultur"
        times: "11:00 - 00:00"
        end_time_mode: "fixed"
        department: "service"

  apply_test:
    schedule: "KW2/2026 (30fd1a35-8fd8-4968-a8b6-7baa74f972ee)"
    apply_1:
      shifts_created: 42
      skipped_existing: 0
      templates_used: 8
    apply_2:
      shifts_created: 0
      skipped_existing: 35
      idempotent: true

  ui_fix:
    problem: "Close+undefinedmin angezeigt"
    solution: "Fallback mit ?? Operator: (template.close_plus_minutes ?? 0)"
    status: "✅ Behoben - Screenshot bestätigt"
    kulturabend_badge: "✅ Lila Badge wird bei event_mode='kultur' angezeigt"

  fazit: |
    ✅ ALLE ZIELE ERREICHT:
    1. Schichtmodelle Normal + Kulturabend implementiert
    2. Endzeiten korrekt (fixed / close_relative)
    3. UI zeigt keine 'undefined' mehr
    4. Apply ist idempotent (keine Duplikate)
    
    KEINE Breaking Changes - additive Änderungen nur.

#====================================================================================================
# Testing Protocol (DO NOT EDIT)
#====================================================================================================

testing_protocol: |
  BACKEND TESTING:
  1. Login mit admin@carlsburg.de / Carlsburg2025!
  2. GET /api/staff/shift-templates prüfen
  3. POST /api/staff/schedules/{id}/apply-templates testen
  4. Idempotenz durch wiederholten Apply verifizieren
  
  FRONTEND TESTING:
  - /shift-templates Seite öffnen
  - Prüfen: Keine "undefined" in Zeiten-Spalte
  - Prüfen: Kulturabend-Badge sichtbar
  
  CREDENTIALS:
  - Admin: admin@carlsburg.de / Carlsburg2025!
  - Backend: http://localhost:8001
