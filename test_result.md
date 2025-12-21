#====================================================================================================
# Service-Terminal Testing - Sprint 8
#====================================================================================================

user_problem_statement: |
  ADD-ON: Dediziertes Service-Terminal Frontend

metadata:
  created_by: "main_agent"
  version: "8.0"
  test_sequence: 10
  run_ui: false

test_plan:
  current_focus:
    - "Service-Terminal UI"
    - "Statuswechsel"
    - "Walk-in & Warteliste"
  stuck_tasks: []
  test_all: true
  test_priority: "high_first"

agent_communication:
  - agent: "main"
    message: "Service-Terminal implementiert. Teste: 1) RBAC (nur Admin/Schichtleiter), 2) Tagesliste lädt, 3) Statuswechsel, 4) Walk-in anlegen, 5) Audit-Log. Login: admin@gastrocore.de / Admin123!"
