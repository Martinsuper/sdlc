"""End-to-end smoke gate (M-D1).

Two kinds of check live here:

1. test_error_visibility.py — runs with NO real LLM. It proves a failing stage
   surfaces its error to the caller (PipelineResult.error) and that `sdlc run`
   exits non-zero. This is the regression guard against the GA bug where a
   red main-path was hidden behind green unit tests. It must always run.

2. test_all_profiles.py — drives every real Profile through a minimal pipeline
   against a live model (local Ollama by default). It requires a reachable
   model and is SKIPPED otherwise, so the full suite stays green offline while
   CI (smoke.yml) runs it against Ollama.

Select just this suite with `pytest -m smoke`.
"""
