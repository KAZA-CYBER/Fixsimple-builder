# ADR-001 — Builder First and FixSimple Ownership

Status: Accepted

## Context

FixSimple needs an execution layer capable of building and repairing its own
software without making a proprietary agent platform the permanent owner of
the system.

Previous factory work demonstrated that excessive orchestration complexity,
hidden execution paths, stale state, retries, and platform-specific behavior
can make the system difficult to control and debug.

## Decision

Build FixSimple Builder first.

The Builder will be FixSimple-owned and portable.

The initial objective is not to recreate the complete FixSimple platform.
The initial objective is the A0 Heartbeat: a minimal engineering loop that can
read, edit, test, observe failure, repair, retest, and report evidence.

Project knowledge must persist in the repository rather than depend on the
memory of any chat or model.

External infrastructure and open-source components may be used when useful,
provided they remain replaceable.

## Consequences

We prioritize a working minimal Builder before advanced orchestration.

Architecture grows only when demonstrated requirements justify it.
