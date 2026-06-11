import pytest

from sdlc.llm.cost import BudgetExceededError, CostTracker


class TestCostTracker:
    def test_initial_state(self):
        tracker = CostTracker()
        assert tracker.total_cost == 0.0
        assert tracker.cost_by_model == {}
        assert tracker.check_budget() is False

    def test_record_single_call(self):
        tracker = CostTracker()
        tracker.record("claude-sonnet-4-6", 1000, 500, 0.03)
        assert tracker.total_cost == 0.03
        assert tracker.cost_by_model == {"claude-sonnet-4-6": 0.03}

    def test_record_multiple_calls_same_model(self):
        tracker = CostTracker()
        tracker.record("claude-sonnet-4-6", 1000, 500, 0.03)
        tracker.record("claude-sonnet-4-6", 2000, 1000, 0.06)
        assert tracker.total_cost == 0.09
        assert tracker.cost_by_model == {"claude-sonnet-4-6": 0.09}

    def test_record_multiple_calls_different_models(self):
        tracker = CostTracker()
        tracker.record("claude-sonnet-4-6", 1000, 500, 0.03)
        tracker.record("claude-opus-4-7", 500, 200, 0.10)
        assert tracker.total_cost == 0.13
        assert tracker.cost_by_model == {"claude-sonnet-4-6": 0.03, "claude-opus-4-7": 0.10}

    def test_check_budget_not_exceeded(self):
        tracker = CostTracker(max_budget_usd=5.0)
        tracker.record("claude-sonnet-4-6", 1000, 500, 0.03)
        assert tracker.check_budget() is False

    def test_check_budget_exceeded(self):
        tracker = CostTracker(max_budget_usd=0.05)
        tracker.record("claude-sonnet-4-6", 1000, 500, 0.03)
        with pytest.raises(BudgetExceededError):
            tracker.record("claude-sonnet-4-6", 2000, 1000, 0.06)
        assert tracker.check_budget() is True

    def test_check_budget_exact_limit(self):
        tracker = CostTracker(max_budget_usd=0.03)
        tracker.record("claude-sonnet-4-6", 1000, 500, 0.03)
        assert tracker.check_budget() is True

    def test_summary_no_calls(self):
        tracker = CostTracker(max_budget_usd=5.0)
        summary = tracker.summary()
        assert summary["total_usd"] == 0.0
        assert summary["budget_usd"] == 5.0
        assert summary["budget_remaining"] == 5.0
        assert summary["budget_exceeded"] is False
        assert summary["by_model"] == {}

    def test_summary_with_calls(self):
        tracker = CostTracker(max_budget_usd=1.0)
        tracker.record("claude-sonnet-4-6", 1000, 500, 0.03)
        tracker.record("claude-opus-4-7", 500, 200, 0.10)
        summary = tracker.summary()
        assert summary["total_usd"] == 0.13
        assert summary["budget_usd"] == 1.0
        assert summary["budget_remaining"] == 0.87
        assert summary["budget_exceeded"] is False
        assert summary["by_model"] == {"claude-sonnet-4-6": 0.03, "claude-opus-4-7": 0.10}

    def test_summary_budget_exceeded(self):
        tracker = CostTracker(max_budget_usd=0.05)
        with pytest.raises(BudgetExceededError):
            tracker.record("claude-sonnet-4-6", 1000, 500, 0.06)
        summary = tracker.summary()
        assert summary["budget_exceeded"] is True
        assert summary["budget_remaining"] == 0.0

    def test_cost_by_model_returns_copy(self):
        tracker = CostTracker()
        tracker.record("claude-sonnet-4-6", 1000, 500, 0.03)
        costs = tracker.cost_by_model
        costs["extra"] = 99.0
        # Original should not be modified
        assert "extra" not in tracker.cost_by_model

    def test_custom_max_budget(self):
        tracker = CostTracker(max_budget_usd=10.0)
        tracker.record("claude-sonnet-4-6", 1000, 500, 0.03)
        assert tracker.max_budget == 10.0
        assert tracker.check_budget() is False

    def test_state_store_param(self):
        tracker = CostTracker(state_store=None, max_budget_usd=2.0)
        assert tracker.state is None
        assert tracker.max_budget == 2.0
