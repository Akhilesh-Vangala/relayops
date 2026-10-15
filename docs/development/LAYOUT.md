# RelayOps component layout

Run commands from the repository root unless a command states otherwise. The file tree is organized by ownership at the root and responsibility inside each component.

```text
relayops/
├── backend/
│   ├── src/relayops/
│   ├── tests/
│   ├── requirements/
│   ├── docker/
│   └── data/
├── frontend/
│   └── apps/
│       ├── demo/
│       │   └── assets/
│       │       ├── scripts/
│       │       ├── styles/
│       │       └── media/
│       └── workbench/
│           └── assets/
│               ├── scripts/
│               └── styles/
├── infrastructure/
│   ├── containers/
│   └── kubernetes/
├── scripts/
│   ├── checks/
│   ├── demos/
│   └── deployment/
├── docs/
│   ├── architecture/
│   ├── operations/
│   ├── evaluation/
│   ├── project/history/
│   └── assets/
│       ├── branding/
│       ├── diagrams/
│       ├── screenshots/
│       └── demos/
└── .github/
```

## Ownership and runtime boundaries

Backend APIs own request validation, identity and action authority. Agents propose bounded decisions; verification and execution code own whether a proposal passes and which effects may occur. Persistence and workers own recovery and claims. Frontend code owns presentation and browser interactions. Tests are grouped by capability, with shared fixtures and cross-component browser journeys identified separately.

Only GitHub/Python/Vercel discovery files, private-configuration examples and the primary README remain at the root. Compose is under infrastructure/containers; `scripts/deployment/compose.sh` supplies the repository project directory so build contexts, private root .env and existing volume naming retain their intended meaning. No live-model call or cloud apply is part of this reorganization.

Source-path changes intentionally change runtime and review fingerprints. Preserve old results; start a fresh investigation when stale checkpoints or checked proposals are rejected. The exportable VerifyOps investigator deliberately keeps a small flat runtime when copied into an isolated workspace; evaluator references remain outside that runtime.

[Branch policy](BRANCHING.md) · [Backend](../../backend/README.md) · [Frontend](../../frontend/README.md) · [Infrastructure](../../infrastructure/README.md) · [Scripts](../../scripts/README.md)

## Full directory navigation

```text
relayops/
├── .github/
│   ├── ISSUE_TEMPLATE/
│   └── workflows/
├── backend/
│   ├── data/
│   ├── docker/
│   ├── requirements/
│   ├── src/
│   │   └── relayops/
│   │       ├── agents/
│   │       ├── api/
│   │       ├── cli/
│   │       ├── domain/
│   │       ├── evaluation/
│   │       ├── execution/
│   │       ├── persistence/
│   │       ├── verification/
│   │       └── workers/
│   └── tests/
│       ├── agents/
│       ├── api/
│       ├── e2e/
│       ├── persistence/
│       ├── verification/
│       └── workflows/
├── docs/
│   ├── architecture/
│   ├── assets/
│   │   ├── branding/
│   │   ├── demos/
│   │   ├── diagrams/
│   │   └── screenshots/
│   ├── demos/
│   │   └── history/
│   ├── development/
│   ├── evaluation/
│   ├── evidence/
│   ├── operations/
│   ├── product/
│   └── project/
│       └── history/
├── frontend/
│   └── apps/
│       ├── demo/
│       │   └── assets/
│       │       ├── media/
│       │       ├── scripts/
│       │       └── styles/
│       └── workbench/
│           └── assets/
│               ├── scripts/
│               └── styles/
├── infrastructure/
│   ├── containers/
│   └── kubernetes/
│       ├── base/
│       └── overlays/
│           └── kind/
└── scripts/
    ├── checks/
    ├── demos/
    └── deployment/
```
