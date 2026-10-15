# Repository guide

The current entry point is the [README](../../README.md). This guide maps a technical review to the implementation and separates current evidence from release goals.

## A five-minute review

1. Read the business contract and engineering boundaries in the README.
2. Start the scripted workbench and open the short-shipment case. The controller collects actual browser evidence and demonstrates a rejected plan followed by a correction.
3. Inspect the cited hypotheses, proposal, private-copy checks and exact-version review.
4. Run the tests and development matrix. Read their scope before interpreting the counts.
5. Inspect the action broker and reconciliation tests: uncertainty must survive interruption and block blind retry.

## Where the implementation lives

| Concern | Source |
| --- | --- |
| Dynamic investigation and graph state | [agent.py](../../backend/src/relayops/agent.py) |
| Official SDK, typed streaming, budget receipts | [agent_transport.py](../../backend/src/relayops/agent_transport.py) |
| Browser evidence and restricted observation | [browser.py](../../backend/src/relayops/browser.py) |
| Strict plans and source binding | [domain.py](../../backend/src/relayops/domain.py), [policy.py](../../backend/src/relayops/policy.py) |
| Synthetic business environment and journal | [environment.py](../../backend/src/relayops/environment.py) |
| Private-copy simulation | [workflow.py](../../backend/src/relayops/workflow.py) |
| Approval-bound actions and reconciliation | [executor.py](../../backend/src/relayops/executor.py) |
| Independent business-state evaluation | [evaluator.py](../../backend/src/relayops/evaluator.py) |
| Operator application and native HTML/CSS/JavaScript | [web.py](../../backend/src/relayops/web.py) |
| Known scripted development matrix | [benchmark.py](../../backend/src/relayops/benchmark.py) |
| Reproducible CI | [checks.yml](../../.github/workflows/checks.yml) |

## Design tradeoffs

| Decision | Why it exists | Practical limit |
| --- | --- | --- |
| Read-only model tools; separate action broker | A proposal must not authorize its own business effects. | The only executable lane is the declared synthetic short-shipment contract. |
| Private simulation plus separate final-state checks | Catch policy-valid plans whose resulting business state is wrong. | Known fixtures and a shared declared contract do not establish generalization or formal proof. |
| SQLite checkpoints, model and action receipts | Make local interruption, replay and unknown outcomes inspectable. | Local transactions cannot guarantee atomicity across independent external services. |
| Browser-rendered documents with original pixels | Exercise multimodal transport, source hashes and observation provenance. | No live VLM score, scanned-PDF extraction or general GUI action capability is established. |
| Recent-image context with retained original artifacts | Bound image payloads while preserving the evidence record. | Text history is not general context compaction; long-task performance remains unmeasured. |
| Strict generation budgets and no automatic replay | Preserve unknown spend commitments and interrupted calls. | Per-run estimates are not provider invoices or a shared billing system. |

## Evidence and release gates

The implemented controller is **relay-agent-1**. Local source tests recorded 47 unit/integration tests, 16 browser journey checks and 12 known scripted assessments. CI runs those checks in fresh Linux environments; its actual status is linked from the README. Generated reports, screenshots, SQLite stores and logs are uploaded as CI artifacts and remain ignored locally.

No live model quality, frozen held-out accuracy, real customer feedback, production connectors, individual identity, distributed infrastructure or cloud operation is claimed. See [the release plan](../project/PLAN.md) and [agent/workbench details](../architecture/AGENT-WORKBENCH.md).

## Visual provenance

The repository banner and system map are original SVG illustrations. The PNGs are real, read-only captures from the local workbench using original synthetic data and scripted model choices. The full investigation screenshot shows an unreviewed proposal, not a real customer approval. No screenshot represents a live model benchmark.
