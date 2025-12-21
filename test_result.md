#====================================================================================================
# START - Testing Protocol - DO NOT EDIT OR REMOVE THIS SECTION
#====================================================================================================

# THIS SECTION CONTAINS CRITICAL TESTING INSTRUCTIONS FOR BOTH AGENTS
# BOTH MAIN_AGENT AND TESTING_AGENT MUST PRESERVE THIS ENTIRE BLOCK

# Communication Protocol:
# If the `testing_agent` is available, main agent should delegate all testing tasks to it.
#
# You have access to a file called `test_result.md`. This file contains the complete testing state
# and history, and is the primary means of communication between main and the testing agent.
#
# Main and testing agents must follow this exact format to maintain testing data. 

#====================================================================================================
# END - Testing Protocol - DO NOT EDIT OR REMOVE THIS SECTION
#====================================================================================================

user_problem_statement: |
  FULL QA AUDIT Sprint 1-7 für GastroCore

backend:
  - task: "Auth & RBAC"
    implemented: true
    working: true
    file: "/app/backend/core/auth.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: false
        agent: "testing"
        comment: "Admin login failed (401) - password hash mismatch"
      - working: true
        agent: "main"
        comment: "Fixed password hashes for all users"
      - working: true
        agent: "testing"
        comment: "✅ VERIFIED: All 3 roles login successfully. Admin/Schichtleiter/Mitarbeiter auth working. RBAC properly blocks Mitarbeiter from /api/reservations (403). GET /api/auth/me returns correct role data."

  - task: "Guest Search API"
    implemented: true
    working: true
    file: "/app/backend/server.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: false
        agent: "testing"
        comment: "MongoDB regex error with special characters (+)"
      - working: true
        agent: "main"
        comment: "Added re.escape() for safe regex search"
      - working: true
        agent: "testing"
        comment: "✅ VERIFIED: GET /api/guests?search=+49 works correctly. Special character + no longer causes regex errors. Found 2 guests in search results."

  - task: "Waitlist Conversion"
    implemented: true
    working: true
    file: "/app/backend/server.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: false
        agent: "testing"
        comment: "422 error - time parameter missing"
      - working: true
        agent: "main"
        comment: "Endpoint works correctly with time query parameter"
      - working: true
        agent: "testing"
        comment: "✅ VERIFIED: POST /api/waitlist/{id}/convert?time=18:30 works correctly. Successfully converted waitlist entry to reservation ID: bc72cbb6-919b-40a8-bdf8-5a74cce53a3e"

  - task: "Reservations CRUD"
    implemented: true
    working: true
    file: "/app/backend/server.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: true
        agent: "testing"
        comment: "✅ VERIFIED: Full reservation workflow working. GET /api/reservations (18 entries), POST /api/reservations creates successfully, Status transitions neu→bestaetigt→angekommen→abgeschlossen all work correctly."

  - task: "Public Booking Widget"
    implemented: true
    working: true
    file: "/app/backend/server.py"
    stuck_count: 0
    priority: "medium"
    needs_retesting: false
    status_history:
      - working: true
        agent: "testing"
        comment: "✅ VERIFIED: POST /api/public/book creates reservations successfully. GET /api/public/availability returns 21 available slots for 2025-12-25."

  - task: "Walk-ins Quick Entry"
    implemented: true
    working: true
    file: "/app/backend/server.py"
    stuck_count: 0
    priority: "medium"
    needs_retesting: false
    status_history:
      - working: true
        agent: "testing"
        comment: "✅ VERIFIED: POST /api/walk-ins creates walk-in with status 'angekommen' immediately as expected."

  - task: "Waitlist Management"
    implemented: true
    working: true
    file: "/app/backend/server.py"
    stuck_count: 0
    priority: "medium"
    needs_retesting: false
    status_history:
      - working: true
        agent: "testing"
        comment: "✅ VERIFIED: GET /api/waitlist (4 entries), POST /api/waitlist creates entries successfully, conversion to reservations working."

  - task: "Guest Management"
    implemented: true
    working: true
    file: "/app/backend/server.py"
    stuck_count: 0
    priority: "medium"
    needs_retesting: false
    status_history:
      - working: true
        agent: "testing"
        comment: "✅ VERIFIED: POST /api/guests creates guests, PATCH /api/guests/{id} updates flags to greylist successfully. Search with special characters working."

  - task: "Payments System"
    implemented: false
    working: false
    file: "/app/backend/server.py"
    stuck_count: 1
    priority: "medium"
    needs_retesting: true
    status_history:
      - working: false
        agent: "testing"
        comment: "❌ CRITICAL: POST /api/payments/rules returns 422 validation error. GET /api/payments/check-required missing 'required' field. Payment endpoints exist but validation/logic incomplete."

  - task: "Staff & Dienstplan"
    implemented: false
    working: false
    file: "/app/backend/server.py"
    stuck_count: 1
    priority: "medium"
    needs_retesting: true
    status_history:
      - working: false
        agent: "testing"
        comment: "❌ CRITICAL: POST /api/staff/schedules returns 422 validation error. GET /api/staff/hours-overview returns 422. Staff endpoints exist but validation/logic incomplete."

  - task: "Tax Office Export"
    implemented: true
    working: true
    file: "/app/backend/server.py"
    stuck_count: 0
    priority: "low"
    needs_retesting: false
    status_history:
      - working: true
        agent: "testing"
        comment: "✅ VERIFIED: GET /api/taxoffice/settings (9 fields), POST /api/taxoffice/jobs creates jobs successfully, download endpoints working (127 bytes CSV downloaded)."

  - task: "Loyalty System"
    implemented: false
    working: false
    file: "/app/backend/server.py"
    stuck_count: 1
    priority: "low"
    needs_retesting: true
    status_history:
      - working: false
        agent: "testing"
        comment: "❌ CRITICAL: All loyalty endpoints return 404. POST /api/customer/request-otp, GET /api/loyalty/settings, GET /api/loyalty/rewards not implemented."

  - task: "Audit Logs"
    implemented: true
    working: true
    file: "/app/backend/server.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: true
        agent: "testing"
        comment: "✅ VERIFIED: GET /api/audit-logs returns 77 entries. Status changes properly logged (20 status change entries found). Audit system fully functional."

metadata:
  created_by: "main_agent"
  version: "7.0"
  test_sequence: 4
  run_ui: false

test_plan:
  current_focus:
    - "Auth & RBAC"
    - "Guest Search API"
    - "Waitlist Conversion"
    - "Full QA Audit Sprint 1-7"
  stuck_tasks: []
  test_all: true
  test_priority: "high_first"

agent_communication:
  - agent: "main"
    message: "BUGS FIXED: 1) Admin login - password hashes reset, 2) Guest search - regex escaping added, 3) Waitlist conversion works. Run FULL QA AUDIT again. Login: admin@gastrocore.de / Admin123!"
  - agent: "testing"
    message: "FULL QA AUDIT COMPLETE - Sprint 1-7 tested. SUCCESS RATE: 80.6% (29/36 tests passed). CRITICAL FINDINGS: 1) Auth & RBAC ✅ WORKING, 2) Guest Search ✅ WORKING, 3) Waitlist Conversion ✅ WORKING. FAILURES: Sprint 6 Payments (422 errors), Sprint 7 Staff (422 errors), Sprint 9 Loyalty (404 endpoints missing). Core functionality operational but some advanced features need implementation."
