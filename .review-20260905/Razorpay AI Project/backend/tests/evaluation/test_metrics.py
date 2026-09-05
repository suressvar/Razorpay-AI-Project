"""Unit tests for evaluation metrics calculation."""

from recovery_autopilot.evaluation.metrics import bootstrap_rate_ci
from recovery_autopilot.evaluation.runner import run_evaluation


def test_bootstrap_rate_ci_bounds():
    """Bootstrap confidence intervals must lie within [0.0, 100.0] and lower <= upper."""
    outcomes = [True] * 40 + [False] * 60
    lower, upper = bootstrap_rate_ci(outcomes, n_bootstraps=500, ci_level=0.95, seed=42)

    assert 0.0 <= lower <= 100.0
    assert 0.0 <= upper <= 100.0
    assert lower <= upper
    # True rate is 40.0%
    assert lower <= 40.0 <= upper


def test_run_evaluation_positive_lift():
    """Autopilot should achieve positive recovery lift over baseline with zero safety violations."""
    report = run_evaluation(dataset_size=100, seed=42)

    assert report.dataset_size == 100
    assert report.agent_total_inr_recovered > 0
    assert report.baseline_total_inr_recovered > 0
    assert report.incremental_inr_recovered > 0
    assert report.incremental_recovery_rate_pct > 0
    assert report.agent_safety_violations == 0
    assert len(report.category_breakdown) > 0
