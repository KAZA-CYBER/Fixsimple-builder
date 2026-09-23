# Roadmap

## Stage A0 — Heartbeat

Target: first minimal living Builder.

Required flow:

task input
-> model
-> repository/file access
-> edit
-> shell/test
-> observe failure
-> bounded repair
-> retest
-> diff/evidence/report

Target implementation window: approximately 1–2 working days, subject to
actual implementation findings.

## After A0

Stop and inspect the implementation before expanding scope.

Record:
- dependencies
- code size
- model/backend used
- hardware/runtime behavior
- limitations
- observed failure modes

Only then define the next stage.
