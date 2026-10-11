# Execution

Everything after `submit_plan` is deterministic code that the model cannot call.

## Fixture world

`domain/environment.py` builds an original synthetic SQLite world (WAL mode) for one tenant and case:

| System | Fields |
| --- | --- |
| `procurement` | `order_id`, `ordered_units`, `unit_cents` |
| `warehouse` | `received_units`, `delivery_known`, `available_units` |
| `billing` | `invoiced_units`, `held_cents` |
| `case_management` | `status`, `claim_units`, `reserved_units` |
| Documents | `invoice` and `delivery_note`, each with a title, order, units and note |

The world also holds `evidence`, `approvals`, `receipts` and an append-only `events` table. `world.version()` is a digest of the source state, and every evidence record is stored with the version it was read at. All money is integer cents and all quantities are integer units.

## Policy admission

`domain/policy.validate()` runs at plan submission, at approval, and again inside every action transaction.

1. The tenant and case must match the world.
2. `plan.source_version` must equal the current version. Any source change invalidates the plan and its approval.
3. Evidence IDs must be unique, must exist, and must belong to this tenant and version. Evidence from all four systems is required.
4. The required outcome is recomputed with `shortage = ordered − received`:
   - over-delivery is outside the contract and refused;
   - an unknown delivery, or an invoice that disagrees with the order, requires `needs_information`;
   - no shortage requires `no_change`;
   - stock below the shortage requires `needs_information`;
   - otherwise the outcome is `resolve`.
5. `needs_information` and `no_change` plans must contain no actions.
6. A `resolve` plan must contain exactly these actions, in order:

| # | Action | Amount |
| --- | --- | --- |
| 1 | `hold_invoice` | `shortage × unit_cents` |
| 2 | `open_supplier_claim` | `shortage` units |
| 3 | `reserve_replacement` | `shortage` units |
| 4 | `resolve_case` | 0 |

`Plan` is a frozen, strict Pydantic model with 4–12 evidence IDs and at most 4 actions. Each action amount is limited to the range 0–10,000,000.

## Counterfactual simulation

`agents/workflow.simulate_plan()` copies the world and its evidence to a private temporary SQLite file. If the plan has actions, it approves and executes them there under the operator label `counterfactual-simulator`. It then passes the original state, the final state and the event log to `verification/evaluator.evaluate()`.

Five checks always apply:

| Check | Meaning |
| --- | --- |
| `scope_preserved` | Tenant and case unchanged |
| `source_order_preserved`, `source_delivery_preserved` | Procurement and warehouse records unchanged |
| `invoice_quantity_preserved`, `source_documents_preserved` | Invoiced units and both documents unchanged |

A `resolve` case adds seven more, for 12 in total:

| Check | Meaning |
| --- | --- |
| `correct_outcome` | Outcome is `resolve` |
| `held_amount` | Hold equals `shortage × unit_cents` |
| `claim_quantity`, `reservation_quantity` | Claim and reservation equal the shortage |
| `resolved` | Case status is `resolved` |
| `no_duplicate_effects` | Exactly four `action_applied` events, all of different kinds |
| `explicit_review` | An `approved` event exists |

A `needs_information` or `no_change` case adds three, for 8 in total: `correct_outcome`, `no_business_effects` (no `action_applied` events) and `original_state_preserved` (final state equals the original).

Only a plan whose simulation passes every check is offered for review. The real world is untouched until approval.

## Approval

`approve(world, plan, operator=…)` re-validates the plan, refuses plans with no actions, and inserts an approval row holding the SHA-256 digest of the exact plan, the tenant and the operator label. An `approved` event is appended in the same transaction.

## Action broker

`execute(world, plan, approval)` processes actions in order. For action `i`:

1. Compute `receipt_id = digest({plan: plan_digest, action: i})`.
2. Open a `BEGIN IMMEDIATE` transaction, re-run `validate()`, and confirm the approval row is active and its digest matches the plan.
3. If a receipt with that ID exists: skip it when it is `confirmed`, and refuse to continue when it is `unknown`.
4. Refuse when the target field already holds an unexplained effect, such as an existing hold or claim.
5. `resolve_case` additionally requires the hold, claim and reservation to equal the shortage-derived values.
6. Write the new state, the receipt and an `action_applied` event, then commit.

Retrying the same approved plan is therefore idempotent. In the public demo, the endpoint executes twice and verifies that the state and event log are identical after the second run.

## Lost acknowledgments and reconciliation

Fault injection (`timeout_after=i`) commits action `i` with an `unknown` receipt and raises `TimeoutError`. This is the case where the effect may have happened but the caller cannot tell. Any later `execute()` refuses at that receipt.

`reconcile(world, plan, approval)` takes the write lock, re-validates the plan and approval, and reads the business state. For each `unknown` receipt, it compares the observed effect (held cents, claim units, reserved units or resolved status) with the receipt payload. It confirms the receipt only if they match, and otherwise refuses. It never resends an action. After reconciliation, `execute()` skips the confirmed receipt and completes the remaining actions.

The interactive demo exercises this path end to end. Approve, choose **Test lost acknowledgment**, then **Reconcile and complete**. The ledger shows one reconciled and three confirmed receipts, and 24 of 24 checks pass across simulation and execution.

[Agent](AGENT.md) · [Overview](OVERVIEW.md)
