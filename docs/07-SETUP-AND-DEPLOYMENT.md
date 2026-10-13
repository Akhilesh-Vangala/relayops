# Setup and deployment

Python3.11.17 local environment; requirements.txt is fully pinned with hashes from requirements.in. Fresh checkout: python3.11 -m venv .venv; install with .venv/bin/python -m pip install --require-hashes -r requirements.txt. Use PYTHONPATH=src for module execution/tests; see README commands. This Mac uses an isolated uv-created environment; no system Python or VerifyOps package/environment changed.

No application server, browser product, Docker image, remote CI or cloud deployment yet. Do not describe prepared architecture as executed infrastructure. GitHub repository is TBD; the project has not been published.

Proposed deployment: container-hosted API/worker/browser sessions; managed PostgreSQL; Temporal service; object artifacts; OIDC; TLS; OTel/Phoenix. Vercel may host a separated frontend later but is not the persistent browser worker. Provider/account choice, costs, isolation, monitored operation, rollback and failure tests precede release.

Live configuration uses exported values, not automatic .env loading. Never paste keys into chat/Git or load another project's private credentials. The current billing admission is one-run-local; shared cross-worker financial accounting remains release work.
