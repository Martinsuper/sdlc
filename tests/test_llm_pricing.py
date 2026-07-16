"""Tests for three-tier LLM price resolution (sdlc/llm/pricing.py).

Regression coverage for the bug where models absent from a provider's PRICING
table resolved to cost=0 — defeating budget enforcement and making stats/ROI
report zero spend for custom-gateway / third-party models.
"""

from __future__ import annotations

from sdlc.llm.anthropic_provider import AnthropicProvider
from sdlc.llm.pricing import compute_cost, resolve_price


def test_exact_match_uses_provider_table():
    price, source = resolve_price("claude-opus-4-20250514", AnthropicProvider.PRICING)
    assert source == "exact"
    assert price.input_per_m == 15.0
    assert price.output_per_m == 75.0


def test_exact_match_cost_matches_legacy_formula():
    # Regression: exact-match cost must equal the pre-refactor arithmetic.
    cost, source = compute_cost(
        "claude-sonnet-4-20250514", 1_000_000, 1_000_000, AnthropicProvider.PRICING
    )
    assert source == "exact"
    assert cost == 3.0 + 15.0  # 1M in @ $3 + 1M out @ $15


def test_family_prefix_variant_name():
    # A gateway variant name not in the table but sharing a known family.
    price, source = resolve_price("claude-3-5-sonnet-20999999", AnthropicProvider.PRICING)
    assert source == "family"
    assert price.input_per_m == 3.0
    assert price.output_per_m == 15.0


def test_family_prefix_specific_wins_over_general():
    # "gpt-4o-mini" must not be captured by a "gpt-4o" prefix.
    price, source = resolve_price("gpt-4o-mini-2099", exact=None)
    assert source == "family"
    assert price.input_per_m == 0.15


def test_unknown_model_falls_back_to_nonzero_estimate():
    cost, source = compute_cost("totally-unknown-model-x", 1_000_000, 1_000_000, exact=None)
    assert source == "estimate"
    assert cost > 0  # the whole point: never silently 0 for unknown models


def test_ollama_zero_priced_via_exact_stays_zero():
    # Local models legitimately price at 0 through an exact table entry; only
    # *unknown* models should hit the non-zero estimate.
    exact = {"llama3": {"in": 0.0, "out": 0.0}}
    cost, source = compute_cost("llama3", 1_000_000, 1_000_000, exact)
    assert source == "exact"
    assert cost == 0.0
