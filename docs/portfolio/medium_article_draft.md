# Draft — Medium

**Title:** Beyond Prompting: A Policy-Governed Runtime for AI Agents

**Subtitle:** How we built enforceable gates for tools, budgets, and approvals—without pretending governance is “just better prompts.”

---

Most “agent safety” conversations stop at system prompts and model choice. That is necessary but insufficient for systems that call tools, spend money, and touch regulated workflows. Models can be helpful and still wrong; the question is what the *platform* does before side effects become irreversible.

This project is a reference **policy-governed AI agent runtime**. It is intentionally backend-first: a FastAPI surface, a state-machine orchestrator, explicit policy and risk engines, budget enforcement, human-in-the-loop approvals, and structured audit trails stored as JSONL for inspection and replay.

**What problem it solves**

Autonomous workflows need the same operational discipline as any distributed system: deterministic control points, economic guardrails, and evidence. The runtime routes each step through validation, policy evaluation, optional approval, and budget checks before executing registered tools. Decisions include reasons and matched rules—not a black-box “trust me.”

**Architecture in one breath**

Inbound requests are thin. Orchestration owns state transitions. Policy and risk classify intent and exposure. Economics tracks spend. Approvals pause high-impact paths. Audit records the narrative of the run for governance and debugging.

**What “done” looks like**

We validate behavior with synthetic scenarios: allow/deny, approval branches, budget blocks, traceability of policy reasons, and lifecycle tests for approve vs reject. The goal is reproducible evidence, not a one-off demo video.

**Credible limits**

This is a portfolio-grade reference, not a production appliance. There is no claim of universal safety; there is a claim of **explicit control surfaces** and **auditable behavior** that teams can extend.

**Closing thought**

If AI agents are to operate next to real processes, we should evaluate them like systems: interfaces, invariants, failure modes, and logs. Prompts matter; **runtime governance** is what makes that operational.

---

*Word count target: 650–900. Add one diagram (state machine or sequence) before publishing.*
