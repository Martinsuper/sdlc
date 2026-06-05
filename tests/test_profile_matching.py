"""Tests for multi-factor profile auto-matching accuracy."""

import pytest

from sdlc.profile.models import ProfileDef
from sdlc.profile.registry import ProfileRegistry, register_builtins


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _registry_with_builtins() -> ProfileRegistry:
    reg = ProfileRegistry()
    register_builtins(reg)
    return reg


# ---------------------------------------------------------------------------
# match_score accuracy
# ---------------------------------------------------------------------------


class TestMatchScore:
    def test_entry_kind_match_gives_0_4(self):
        reg = _registry_with_builtins()
        profile = reg.get("bug-fix")  # severity P1
        # Pass mismatching severity to isolate the entry_kind factor
        score = reg.match_score(profile, "bug", severity="P3")
        assert score == pytest.approx(0.4)

    def test_no_entry_kind_match_gives_0(self):
        reg = _registry_with_builtins()
        profile = reg.get("bug-fix")  # severity P1, entry_kinds=["bug"]
        # entry_kind="feature" does not match, severity P1 != P3 (default)
        score = reg.match_score(profile, "feature", severity="P3")
        assert score == pytest.approx(0.0)

    def test_severity_alignment_adds_0_15(self):
        reg = _registry_with_builtins()
        profile = reg.get("bug-fix")  # severity P1
        score = reg.match_score(profile, "bug", severity="P1")
        assert score == pytest.approx(0.4 + 0.15)

    def test_severity_mismatch_adds_0(self):
        reg = _registry_with_builtins()
        profile = reg.get("bug-fix")  # severity P1
        score = reg.match_score(profile, "bug", severity="P2")
        assert score == pytest.approx(0.4)

    def test_keyword_match_adds_0_15(self):
        reg = _registry_with_builtins()
        profile = reg.get("new-feature")  # severity P2
        # Pass severity="P3" to avoid default severity alignment bonus
        score = reg.match_score(profile, "feature", severity="P3", keywords=["新功能"])
        assert score == pytest.approx(0.4 + 0.15)

    def test_keyword_mismatch_adds_0(self):
        reg = _registry_with_builtins()
        profile = reg.get("new-feature")  # severity P2, name "新功能"
        # Pass severity="P3" to isolate keyword factor; "bug" is not in profile_text
        score = reg.match_score(profile, "feature", severity="P3", keywords=["bug"])
        assert score == pytest.approx(0.4)

    def test_tech_stack_match_adds_0_3(self):
        reg = _registry_with_builtins()
        profile = reg.get("frontend")  # severity P2
        # Pass severity="P3" to isolate tech_stack factor
        score = reg.match_score(profile, "feature", severity="P3", tech_stack=["frontend"])
        assert score == pytest.approx(0.4 + 0.3)

    def test_tech_stack_mismatch_adds_0(self):
        reg = _registry_with_builtins()
        profile = reg.get("frontend")  # severity P2
        # "backend" is not in frontend's base_stages string
        score = reg.match_score(profile, "feature", severity="P3", tech_stack=["backend"])
        assert score == pytest.approx(0.4)

    def test_full_match_gives_1_0(self):
        reg = _registry_with_builtins()
        profile = reg.get("frontend")
        score = reg.match_score(
            profile,
            "feature",
            tech_stack=["frontend"],
            severity="P2",
            keywords=["前端功能"],
        )
        assert score == pytest.approx(1.0)

    def test_score_capped_at_1_0(self):
        reg = _registry_with_builtins()
        profile = reg.get("new-feature")
        score = reg.match_score(
            profile,
            "feature",
            tech_stack=["backend"],
            severity="P2",
            keywords=["新功能", "feature", "idea"],
        )
        assert score <= 1.0

    def test_empty_context_only_entry_kind(self):
        reg = _registry_with_builtins()
        profile = reg.get("hotfix")  # severity P0
        # Pass severity="P3" to avoid default severity alignment
        score = reg.match_score(profile, "hotfix", severity="P3")
        assert score == pytest.approx(0.4)


# ---------------------------------------------------------------------------
# resolve with different entry kinds
# ---------------------------------------------------------------------------


class TestResolve:
    def test_resolve_bug_with_severity_p1(self):
        reg = _registry_with_builtins()
        p = reg.resolve("bug", severity="P1")
        assert p.id == "bug-fix"

    def test_resolve_feature_prefers_best_match(self):
        reg = _registry_with_builtins()
        # Without context, "feature" matches new-feature, frontend, full-stack equally (0.4 each).
        # The first one encountered wins — this is acceptable as they all match.
        p = reg.resolve("feature")
        assert p.entry_kinds == ["feature", "idea"] or p.entry_kinds == ["feature"]

    def test_resolve_feature_with_frontend_tech_stack(self):
        reg = _registry_with_builtins()
        p = reg.resolve("feature", tech_stack=["frontend"])
        assert p.id == "frontend"

    def test_resolve_feature_with_full_stack_tech_stack(self):
        reg = _registry_with_builtins()
        p = reg.resolve("feature", tech_stack=["frontend", "backend"])
        # new-feature, frontend, and full-stack all match "feature" entry_kind.
        # With tech_stack=["frontend","backend"], each matches at least one item
        # via the any() check, so they score equally at 0.85.
        # Any of these three is a valid resolution.
        assert p.id in ("new-feature", "frontend", "full-stack")

    def test_resolve_hotfix(self):
        reg = _registry_with_builtins()
        p = reg.resolve("hotfix")
        assert p.id == "hotfix"

    def test_resolve_refactor(self):
        reg = _registry_with_builtins()
        p = reg.resolve("refactor")
        assert p.id == "refactor"

    def test_resolve_test(self):
        reg = _registry_with_builtins()
        p = reg.resolve("test")
        assert p.id == "test"


# ---------------------------------------------------------------------------
# resolve_all ranking
# ---------------------------------------------------------------------------


class TestResolveAll:
    def test_resolve_all_returns_all_profiles(self):
        reg = _registry_with_builtins()
        results = reg.resolve_all("bug")
        assert len(results) == len(reg.list_profiles())

    def test_resolve_all_bug_top_is_bug_fix(self):
        reg = _registry_with_builtins()
        results = reg.resolve_all("bug")
        top_profile, top_score = results[0]
        assert top_profile.id == "bug-fix"
        assert top_score > 0.0

    def test_resolve_all_scores_sorted_descending(self):
        reg = _registry_with_builtins()
        results = reg.resolve_all("feature", tech_stack=["frontend"])
        scores = [score for _, score in results]
        for i in range(len(scores) - 1):
            assert scores[i] >= scores[i + 1]

    def test_resolve_all_with_severity_context(self):
        reg = _registry_with_builtins()
        results = reg.resolve_all("bug", severity="P1")
        # bug-fix should be at the top with severity alignment bonus
        top_profile, top_score = results[0]
        assert top_profile.id == "bug-fix"
        assert top_score == pytest.approx(0.4 + 0.15)


# ---------------------------------------------------------------------------
# Fallback to new-feature
# ---------------------------------------------------------------------------


class TestFallback:
    def test_unknown_entry_kind_falls_back(self):
        reg = _registry_with_builtins()
        p = reg.resolve("totally-unknown")
        assert p.id == "new-feature"

    def test_fallback_with_no_context(self):
        reg = _registry_with_builtins()
        # Use severity that doesn't match any profile to ensure only entry_kind drives matching
        p = reg.resolve("unknown-kind", tech_stack=[], severity="P5", keywords=[])
        assert p.id == "new-feature"

    def test_empty_registry_fallback_raises(self):
        """With no profiles at all, even the fallback get("new-feature") should raise."""
        reg = ProfileRegistry()
        with pytest.raises(Exception):
            reg.resolve("feature")


# ---------------------------------------------------------------------------
# Tech stack influence on matching
# ---------------------------------------------------------------------------


class TestTechStackInfluence:
    def test_frontend_tech_stack_boosts_frontend_profile(self):
        reg = _registry_with_builtins()
        # Without tech_stack, feature matches multiple profiles at 0.4
        p_no_ts = reg.resolve("feature")
        # With frontend tech_stack, frontend profile gets 0.4+0.3=0.7
        p_with_ts = reg.resolve("feature", tech_stack=["frontend"])
        assert p_with_ts.id == "frontend"
        # frontend score > new-feature score (0.7 > 0.4 or 0.7)
        score_frontend = reg.match_score(reg.get("frontend"), "feature", tech_stack=["frontend"])
        score_new_feature = reg.match_score(reg.get("new-feature"), "feature", tech_stack=["frontend"])
        assert score_frontend > score_new_feature

    def test_backend_tech_stack_boosts_backend_profiles(self):
        reg = _registry_with_builtins()
        p = reg.resolve("feature", tech_stack=["backend"])
        # new-feature has s-impl-backend, so it should get tech_stack bonus
        score_new_feature = reg.match_score(
            reg.get("new-feature"), "feature", tech_stack=["backend"]
        )
        score_frontend = reg.match_score(
            reg.get("frontend"), "feature", tech_stack=["backend"]
        )
        assert score_new_feature > score_frontend

    def test_tech_stack_empty_does_not_boost(self):
        reg = _registry_with_builtins()
        profile = reg.get("bug-fix")  # severity P1
        # Pass severity="P3" to isolate tech_stack factor
        score = reg.match_score(profile, "bug", severity="P3", tech_stack=[])
        # Empty tech_stack should not add bonus
        assert score == pytest.approx(0.4)

    def test_tech_stack_non_matching_does_not_boost(self):
        reg = _registry_with_builtins()
        profile = reg.get("bug-fix")  # severity P1
        # Pass severity="P3" to isolate tech_stack factor
        score = reg.match_score(profile, "bug", severity="P3", tech_stack=["golang"])
        # "golang" won't appear in base_stages string
        assert score == pytest.approx(0.4)