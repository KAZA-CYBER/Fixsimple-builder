# Known Gaps

## Builder Implementation

No executable Builder exists yet.

## Model Backend

No model/backend has been selected or integrated yet.

The future backend must remain replaceable behind the FixSimple Model Interface.

## A0

Heartbeat implementation and acceptance test are not yet built.

## Durability

Local Git is currently the primary repository history.
A remote Git durability layer may be added later and is not a prerequisite for
A0.

## A0 lessons / resolved integration failures — 2026-09-23

- llama CLI initially remained interactive after generation.
  Resolution: --single-turn + --simple-io.
- Local model process was killed with exit code 137 under the default memory profile.
  Resolution: ctx-size 512, batch-size 64, ubatch-size 64, threads 2.
- llama stdout contained UI/logging content.
  Resolution: isolate generated output with --output-file.
- output-file contained rendered User/Assistant conversation.
  Resolution: extract only the final Assistant response before writing source.
- Model artifact was previously observed truncated after an interrupted lifecycle.
  Operational rule: download to temporary artifact, validate, then atomically promote.
- Python bytecode caching previously caused stale verification after rapid same-size rewrite.
  Verification uses python3 -B.
- Test module naming previously caused discovery collision.
  Test naming was normalized.
- Intermittent container DNS resolution was observed during model acquisition.

These are historical/resolved A0 issues unless they recur.

## A0 lessons / resolved integration failures — 2026-09-23

- llama CLI initially remained interactive after generation.
  Resolution: --single-turn + --simple-io.
- Local model process was killed with exit code 137 under the default memory profile.
  Resolution: ctx-size 512, batch-size 64, ubatch-size 64, threads 2.
- llama stdout contained UI/logging content.
  Resolution: isolate generated output with --output-file.
- output-file contained rendered User/Assistant conversation.
  Resolution: extract only the final Assistant response before writing source.
- Model artifact was previously observed truncated after an interrupted lifecycle.
  Operational rule: download to temporary artifact, validate, then atomically promote.
- Python bytecode caching previously caused stale verification after rapid same-size rewrite.
  Verification uses python3 -B.
- Test module naming previously caused discovery collision.
  Test naming was normalized.
- Intermittent container DNS resolution was observed during model acquisition.

These are historical/resolved A0 issues unless they recur.

## A0 lessons / resolved integration failures — 2026-09-23

- llama CLI initially remained interactive after generation.
  Resolution: --single-turn + --simple-io.
- Local model process was killed with exit code 137 under the default memory profile.
  Resolution: ctx-size 512, batch-size 64, ubatch-size 64, threads 2.
- llama stdout contained UI/logging content.
  Resolution: isolate generated output with --output-file.
- output-file contained rendered User/Assistant conversation.
  Resolution: extract only the final Assistant response before writing source.
- Model artifact was previously observed truncated after an interrupted lifecycle.
  Operational rule: download to temporary artifact, validate, then atomically promote.
- Python bytecode caching previously caused stale verification after rapid same-size rewrite.
  Verification uses python3 -B.
- Test module naming previously caused discovery collision.
  Test naming was normalized.
- Intermittent container DNS resolution was observed during model acquisition.

These are historical/resolved A0 issues unless they recur.
