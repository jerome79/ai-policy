# Architecture

Phase 1 implements a governed workflow runtime with these layers:

- orchestrator with explicit state transitions
- policy engine for allow/deny/require approval decisions
- budget guard and cost tracker
- pluggable tool registry
- JSONL audit and run persistence
