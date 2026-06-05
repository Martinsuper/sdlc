from __future__ import annotations


class CostTracker:
    """Track LLM call costs in real-time."""

    def __init__(self, state_store: object | None = None, max_budget_usd: float = 5.0) -> None:
        self.state = state_store
        self.max_budget = max_budget_usd
        self._session_cost = 0.0
        self._costs_by_model: dict[str, float] = {}

    def record(self, model: str, input_tokens: int, output_tokens: int, cost_usd: float) -> None:
        """Record a single LLM call cost."""
        self._session_cost += cost_usd
        self._costs_by_model[model] = self._costs_by_model.get(model, 0.0) + cost_usd

    def check_budget(self) -> bool:
        """Return True if budget exceeded."""
        return self._session_cost >= self.max_budget

    @property
    def total_cost(self) -> float:
        return self._session_cost

    @property
    def cost_by_model(self) -> dict[str, float]:
        return dict(self._costs_by_model)

    def summary(self) -> dict[str, object]:
        return {
            "total_usd": self._session_cost,
            "budget_usd": self.max_budget,
            "budget_remaining": max(0.0, self.max_budget - self._session_cost),
            "budget_exceeded": self.check_budget(),
            "by_model": dict(self._costs_by_model),
        }
