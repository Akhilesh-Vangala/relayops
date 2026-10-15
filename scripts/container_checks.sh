#!/bin/sh
set -eu
python -m unittest discover -s backend/tests -v
python tests/e2e/browser_workbench.py
python -m relayops.benchmark --output artifacts/generated/container-matrix
