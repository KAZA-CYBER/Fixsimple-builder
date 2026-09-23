# Active Task

Task: A0-HEARTBEAT

## Current verified state

Execution layer is proven:

task fixture
-> file write
-> verification
-> FAIL observation
-> bounded repair
-> fresh verification
-> PASS
-> evidence

FixSimple Model Interface also exists and is tested.

## Remaining requirement

Replace the hard-coded repair decision with a decision produced through the
FixSimple Model Interface.

A0 is not complete until the model-driven loop is physically verified.

## Protected principles

- Builder remains FixSimple-owned.
- Model backend remains replaceable.
- No provider-specific semantics in the Builder control loop.
- No paid external model API becomes a permanent runtime dependency.
