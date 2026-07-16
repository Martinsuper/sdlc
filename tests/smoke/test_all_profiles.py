"""Full-Profile smoke: drive every real Profile end-to-end against a live model.

Skipped when no model is reachable (see conftest.llm_reachable), so the suite
stays green offline. CI (smoke.yml) runs this against a local Ollama, and
SDLC_SMOKE_REQUIRE=1 turns "unreachable" into a hard failure there so a broken
main-path cannot pass silently — the exact gap that let the GA P0 ship.
"""

from __future__ import annotations

import pytest

from sdlc.cli.deps import build_deps
from tests.smoke.conftest import MINIMAL_INPUTS

pytestmark = pytest.mark.smoke

# Real profiles shipped in sdlc/builtin/profiles/ (kept in sync with that dir).
ALL_PROFILES = sorted(MINIMAL_INPUTS)


@pytest.mark.asyncio
@pytest.mark.parametrize("profile", ALL_PROFILES)
async def test_profile_completes(profile, llm_reachable):
    reachable, detail = llm_reachable
    if not reachable:
        pytest.skip(f"LLM not reachable ({detail}); smoke profile run skipped")

    deps = build_deps()
    result = await deps.coordinator.run(
        input_text=MINIMAL_INPUTS[profile],
        profile_id=profile,
    )
    assert result.status == "completed", (
        f"profile {profile!r} did not complete: status={result.status} error={result.error}"
    )


def test_all_builtin_profiles_are_covered():
    """Guard: every builtin profile YAML has a minimal input here.

    Runs without a model — fails if someone adds a Profile but forgets to give
    the smoke gate an input for it (which would otherwise silently under-cover).
    """
    from pathlib import Path

    import sdlc

    profiles_dir = Path(sdlc.__file__).parent / "builtin" / "profiles"
    yaml_ids = {p.stem for p in profiles_dir.glob("*.yaml")}
    missing = yaml_ids - set(MINIMAL_INPUTS)
    assert not missing, f"Profiles with no smoke input: {sorted(missing)}"
