# Setup and deployment

October 13 current repository: [RelayOps](https://github.com/Akhilesh-Vangala/relayops). Use the [README quick start](../README.md#run-locally), [CI workflow](../.github/workflows/checks.yml) and [contribution guide](../CONTRIBUTING.md). The local operator app is implemented; Both Linux jobs passed at the publication baseline; [actual CI evidence](11-GITHUB-PUBLICATION.md) includes logs/artifact verification. The earlier no-server/no-publication paragraph below is the superseded foundation record. No Docker runtime or cloud deployment is claimed.

October12 current implementation: [model-directed agent and local workbench](09-AGENT-AND-WORKBENCH.md) add persistent dynamic tool selection, real browser/document screenshots, cited public hypotheses, bounded correction, actual SDK HTTP/SSE checks and operator pages. Earlier no-browser/no-server/single-call-only statements below describe the initial foundation and are superseded for current coverage; live quality, arbitrary UI actions, scanned-document extraction and distributed/cloud release remain pending.

Python3.11.17 local environment; requirements.txt is fully pinned with hashes from requirements.in. Fresh checkout: python3.11 -m venv .venv; install with .venv/bin/python -m pip install --require-hashes -r requirements.txt. Use PYTHONPATH=src for module execution/tests; see README commands. This Mac uses an isolated uv-created environment; no system Python or VerifyOps package/environment changed.

No application server, browser product, Docker image, remote CI or cloud deployment yet. Do not describe prepared architecture as executed infrastructure. GitHub repository is TBD; the project has not been published.

Proposed deployment: container-hosted API/worker/browser sessions; managed PostgreSQL; Temporal service; object artifacts; OIDC; TLS; OTel/Phoenix. Vercel may host a separated frontend later but is not the persistent browser worker. Provider/account choice, costs, isolation, monitored operation, rollback and failure tests precede release.

Live configuration uses exported values, not automatic .env loading. Never paste keys into chat/Git or load another project's private credentials. The current billing admission is one-run-local; shared cross-worker financial accounting remains release work.
