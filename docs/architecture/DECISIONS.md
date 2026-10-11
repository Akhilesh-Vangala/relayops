# Design decisions

## Separate proposal authority from action authority

**Decision.** The model has read-only tools and one `submit_plan` tool. Policy admission, simulation, approval, execution and reconciliation are ordinary functions that no tool can reach.

**Why.** An agent that can call a write tool turns every hallucination into a side effect. Keeping writes behind deterministic code means the worst a model can do is propose a plan that gets refused.

**Tradeoff.** The model cannot take incremental actions and observe their results. Multi-step write workflows have to be expressed as a single typed plan.

## Recompute the plan instead of trusting it

**Decision.** `validate()` recomputes the required outcome and exact action amounts from current state. A plan is admitted only if it matches.

**Why.** Typed output stops malformed plans, not wrong ones. Recomputation makes the policy the source of truth for amounts, and makes the model responsible for gathering grounded evidence and choosing the right outcome.

**Tradeoff.** The contract is narrow and explicit. Each new exception type needs its own policy, rather than an open-ended planner.

## Counterfactual simulation before review

**Decision.** Every admitted plan is executed on a private copy of the world and checked by an evaluator the agent cannot import.

**Why.** Reviewers approve outcomes more reliably than diffs. Showing the operator the simulated final state, checked independently, turns approval into a check of results rather than intent.

**Tradeoff.** Simulation fidelity is bounded by the fixture. External systems with side effects the copy cannot model would need their own sandbox.

## Approval binds to a digest

**Decision.** Approval stores the SHA-256 of the exact `Plan`. Every action re-validates the plan and compares that digest inside its transaction.

**Why.** It prevents the classic gap where a plan is approved and then a slightly different one executes, or the source changes between approval and execution.

**Tradeoff.** Any source change invalidates the approval, which forces a fresh investigation.

## Deterministic receipts and explicit reconciliation

**Decision.** Each action's receipt ID is derived from the plan digest and the action index. A lost acknowledgment leaves an `unknown` receipt that blocks progress until `reconcile()` proves the effect from business state.

**Why.** Retrying an action after a timeout is how duplicate payments and double shipments happen. Deterministic IDs make retries idempotent, and reconciliation replaces guessing with observation.

**Tradeoff.** An uncertain action needs an explicit recovery step, so recovery is not automatic.

## Model receipts and zero generation retries

**Decision.** Each paid generation is reserved against a cumulative cap before it starts and recorded as a receipt before the graph checkpoint commits. The SDK runs with `max_retries=0`, and unknown receipts block replay.

**Why.** The same idempotency argument applies to model calls, because a silent retry is a silent charge. Budgets are enforced before spending rather than reconciled after.

**Tradeoff.** A transient provider error fails the run instead of retrying in place.

## PostgreSQL queue before replicas

**Decision.** Investigations are persisted in PostgreSQL. Separate workers claim them with `FOR UPDATE SKIP LOCKED`, hold renewed leases, and publish only while they own the lease. An expired lease is marked interrupted, never requeued.

**Why.** It makes API restarts independent of in-flight work and gives Kubernetes a meaningful liveness signal, without replaying paid work after a crash.

**Tradeoff.** Fixture worlds, action receipts and LangGraph checkpoints remain SQLite files on a shared volume. API and workers are therefore scheduled on one node with a ReadWriteOnce volume.

## Request-scoped public sandbox

**Decision.** The public build rebuilds a fresh fixture for every request and carries only a signed, cookie-bound envelope between stages. It uses the deterministic diagnostic planner and makes no model calls.

**Why.** It lets anyone run the real policy, simulator, executor and reconciliation path on a serverless host with no shared state, no credentials and no cost exposure.

**Tradeoff.** Public history lives in the visitor's browser session, and a signed stage can be replayed until it expires. Each replay operates on a new isolated fixture.
