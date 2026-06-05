#!/bin/bash
# Run locust performance tests headless
cd "$(dirname "$0")/../.."
uv run locust -f tests/perf/locustfile.py --headless -u 100 -r 10 -t 30s --host http://localhost:0
