<p align="center">
  <img src="docs/assets/relayops-banner.svg" alt="RelayOps — evidence to verified action; observe, propose, verify, authorize" width="100%">
</p>

<p align="center">
  <a href="https://github.com/Akhilesh-Vangala/relayops/actions/workflows/checks.yml"><img src="https://github.com/Akhilesh-Vangala/relayops/actions/workflows/checks.yml/badge.svg" alt="RelayOps workbench CI status"></a>
  &nbsp; Python 3.11 · LangGraph · AsyncAnthropic · Playwright · FastAPI
</p>

<p align="center">
  <a href="#the-business-problem">Problem</a> ·
  <a href="#inside-the-agent">Agent architecture</a> ·
  <a href="#the-operator-workbench">Workbench</a> ·
  <a href="#run-locally">Quick start</a> ·
  <a href="#engineering-evidence">Evidence</a> ·
  <a href="docs/README.md">Technical documentation</a>
</p>

# RelayOps

**A workflow agent that observes business systems, grounds a proposal in evidence, and executes only an explicitly approved version.**

RelayOps investigates operational exceptions across procurement, warehouse, billing and case management. Its checkpointed LangGraph agent selects read-only tools, inspects browser and document evidence, records cited hypotheses, and corrects rejected plans. A separate runtime simulates the proposed effects, checks the resulting business state, and presents the exact proposal for operator review.

> **Development release.** The local app, dynamic agent loop, official model transport and sandbox execution are implemented and integration-tested. The default demo uses scripted model choices and makes no model calls. Live AI quality, scanned-document extraction, production connectors, individual identity and cloud operation remain pending.

## The business problem

A supplier invoices **100 units at $25 each**, but the warehouse confirms receipt of **80 units**. Paying the entire invoice or retrying an uncertain action can create an incorrect business outcome. Resolving the exception requires consistent evidence from several systems and verified effects after review.

| Source-backed finding | Proposed action under the supported contract |
| --- | --- |
| Confirmed 20-unit shortage; consistent order and invoice; sufficient stock | Hold **$500**, create a **20-unit** supplier claim, reserve **20 replacement units**, then resolve the case. |
| Unknown delivery, conflicting invoice quantity or insufficient stock | Request clarification and produce **no business actions**. |
| Complete, consistent delivery | Return **no change**. |

This is an original synthetic workflow with a declared action contract. It supports reviewable engineering experiments; additional business lanes require new contracts and validation environments.

## The operator workbench

![Actual RelayOps home page with operational cases, stored investigations and live-model configuration status](docs/assets/workbench-overview.png)

The app has overview, case catalog, case detail, investigation history, investigation detail and architecture pages. Open a case, run an investigation, inspect source screenshots and cited hypotheses, review the proposal, then explicitly execute approved sandbox actions. Activity and outcomes come from stored records.

<details>
<summary><strong>Inspect the real investigation screen and source evidence</strong></summary>

![Actual investigation with cited hypotheses, proposed business actions and recorded agent activity](docs/assets/investigation.png)

![Full investigation with an expanded original source observation and counterfactual checks](docs/assets/investigation-full.png)

These captures use original synthetic data and scripted model choices. The shown proposal has not been approved; screenshots do not establish live AI accuracy or customer usage.

</details>

## Inside the agent

![RelayOps system map separating read-only model tools, runtime verification, operator review and sandbox action recovery](docs/assets/relayops-architecture.svg)

The model chooses `observe_system`, `inspect_document`, `record_hypotheses` and `submit_plan`. It cannot approve or execute its own proposal. **relay-agent-1** uses actual conditional graph transitions, durable investigation checkpoints and model-result receipts. Public policy feedback permits at most two corrections; private evaluator answers do not enter the feedback loop.

<details>
<summary><strong>Expand the detailed agent flow and implemented layers</strong></summary>

```mermaid
%%{init: {"theme": "neutral"}}%%
flowchart TD
    Goal[Scoped case and task] --> Model[Bounded model round with public memory]
    Model --> Choice{Model tool choice}
    Choice --> Observe[System and document observations]
    Observe --> Pixels[Real browser screenshot and accessibility tree]
    Pixels --> Model
    Choice --> Memory[Validate cited public hypotheses]
    Memory --> Model
    Choice --> Plan[Submit strict evidence-bound plan]
    Plan --> Public[Scope, source version, citations and action policy]
    Public -->|Rejected| Feedback[At most two public corrections]
    Feedback --> Model
    Public -->|Accepted| Simulate[Execute on private fixture copy]
    Simulate --> Verify[Independent final-state checks]
    Verify --> Review[Exact-version operator review]
    Review --> Execute[Sandbox action broker and receipts]
    Execute --> Unknown{Outcome uncertain?}
    Unknown -->|Yes| Reconcile[Explicit state reconciliation before retry]
    Unknown -->|No| Final[Verify actual business effects]
```

| Layer | Actual behavior |
| --- | --- |
| **Model-directed tool use** | Agent chooses `observe_system`, `inspect_document`, `record_hypotheses` or `submit_plan`. No fixed collection sequence in the live controller. |
| **Multimodal observations** | Playwright captures original local pages, screenshots and accessibility trees; image content is passed to the model. This is not yet real scanned-document extraction or general GUI navigation. |
| **Grounded public memory** | Hypotheses cite observed evidence; current interpretations and recent evidence IDs are included in model context. No hidden chain-of-thought is requested or displayed. |
| **Context management** | Only the latest two images stay in model context; original PNGs/hashes and textual observations remain stored. Byte/token bounds apply before generation. |
| **Critique and correction** | Strict schema, evidence coverage, source and business-policy feedback permit two corrections; private evaluator answers never enter feedback. |
| **Persistent investigation** | SQLite LangGraph checkpoints plus model-result receipts; recovery requires identical source/runtime/client/pricing/browser configuration. Uncertain generations block replay. |
| **Independent checking** | Private-copy simulation, separate final-state evaluator and unchanged-source/duplicate-effect checks. These are scoped checks, not universal proof. |
| **Review and action control** | Immutable exact-version sandbox review; stale/tampered/source-changed assessments blocked. Controlled actions retain receipts, uncertain outcomes and partial state. |
| **Operator visibility** | Home, cases, investigation history/detail, evidence screenshots, hypothesis memory, real activity, proposed changes, verification and architecture pages. |

</details>

| Engineering boundary | Current behavior |
| --- | --- |
| **Source grounding** | Four system observations and two document observations; cited evidence, source-version checks and hashed real screenshots. |
| **Multimodal context** | Browser pixels and accessibility text enter model tool results. Only the latest two images remain in context; original image artifacts stay retained. |
| **Verification** | Public action policy, private-copy simulation and a separate final-state evaluator. Execution is followed by independent actual-effect checks. |
| **Approval integrity** | Immutable exact-version sandbox review; changed source, runtime, report or artifacts block stale approval. |
| **Recovery** | Completed model receipts avoid a second generation; uncertain generations block replay. Action receipts retain partial effects and require explicit reconciliation before retry. |
| **Model bounds** | 12 rounds, 24 evidence calls, 3 identical calls, 2 corrections; 8,000 input tokens per request / 64,000 cumulative; 2,048 requested output per round / 12,000 total; 240 active model seconds; 2 MB request body. |
| **Estimated spending** | $0.50 cumulative commitment allowance per run; unknown usage retains reservations. Reported overruns are accounted for before another generation. This is not a provider invoice cap or shared billing service. |

SQLite state, local background tasks and browser contexts are single-host development infrastructure. External side effects, distributed workflow guarantees and OS-level execution isolation require additional implementation.

[Implementation and boundaries](docs/09-AGENT-AND-WORKBENCH.md) · [Source map and tradeoffs](docs/10-REPOSITORY-GUIDE.md) · [Decisions](docs/DECISIONS.md)

## Run locally

Use Python **3.11**; the recorded local runtime and CI target **3.11.17**. From a fresh checkout:

```sh
git clone https://github.com/Akhilesh-Vangala/relayops.git
cd relayops
python3.11 -m venv .venv
.venv/bin/python -m pip install --require-hashes -r requirements.txt
.venv/bin/python -m playwright install chromium
PYTHONPATH=src RELAY_ALLOW_LIVE=0 .venv/bin/python -m relayops.web --port 8100
```

Open **http://127.0.0.1:8100**. The default scripted integration demonstrates actual evidence collection, a rejected proposal, correction, independent simulation and explicit sandbox review. No API key is needed. The server binds to loopback; persistent local data is stored under `artifacts/generated/app`.

<details>
<summary><strong>Run the CLI, checks and known development matrix</strong></summary>

```sh
PYTHONPATH=src RELAY_ALLOW_LIVE=0 .venv/bin/python -m unittest discover -s tests -v
PYTHONPATH=src RELAY_ALLOW_LIVE=0 .venv/bin/python tests/browser_workbench.py
PYTHONPATH=src RELAY_ALLOW_LIVE=0 .venv/bin/python -m relayops.agent_cli --output artifacts/generated/browser-demo --browser --test-correction
PYTHONPATH=src RELAY_ALLOW_LIVE=0 .venv/bin/python -m relayops.benchmark --output artifacts/generated/development-matrix
```

Use fresh output directories. `agent_cli --recover` explicitly resumes a compatible saved investigation. The legacy `python -m relayops` CLI retains the foundation assessment and acknowledgement-loss sandbox examples.

</details>

<details>
<summary><strong>Enable a bounded live model run privately</strong></summary>

Configure exported `ANTHROPIC_API_KEY`, `RELAY_ALLOW_LIVE=1` and `RELAY_MODEL` matching the trusted pricing profile. Then select the live workbench mode or `agent_cli --client anthropic`. The project uses the official async SDK and typed streaming; generation retries are disabled. It never imports another project's private configuration.

Live runs are billable and must pass model, token and estimated-spend admission. No live generation has been performed in the recorded evidence below. [Configuration and limits](docs/09-AGENT-AND-WORKBENCH.md).

</details>

## Engineering evidence

The recorded local checks below belong to implementation baseline [`dc85c15`](https://github.com/Akhilesh-Vangala/relayops/commit/dc85c1536d9cb95054bfd26542d9b46ed2e8c2ef). Presentation and CI additions preserve that source implementation.

| Check | Recorded local result | What it tests |
| --- | --- | --- |
| Unit and integration suite | **47 passed** | SDK HTTP/SSE assembly over mocked transport, checkpoint recovery, strict citations, receipt reuse, review integrity and duplicate prevention. |
| Actual browser journey | **16 checks passed** | Six source captures, proposal correction, review/execution, grounded clarification, five pages across four viewport widths, no runtime errors. |
| Known scripted development matrix | **12/12 assessments passed** | Original short-shipment variants, missing evidence, conflicting quantities, stock boundaries and no-change cases. |
| Fresh-process / concurrency tests | Included in the unit suite | Explicit uncertain-action reconciliation in a new Python process and concurrent duplicate-effect prevention. |

These counts are **engineering and integration evidence**, not live model accuracy, held-out performance or customer validation. The CI badge links to current-branch Linux checks. Actions uploads browser evidence and matrix reports; generated runtime stores and logs stay out of Git.

## Repository map

```text
relayops/
├── src/relayops/        Agent, browser tools, policy, action broker, API and UI
├── tests/              Protocol, recovery, execution and browser journeys
├── docs/               Architecture, AI design, evaluation, setup and original visuals
├── .github/            Reproducible checks and review templates
├── requirements.txt    Fully pinned dependency hashes
├── PLAN.md             Implementation and release gates
└── CONTRIBUTING.md     Local verification and evidence conventions
```

[Technical documentation](docs/README.md) · [Code and design tradeoffs](docs/10-REPOSITORY-GUIDE.md) · [Research references](docs/REFERENCES.md) · [Progress](PROGRESS.md) · [Handoff](HANDOFF.md)

## Next release gates

Controlled live model comparisons; noisy document extraction with field provenance; new frozen workflow/layout tasks and safety evaluations; external action adapters; PostgreSQL/Temporal and individual identity; isolated execution and monitored cloud delivery; actual user feedback. [Full implementation plan](PLAN.md).
