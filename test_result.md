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
# The testing data must be entered in yaml format Below is the data structure:
# 
## user_problem_statement: {problem_statement}
## backend:
##   - task: "Task name"
##     implemented: true
##     working: true  # or false or "NA"
##     file: "file_path.py"
##     stuck_count: 0
##     priority: "high"  # or "medium" or "low"
##     needs_retesting: false
##     status_history:
##         -working: true  # or false or "NA"
##         -agent: "main"  # or "testing" or "user"
##         -comment: "Detailed comment about status"
##
## frontend:
##   - task: "Task name"
##     implemented: true
##     working: true  # or false or "NA"
##     file: "file_path.js"
##     stuck_count: 0
##     priority: "high"  # or "medium" or "low"
##     needs_retesting: false
##     status_history:
##         -working: true  # or false or "NA"
##         -agent: "main"  # or "testing" or "user"
##         -comment: "Detailed comment about status"
##
## metadata:
##   created_by: "main_agent"
##   version: "1.0"
##   test_sequence: 0
##   run_ui: false
##
## test_plan:
##   current_focus:
##     - "Task name 1"
##     - "Task name 2"
##   stuck_tasks:
##     - "Task name with persistent issues"
##   test_all: false
##   test_priority: "high_first"  # or "sequential" or "stuck_first"
##
## agent_communication:
##     -agent: "main"  # or "testing" or "user"
##     -message: "Communication message between agents"

# Protocol Guidelines for Main agent
#
# 1. Update Test Result File Before Testing:
#    - Main agent must always update the `test_result.md` file before calling the testing agent
#    - Add implementation details to the status_history
#    - Set `needs_retesting` to true for tasks that need testing
#    - Update the `test_plan` section to guide testing priorities
#    - Add a message to `agent_communication` explaining what you've done
#
# 2. Incorporate User Feedback:
#    - When a user provides feedback that something is or isn't working, add this information to the relevant task's status_history
#    - Update the working status based on user feedback
#    - If a user reports an issue with a task that was marked as working, increment the stuck_count
#    - Whenever user reports issue in the app, if we have testing agent and task_result.md file so find the appropriate task for that and append in status_history of that task to contain the user concern and problem as well 
#
# 3. Track Stuck Tasks:
#    - Monitor which tasks have high stuck_count values or where you are fixing same issue again and again, analyze that when you read task_result.md
#    - For persistent issues, use websearch tool to find solutions
#    - Pay special attention to tasks in the stuck_tasks list
#    - When you fix an issue with a stuck task, don't reset the stuck_count until the testing agent confirms it's working
#
# 4. Provide Context to Testing Agent:
#    - When calling the testing agent, provide clear instructions about:
#      - Which tasks need testing (reference the test_plan)
#      - Any authentication details or configuration needed
#      - Specific test scenarios to focus on
#      - Any known issues or edge cases to verify
#
# 5. Call the testing agent with specific instructions referring to test_result.md
#
# IMPORTANT: Main agent must ALWAYS update test_result.md BEFORE calling the testing agent, as it relies on this file to understand what to test next.

#====================================================================================================
# END - Testing Protocol - DO NOT EDIT OR REMOVE THIS SECTION
#====================================================================================================



#====================================================================================================
# Testing Data - Main Agent and testing sub agent both should log testing data below this section
#====================================================================================================

user_problem_statement: |
  Sprint 4 für GastroCore - Payment-Modul (ADDITIV):
  Zahlungen für Reservierungen & Events mit Stripe.
  
  Features:
  - Payment Rules (konfigurierbar): Event, Großgruppen, Greylist, Feiertag
  - Payment Types: Anzahlung pro Person, Fixe Anzahlung, Komplettzahlung
  - Stripe Checkout Integration
  - Zahlungsstatus im Dashboard sichtbar
  - Manual Payment (Admin only)
  - Refund-Funktion
  - Payment Logs und Audit

backend:
  - task: "Payment Rules CRUD API"
    implemented: true
    working: true
    file: "/app/backend/payment_module.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: true
        agent: "main"
        comment: "GET/POST/PATCH/DELETE /api/payments/rules - Zahlungsregeln verwalten"

  - task: "Payment Checkout API"
    implemented: true
    working: true
    file: "/app/backend/payment_module.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: true
        agent: "main"
        comment: "POST /api/payments/checkout/create - Stripe Checkout Session erstellen"

  - task: "Payment Status & Webhook"
    implemented: true
    working: true
    file: "/app/backend/payment_module.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: true
        agent: "main"
        comment: "GET /api/payments/checkout/status/{session_id}, POST /api/webhook/stripe"

  - task: "Manual Payment & Refund"
    implemented: true
    working: true
    file: "/app/backend/payment_module.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: true
        agent: "main"
        comment: "POST /api/payments/manual/{id}, POST /api/payments/refund/{id}"

  - task: "Payment Transactions & Logs"
    implemented: true
    working: true
    file: "/app/backend/payment_module.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: true
        agent: "main"
        comment: "GET /api/payments/transactions, GET /api/payments/logs"

  - task: "Event CRUD API"
    implemented: true
    working: true
    file: "/app/backend/events_module.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: true
        agent: "main"
        comment: "GET/POST/PATCH/DELETE /api/events with publish/cancel actions"
      - working: true
        agent: "testing"
        comment: "✅ TESTED: All CRUD operations working. GET /api/events retrieves events, POST creates with draft status, PATCH updates, GET /{id} retrieves single event, POST /{id}/publish publishes, POST /{id}/cancel cancels events. Admin and Schichtleiter access confirmed."

  - task: "EventProducts CRUD API"
    implemented: true
    working: true
    file: "/app/backend/events_module.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: true
        agent: "main"
        comment: "GET/POST/PATCH/DELETE /api/events/{id}/products"
      - working: true
        agent: "testing"
        comment: "✅ TESTED: All EventProducts CRUD operations working. GET /api/events/{id}/products lists products, POST creates new products, PATCH updates existing products, DELETE archives products. Tested with Gänseabend event."

  - task: "EventBookings API"
    implemented: true
    working: true
    file: "/app/backend/events_module.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: true
        agent: "main"
        comment: "GET/PATCH /api/events/{id}/bookings with status changes"
      - working: true
        agent: "testing"
        comment: "✅ TESTED: EventBookings management working. GET /api/events/{id}/bookings lists bookings with items and product names, PATCH /api/events/{id}/bookings/{booking_id} updates booking status and notes successfully."

  - task: "Public Event Booking API"
    implemented: true
    working: true
    file: "/app/backend/events_module.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: true
        agent: "main"
        comment: "GET /api/public/events, POST /api/public/events/{id}/book with capacity validation"
      - working: true
        agent: "testing"
        comment: "✅ TESTED: Public booking API fully functional. GET /api/public/events lists published events (no auth), GET /api/public/events/{id} shows event details with products. POST /api/public/events/{id}/book works for both ticket_only (Kabarett) and reservation_with_preorder (Gänseabend) modes. Capacity validation working - large bookings rejected with 422 status. Confirmation codes generated successfully."

frontend:
  - task: "Events Admin Page"
    implemented: true
    working: true
    file: "/app/frontend/src/pages/Events.jsx"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: true
        agent: "main"
        comment: "Event list with status filter, create/edit dialog, publish/cancel actions"

  - task: "EventProducts Editor"
    implemented: true
    working: true
    file: "/app/frontend/src/pages/EventProducts.jsx"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: true
        agent: "main"
        comment: "Create/edit products with price_delta, required flag"

  - task: "EventBookings Page"
    implemented: true
    working: true
    file: "/app/frontend/src/pages/EventBookings.jsx"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: true
        agent: "main"
        comment: "Bookings list with stats, preorder summary for kitchen, status changes"

  - task: "Public Events List"
    implemented: true
    working: true
    file: "/app/frontend/src/pages/PublicEventsList.jsx"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: true
        agent: "main"
        comment: "Public /events-public page with event cards"

  - task: "Public Event Booking Flow"
    implemented: true
    working: true
    file: "/app/frontend/src/pages/PublicEventBooking.jsx"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: true
        agent: "main"
        comment: "Multi-step form: contact -> preorder selection -> confirmation"

metadata:
  created_by: "main_agent"
  version: "4.0"
  test_sequence: 1
  run_ui: false

test_plan:
  current_focus:
    - "Event CRUD API"
    - "Public Event Booking"
    - "Preorder Selection Validation"
  stuck_tasks: []
  test_all: false
  test_priority: "high_first"

agent_communication:
  - agent: "main"
    message: "Sprint 4 Veranstaltungen-Modul ADDITIV implementiert. Teste: 1) GET /api/events (Admin), 2) POST /api/public/events/{id}/book mit items[], 3) Kapazitätsprüfung, 4) Preorder-Validierung. Seed-Events: Kabarett (ticket_only, 29€) + Gänseabend (reservation_with_preorder, 49€). Login: admin@gastrocore.de / NewAdmin123!"
  - agent: "testing"
    message: "✅ SPRINT 4 EVENTS MODULE TESTING COMPLETE - ALL TESTS PASSED (39/39 - 100% success rate). Comprehensive testing performed: 1) Seed Events verified (Kabarett-Abend ticket_only 29€, Gänseabend reservation_with_preorder 49€ with 3 products), 2) Authentication working for admin/schichtleiter access to /api/events, 3) Full Events CRUD (create/read/update/publish/cancel), 4) EventProducts CRUD (create/update/archive), 5) Public Events API (list/detail without auth), 6) Public Event Booking (both ticket_only and reservation_with_preorder modes with confirmation codes), 7) EventBookings management (list/update status), 8) Capacity validation (large bookings rejected, capacity tracking working). All backend APIs functional and ready for production."