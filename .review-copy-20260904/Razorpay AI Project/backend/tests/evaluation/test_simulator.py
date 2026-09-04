"""Unit tests for the outcome simulator."""

from recovery_autopilot.domain.enums import FailureCategory, RecoveryAction
from recovery_autopilot.evaluation.simulator import OutcomeSimulator
from recovery_autopilot.synthetic.generator import generate_synthetic_dataset


def test_simulator_determinism():
    """Simulating the same scenario with the same action must produce deterministic results."""
    scenarios = generate_synthetic_dataset(count=20, seed=42)
    simulator = OutcomeSimulator()

    for s in scenarios:
        res_1 = simulator.simulate(s, RecoveryAction.SEND_PAYMENT_LINK)
        res_2 = simulator.simulate(s, RecoveryAction.SEND_PAYMENT_LINK)

        assert res_1.recovered == res_2.recovered
        assert res_1.recovered_amount == res_2.recovered_amount
        assert res_1.time_to_recovery_hours == res_2.time_to_recovery_hours
        assert res_1.safety_violation_occurred == res_2.safety_violation_occurred


def test_simulator_expired_card_retry_fails():
    """Retrying an expired card must yield 0% probability and failure."""
    scenarios = generate_synthetic_dataset(count=100, seed=42)
    expired_scenarios = [s for s in scenarios if s.context.failure_category == FailureCategory.EXPIRED_CARD]
    assert len(expired_scenarios) > 0

    simulator = OutcomeSimulator()
    for s in expired_scenarios:
        res = simulator.simulate(s, RecoveryAction.WAIT_FOR_RETRY)
        assert res.recovered is False
        assert res.recovered_amount == 0.0


def test_simulator_safety_violation_on_opted_out():
    """Contacting an opted out customer must trigger a safety violation."""
    scenarios = generate_synthetic_dataset(count=200, seed=42)
    opted_out_cases = [s for s in scenarios if s.context.opted_out]
    if not opted_out_cases:
        # Manually create one for testing
        s = scenarios[0].model_copy(deep=True)
        s.context = s.context.model_copy(update={"opted_out": True})
        opted_out_cases = [s]

    simulator = OutcomeSimulator()
    for s in opted_out_cases:
        res = simulator.simulate(s, RecoveryAction.SEND_REMINDER)
        assert res.safety_violation_occurred is True
        assert res.violation_reason == "VIOLATION_CONTACTED_OPTED_OUT_CUSTOMER"
        assert res.recovered is False


def test_simulator_contact_increments():
    """Non-contact actions like WAIT_FOR_RETRY must not increment contacts."""
    scenario = generate_synthetic_dataset(count=1, seed=42)[0]
    initial_contacts = scenario.context.previous_contacts

    simulator = OutcomeSimulator()
    res_wait = simulator.simulate(scenario, RecoveryAction.WAIT_FOR_RETRY)
    assert res_wait.customer_contact_count == initial_contacts

    res_link = simulator.simulate(scenario, RecoveryAction.SEND_PAYMENT_LINK)
    assert res_link.customer_contact_count == initial_contacts + 1
