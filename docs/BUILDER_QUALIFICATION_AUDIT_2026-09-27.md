# Builder Qualification Audit — 2026-09-27

## Scope

Read-only audit of the Builder baseline before defining the qualification pack.

Audited baseline:
- repository: KAZA-CYBER/Fixsimple-builder
- branch: main
- commit: 6b7ad9713126652e874600bf02a0ade4f4c0f024
- baseline label: V0.52

No claim in this document treats an open PR as merged capability.

## Verified baseline capabilities from repository evidence

The main branch contains implementation/tests for:
- bounded task contracts and verification commands
- repository understanding and target selection
- explicit target approval before execution
- single-file repair
- multi-file repair
- bounded repair iterations with verification feedback
- rollback after exhausted repair attempts
- protected-path/target containment
- exact patch and multi-patch response contracts
- transactional multi-file patch planning
- transactional multi-file writes with rollback on write failure
- pre-commit verification in a copied sandbox
- persisted run/audit/report artifacts

The commit history on main shows the progression through V0.52, including live-Qwen E2E milestones for target selection, multi-file work, retry recovery and patch editing.

## Pending capabilities

### PR #16 — V0.53 target-drift guard

Status at audit time:
- open
- draft
- mergeable/clean relative to the audited main
- not part of baseline

Purpose: detect an external change to an approved target between planning and commit and abort rather than overwrite it.

This closes a meaningful concurrency/integrity gap and is required by Qualification Q8 before Working Engineer status.

### PR #17 — P0 automatic RunPod lifecycle

Status at audit time:
- open
- draft
- mergeable/clean relative to the audited main
- not part of baseline

Purpose: start/stop the configured RunPod around remote model demand with leases and audit.

This is operational convenience/cost control, not a correctness prerequisite for Builder qualification. Keep it decoupled from the qualification baseline until the remote runtime is available for controlled E2E.

## Documentation drift

The canonical project documents are materially stale:
- docs/CURRENT_STATE.md still says no executable Builder exists.
- docs/ROADMAP.md still presents A0 Heartbeat as the current target.

This conflicts with the actual V0.52 implementation and violates the repository's own rule that project documentation is canonical truth.

Do not update these documents by guessing future state. Reconcile them only to physically observed/merged repository state.

## Qualification coverage map

| Qualification | Existing evidence on main | Gap |
|---|---|---|
| Q1 single-file diagnosis/repair | task runner + real/live E2E coverage | rerun against candidate runtime |
| Q2 ambiguous target selection | test_qwen_ambiguous_repo_e2e.py | rerun against candidate runtime |
| Q3 multi-file coordinated repair | test_qwen_multifile_e2e.py and multi-patch E2E | rerun against candidate runtime |
| Q4 feedback recovery | test_qwen_retry_recovery_e2e.py | rerun against candidate runtime |
| Q5 final failure rollback | test_qwen_final_failure_rollback_e2e.py | include in frozen run |
| Q6 protected containment | test_protected_path_containment_e2e.py | include in frozen run |
| Q7 pre-commit sandbox | V0.52 implementation/tests | include in frozen run |
| Q8 target drift | PR #16 only | resolve/test PR #16 |
| Q9 real FixSimple task #1 | absent | define bounded real task |
| Q10 real FixSimple task #2 | absent | define second subsystem task |

## Key conclusion

The Builder is no longer at the stage of proving that it can edit a file. The next evidence question is whether the complete bounded engineering system can repeatedly solve frozen, non-toy tasks without human implementation help while preserving repository integrity.

The shortest path is therefore:
1. reconcile canonical docs
2. resolve Q8 target-drift protection
3. freeze qualification cases
4. restore a candidate 14B remote runtime
5. rerun the frozen pack
6. use two real platform tasks as probation
7. decide readiness from recorded evidence, not impression
