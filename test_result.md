#====================================================================================================
# Security Enhancement Testing - Sprint 7.2
#====================================================================================================

user_problem_statement: |
  ADD-ON: HR-Sensitivdaten (Steuer-ID, SV-Nummer, IBAN) absichern – ohne Breaking Changes

metadata:
  created_by: "main_agent"
  version: "7.2"
  test_sequence: 8
  run_ui: false

test_plan:
  current_focus:
    - "Encryption at rest"
    - "Masked field display"
    - "RBAC field filtering"
    - "Audit logging for reveal actions"
  stuck_tasks: []
  test_all: true
  test_priority: "high_first"

agent_communication:
  - agent: "main"
    message: "Security Enhancement implementiert. Teste: 1) Verschlüsselung bei Speicherung, 2) Maskierte Darstellung, 3) RBAC (Schichtleiter darf KEINE sensitiven Felder sehen), 4) Reveal-Endpoint mit Audit-Log. Login: admin@gastrocore.de / Admin123!"
