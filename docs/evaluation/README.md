# Evaluation

All suites run in the required CI jobs on every pull request and every push to `main`. None of them calls a live model. Each one exercises the real policy, simulator, executor and evaluator, so the checks are about system behavior and authority boundaries, not model quality.

## Suites

| Suite | Entry point | Establishes |
| --- | --- | --- |
| Unit and integration | `python -m unittest discover -s backend/tests` | 109 tests. Covers policy refusal paths, receipt idempotency, reconciliation, model-transport accounting against the real SDK over mocked HTTP and SSE, checkpoint recovery, run-store concurrency and leases, imports, signing and the public sandbox's tamper and scope checks. 3 tests require PostgreSQL and run against the CI service. |
| Scripted case matrix | `python -m relayops.evaluation.benchmark` | 12 cases across `resolve`, `needs_information` and `no_change`, driven through the full agent graph by `ScriptedAgent(incorrect_first=True)` |
| Interactive demo | `scripts/demos/public_demo_browser.py` | The full public journey in Chromium, described below |
| Operator workbench | `backend/tests/e2e/browser_workbench.py` | 16 checks: tool choices and correction, six captured observations, immutable review, stale-proposal rejection, execution-before-review denial, duplicate-effect prevention, grounded clarification and responsive layouts |
| Product | `scripts/demos/product_browser.py --axe …` | 12 journey checks and 14 axe-core views |
| Imports | `scripts/demos/import_browser.py --axe …` | 8 checks across all five formats |
| Row-level security | `scripts/checks/product_rls.py` | Owner isolation, spoofing and update denial, concurrent quotas |
| Topology | `compose_smoke.sh`, `kind_smoke.sh` | API restart with a queued run, two workers, six browser observations, idempotent re-execution |
| Repository | `scripts/checks/check_repository.py` | Layout, links and anchors, and recording hashes against tracked sources |

The interactive demo journey steps are:

1. Investigate a case, then approve the proposal.
2. Lose the acknowledgment of the first action, and require the unknown receipt.
3. Reconcile, then require 4 confirmed receipts and 24 passing checks.
4. Download the report, reload, and confirm a second browser cannot see the run.
5. Check the 390 px layout and video playback.

## Scripted case matrix

| Case | Outcome | Rounds | Evidence calls | Corrections |
| --- | --- | --- | --- | --- |
| `short-default`, `short-small`, `short-one`, `short-large`, `short-stock-boundary` | `resolve` | 5 | 6 | 1 |
| `missing-delivery`, `low-stock`, `invoice-disagreement`, `missing-delivery-and-stock` | `needs_information` | 4 | 6 | 0 |
| `healthy-default`, `healthy-small`, `healthy-empty` | `no_change` | 4 | 6 | 0 |

All 12 assessments pass, and the original business state is unchanged in every case. In each `resolve` case, the scripted client first submits a plan with a wrong amount. Policy refuses it with bounded feedback, the client corrects it, and the corrected plan passes simulation. This exercises the correction path and its budget, not reasoning quality.

## Acceptance boundary

The evaluator (`verification/evaluator.py`) shares the declared business contract with the policy but not its code. It compares the original and final fixtures directly and reads the event log for duplicate effects and the approval event. The agent module does not import it, and no tool exposes it.

[Execution](../architecture/EXECUTION.md) · [Agent](../architecture/AGENT.md)
