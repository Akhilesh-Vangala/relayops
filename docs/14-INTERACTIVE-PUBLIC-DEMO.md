# Interactive public app and recording

The [public RelayOps app](https://relayops-two.vercel.app/demo) now has an executable guided sandbox, in addition to the full private workbench. [Watch the continuous browser recording](https://relayops-two.vercel.app/demo/recording). This supersedes the earlier read-only public deployment for the `/demo` experience; legacy private write routes remain blocked.

## Actual workflow

Choose a shortage → inspect the real LangGraph diagnostic and private-copy simulation → approve the checked proposal → execute sandbox actions → reconcile a deliberately lost acknowledgment → independently verify final state. Four confirmed action receipts and a repeated execution check are visible.

These are original synthetic fixtures and actual existing planner/verifier/executor calculations. The public mode deliberately uses the guided diagnostic, with no paid or live model calls. The private product retains the separately documented model-directed agent and durable worker paths. Vercel does not execute the full dbt/browser worker pipeline.

## Request and authority boundaries

- `app.py` selects public mode and disables provider keys, persistent databases and embedded workers. Exact `/api/demo/*` POST paths are permitted; legacy writes remain HTTP405.
- `src/relayops/public_demo.py` reconstructs an isolated original fixture for each request and calls the existing implementation. No client-supplied business state is trusted.
- `demo_security.py` signs expiring source/result/stage envelopes with a private deployment secret. The envelope is bound to an HttpOnly, SameSite=Strict anonymous browser cookie; changed source/result versions, tampering and cross-browser reuse are rejected.
- Session history is kept in this browser's sessionStorage. Exported JSON omits the workflow envelope. There is no shared public history or durable review ledger.
- A previously signed branch can be replayed or forked until expiry. Each replay starts a fresh isolated fixture. This is not global exactly-once execution, irrevocable review, tenant identity or production business mutation.
- The functions use temporary files and bounded inputs. VerifyOps limits each instance to two concurrent investigations and checks a25second execution allowance. These are per-instance controls, not a distributed rate limiter or a billing cap.
- Secrets `RELAY_DEMO_SECRET` must be configured privately (at least48characters); never put them in tracked files or a browser bundle. No model key is needed for this sandbox.

## Reproduce and inspect

```sh
python scripts/public_demo_browser.py
python scripts/public_demo_browser.py --url https://relayops-two.vercel.app
python scripts/public_demo_browser.py --record --publish-assets --output artifacts/generated/public-demo-recording
```

The browser runner exercises actual actions, failed-state boundaries, a JSON download, reload/history, a second isolated browser, mobile layout and the native video player. Unit tests in `tests/test_public_demo.py` cover tampering, cross-browser scope and version/review/write gates. CI also retains the existing private integration, container and infrastructure checks.

Recordings are continuous Playwright WebM captures of real interactions, with no fabricated results. The tracked file is `src/relayops/demo_assets/walkthrough.webm`; the README GIF is a separate six-frame preview. [Source hashes and recording provenance](demos/interactive-recording.json) identify the source at capture. Automated synthetic review is not user feedback or evidence of live-model quality.

Local verification: 65 unit tests, with3 PostgreSQL-only skips; the new public browser journey passes. Remote PostgreSQL/container/dbt checks and actual Vercel execution must also pass before promotion; current results are linked from the PR and deployment evidence.

Persistent monitored cloud workers, individual identity, live model evaluations and actual user feedback remain separate delivery gates. The public sandbox does not complete those milestones.
