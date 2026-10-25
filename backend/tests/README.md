# Tests

Grouped by the capability under test: `agents/`, `api/`, `persistence/`, `verification/` and `workflows/`. `e2e/browser_workbench.py` is the operator workbench browser journey. PostgreSQL queue tests run when `RELAY_TEST_DATABASE_URL` is set.

```sh
PYTHONPATH=backend/src RELAY_ALLOW_LIVE=0 python -m unittest discover -s backend/tests -v
```

[Evaluation](../../docs/evaluation/README.md)
