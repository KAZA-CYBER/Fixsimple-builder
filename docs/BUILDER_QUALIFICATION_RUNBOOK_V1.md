# Qualification Execution Runbook v1

## Goal

Run Builder Qualification v1 reproducibly when the candidate 14B runtime is available.

Do not modify the benchmark after candidate results are observed.

## Preconditions

- qualification pack version: v1
- candidate repository baseline recorded by exact commit SHA
- model identifier recorded exactly
- remote endpoint health confirmed
- no secret values committed or copied into evidence
- clean working tree before each case
- Q8 is run only on a baseline that includes execution-verified target-drift protection

## Candidate metadata

Record before execution:
- repository commit
- qualification-pack commit
- model name
- model quantization/runtime
- endpoint/runtime type
- Builder backend configuration
- Python/runtime version if it can affect results

## Offline gate first

Before spending GPU time, run the deterministic test suite with no remote endpoint configured.

Expected behavior:
- deterministic tests pass
- remote live-model tests skip rather than fail when their endpoint environment variable is absent

Any deterministic regression blocks live qualification.

## Live qualification order

Run cases in increasing blast radius:

1. Q1 single-file diagnosis/repair
2. Q2 ambiguous target selection
3. Q3 coordinated multi-file repair
4. Q4 verification-feedback recovery
5. Q5 exhausted-failure rollback
6. Q6 protected-path containment
7. Q7 pre-commit sandbox rejection
8. Q8 target-drift protection
9. Q9 issue #19 — real contract-boundary probation
10. Q10 issue #20 — real Engine-transition probation

Stop immediately on a hard disqualifier. Ordinary clean FAIL results are recorded and the suite may continue.

## Evidence capture

For every case retain:
- exact task/fixture revision
- selected targets
- approved targets
- model responses as allowed by the run audit
- attempt count
- verification outputs
- final diff
- run/audit/report manifests
- whether rollback occurred
- human intervention count
- elapsed time when available

Never convert an ERROR/FAIL to PASS manually. If infrastructure invalidates a run, mark it INVALID and repeat without changing the task.

## Human intervention definition

The following count as intervention:
- changing source code for the candidate
- giving a line-level implementation solution
- changing a failing acceptance test to fit candidate output
- adding a new target after observing candidate failure
- changing the prompt/instruction after observing candidate failure

The following do not count:
- starting the frozen run
- restoring an unavailable external runtime
- collecting evidence
- stopping on a safety condition

## Result

Populate `docs/BUILDER_QUALIFICATION_SCORECARD_V1.md` from evidence.

A model/runtime does not become Working Engineer merely because existing live-Qwen tests once passed. Qualification is candidate-specific and must be rerun against the frozen pack.
