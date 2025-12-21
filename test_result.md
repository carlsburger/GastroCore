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
  Sprint 3 für GastroCore - Reminder & No-Show System:
  1) Reminder-System (E-Mail + WhatsApp Deep-Link)
  2) Storno & Bestätigung durch Gast
  3) No-Show-Logik (Greylist/Blacklist)
  4) Service-Terminal Erweiterungen
  5) Message-Log

backend:
  - task: "Reminder Rules CRUD"
    implemented: true
    working: true
    file: "/app/backend/server.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: true
        agent: "main"
        comment: "GET/POST/PATCH/DELETE /api/reminder-rules implemented"
      - working: true
        agent: "testing"
        comment: "✅ TESTED: All CRUD operations working. GET returns rules, POST creates with validation, PATCH updates correctly, DELETE archives properly. Authentication required (admin only)."

  - task: "WhatsApp Deep-Link Generator"
    implemented: true
    working: true
    file: "/app/backend/server.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: true
        agent: "main"
        comment: "POST /api/reservations/{id}/whatsapp-reminder generates wa.me link"
      - working: true
        agent: "testing"
        comment: "✅ TESTED: WhatsApp deep-link generation working perfectly. Generates proper wa.me URLs with encoded messages in German. Requires manager+ role. Message logs created correctly."

  - task: "Guest Confirmation by Link"
    implemented: true
    working: true
    file: "/app/backend/server.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: true
        agent: "main"
        comment: "GET/POST /api/public/reservations/{id}/confirm-info and confirm"
      - working: true
        agent: "testing"
        comment: "✅ TESTED: Guest confirmation working. GET confirm-info returns reservation details, POST confirm updates status to 'bestaetigt'. Token validation working correctly. Public endpoints (no auth required)."

  - task: "Cancellation Deadline Check"
    implemented: true
    working: true
    file: "/app/backend/server.py"
    stuck_count: 0
    priority: "medium"
    needs_retesting: false
    status_history:
      - working: true
        agent: "main"
        comment: "GET /api/public/reservations/{id}/cancel-info with deadline check"
      - working: true
        agent: "testing"
        comment: "✅ TESTED: Cancellation functionality working as part of existing public cancellation system."

  - task: "Message Log"
    implemented: true
    working: true
    file: "/app/backend/server.py"
    stuck_count: 0
    priority: "medium"
    needs_retesting: false
    status_history:
      - working: true
        agent: "main"
        comment: "GET /api/message-logs - logs all sent messages"
      - working: true
        agent: "testing"
        comment: "✅ TESTED: Message logs working perfectly. GET /api/message-logs returns all logs, filtering by channel (whatsapp/email) works correctly. Admin authentication required."

  - task: "Guest Status Check"
    implemented: true
    working: true
    file: "/app/backend/server.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: true
        agent: "main"
        comment: "GET /api/guests/check/{phone} returns flag and no_show_count"
      - working: true
        agent: "testing"
        comment: "✅ TESTED: Guest status check working. Returns proper flag (none/greylist/blacklist) and no_show_count. Manager+ authentication required."

frontend:
  - task: "Settings Page (Reminder & No-Show Config)"
    implemented: true
    working: true
    file: "/app/frontend/src/pages/Settings.jsx"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: true
        agent: "main"
        comment: "Tabs for Reminders, No-Show Rules, Cancellation settings"

  - task: "Confirm Reservation Page"
    implemented: true
    working: true
    file: "/app/frontend/src/pages/ConfirmReservation.jsx"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: true
        agent: "main"
        comment: "Public /confirm/:id page for guest confirmation"

  - task: "Message Logs Page"
    implemented: true
    working: true
    file: "/app/frontend/src/pages/MessageLogs.jsx"
    stuck_count: 0
    priority: "medium"
    needs_retesting: true
    status_history:
      - working: true
        agent: "main"
        comment: "Admin view for all sent messages"

  - task: "Dashboard - WhatsApp Button & Guest Flags"
    implemented: true
    working: true
    file: "/app/frontend/src/pages/Dashboard.jsx"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: true
        agent: "main"
        comment: "WhatsApp button, Greylist/Blacklist markers, unconfirmed warning"

metadata:
  created_by: "main_agent"
  version: "3.0"
  test_sequence: 1
  run_ui: false

test_plan:
  current_focus:
    - "Reminder Rules CRUD"
    - "WhatsApp Deep-Link Generator"
    - "Guest Confirmation"
    - "Guest Status Check"
  stuck_tasks: []
  test_all: false
  test_priority: "high_first"

agent_communication:
  - agent: "main"
    message: "Sprint 3 features implemented. Please test: 1) GET/POST /api/reminder-rules, 2) POST /api/reservations/{id}/whatsapp-reminder, 3) GET/POST /api/public/reservations/{id}/confirm-info and confirm?token=..., 4) GET /api/guests/check/{phone}, 5) GET /api/message-logs. Test users: admin@gastrocore.de / NewAdmin123!"