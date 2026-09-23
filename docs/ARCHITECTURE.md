# FixSimple Builder Architecture

## Core Principle

The Builder is a FixSimple-owned engineering agent.

The model is a replaceable reasoning component. It is not the identity of the
Builder and does not own Builder state.

## Initial Architecture

User / Task Input
        |
        v
FixSimple Builder Control Loop
        |
        +--> FixSimple Model Interface
        |        |
        |        +--> replaceable provider adapter
        |
        +--> Repository / File Tools
        |
        +--> Shell / Test Execution
        |
        +--> Observation
        |
        +--> Repair Iteration
        |
        +--> Diff / Evidence / Report

## A0 Heartbeat

The first executable milestone must prove this minimal loop:

1. Receive a bounded task.
2. Read repository files.
3. Ask the configured model for a plan/action.
4. Modify code.
5. Run a test or verification command.
6. Observe PASS or FAIL.
7. If FAIL, perform at least one bounded repair iteration.
8. Re-run verification.
9. Return diff and evidence.

A0 is intentionally small.

A0 does NOT require:
- multi-agent architecture
- graphical UI
- full FixSimple production factory
- advanced context management
- autonomous deployment
- production orchestration
- visual-production agents

## Future Direction

Later the FixSimple platform may contain:
- Builder Agent
- Production Agent
- Visual Agent
- thin control-plane / Engine
- persistent state and storage
- tool bus
- FixSimple-owned model interface

The Engine should remain thin: state, routing, jobs/contracts, gates, bounded
retry policy, audit and progress. Domain reasoning belongs in agents.
