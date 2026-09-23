# FixSimple Builder

FixSimple Builder is the FixSimple-owned engineering agent.

Its purpose is to inspect repositories, reason about bounded engineering tasks,
edit code, run tests, observe failures, repair its work, and return evidence.

## Ownership Principle

FixSimple owns the agent, control loop, project state, permissions, interfaces,
and canonical project knowledge.

External models, inference servers, hosting providers, search services, and
other tools are replaceable capabilities. They must not become the owner of
FixSimple's architecture or project state.

## Current Stage

Baseline 001 — project memory and repository structure only.

No executable Builder code exists yet.

Next milestone: A0 Heartbeat.
