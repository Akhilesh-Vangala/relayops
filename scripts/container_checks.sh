#!/bin/sh
set -eu
python -m unittest discover -s tests -v
python tests/browser_workbench.py
python -m relayops.benchmark --output artifacts/generated/container-matrix
