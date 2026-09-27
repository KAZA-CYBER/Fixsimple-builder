# Builder Engineering Backlog v1

## Objective

Move from Builder capability testing to bounded construction of the independent FixSimple platform without turning the Builder into the production runtime.

## Entry condition

Do not begin this backlog as autonomous Builder work until Builder Qualification Gate A passes. Use the first two bounded backlog items as Gate B real-work probation tasks when their acceptance tests are prepared.

## Priority 0 — Establish canonical truth

1. Reconcile project-state documentation with the actual repository baseline.
2. Resolve or explicitly defer pending PR #16 (target-drift guard).
3. Keep PR #17 (RunPod lifecycle) independent from core engineering qualification; GPU lifecycle convenience is not a Builder correctness requirement.
4. Establish repeatable local/CI verification that does not require a live GPU for deterministic tests.

## Platform construction sequence

### F1 — Platform skeleton and contract boundary
Create the minimal independent platform package/repository structure and a versioned job/contract schema.

Acceptance must prove:
- invalid contracts are rejected deterministically
- version is explicit
- domain reasoning is absent from the control-plane schema
- no model/provider semantics leak into the contract boundary

### F2 — Durable job queue
Implement enqueue, claim/lease, complete, fail and retry state transitions against persistent storage.

Acceptance must prove:
- jobs survive process restart
- one job cannot be successfully claimed by two workers simultaneously
- expired leases can be recovered
- retry count is bounded
- state transitions are auditable

### F3 — Thin Engine state machine
Implement state/routing/gates only.

Acceptance must prove:
- Engine issues contracts and consumes results
- Engine contains no product/domain reasoning
- invalid transitions are rejected
- Human Gate can pause/resume explicitly
- restart does not require manual reconstruction of state

### F4 — Model Adapter
Expose a FixSimple-owned model interface with provider adapters behind it.

Acceptance must prove:
- provider can be replaced without changing Engine contracts
- timeout/error semantics are normalized
- model identity is recorded in evidence

### F5 — Tool Gateway
Implement explicit tool permissions, budgets and audit.

Acceptance must prove:
- unapproved tools are denied
- calls are attributable to a contract/run
- budgets are enforced outside model prompts
- secrets are not exposed in audit output

### F6 — Result Validator and evidence
Validate contract-specific outputs before Engine state transition.

Acceptance must prove:
- malformed output cannot advance state
- evidence and validator result are persisted
- validator failure is distinguishable from model/runtime failure

### F7 — Replayable event log
Persist enough state-transition and execution evidence to reconstruct a run.

Acceptance must prove:
- a failed run can be traced contract-by-contract
- duplicate delivery is idempotent
- replay/inspection does not require conversational memory

### F8 — First Deep Research round-trip
Run one bounded FixSimple research contract end-to-end through the independent platform.

Acceptance must prove:
- request -> Engine -> queue -> agent/model -> tools -> validator -> result -> Engine
- no manual wake-up between stages
- failure is explicit and recoverable
- evidence identifies every stage

## Architectural constraints

- Engine stays thin.
- Agents do not call one another directly.
- Contracts are the interface.
- Runtime correctness must not depend on model obedience.
- Permissions, retries, budgets and state transitions live outside prompts.
- Builder may modify platform code only under an approved engineering task; production agents cannot modify their own runtime.
