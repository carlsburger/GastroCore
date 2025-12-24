#====================================================================================================
# Schichtmodelle Session - Normal vs Kulturabend + Apply Idempotent + UI-Fix
#====================================================================================================

user_problem_statement: |
  SESSION TASK – Schichtmodelle korrekt machen (Normal vs Kulturabend) + Apply idempotent + UI-Fix "Close+undefinedmin"
  
  ZIELE:
  1. Schichtmodelle in zwei Betriebsarten: Normal + Kulturabend (bis 00:00 bei Veranstaltungen)
  2. Schichtende korrekt abbilden (fixed / close_relative)
  3. UI-Fix: close-relative Ende wird korrekt angezeigt (kein undefined)
  4. Apply wird idempotent: keine Duplikate bei erneutem Apply

frontend:
  - task: "UI-Fix Close+undefinedmin"
    implemented: true
    working: true
    file: "ShiftTemplates.jsx"
    stuck_count: 0
    priority: "critical"
    needs_retesting: false
    status_history:
      - working: true
        agent: "main"
        comment: "✅ FIXED: Zeile 368-370 korrigiert. Jetzt wird 'Close + 30 min' statt 'Close+undefinedmin' angezeigt. Fallback mit ?? Operator implementiert. Kulturabend-Badge hinzugefügt."

  - task: "Kulturabend-Badge in UI"
    implemented: true
    working: true
    file: "ShiftTemplates.jsx"
    stuck_count: 0
    priority: "medium"
    needs_retesting: false
    status_history:
      - working: true
        agent: "main"
        comment: "✅ Lila Badge 'Kulturabend' wird bei event_mode='kultur' angezeigt. Event-Mode Dropdown im Dialog hinzugefügt."

backend:
  - task: "event_mode Enum + Models"
    implemented: true
    working: true
    file: "staff_module.py"
    stuck_count: 0
    priority: "critical"
    needs_retesting: false
    status_history:
      - working: true
        agent: "main"
        comment: "✅ EventMode Enum (normal/kultur) hinzugefügt. ShiftTemplateCreate/Update erweitert mit event_mode Feld."

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
