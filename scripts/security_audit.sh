#!/bin/bash
# Security audit script for the SDLC project.
# Runs bandit for code-level security checks and pip-audit for dependency
# vulnerability scanning.
set -e

echo "=== SDLC Security Audit ==="
echo ""

echo "Running bandit security scan..."
uv run bandit -r sdlc/ -ll
echo ""

echo "Running pip-audit..."
uv run pip-audit
echo ""

echo "Security audit complete - 0 critical/high issues"
