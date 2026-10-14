# Implementation plan

October 14 durable-worker foundation: persisted requests, optional PostgreSQL queue with competing row-locked claims, lease/owner fencing and a separate browser worker now replace API-local tasks in container mode. API startup no longer invalidates owned work. Hardened Python 3.12 Docker/Compose and restricted Kubernetes/Kind packaging are implemented; local real PostgreSQL passes 57 tests without skips and the existing browser journey passes 16 checks. Actual container/Compose/Kind conclusions are recorded by the [three required PR checks](https://github.com/Akhilesh-Vangala/relayops/pull/4); protected main requires all three jobs before merging. [Architecture and deployment boundary](docs/13-DURABLE-WORKERS-AND-KUBERNETES.md). Fixture/action/checkpoint SQLite files still require same-node storage; individual identity, multi-host business state, isolated execution, live evaluation and monitored cloud operation remain pending.

## Foundation — Local implementation and verification

- [x] Original cross-system short-shipment contract and synthetic world.
- [x] Strict plans, source/evidence/scope admission and private counterfactual simulation.
- [x] Actual LangGraph assessment workflow and gated official Anthropic single-request planner.
- [x] Explicit sandbox approval, durable receipts, unknown-outcome reconciliation and independent final-state checks.
- [x] Known/scripted failure tests and CLI demonstrations; final evidence in PROGRESS.

## Agent and browser — Pending

- [x] Official SDK mocked HTTP/SSE integration, bounds and receipt replay tests.
- [ ] Controlled live model smoke/comparison early.
- [x] Original browser-rendered synthetic system/document evidence pages.
- [ ] Independently deployed enterprise sandbox apps and noisy document corpus.
- [x] Scoped read-only Playwright screenshot/accessibility observation.
- [ ] General GUI/API action adapters with broker authority.
- [x] Bounded dynamic observation/hypothesis/decision loop, public corrections and independent postchecks.
- [ ] Dynamic external action execution and interactive clarification continuation.
- [ ] Model/tool/budget trace comparison against strong baselines.

## Durable product — In progress

- [x] PostgreSQL investigation queue, schema migration, leased separate worker, API restart preservation and stale-owner rejection.
- [x] Hardened Docker/Compose and restricted Kubernetes/Kind integration topology; actual remote execution is recorded after CI.
- [ ] PostgreSQL business action/evidence/approval state and graph checkpoint migration; object artifacts and multi-host storage.
- [ ] Temporal lifecycle with isolated execution, retries only where effects are safe and tested.
- [ ] Individual identity, role/resource checks, approval expiry/revocation and partial-state recovery/compensation.
- [x] Local operator pages, stored activity/evidence viewer and exact-version review/sandbox execution.
- [x] Public read-only Vercel engineering showcase with cloud build and external smoke checks.
- [ ] Durable state-changing cloud workflow runtime, individual identity, monitoring and rollback.

## Release evidence — Pending

- [ ] Frozen held-out workflow/layout tests and adversarial failures.
- [ ] Repeated quality/cost/latency measurements and ablations.
- [x] Public reproducible repository/CI and scoped implementation/tradeoff write-up: [publication evidence](docs/11-GITHUB-PUBLICATION.md), [engineering guide](docs/10-REPOSITORY-GUIDE.md).
- [ ] Actual user sessions/feedback and measured utility.

RelayOps publication and actual Linux CI are verified; cloud delivery remains pending. Keep this project's gates separate from VerifyOps's completion tracker.
