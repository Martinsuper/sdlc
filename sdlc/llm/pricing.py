"""Three-tier LLM price resolution: exact → family-prefix → conservative estimate.

Custom gateways and third-party models frequently report model names that are
not in any provider's ``PRICING`` table (variant suffixes, private aliases).
Before this module, such calls resolved to ``cost=0`` — which silently defeats
budget enforcement and makes ``stats``/ROI report zero spend. Here we fall back
through progressively looser matches and, as a last resort, a conservative
estimate that is *non-zero* (so budget protection still trips) rather than 0.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Price:
    input_per_m: float  # USD per 1M input tokens
    output_per_m: float  # USD per 1M output tokens


# Family matching for variant/gateway names not in any exact table. Each entry
# is (required_tokens, price): a model matches when *all* tokens appear as
# substrings (case-insensitive). Token matching (rather than a strict prefix)
# is required because vendors interleave version segments into the tier word —
# e.g. both "claude-sonnet-4-20250514" and "claude-3-5-sonnet-20241022" must
# map to sonnet pricing. Order matters: more-specific entries first so
# "gpt-4o-mini" wins over "gpt-4o", and "deepseek-reasoner" over "deepseek".
_FAMILY_MATCHERS: tuple[tuple[tuple[str, ...], Price], ...] = (
    (("claude", "opus"), Price(15.0, 75.0)),
    (("claude", "sonnet"), Price(3.0, 15.0)),
    (("claude", "haiku"), Price(0.80, 4.0)),
    (("gpt-4o-mini",), Price(0.15, 0.60)),
    (("gpt-4o",), Price(5.0, 15.0)),
    (("deepseek-reasoner",), Price(0.55, 2.19)),
    (("deepseek",), Price(0.14, 0.28)),
)

# Conservative estimate for wholly-unknown models. Deliberately non-trivial
# (sonnet tier) so unknown spend is over- rather than under-counted, keeping
# budget protection effective instead of silently passing at cost=0.
_FALLBACK_ESTIMATE = Price(3.0, 15.0)


def resolve_price(
    model: str, exact: dict[str, dict[str, float]] | None = None
) -> tuple[Price, str]:
    """Resolve a model's price and the source of that resolution.

    Returns ``(price, source)`` where ``source`` is one of:
      - ``"exact"``    — matched the provider's own ``PRICING`` table
      - ``"family"``   — matched a known family (all tokens present)
      - ``"estimate"`` — no match; conservative fallback estimate

    The ``source`` label lets callers mark estimated costs (via
    ``CompletionResponse.cost_source``) so ``stats``/ROI can distinguish
    measured from estimated spend.
    """
    if exact and model in exact:
        p = exact[model]
        return Price(p["in"], p["out"]), "exact"
    lowered = model.lower()
    for tokens, price in _FAMILY_MATCHERS:
        if all(tok in lowered for tok in tokens):
            return price, "family"
    return _FALLBACK_ESTIMATE, "estimate"


def compute_cost(
    model: str,
    input_tokens: int,
    output_tokens: int,
    exact: dict[str, dict[str, float]] | None = None,
) -> tuple[float, str]:
    """Compute cost in USD for a call, returning ``(cost_usd, source)``.

    Ollama / local models legitimately price at 0 via an exact table entry;
    only *unknown* models fall through to the non-zero estimate.
    """
    price, source = resolve_price(model, exact)
    cost = (input_tokens * price.input_per_m + output_tokens * price.output_per_m) / 1_000_000
    return cost, source
