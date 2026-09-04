"""End-to-end evaluation runner comparing Recovery Autopilot against Fixed Baseline."""

import json
from pathlib import Path
from typing import List, Optional

from recovery_autopilot.domain.enums import FailureCategory, RecoveryAction
from recovery_autopilot.evaluation.baseline import FixedRuleBaseline
from recovery_autopilot.evaluation.metrics import BenchmarkReport, calculate_benchmark_report
from recovery_autopilot.evaluation.simulator import OutcomeSimulator, SimulationResult
from recovery_autopilot.synthetic.generator import generate_synthetic_dataset
from recovery_autopilot.synthetic.scenarios import SyntheticScenario


def determine_autopilot_action(
    scenario: SyntheticScenario, human_review_threshold: float = 15000.0
) -> RecoveryAction:
    """Determine policy-guarded Autopilot recovery intervention for a scenario."""
    ctx = scenario.context

    # 1. Opt-out check -> immediate STOP
    if ctx.opted_out:
        return RecoveryAction.STOP

    # 2. Maximum contact attempts reached -> STOP
    if ctx.previous_contacts >= 3:
        return RecoveryAction.STOP

    # 3. High value case or Unknown failure -> Escalate to HUMAN_REVIEW
    if ctx.amount_inr >= human_review_threshold or ctx.failure_category == FailureCategory.UNKNOWN_FAILURE:
        return RecoveryAction.HUMAN_REVIEW

    # 4. Domain-intelligent action selection based on failure category
    if ctx.failure_category in [FailureCategory.BANK_TIMEOUT, FailureCategory.NETWORK_FAILURE]:
        # Infrastructure failure: wait for retry to avoid spamming customer
        return RecoveryAction.WAIT_FOR_RETRY

    elif ctx.failure_category == FailureCategory.EXPIRED_CARD:
        # Expired card cannot be retried; customer must update instrument
        return RecoveryAction.REQUEST_METHOD_UPDATE

    elif ctx.failure_category == FailureCategory.MANDATE_REVOKED:
        return RecoveryAction.SEND_PAYMENT_LINK

    elif ctx.failure_category == FailureCategory.CUSTOMER_ACTION_REQUIRED:
        return RecoveryAction.SEND_PAYMENT_LINK

    elif ctx.failure_category == FailureCategory.INSUFFICIENT_FUNDS:
        # If near salary date, wait; otherwise send payment link
        if scenario.salary_day_near and ctx.previous_failures <= 1:
            return RecoveryAction.WAIT_FOR_RETRY
        return RecoveryAction.SEND_PAYMENT_LINK

    elif ctx.failure_category == FailureCategory.LIMIT_EXCEEDED:
        return RecoveryAction.WAIT_FOR_RETRY

    return RecoveryAction.HUMAN_REVIEW


def run_evaluation(
    dataset_size: int = 500,
    seed: int = 42,
    output_path: Optional[Path] = None,
) -> BenchmarkReport:
    """Execute complete deterministic evaluation on synthetic dataset."""
    scenarios = generate_synthetic_dataset(count=dataset_size, seed=seed)
    simulator = OutcomeSimulator()
    baseline = FixedRuleBaseline()

    agent_results: List[SimulationResult] = []
    baseline_results: List[SimulationResult] = []

    for scenario in scenarios:
        # Run Autopilot
        ap_action = determine_autopilot_action(scenario)
        ap_res = simulator.simulate(scenario, ap_action)
        agent_results.append(ap_res)

        # Run Fixed Baseline
        base_action = baseline.decide_action(scenario)
        base_res = simulator.simulate(scenario, base_action)
        baseline_results.append(base_res)

    report = calculate_benchmark_report(
        scenarios=scenarios,
        agent_results=agent_results,
        baseline_results=baseline_results,
        seed=seed,
    )

    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(report.model_dump(), f, indent=2)

    return report
