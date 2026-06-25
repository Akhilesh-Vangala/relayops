# Contributing

Use the [branch and release workflow](../docs/development/BRANCHING.md): short-lived work branch → pull request → required CI → squash merge into protected `main`.

Use the [README quick start](../README.md#run-locally) to create a Python 3.11 environment from the hashed dependency lock. Development checks require Chromium. Use original synthetic fixtures and fresh generated output directories.

## Verify a change

```sh
PYTHONPATH=backend/src RELAY_ALLOW_LIVE=0 .venv/bin/python -m unittest discover -s backend/tests -v
PYTHONPATH=backend/src RELAY_ALLOW_LIVE=0 .venv/bin/python backend/tests/e2e/browser_workbench.py
PYTHONPATH=backend/src RELAY_ALLOW_LIVE=0 .venv/bin/python -m relayops.evaluation.benchmark --output artifacts/generated/contribution-matrix
```

The [CI workflow](workflows/checks.yml) installs the pinned hash-verified dependencies on Linux and runs these checks without live model credentials. Never enable paid model calls in pull-request CI. Review changes to source fingerprints and recovery compatibility when modifying the controller or dependencies.

## Review expectations

- Explain the business behavior, authority boundary and observed failure that motivated the change.
- Separate scripted/fake-transport integration results from live model or held-out performance.
- Keep model tools read-only; preserve exact-version review, unknown receipts and explicit reconciliation.
- Add focused failure tests when changing execution, recovery, evidence or budget behavior.
- Use focused conventional commits, such as `feat(agent): ...`, `fix(execution): ...` or `docs(readme): ...`.
- Keep credentials, generated stores, private data and local environments out of Git. Preserve dated design history and update the current implementation docs.

The supported workflow and infrastructure limits are in the [repository guide](../docs/development/REPOSITORY.md). The app is a local research workbench; public multitenant hosting requires the identity and isolation release gates in [PLAN.md](../docs/project/PLAN.md).
