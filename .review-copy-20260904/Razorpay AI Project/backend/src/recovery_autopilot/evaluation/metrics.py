"""Evaluation metrics and statistical benchmarking."""

import random
from statistics import median
from typing import List

from pydantic import BaseModel

from recovery_autopilot.evaluation.simulator import SimulationResult
from recovery_autopilot.synthetic.scenarios import SyntheticScenario


class CategoryMetric(BaseModel):
    """Metrics aggregated per failure category."""

    category: str
    total_cases: int
    agent_recovered_count: int
    agent_recovery_rate: float
    baseline_recovered_count: int
    baseline_recovery_rate: float
    incremental_rate_pct: float
    agent_inr_recovered: float
    baseline_inr_recovered: float


class BenchmarkReport(BaseModel):
    """Comprehensive benchmark comparison report."""

    dataset_size: int
    random_seed: int

    # Agent Metrics
    agent_total_inr_recovered: float
    agent_recovery_rate: float
    agent_median_recovery_time_hours: float
    agent_contacts_per_recovered: float
    agent_human_review_rate: float
    agent_safety_violations: int

    # Baseline Metrics
    baseline_total_inr_recovered: float
    baseline_recovery_rate: float
    baseline_median_recovery_time_hours: float
    baseline_contacts_per_recovered: float
    baseline_safety_violations: int

    # Comparative Lift
    incremental_inr_recovered: float
    incremental_recovery_rate_pct: float
    unnecessary_contacts_avoided: int

    # Statistical Confidence (95% Bootstrap CI on Recovery Rate)
    agent_recovery_rate_ci_lower: float
    agent_recovery_rate_ci_upper: float
    baseline_recovery_rate_ci_lower: float
    baseline_recovery_rate_ci_upper: float

    # Category Breakdown
    category_breakdown: List[CategoryMetric]


def bootstrap_rate_ci(
    outcomes: List[bool], n_bootstraps: int = 1000, ci_level: float = 0.95, seed: int = 42
) -> tuple[float, float]:
    """Compute empirical bootstrap confidence interval for a binary success rate."""
    if not outcomes:
        return 0.0, 0.0

    n = len(outcomes)
    rng = random.Random(seed)
    rates: List[float] = []

    for _ in range(n_bootstraps):
        sample = [outcomes[rng.randint(0, n - 1)] for _ in range(n)]
        rate = sum(sample) / n
        rates.append(rate)

    rates.sort()
    alpha = (1.0 - ci_level) / 2.0
    lower_idx = max(0, int(alpha * n_bootstraps))
    upper_idx = min(n_bootstraps - 1, int((1.0 - alpha) * n_bootstraps))

    return round(rates[lower_idx] * 100, 2), round(rates[upper_idx] * 100, 2)


def calculate_benchmark_report(
    scenarios: List[SyntheticScenario],
    agent_results: List[SimulationResult],
    baseline_results: List[SimulationResult],
    seed: int = 42,
) -> BenchmarkReport:
    """Compile exhaustive comparison metrics between Recovery Autopilot and Fixed Baseline."""
    n = len(scenarios)
    assert len(agent_results) == n
    assert len(baseline_results) == n

    # Agent aggregates
    agent_recovered = [r for r in agent_results if r.recovered]
    agent_total_inr = sum(r.recovered_amount for r in agent_results)
    agent_rate = (len(agent_recovered) / n * 100) if n else 0.0
    agent_times = [r.time_to_recovery_hours for r in agent_recovered] or [0.0]
    agent_median_time = median(agent_times)
    agent_contacts = sum(r.customer_contact_count for r in agent_results)
    agent_contacts_per_rec = (agent_contacts / len(agent_recovered)) if agent_recovered else 0.0
    agent_human_reviews = sum(1 for r in agent_results if r.human_review_needed)
    agent_human_review_rate = (agent_human_reviews / n * 100) if n else 0.0
    agent_violations = sum(1 for r in agent_results if r.safety_violation_occurred)

    # Baseline aggregates
    baseline_recovered = [r for r in baseline_results if r.recovered]
    baseline_total_inr = sum(r.recovered_amount for r in baseline_results)
    baseline_rate = (len(baseline_recovered) / n * 100) if n else 0.0
    baseline_times = [r.time_to_recovery_hours for r in baseline_recovered] or [0.0]
    baseline_median_time = median(baseline_times)
    baseline_contacts = sum(r.customer_contact_count for r in baseline_results)
    baseline_contacts_per_rec = (baseline_contacts / len(baseline_recovered)) if baseline_recovered else 0.0
    baseline_violations = sum(1 for r in baseline_results if r.safety_violation_occurred)

    # Comparative Lift
    incremental_inr = agent_total_inr - baseline_total_inr
    incremental_rate = agent_rate - baseline_rate
    contacts_avoided = max(0, baseline_contacts - agent_contacts)

    # Bootstrap CIs
    a_low, a_high = bootstrap_rate_ci([r.recovered for r in agent_results], seed=seed)
    b_low, b_high = bootstrap_rate_ci([r.recovered for r in baseline_results], seed=seed)

    # Breakdown by category
    categories = sorted(list({s.context.failure_category.value for s in scenarios}))
    breakdowns: List[CategoryMetric] = []

    for cat in categories:
        cat_indices = [i for i, s in enumerate(scenarios) if s.context.failure_category.value == cat]
        cat_n = len(cat_indices)
        if not cat_n:
            continue

        cat_agent_res = [agent_results[i] for i in cat_indices]
        cat_base_res = [baseline_results[i] for i in cat_indices]

        cat_agent_rec = sum(1 for r in cat_agent_res if r.recovered)
        cat_base_rec = sum(1 for r in cat_base_res if r.recovered)

        cat_agent_rate = round(cat_agent_rec / cat_n * 100, 2)
        cat_base_rate = round(cat_base_rec / cat_n * 100, 2)

        breakdowns.append(
            CategoryMetric(
                category=cat,
                total_cases=cat_n,
                agent_recovered_count=cat_agent_rec,
                agent_recovery_rate=cat_agent_rate,
                baseline_recovered_count=cat_base_rec,
                baseline_recovery_rate=cat_base_rate,
                incremental_rate_pct=round(cat_agent_rate - cat_base_rate, 2),
                agent_inr_recovered=round(sum(r.recovered_amount for r in cat_agent_res), 2),
                baseline_inr_recovered=round(sum(r.recovered_amount for r in cat_base_res), 2),
            )
        )

    return BenchmarkReport(
        dataset_size=n,
        random_seed=seed,
        agent_total_inr_recovered=round(agent_total_inr, 2),
        agent_recovery_rate=round(agent_rate, 2),
        agent_median_recovery_time_hours=round(agent_median_time, 1),
        agent_contacts_per_recovered=round(agent_contacts_per_rec, 2),
        agent_human_review_rate=round(agent_human_review_rate, 2),
        agent_safety_violations=agent_violations,
        baseline_total_inr_recovered=round(baseline_total_inr, 2),
        baseline_recovery_rate=round(baseline_rate, 2),
        baseline_median_recovery_time_hours=round(baseline_median_time, 1),
        baseline_contacts_per_recovered=round(baseline_contacts_per_rec, 2),
        baseline_safety_violations=baseline_violations,
        incremental_inr_recovered=round(incremental_inr, 2),
        incremental_recovery_rate_pct=round(incremental_rate, 2),
        unnecessary_contacts_avoided=contacts_avoided,
        agent_recovery_rate_ci_lower=a_low,
        agent_recovery_rate_ci_upper=a_high,
        baseline_recovery_rate_ci_lower=b_low,
        baseline_recovery_rate_ci_upper=b_high,
        category_breakdown=breakdowns,
    )
