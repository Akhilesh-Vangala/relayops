# Development

Python 3.12 is used locally, in CI and in the container images. Dependencies are installed from the hash-locked `backend/requirements/runtime.txt`. Generated output goes to the git-ignored `artifacts/generated/`.

## Setup

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install --require-hashes -r backend/requirements/runtime.txt
.venv/bin/python -m playwright install chromium
export PYTHONPATH=backend/src RELAY_ALLOW_LIVE=0
```

## Running

| Target | Command | URL |
| --- | --- | --- |
| Operator workbench (scripted agent, local SQLite) | `python -m relayops.api.web` | `http://127.0.0.1:8100` |
| Public build (product, demo, uploads) | `RELAY_DEMO_SECRET=<48+ chars> python -m uvicorn app:app --port 8000` | `http://127.0.0.1:8000` |
| Worker process | `RELAY_EMBEDDED_WORKER=0 python -m relayops.workers.worker` | none |
| Compose topology | `scripts/deployment/compose.sh up --build --wait` | `http://127.0.0.1:8100` |

## Configuration

| Variable | Purpose |
| --- | --- |
| `RELAY_ALLOW_LIVE` | `1` enables paid model calls. Defaults to off. |
| `ANTHROPIC_API_KEY`, `RELAY_MODEL` | Provider key and model. The model must match `backend/data/pricing.json`. |
| `RELAY_DATABASE_URL` | PostgreSQL run store. Unset uses SQLite. |
| `RELAY_EMBEDDED_WORKER` | `0` disables in-API execution |
| `RELAY_STATE_DIR` | Location of run worlds and checkpoints |
| `RELAY_ACCESS_TOKEN`, `RELAY_PUBLIC_ORIGIN` | Operator authentication and the public HTTPS origin |
| `RELAY_POSTGRES_PASSWORD` | Compose database password |
| `RELAY_DEMO_SECRET` | Public sandbox signing secret, at least 48 characters |
| `RELAY_REPORT_SIGNING_KEY` | Product report HMAC key, at least 48 characters |
| `RELAY_SUPABASE_URL`, `RELAY_SUPABASE_PUBLISHABLE_KEY`, `RELAY_ACCOUNT_SIGNUP` | Optional accounts |

Runtime code never auto-loads `.env`. Export values in the shell, or let Compose read them. `.env.example` is the template.

## Live model mode

Live mode needs all three of `RELAY_ALLOW_LIVE=1`, `ANTHROPIC_API_KEY`, and a `RELAY_MODEL` that matches the pricing profile. Every request is still subject to the input, output, time and $0.50 cumulative caps, and generation retries stay at zero. CI and the public build never enable it.

## Checks

```sh
python -m unittest discover -s backend/tests -v
python -m relayops.evaluation.benchmark --output artifacts/generated/matrix
python scripts/demos/public_demo_browser.py
python scripts/demos/product_browser.py --axe <path to axe.min.js>
python scripts/demos/import_browser.py --axe <path to axe.min.js>
python backend/tests/e2e/browser_workbench.py
python scripts/checks/check_repository.py
pipx run ruff==0.14.0 check . && pipx run ruff==0.14.0 format --check .
```

PostgreSQL-backed tests run when `RELAY_TEST_DATABASE_URL` is set. `scripts/checks/product_rls.py` needs `RELAY_PRODUCT_TEST_ADMIN_URL` pointing at a disposable server.

## Recording demos

```sh
python scripts/demos/public_demo_browser.py --record --publish-assets
python scripts/demos/product_browser.py --record
```

Both start an isolated local server, drive Chromium through the real journey, and write frames, a continuous WebM and a report with source hashes. With `--publish-assets`, the demo recorder copies its WebM and poster into `frontend/apps/demo/assets/media/`. The product walkthrough is served from `frontend/apps/uploads/`. The manifests in `docs/demos/` record frame, media and source hashes, and `check_repository.py` fails when tracked sources drift from them.

[Layout](LAYOUT.md) · [Branching](BRANCHING.md)
