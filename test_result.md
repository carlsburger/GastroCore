#====================================================================================================
# FULL QA AUDIT - Sprint 1 bis 7
#====================================================================================================

user_problem_statement: |
  Vollständige technische und funktionale Prüfung aller Sprints

metadata:
  created_by: "main_agent"
  version: "7.1"
  test_sequence: 5
  run_ui: false

test_plan:
  current_focus:
    - "Sprint 1-7 Full QA Audit"
  stuck_tasks: []
  test_all: true
  test_priority: "high_first"

agent_communication:
  - agent: "main"
    message: "DEEP QA AUDIT nach detailliertem Prüfkatalog. Login: admin@gastrocore.de / Admin123!, schichtleiter@gastrocore.de / Schicht123!, mitarbeiter@gastrocore.de / Mitarbeiter123!"
