# RelayOps

A workflow agent for a short-shipment across procurement, warehouse, billing, and case systems. It observes those systems, proposes typed actions, and simulates them on a private copy. Nothing is executed until that exact version passes independent checks.

[Open the app](https://relayops-two.vercel.app/) · [Upload a file](https://relayops-two.vercel.app/uploads) · [Architecture](docs/architecture/OVERVIEW.md) · [What the checks measure](docs/evaluation/README.md) · [Run locally](docs/operations/DEVELOPMENT.md)

<p align="center"><a href="https://github.com/Akhilesh-Vangala/relayops/actions/workflows/checks.yml"><img src="https://github.com/Akhilesh-Vangala/relayops/actions/workflows/checks.yml/badge.svg" alt="Required engineering checks"></a> &nbsp; Python · LangGraph · FastAPI · PostgreSQL</p>

The public app uses synthetic fixtures and does not call a model. Live model quality is not a result of this repository.

## Architecture

The model can observe and propose. Simulation, final-state checks, and the action broker are separate. An uncertain acknowledgment is reconciled before any retry, so a lost response does not become a second payment or a second shipment.

![System map: observation, grounded plan, private-copy simulation, exact-version review, receipted actions](docs/assets/diagrams/relayops-architecture.svg)

| Layer | Where | Responsibility |
| --- | --- | --- |
| Frontend | `frontend/` | Operator workbench, evidence, review, exports |
| Agent | `backend/src/relayops/agents/` | Observation, typed proposal. It does not execute. |
| Backend | `backend/src/relayops/` | API, private-copy simulation, checks, receipts, workers |

The agent package stays inside the backend import root so the service can call it. It is not the API, and it is not the checker.

## Repository layout

```text
frontend/                         workbench and demo
backend/src/relayops/agents/      model loop, browser evidence, planner
backend/src/relayops/             API, simulation, verification, workers
```

## Run locally

```sh
git clone https://github.com/Akhilesh-Vangala/relayops.git
cd relayops
python3.12 -m venv .venv
.venv/bin/python -m pip install --require-hashes -r backend/requirements/runtime.txt
.venv/bin/python -m playwright install chromium
PYTHONPATH=backend/src RELAY_ALLOW_LIVE=0 .venv/bin/python -m relayops.api.web
```

Open **http://127.0.0.1:8100**. [Full development guide](docs/operations/DEVELOPMENT.md).

## Checks

```sh
PYTHONPATH=backend/src RELAY_ALLOW_LIVE=0 python -m unittest discover -s backend/tests -v
python scripts/checks/check_repository.py
```

Public demos use guided synthetic fixtures (no live inference claim). Live model quality and customer production certification remain out of scope. [Evaluation](docs/evaluation/README.md) · [Demo notes](docs/DEMO.md)
