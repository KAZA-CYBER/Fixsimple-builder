# Current State

## Verified baseline

The default branch `main` is physically at V0.52, commit
`6b7ad9713126652e874600bf02a0ade4f4c0f024`.

The Builder is executable. The repository contains a bounded engineering loop
with repository understanding, target selection/approval, model-backed repair,
verification feedback, multi-file editing, rollback, protected-path
containment, transactional writes, exact patch editing, persisted run evidence,
and pre-commit sandbox verification.

This document records merged/default-branch state only. Open pull requests are
not treated as completed capability.

## Pending work

- PR #16: V0.53 target-drift guard. Code-reviewed during qualification audit,
  but not execution-verified by repository CI and not merged.
- PR #17: optional RunPod lifecycle automation. Not merged and not a Builder
  correctness prerequisite.
- PR #18: Builder Qualification Pack v1 documentation. Not merged.
- Issues #19 and #20: frozen real-work probation tasks for qualification.

## Current objective

Qualify the Builder as a bounded FixSimple engineering agent using frozen,
evidence-based tests rather than adding more toy milestones.

The next candidate runtime is a 14B coding model. GPU availability is currently
an external dependency for live-model qualification.

## Truth boundary

Repository state and physically observed execution evidence are canonical.
Conversational memory and unmerged PRs are not proof of completed capability.
