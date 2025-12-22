#====================================================================================================
# Dienstplan Live-Ready Testing - Sprint 9
#====================================================================================================

user_problem_statement: |
  SPRINT: DIENSTPLAN – LIVE-READY (ADDITIV)
  - Konflikterkennung (Doppelbelegung, Ruhezeit 11h)
  - Audit-Logs für Schichten
  - Woche kopieren
  - Mitarbeiter-Selbstansicht
  - CSV-Export

backend:
  - task: "Konflikterkennung Doppelbelegung"
    implemented: true
    working: true
    file: "staff_module.py"
    stuck_count: 0
    priority: "critical"
    needs_retesting: false
    status_history:
      - working: true
        agent: "testing"
        comment: "✅ CRITICAL TEST PASSED: Conflict detection working correctly. Attempting to create duplicate shift returns HTTP 409 with message 'Konflikt: Mitarbeiter ist bereits eingeplant (10:00-18:00)'. Tested with shift on 2025-12-22 10:00-18:00."

  - task: "Konflikterkennung Ruhezeit 11h"
    implemented: true
    working: true
    file: "staff_module.py"
    stuck_count: 0
    priority: "critical"
    needs_retesting: false
    status_history:
      - working: true
        agent: "testing"
        comment: "✅ CRITICAL TEST PASSED: Rest time validation working correctly. Creating shift with only 7h rest between evening (18:00-23:00) and morning (06:00-14:00) returns HTTP 409 with message 'Ruhezeit von 11h unterschritten (nur 7.0h seit Schichtende am Vortag)'."

  - task: "Audit-Logs Schicht Create/Update/Delete"
    implemented: true
    working: true
    file: "staff_module.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: true
        agent: "testing"
        comment: "✅ Audit logging working correctly. Found 2 shift create audit entries with entity_type='shift' and action='create'. All shift operations are properly logged to audit system."

  - task: "Woche kopieren POST /schedules/{id}/copy"
    implemented: true
    working: true
    file: "staff_module.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: true
        agent: "testing"
        comment: "✅ Week copy functionality working correctly. POST /api/staff/schedules/{id}/copy returns HTTP 200 with new_schedule_id, shifts_copied count (2 shifts), and new schedule has status 'entwurf' as expected."

  - task: "My-Shifts GET /staff/my-shifts"
    implemented: true
    working: true
    file: "staff_module.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: true
        agent: "testing"
        comment: "✅ My-Shifts endpoint working correctly. GET /api/staff/my-shifts returns HTTP 200 with array of shifts (0 shifts for admin user as expected). Endpoint accepts date_from and date_to parameters."

  - task: "CSV-Export GET /staff/export/shifts/csv"
    implemented: true
    working: true
    file: "staff_module.py"
    stuck_count: 0
    priority: "medium"
    needs_retesting: false
    status_history:
      - working: true
        agent: "testing"
        comment: "✅ CSV export working correctly. GET /api/staff/export/shifts/csv?year=2025&week=52 returns HTTP 200 with CSV file (161 bytes). Content-Type header indicates CSV format."

frontend:
  - task: "Schedule UI mit Kopieren/CSV Buttons"
    implemented: true
    working: "needs_testing"
    file: "Schedule.jsx"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history: []

  - task: "MyShifts Seite"
    implemented: true
    working: "needs_testing"
    file: "MyShifts.jsx"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history: []

metadata:
  created_by: "main_agent"
  version: "9.0"
  test_sequence: 1
  run_ui: false

test_plan:
  current_focus:
    - "Konflikterkennung"
    - "Audit-Logs"
    - "Woche kopieren"
    - "My-Shifts"
    - "CSV-Export"
  stuck_tasks: []
  test_all: true
  test_priority: "critical_first"

agent_communication:
  - agent: "main"
    message: |
      DIENSTPLAN LIVE-READY SMOKE TESTS
      
      Login: admin@carlsburg.de / Carlsburg2025! (oder admin@gastrocore.de / Admin123!)
      
      KRITISCHE TESTS:
      1. KONFLIKTERKENNUNG DOPPELBELEGUNG:
         - Erstelle Schedule für aktuelle KW falls nötig: POST /api/staff/schedules
         - Erstelle Schicht: POST /api/staff/shifts (staff_member_id, shift_date, start_time: "10:00", end_time: "18:00")
         - Versuche GLEICHE Schicht nochmal → MUSS 409 mit "Konflikt: Mitarbeiter ist bereits eingeplant" zurückgeben
      
      2. KONFLIKTERKENNUNG RUHEZEIT:
         - Erstelle Schicht am Tag X: 18:00-23:00
         - Erstelle Schicht am Tag X+1: 06:00-14:00 (nur 7h Abstand!)
         - → MUSS 409 mit "Ruhezeit von 11h unterschritten" zurückgeben
      
      3. AUDIT-LOGS:
         - Nach Schicht-Create: GET /api/audit-logs?entity_type=shift&limit=1 → Muss "create" Action zeigen
         - Nach Schicht-Update: PATCH Schicht → Audit-Log mit "update"
         - Nach Schicht-Delete: DELETE Schicht → Audit-Log mit "archive"
      
      4. WOCHE KOPIEREN:
         - POST /api/staff/schedules/{schedule_id}/copy
         - → Neuer Schedule in nächster KW mit Status "entwurf"
         - → Alle Schichten mitkopiert
      
      5. MY-SHIFTS:
         - Login als Mitarbeiter (falls vorhanden) oder Admin
         - GET /api/staff/my-shifts?date_from=2025-01-01&date_to=2025-12-31
         - → Nur eigene Schichten zurück
      
      6. CSV-EXPORT:
         - GET /api/staff/export/shifts/csv?year=2025&week=52
         - → CSV-Datei mit Schichtdaten

#====================================================================================================
# Testing Protocol (DO NOT EDIT)
#====================================================================================================
# 1. Read test_result.md before testing
# 2. Update status_history after each test
# 3. Set working: true/false based on results
# 4. Report stuck_count if same issue persists
# 5. Focus on current_focus tasks first
