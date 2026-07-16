"""Fixtures for the smoke gate.

``ollama_available`` probes a local Ollama endpoint (or an explicitly configured
LLM) with the shared smoke_test helper; the profile-completion tests skip when
no model answers, so the suite is green offline and meaningful in CI.
"""

from __future__ import annotations

import os

import pytest

# The minimal one-line request handed to each profile's pipeline. Kept trivial
# so a small local model can complete it quickly.
MINIMAL_INPUTS: dict[str, str] = {
    "new-feature": "add a health-check endpoint",
    "bug-fix": "fix an off-by-one in pagination",
    "hotfix": "P0: null pointer on login",
    "refactor": "extract a helper for date parsing",
    "test": "add a unit test for the parser",
    "doc": "document the config file format",
    "infra": "add a CI lint step",
    "release": "cut a patch release",
    "revert": "revert the last commit",
    "migrate": "migrate a column to not-null",
    "audit": "audit auth for missing checks",
    "idea": "explore adding a plugin system",
    "frontend": "add a loading spinner to the list",
    "full-stack": "add a settings page end to end",
}


def _probe_llm() -> tuple[bool, str]:
    """Return (reachable, detail) for the configured/local model."""
    try:
        from sdlc.llm.smoke import smoke_test
        from sdlc.utils.config_loader import load_config

        cfg = load_config()
        return smoke_test(cfg.llm, timeout=20.0)
    except Exception as e:
        return False, str(e)


@pytest.fixture(scope="session")
def llm_reachable() -> tuple[bool, str]:
    # Opt-in override for CI: SDLC_SMOKE_REQUIRE=1 turns an unreachable model
    # into a hard failure instead of a skip (so CI can't silently pass).
    ok, detail = _probe_llm()
    if not ok and os.environ.get("SDLC_SMOKE_REQUIRE") == "1":
        pytest.fail(f"SDLC_SMOKE_REQUIRE=1 but LLM not reachable: {detail}")
    return ok, detail
