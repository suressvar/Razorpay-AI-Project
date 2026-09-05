"""Evaluation module for Recovery Autopilot."""

from recovery_autopilot.evaluation.baseline import FixedRuleBaseline
from recovery_autopilot.evaluation.metrics import BenchmarkReport, calculate_benchmark_report
from recovery_autopilot.evaluation.runner import run_evaluation
from recovery_autopilot.evaluation.simulator import OutcomeSimulator, SimulationResult

__all__ = [
    "BenchmarkReport",
    "FixedRuleBaseline",
    "OutcomeSimulator",
    "SimulationResult",
    "calculate_benchmark_report",
    "run_evaluation",
]
