# Engineering Rules

## 1. Project Is Truth

Agent conversational memory is cache.
The repository and its project documentation are canonical truth.

## 2. Evidence Before Claims

An operation may be recorded as completed only after it was physically executed
and its result was observed.

Never claim that code was changed, tested, committed, deployed, or verified
without evidence.

## 3. Bounded Work

Each engineering task must define:
- required outcome
- relevant architecture
- acceptance tests
- protected areas / DO NOT MODIFY boundaries

## 4. State Gate

A completed task must leave:
- code/tests consistent with the result
- CURRENT_STATE updated when state changed
- ACTIVE_TASK updated
- COMPLETED updated for completed work
- KNOWN_GAPS updated when gaps were found
- ADR added when an architectural decision was made
- Git history representing the completed state

## 5. Ownership

Do not introduce a dependency that makes an external agent platform the owner
of the Builder control loop, permissions, state, project memory, or identity.

Open-source components may be reused as parts.

## 6. Model Independence

Builder code must depend on a FixSimple-owned model interface.

Provider-specific behavior must remain behind replaceable adapters.

LiteLLM may be used as an optional adapter, but the Builder control loop must
not depend on LiteLLM-specific semantics.

## 7. Safety Gates

Autonomous engineering work is desirable, but destructive/high-risk operations
must remain gated, including:
- secrets / credential changes
- permission-root changes
- destructive data operations
- production deployment
- major architecture changes outside an approved task

## 8. Failed Approaches Matter

Failures and rejected approaches that could otherwise be repeated must be
recorded in project history or KNOWN_GAPS with enough context to avoid repeating
the same mistake.
