#!/usr/bin/env python3
"""Script to run deterministic evaluation comparing Recovery Autopilot vs Baseline."""

import argparse
import sys
from pathlib import Path

# Ensure backend/src is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend" / "src"))

from recovery_autopilot.evaluation.metrics import generate_markdown_report
from recovery_autopilot.evaluation.runner import run_evaluation


def main():
    parser = argparse.ArgumentParser(description="Run Recovery Autopilot vs Baseline Evaluation")
    parser.add_argument("--size", type=int, default=500, help="Number of scenarios to evaluate (default: 500)")
    parser.add_argument("--seed", type=int, default=42, help="Random seed (default: 42)")
    parser.add_argument(
        "--output",
        type=str,
        default=str(REPO_ROOT / "data" / "scenarios" / "evaluation_results.json"),
        help="Destination path for benchmark JSON",
    )
    parser.add_argument(
        "--md-output",
        type=str,
        default=str(REPO_ROOT / "docs" / "BENCHMARK_REPORT.md"),
        help="Destination path for benchmark Markdown summary",
    )
    args = parser.parse_args()

    print("=" * 80)
    print(" RECOVERY AUTOPILOT — REVENUE RECOVERY BENCHMARK ")
    print(f" Dataset Size: {args.size} cases | Seed: {args.seed}")
    print("=" * 80)

    report = run_evaluation(dataset_size=args.size, seed=args.seed, output_path=Path(args.output))

    # Generate and save Markdown report
    md_content = generate_markdown_report(report)
    md_path = Path(args.md_output)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(md_content, encoding="utf-8")

    print(f"\nSaved detailed JSON to: {args.output}")
    print(f"Saved Markdown report to: {args.md_output}")
    print("\n--- OVERALL RESULTS ---")
    print(f"Recovery Autopilot Total Recovered:   INR {report.agent_total_inr_recovered:,.2f}")
    print(f"Fixed-Rule Baseline Total Recovered:  INR {report.baseline_total_inr_recovered:,.2f}")
    print(f"Incremental Revenue Lift:             +INR {report.incremental_inr_recovered:,.2f} ({report.incremental_recovery_rate_pct:+.2f} percentage points)")
    print()
    print(f"Recovery Autopilot Success Rate:      {report.agent_recovery_rate:.2f}% (95% CI: [{report.agent_recovery_rate_ci_lower}%, {report.agent_recovery_rate_ci_upper}%])")
    print(f"Fixed-Rule Baseline Success Rate:     {report.baseline_recovery_rate:.2f}% (95% CI: [{report.baseline_recovery_rate_ci_lower}%, {report.baseline_recovery_rate_ci_upper}%])")
    print(f"Median Recovery Time:                 {report.agent_median_recovery_time_hours} hrs vs {report.baseline_median_recovery_time_hours} hrs")
    print(f"Contacts Per Recovered Case:          {report.agent_contacts_per_recovered:.2f} vs {report.baseline_contacts_per_recovered:.2f}")
    print(f"Unnecessary Customer Contacts Saved:  {report.unnecessary_contacts_avoided:,}")
    print(f"Cases Escalated to Human Review:      {report.agent_human_review_rate:.2f}%")
    print(f"Safety Policy Violations:             {report.agent_safety_violations} (Zero Violation Guarantee)")

    print("\n--- PERFORMANCE BY FAILURE CATEGORY ---")
    header = f"{'Category':<28} | {'Cases':<6} | {'Agent %':<8} | {'Base %':<8} | {'Lift %':<8} | {'Agent INR':<14} | {'Base INR':<14}"
    print(header)
    print("-" * len(header))
    for cat in report.category_breakdown:
        print(
            f"{cat.category:<28} | {cat.total_cases:<6} | {cat.agent_recovery_rate:<7.1f}% | "
            f"{cat.baseline_recovery_rate:<7.1f}% | {cat.incremental_rate_pct:<+7.1f}% | "
            f"INR {cat.agent_inr_recovered:<10,.0f} | INR {cat.baseline_inr_recovered:<10,.0f}"
        )
    print("=" * 80)


if __name__ == "__main__":
    main()
