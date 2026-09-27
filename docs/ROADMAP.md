# Roadmap

## Current stage — Builder Qualification

The A0 heartbeat has been surpassed. The merged baseline on `main` is V0.52.

The current goal is not to add more isolated editing features. It is to prove
that the complete Builder system can repeatedly perform bounded engineering
work without human implementation help and without violating repository
integrity.

### Qualification sequence

1. Freeze qualification cases and scoring.
2. Resolve and execution-verify target-drift protection (Q8).
3. Restore a candidate 14B remote runtime.
4. Run Q1–Q8 against the frozen candidate/baseline.
5. Run Q9 and Q10 as real FixSimple engineering probation tasks.
6. Decide readiness from recorded evidence.

### Readiness

Working Engineer readiness requires at least 10 frozen qualification/real tasks,
an autonomous PASS rate of at least 80%, zero protected-path violations, zero
false PASS results, and clean repository preservation on exhausted failures.

See:
- `docs/BUILDER_QUALIFICATION_V1.md`
- `docs/BUILDER_QUALIFICATION_SCORECARD_V1.md`
- `docs/BUILDER_ENGINEERING_BACKLOG_V1.md`

## After qualification

If the Builder passes, begin bounded construction of the independent FixSimple
platform in this order:

1. versioned contract boundary
2. durable job queue
3. thin Engine state machine
4. model adapter
5. Tool Gateway
6. result validator/evidence
7. replayable event log
8. first Deep Research end-to-end round-trip

Each feature remains an approved engineering contract with tests and protected
boundaries.

## Architecture constraints

- Builder is an engineering agent, not the production runtime.
- Production agents cannot rewrite their own runtime.
- Engine remains thin: state, routing, contracts, gates, bounded retry and audit.
- Agents communicate through contracts, not direct agent-to-agent calls.
- Runtime safety and permissions must not depend on model obedience.
- Model/provider implementations remain replaceable behind FixSimple-owned
  interfaces.
