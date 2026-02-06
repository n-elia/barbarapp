#!/usr/bin/env bash
set -euo pipefail

# Quick project sanity checks using uv-managed Python
echo "Running syntax check..."
uv run python -m py_compile app.py libs/**/*.py pages/**/*.py

echo "All checks passed."