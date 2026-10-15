> Historical record. [Current project overview](../../../README.md) and [current handoff](../HANDOFF.md) take precedence.

# Setup and deployment

October 14 current implementation: [durable worker and Kubernetes foundation](../../operations/DURABLE-WORKERS.md) adds PostgreSQL investigation coordination, a separate leased browser worker, restart preservation, shared-operator access, hardened Python 3.12 Docker/Compose and a restricted same-node Kind topology. Earlier API-local/no-container/no-queue statements are historical. Business state/checkpoint/object migration and monitored cloud operation remain open.

October 13 current repository: [RelayOps](https://github.com/Akhilesh-Vangala/relayops). The [public Vercel showcase](https://relayops-two.vercel.app) serves the real FastAPI product in an explicit read-only mode; its [deployment record](VERCEL-SHOWCASE.md) defines what this establishes. The local operator app retains state-changing sandbox workflows. Both Linux jobs passed at the publication baseline; [actual CI evidence](GITHUB-PUBLICATION.md) includes logs/artifact verification. Earlier no-server/no-publication text below is retained as history.

October12 current implementation: [model-directed agent and local workbench](../../architecture/AGENT-WORKBENCH.md) add persistent dynamic tool selection, real browser/document screenshots, cited public hypotheses, bounded correction, actual SDK HTTP/SSE checks and operator pages. Earlier no-browser/no-server/single-call-only statements below describe the initial foundation and are superseded for current coverage; live quality, arbitrary UI actions, scanned-document extraction and distributed/cloud release remain pending.

Python3.11.17 local environment; backend/requirements.txt is fully pinned with hashes from backend/requirements.in. Fresh checkout: python3.11 -m venv .venv; install with .venv/bin/python -m pip install --require-hashes -r backend/requirements.txt. Use PYTHONPATH=backend/src for module execution/tests; see README commands. This Mac uses an isolated uv-created environment; no system Python or VerifyOps package/environment changed.

No application server, browser product, Docker image, remote CI or cloud deployment yet. Do not describe prepared architecture as executed infrastructure. GitHub repository is TBD; the project has not been published.

Proposed deployment: container-hosted API/worker/browser sessions; managed PostgreSQL; Temporal service; object artifacts; OIDC; TLS; OTel/Phoenix. Vercel may host a separated frontend later but is not the persistent browser worker. Provider/account choice, costs, isolation, monitored operation, rollback and failure tests precede release.

Live configuration uses exported values, not automatic .env loading. Never paste keys into chat/Git or load another project's private credentials. The current billing admission is one-run-local; shared cross-worker financial accounting remains release work.
