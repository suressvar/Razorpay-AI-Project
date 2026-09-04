"""Unit tests for synthetic dataset generation."""

from recovery_autopilot.domain.enums import FailureCategory
from recovery_autopilot.synthetic.generator import generate_synthetic_dataset


def test_dataset_reproducibility():
    """Identical seeds must yield exact identical scenario outputs."""
    set_a = generate_synthetic_dataset(count=50, seed=42)
    set_b = generate_synthetic_dataset(count=50, seed=42)

    assert len(set_a) == 50
    assert len(set_b) == 50

    for a, b in zip(set_a, set_b):
        assert a.scenario_id == b.scenario_id
        assert a.context.customer_email == b.context.customer_email
        assert a.context.amount_inr == b.context.amount_inr
        assert a.context.failure_category == b.context.failure_category
        assert a.action_recovery_probabilities == b.action_recovery_probabilities


def test_dataset_seed_variance():
    """Different seeds must produce different scenario sequences."""
    set_a = generate_synthetic_dataset(count=50, seed=42)
    set_b = generate_synthetic_dataset(count=50, seed=999)

    # Scenarios should differ
    emails_a = [s.context.customer_email for s in set_a]
    emails_b = [s.context.customer_email for s in set_b]
    assert emails_a != emails_b or set_a[0].context.amount_inr != set_b[0].context.amount_inr


def test_dataset_category_coverage():
    """A 500-case dataset must cover every defined FailureCategory."""
    scenarios = generate_synthetic_dataset(count=500, seed=42)
    categories = {s.context.failure_category for s in scenarios}
    for cat in FailureCategory:
        assert cat in categories, f"Missing category: {cat}"


def test_dataset_synthetic_pii_compliance():
    """All customer identifiers and contacts must be strictly synthetic placeholders."""
    scenarios = generate_synthetic_dataset(count=100, seed=42)
    for s in scenarios:
        assert s.context.customer_email.endswith("@synthetic-test.example.com")
        assert s.context.customer_phone.startswith("+9198000")
        assert s.context.customer_name.startswith("Test ")
        assert s.context.amount_inr > 0
