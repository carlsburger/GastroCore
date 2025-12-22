#====================================================================================================
# Frontend Smoke Tests - Schedule & MyShifts
#====================================================================================================

user_problem_statement: |
  FRONTEND SMOKE TESTS – Schedule (/schedule) & MyShifts (/my-shifts)
  
  TESTDATEN VORHANDEN:
  - Admin: admin@carlsburg.de / Carlsburg2025!
  - Schichtleiter: schichtleiter@gastrocore.de / Schicht2025!
  - Mitarbeiter: mitarbeiter@gastrocore.de / Mitarbeiter2025!
  - 4 Work Areas, 3 Staff Members, 1 Schedule (KW 52), 4+ Shifts

frontend:
  - task: "TESTBLOCK A: Routing & Auth"
    implemented: true
    working: false
    file: "Schedule.jsx, MyShifts.jsx"
    stuck_count: 1
    priority: "critical"
    needs_retesting: false
    status_history:
      - working: false
        agent: "testing"
        comment: "CRITICAL: Frontend-Backend connectivity issue. Login requests to /api/auth/login hang indefinitely. Backend is running (curl works), but frontend proxy configuration appears broken. Submit button stuck in loading state. Network requests show POST to localhost:3000/api/auth/login but no response received."

  - task: "TESTBLOCK B: Schedule Core Flows"
    implemented: true
    working: "NA"
    file: "Schedule.jsx"
    stuck_count: 0
    priority: "critical"
    needs_retesting: true
    status_history:
      - working: "NA"
        agent: "testing"
        comment: "Cannot test - blocked by TESTBLOCK A login issue. Schedule page requires authentication."

  - task: "TESTBLOCK C: Konfliktfehler im UI"
    implemented: true
    working: "NA"
    file: "Schedule.jsx"
    stuck_count: 0
    priority: "critical"
    needs_retesting: true
    status_history:
      - working: "NA"
        agent: "testing"
        comment: "Cannot test - blocked by TESTBLOCK A login issue. Conflict testing requires authenticated access to schedule."

  - task: "TESTBLOCK D: Exports"
    implemented: true
    working: "NA"
    file: "Schedule.jsx"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: "NA"
        agent: "testing"
        comment: "Cannot test - blocked by TESTBLOCK A login issue. Export functionality requires authenticated access."

  - task: "TESTBLOCK E: MyShifts"
    implemented: true
    working: "NA"
    file: "MyShifts.jsx"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: "NA"
        agent: "testing"
        comment: "Cannot test - blocked by TESTBLOCK A login issue. MyShifts page requires authentication."

metadata:
  created_by: "main_agent"
  version: "9.1"
  test_sequence: 1
  run_ui: true

test_plan:
  current_focus:
    - "Schedule UI"
    - "MyShifts UI"
    - "Konfliktfehler-Handling"
    - "Exports"
  stuck_tasks: []
  test_all: true
  test_priority: "critical_first"

agent_communication:
  - agent: "main"
    message: |
      FRONTEND SMOKE TESTS – Schedule & MyShifts
      
      LOGINS:
      - Admin: admin@carlsburg.de / Carlsburg2025!
      - Schichtleiter: schichtleiter@gastrocore.de / Schicht2025!
      - Mitarbeiter: mitarbeiter@gastrocore.de / Mitarbeiter2025!
      
      TESTBLOCK A: ROUTING & AUTH
      A1) Als Admin: /schedule und /my-shifts öffnen → muss laden
      A2) Als Mitarbeiter: /my-shifts öffnen → zeigt nur eigene Schichten
          /schedule öffnen → entweder blockiert oder read-only
      
      TESTBLOCK B: SCHEDULE CORE FLOWS (als Admin)
      B1) Woche wechseln (vor/zurück) → UI stabil
      B2) Plan erstellen falls nicht vorhanden
      B3) Schicht hinzufügen → Dialog öffnen, MA/Bereich/Zeit wählen, speichern
      B4) Schicht bearbeiten → Zeit ändern, speichern
      B5) Schicht löschen
      B6) Veröffentlichen → Status wechselt
      B7) Woche kopieren → neue Woche entsteht
      
      TESTBLOCK C: KONFLIKTFEHLER IM UI (WICHTIG!)
      C1) Doppelbelegung: Für Thomas Koch (dd1d3c82-f6da-4590-8331-346b0d3ece7d) 
          am 22.12.2025 10:00-18:00 existiert bereits eine Schicht.
          Versuche gleiche Schicht nochmal → Toast-Fehler "Konflikt"
      C2) Ruhezeit: Für Thomas Koch existiert Schicht am 23.12.2025 18:00-23:00.
          Versuche Schicht am 24.12.2025 06:00-10:00 → Toast-Fehler "Ruhezeit"
      
      TESTBLOCK D: EXPORTS
      D1) PDF Export klicken
      D2) CSV Export klicken
      
      TESTBLOCK E: MY-SHIFTS
      E1) Als Mitarbeiter anzeigen
      E2) Wochen-Navigation
      E3) Empty State (falls keine Schichten)
      
      WICHTIG:
      - Bei Fehlern: Screenshot + Console Logs
      - 409 Fehler = ERWARTET bei Konflikttests
      - Klare PASS/FAIL Bewertung pro Test

#====================================================================================================
# Testing Protocol (DO NOT EDIT)
#====================================================================================================
