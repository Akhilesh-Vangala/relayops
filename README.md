# RelayOps

A workflow agent for a short-shipment across procurement, warehouse, billing, and case systems. It observes those systems, proposes typed actions, and simulates them on a private copy. Nothing is executed until that exact version passes independent checks.

[Open the app](https://relayops-two.vercel.app/) · [Upload a file](https://relayops-two.vercel.app/uploads) · [Architecture](docs/architecture/OVERVIEW.md) · [What the checks measure](docs/evaluation/README.md) · [Run locally](docs/operations/DEVELOPMENT.md)

<p align="center"><a href="https://github.com/Akhilesh-Vangala/relayops/actions/workflows/checks.yml"><img src="https://github.com/Akhilesh-Vangala/relayops/actions/workflows/checks.yml/badge.svg" alt="Required engineering checks"></a> &nbsp; Python · LangGraph · FastAPI · PostgreSQL</p>

The public app uses synthetic fixtures and does not call a model. Live model quality is not a result of this repository.

## Architecture

The model can observe and propose. Simulation, final-state checks, and the action broker are separate. An uncertain acknowledgment is reconciled before any retry, so a lost response does not become a second payment or a second shipment.

![System map: observation, grounded plan, private-copy simulation, exact-version review, receipted actions](docs/assets/diagrams/relayops-architecture.svg)

| Component | Responsibility |
| --- | --- |
| Frontend | Operator workbench, evidence/review views, session history, exports |
| Backend | FastAPI, typed contracts, LangGraph orchestration, review gates |
| Independent checking | Private-copy final-state evaluation and receipt/duplicate checks |
| Runtime | PostgreSQL queue and leased workers; fixtures remain same-node |

## Repository layout

```text
relayops/
├── backend/          src, tests, requirements, docker, data
├── frontend/         demo + workbench apps
├── infrastructure/   containers, kubernetes
├── scripts/          checks, demos, deployment
├── docs/
└── .github/
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
