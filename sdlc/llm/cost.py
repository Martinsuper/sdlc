from __future__ import annotations

import contextlib
import threading

from sdlc.utils.exceptions import SdlcError


class BudgetExceededError(SdlcError):
    """Raised when an LLM call would cause the budget to be exceeded."""
    pass


class CostTracker:
    """Track LLM call costs in real-time."""

    def __init__(self, state_store: object | None = None, max_budget_usd: float = 5.0) -> None:
        self.state = state_store
        self.max_budget = max_budget_usd
        self._session_cost = 0.0
        self._costs_by_model: dict[str, float] = {}
        self._lock = threading.Lock()

    def would_exceed_budget(self, additional_cost: float) -> bool:
        """Return True if adding additional_cost would exceed the budget.

        This is a pre-check that can be called before making an LLM request
        to avoid spending money that would go over budget.
        """
        with self._lock:
            return (self._session_cost + additional_cost) > self.max_budget

    def record(self, model: str, input_tokens: int, output_tokens: int, cost_usd: float) -> None:
        """Record a single LLM call cost.

        Raises BudgetExceededError if recording this cost would exceed the budget.
        Also persists the cost data to state_store if available.
        """
        with self._lock:
            self._session_cost += cost_usd
            self._costs_by_model[model] = self._costs_by_model.get(model, 0.0) + cost_usd
            new_total = self._session_cost

        if new_total > self.max_budget:
            raise BudgetExceededError(
                f"Budget exceeded: ${new_total:.4f} > ${self.max_budget:.4f} "
                f"(model={model}, cost_usd={cost_usd:.6f})"
            )

        # Persist to state_store if available
        if self.state is not None and hasattr(self.state, "record_llm_call"):
            # Persistence failure should not break cost tracking
            with contextlib.suppress(Exception):
                self.state.record_llm_call(
                    pipeline_id="",
                    stage_id=None,
                    model=model,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    cost_usd=cost_usd,
                    duration_ms=0,
                    cached=False,
                )

    def check_budget(self) -> bool:
        """Return True if budget exceeded."""
        with self._lock:
            return self._session_cost >= self.max_budget

    @property
    def total_cost(self) -> float:
        with self._lock:
            return self._session_cost

    @property
    def cost_by_model(self) -> dict[str, float]:
        with self._lock:
            return dict(self._costs_by_model)

    def summary(self) -> dict[str, object]:
        with self._lock:
            return {
                "total_usd": self._session_cost,
                "budget_usd": self.max_budget,
                "budget_remaining": max(0.0, self.max_budget - self._session_cost),
                "budget_exceeded": self._session_cost >= self.max_budget,
                "by_model": dict(self._costs_by_model),
            }
