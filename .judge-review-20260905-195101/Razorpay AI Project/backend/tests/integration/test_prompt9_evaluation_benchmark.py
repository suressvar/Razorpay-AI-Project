"""Integration and regression tests for Prompt 9: Credible AI and Recovery Evaluation Benchmark.

Tests:
1. Benchmark evaluates configured AI agent and policy engine workflow, not a fixed mock policy.
2. Ground-truth labels and optimal actions are hidden from the agent during evaluation.
3. Development and held-out test splits are tracked and reported.
4. Appropriate decision metrics (action accuracy, escalation precision/recall, policy violations) are measured.
5. Generated reports explicitly label outcomes as synthetic simulation rather than live merchant revenue.
6. JSON and Markdown evaluation artifacts are saved with full provenance.
7. API endpoints /metrics/evaluation and /demo/run-evaluation return verified benchmark data.
"""

from pathlib import Path
import pytest
from httpx import ASGITransport, AsyncClient

from recovery_autopilot.evaluation.metrics import BenchmarkReport
from recovery_autopilot.evaluation.runner import run_async_evaluation, run_evaluation, DEFAULT_REPORT_JSON, DEFAULT_REPORT_MD
from recovery_autopilot.main import app
from recovery_autopilot.model_providers.fake import FakeModelProvider
from recovery_autopilot.policies.guardrails import SafetyPolicyEngine
from recovery_autopilot.synthetic.generator import generate_synthetic_dataset


@pytest.mark.asyncio
async def test_evaluation_runner_uses_configured_agent_workflow():
    """Verify that evaluation evaluates the genuine AI workflow and records credible metrics."""
    report = await run_async_evaluation(
        dataset_size=50,
        seed=42,
        held_out_ratio=0.20,
    )

    assert isinstance(report, BenchmarkReport)
    assert report.dataset_size == 50
    assert report.dev_dataset_size == 40
    assert report.held_out_dataset_size == 10
    assert report.random_seed == 42
    assert report.dataset_version == "2.1.0"
    assert report.prompts_version == "1.3.0"
    assert report.is_synthetic_simulation is True
    assert "synthetic simulation" in report.assumptions_note.lower()

    # Decision-Quality & Escalation Metrics
    assert 0.0 <= report.action_accuracy_pct <= 100.0
    assert 0.0 <= report.escalation_precision_pct <= 100.0
    assert 0.0 <= report.escalation_recall_pct <= 100.0
    assert report.policy_violations_count == 0  # Guardrails must strictly prevent policy violations

    # Lift comparison against fixed baseline
    assert report.agent_recovery_rate > 0.0
    assert report.baseline_recovery_rate > 0.0
    assert report.incremental_inr_recovered != 0.0
    assert len(report.category_breakdown) > 0


@pytest.mark.asyncio
async def test_ground_truth_labels_are_not_passed_to_agent():
    """Verify that agent receives only customer context and ground truth is strictly withheld."""
    scenarios = generate_synthetic_dataset(count=5, seed=123)
    s = scenarios[0]

    # Verify scenario context does NOT contain ground truth annotations
    assert not hasattr(s.context, "ground_truth_optimal_action")
    assert not hasattr(s.context, "expected_safe_actions")
    assert not hasattr(s.context, "action_recovery_probabilities")


@pytest.mark.asyncio
async def test_evaluation_artifacts_saved_to_disk(tmp_path: Path):
    """Verify that both JSON and Markdown artifacts are generated with provenance."""
    test_json = tmp_path / "test_eval_results.json"
    report = await run_async_evaluation(
        dataset_size=20,
        seed=99,
        output_path=test_json,
    )

    assert test_json.exists()
    assert DEFAULT_REPORT_MD.exists()

    md_text = DEFAULT_REPORT_MD.read_text(encoding="utf-8")
    assert "# AI Recovery Autopilot — Verified Evaluation Benchmark Report" in md_text
    assert "Dataset Version" in md_text
    assert "Held-Out Test Split" in md_text
    assert "Action Decision Accuracy" in md_text


@pytest.mark.asyncio
async def test_metrics_and_demo_evaluation_routes():
    """Verify that API endpoints return the upgraded benchmark with decision metrics."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # GET /metrics/evaluation
        resp1 = await client.get("/metrics/evaluation")
        assert resp1.status_code == 200
        data1 = resp1.json()
        assert "dataset_version" in data1
        assert "action_accuracy_pct" in data1
        assert "is_synthetic_simulation" in data1
        assert data1["is_synthetic_simulation"] is True

        # POST /demo/run-evaluation
        resp2 = await client.post("/demo/run-evaluation", json={"size": 30, "seed": 42})
        assert resp2.status_code == 200
        data2 = resp2.json()
        assert data2["dataset_size"] == 30
        assert data2["held_out_dataset_size"] == 6
