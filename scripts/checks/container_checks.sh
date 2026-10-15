#!/bin/sh
set -eu
python -m unittest discover -s backend/tests -v
python backend/tests/e2e/browser_workbench.py
python -m relayops.evaluation.benchmark --output artifacts/generated/container-matrix
