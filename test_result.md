#====================================================================================================
# HR Fields Extension Testing - Sprint 7.1
#====================================================================================================

user_problem_statement: |
  ADD-ON: Mitarbeiter-Modul um fehlende HR-Felder erweitern (ohne Breaking Changes)

metadata:
  created_by: "main_agent"
  version: "7.1"
  test_sequence: 6
  run_ui: false

test_plan:
  current_focus:
    - "HR Fields Extension"
    - "RBAC Field Filtering"
    - "Completeness Score"
    - "Audit Logging"
  stuck_tasks: []
  test_all: true
  test_priority: "high_first"

agent_communication:
  - agent: "main"
    message: "HR-Felder-Erweiterung implementiert. Teste: 1) RBAC Feld-Filterung (Admin vs Schichtleiter), 2) HR-Fields-Update Endpoint, 3) Completeness Score, 4) Audit-Logging für sensitive Felder. Login: admin@gastrocore.de / Admin123!"
