# Repository layout

Root folders are organized by deployable component, and folders inside a component by responsibility. The only top-level files are the Python, Vercel and Git configuration files, `app.py`, `.env.example` and the README. `scripts/checks/check_repository.py` enforces the root-folder allowlist and requires every backend capability package to have its own README.

```text
relayops/
├── .github/                 CI, public health monitor, issue and PR templates, CONTRIBUTING
├── app.py                   Vercel entrypoint (public build)
├── backend/
│   ├── data/                pricing profile for live mode
│   ├── docker/              runtime and test image
│   ├── requirements/        hash-locked dependencies
│   ├── src/relayops/
│   │   ├── agents/          LangGraph agent, transport, browser evidence, planners, workflow
│   │   ├── api/             FastAPI app, public sandbox, envelope signing
│   │   ├── cli/             command-line launch and continuation
│   │   ├── domain/          fixture world, typed models, policy
│   │   ├── evaluation/      scripted case matrix
│   │   ├── execution/       approval, executor, reconciliation
│   │   ├── persistence/     run store and migrations
│   │   ├── product/         product routes, accounts, run contract
│   │   ├── uploads/         imports, analysis, SSE, report signing
│   │   ├── verification/    independent evaluator
│   │   └── workers/         leased worker, health, database wait
│   └── tests/
│       ├── agents/  api/  persistence/  verification/  workflows/
│       └── e2e/             operator workbench browser journey
├── frontend/apps/
│   ├── product/             product workspace (ES modules)
│   ├── demo/                interactive sandbox SPA and recorded walkthrough
│   ├── workbench/           operator workbench assets
│   └── uploads/             upload walkthrough recording page and media
├── infrastructure/
│   ├── containers/          Compose topology
│   ├── kubernetes/          base resources and Kind overlay
│   └── supabase/            owner-isolated account migration
├── scripts/
│   ├── checks/              repository, RLS, public health, container entrypoint
│   ├── demos/               browser journeys and recorders
│   └── deployment/          Compose launcher, Compose and Kind smoke tests
└── docs/
    ├── architecture/  product/  operations/  evaluation/  development/
    ├── demos/               recording manifests
    └── assets/demos/        recording preview and product screenshot
```

## Ownership

- **Backend API.** Owns request validation, origin checks, identity and the public write allowlist.
- **Agent.** Owns observation and proposal only.
- **Policy, simulation and evaluation.** Decide whether a proposal is admissible.
- **Execution.** Owns which effects occur and how their receipts are recorded.
- **Persistence and workers.** Own claiming, leases and recovery.
- **Frontend apps.** Own presentation and browser storage, with no build step and no Node service.

Source paths feed the agent's recovery fingerprint, so moving files intentionally invalidates old checkpoints and checked proposals.

[Development](DEVELOPMENT.md) · [Branching](BRANCHING.md)
