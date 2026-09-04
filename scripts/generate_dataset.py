#!/usr/bin/env python3
"""Script to generate synthetic subscription payment failure dataset."""

import argparse
import json
import sys
from pathlib import Path

# Ensure backend/src is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend" / "src"))

from recovery_autopilot.synthetic.generator import generate_synthetic_dataset


def main():
    parser = argparse.ArgumentParser(description="Generate synthetic subscription recovery dataset")
    parser.add_argument("--count", type=int, default=500, help="Number of scenarios to generate (default: 500)")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for deterministic generation (default: 42)")
    parser.add_argument(
        "--output",
        type=str,
        default=str(REPO_ROOT / "data" / "scenarios" / "synthetic_cases_500.json"),
        help="Destination path for JSON dataset",
    )
    args = parser.parse_args()

    print(f"Generating {args.count} synthetic scenarios with seed={args.seed}...")
    scenarios = generate_synthetic_dataset(count=args.count, seed=args.seed)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    data = [s.model_dump(mode="json") for s in scenarios]
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    print(f"Successfully generated {len(scenarios)} cases and saved to: {output_path}")

    # Print summary of categories
    from collections import Counter
    counts = Counter(s.context.failure_category.value for s in scenarios)
    print("\nCategory Distribution:")
    for cat, cnt in counts.most_common():
        pct = (cnt / len(scenarios)) * 100
        print(f"  - {cat:30s}: {cnt:3d} cases ({pct:.1f}%)")


if __name__ == "__main__":
    main()
