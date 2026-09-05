"""Deterministic generator for synthetic subscription payment failure datasets."""

import random
from datetime import datetime, timezone
from typing import List

from recovery_autopilot.domain.enums import (
    CustomerSegment,
    FailureCategory,
    PaymentMethod,
    RecoveryAction,
)
from recovery_autopilot.domain.models import PaymentContext
from recovery_autopilot.synthetic.scenarios import SyntheticScenario

SYNTHETIC_FIRST_NAMES = [
    "Aarav", "Vivaan", "Aditya", "Vihaan", "Arjun", "Sai", "Reyansh", "Ayaan", "Krishna", "Ishaan",
    "Diya", "Saanvi", "Ananya", "Aadhya", "Pari", "Chiara", "Myra", "Riya", "Anvi", "Sneha",
    "Rohan", "Vikram", "Neha", "Pooja", "Karan", "Simran", "Meera", "Siddharth", "Tanvi", "Rahul"
]

SYNTHETIC_LAST_NAMES = [
    "Sharma", "Verma", "Patel", "Mehta", "Reddy", "Nair", "Iyer", "Choudhury", "Gupta", "Malhotra",
    "Bhat", "Deshmukh", "Joshi", "Kulkarni", "Singh", "Das", "Menon", "Pillai", "Rao", "Kapoor"
]

BANKS = ["HDFC", "ICICI", "SBI", "AXIS", "KOTAK", "YES_BANK", "CITI", "PNB"]

CATEGORY_WEIGHTS = {
    FailureCategory.INSUFFICIENT_FUNDS: 0.28,
    FailureCategory.BANK_TIMEOUT: 0.18,
    FailureCategory.EXPIRED_CARD: 0.14,
    FailureCategory.MANDATE_REVOKED: 0.10,
    FailureCategory.LIMIT_EXCEEDED: 0.10,
    FailureCategory.NETWORK_FAILURE: 0.10,
    FailureCategory.CUSTOMER_ACTION_REQUIRED: 0.06,
    FailureCategory.UNKNOWN_FAILURE: 0.04,
}

GATEWAY_ERRORS = {
    FailureCategory.INSUFFICIENT_FUNDS: ("BAD_REQUEST_PAYMENT_FAILED", "Insufficient funds in customer account"),
    FailureCategory.BANK_TIMEOUT: ("GATEWAY_TIMEOUT", "Issuing bank processing timed out after 30s"),
    FailureCategory.EXPIRED_CARD: ("EXPIRED_CARD_INSTRUMENT", "Card expiry date has lapsed"),
    FailureCategory.MANDATE_REVOKED: ("MANDATE_CANCELLED_BY_USER", "Standing mandate revoked by customer"),
    FailureCategory.LIMIT_EXCEEDED: ("CARD_VELOCITY_LIMIT_EXCEEDED", "Daily transaction limit exceeded for card"),
    FailureCategory.NETWORK_FAILURE: ("NETWORK_COMMUNICATION_ERROR", "TLS handshake failure with issuing switch"),
    FailureCategory.CUSTOMER_ACTION_REQUIRED: ("ACTION_REQUIRED_OTP", "Mandate renewal requires customer authentication"),
    FailureCategory.UNKNOWN_FAILURE: ("INTERNAL_GATEWAY_ERROR_999", "Unrecognized upstream bank response"),
}


def compute_simulation_probabilities(
    category: FailureCategory,
    amount_inr: float,
    previous_contacts: int,
    bank_degraded: bool,
    salary_day_near: bool,
    payment_method: PaymentMethod,
) -> dict[str, float]:
    """Calculate transparent ground-truth recovery probabilities for each permitted action."""
    probs: dict[str, float] = {}

    if category == FailureCategory.INSUFFICIENT_FUNDS:
        # If salary day is near, waiting or delayed payment link recovers best
        base_link = 0.72 if salary_day_near else 0.58
        base_wait = 0.65 if salary_day_near else 0.35
        base_reminder = 0.40
        base_method = 0.45
        probs[RecoveryAction.SEND_PAYMENT_LINK.value] = min(0.92, base_link)
        probs[RecoveryAction.WAIT_FOR_RETRY.value] = min(0.90, base_wait)
        probs[RecoveryAction.SEND_REMINDER.value] = min(0.70, base_reminder)
        probs[RecoveryAction.REQUEST_METHOD_UPDATE.value] = min(0.75, base_method)
        probs[RecoveryAction.HUMAN_REVIEW.value] = 0.60
        probs[RecoveryAction.STOP.value] = 0.0

    elif category == FailureCategory.BANK_TIMEOUT:
        # Bank timeout resolves automatically if we wait for retry
        probs[RecoveryAction.WAIT_FOR_RETRY.value] = 0.88
        probs[RecoveryAction.SEND_PAYMENT_LINK.value] = 0.70  # Works, but creates unnecessary contact
        probs[RecoveryAction.SEND_REMINDER.value] = 0.35
        probs[RecoveryAction.REQUEST_METHOD_UPDATE.value] = 0.20
        probs[RecoveryAction.HUMAN_REVIEW.value] = 0.75
        probs[RecoveryAction.STOP.value] = 0.0

    elif category == FailureCategory.EXPIRED_CARD:
        # Retrying or waiting will NEVER work for an expired card!
        probs[RecoveryAction.REQUEST_METHOD_UPDATE.value] = 0.74
        probs[RecoveryAction.SEND_PAYMENT_LINK.value] = 0.52
        probs[RecoveryAction.SEND_REMINDER.value] = 0.22
        probs[RecoveryAction.WAIT_FOR_RETRY.value] = 0.00  # Impossible to recover by retrying
        probs[RecoveryAction.HUMAN_REVIEW.value] = 0.65
        probs[RecoveryAction.STOP.value] = 0.0

    elif category == FailureCategory.MANDATE_REVOKED:
        # Retrying fails; customer needs a new payment link or method update
        probs[RecoveryAction.SEND_PAYMENT_LINK.value] = 0.68
        probs[RecoveryAction.REQUEST_METHOD_UPDATE.value] = 0.62
        probs[RecoveryAction.SEND_REMINDER.value] = 0.25
        probs[RecoveryAction.WAIT_FOR_RETRY.value] = 0.00
        probs[RecoveryAction.HUMAN_REVIEW.value] = 0.60
        probs[RecoveryAction.STOP.value] = 0.0

    elif category == FailureCategory.LIMIT_EXCEEDED:
        # Waiting for limit reset (24h) or sending payment link with alternative instrument
        probs[RecoveryAction.WAIT_FOR_RETRY.value] = 0.65
        probs[RecoveryAction.SEND_PAYMENT_LINK.value] = 0.70
        probs[RecoveryAction.REQUEST_METHOD_UPDATE.value] = 0.60
        probs[RecoveryAction.SEND_REMINDER.value] = 0.30
        probs[RecoveryAction.HUMAN_REVIEW.value] = 0.65
        probs[RecoveryAction.STOP.value] = 0.0

    elif category == FailureCategory.NETWORK_FAILURE:
        # Transient network issues resolve quickly with a wait
        probs[RecoveryAction.WAIT_FOR_RETRY.value] = 0.86
        probs[RecoveryAction.SEND_PAYMENT_LINK.value] = 0.68
        probs[RecoveryAction.SEND_REMINDER.value] = 0.30
        probs[RecoveryAction.REQUEST_METHOD_UPDATE.value] = 0.25
        probs[RecoveryAction.HUMAN_REVIEW.value] = 0.70
        probs[RecoveryAction.STOP.value] = 0.0

    elif category == FailureCategory.CUSTOMER_ACTION_REQUIRED:
        # Customer action required: payment link enables 3DS OTP verification
        probs[RecoveryAction.SEND_PAYMENT_LINK.value] = 0.78
        probs[RecoveryAction.REQUEST_METHOD_UPDATE.value] = 0.55
        probs[RecoveryAction.SEND_REMINDER.value] = 0.40
        probs[RecoveryAction.WAIT_FOR_RETRY.value] = 0.05
        probs[RecoveryAction.HUMAN_REVIEW.value] = 0.65
        probs[RecoveryAction.STOP.value] = 0.0

    else:  # UNKNOWN_FAILURE
        # Unknown failures are unpredictable: human review is the safest intervention
        probs[RecoveryAction.HUMAN_REVIEW.value] = 0.60
        probs[RecoveryAction.SEND_PAYMENT_LINK.value] = 0.35
        probs[RecoveryAction.WAIT_FOR_RETRY.value] = 0.20
        probs[RecoveryAction.SEND_REMINDER.value] = 0.15
        probs[RecoveryAction.REQUEST_METHOD_UPDATE.value] = 0.25
        probs[RecoveryAction.STOP.value] = 0.0

    # Contact fatigue penalty: each previous contact reduces response probability by 8%
    penalty = max(0.0, previous_contacts * 0.08)
    for act in [
        RecoveryAction.SEND_PAYMENT_LINK.value,
        RecoveryAction.REQUEST_METHOD_UPDATE.value,
        RecoveryAction.SEND_REMINDER.value,
    ]:
        probs[act] = max(0.05, probs[act] - penalty)

    return probs


def generate_synthetic_dataset(count: int = 500, seed: int = 42) -> List[SyntheticScenario]:
    """Generate a deterministic synthetic dataset of subscription payment failure scenarios."""
    rng = random.Random(seed)
    categories = list(CATEGORY_WEIGHTS.keys())
    weights = list(CATEGORY_WEIGHTS.values())

    scenarios: List[SyntheticScenario] = []

    for idx in range(1, count + 1):
        category = rng.choices(categories, weights=weights, k=1)[0]
        first_name = rng.choice(SYNTHETIC_FIRST_NAMES)
        last_name = rng.choice(SYNTHETIC_LAST_NAMES)
        full_name = f"Test {first_name} {last_name}"
        email = f"user_{idx:04d}@synthetic-test.example.com"
        phone = f"+9198000{idx:05d}"
        cust_id = f"cust_syn_{idx:05d}"
        pay_id = f"pay_syn_{idx:05d}"
        sub_id = f"sub_syn_{idx:05d}"
        inv_id = f"inv_syn_{idx:05d}"

        # Segment distribution: 50% SMB, 25% Starter, 15% Growth, 10% Enterprise
        segment = rng.choices(
            [CustomerSegment.STARTER, CustomerSegment.SMB, CustomerSegment.GROWTH, CustomerSegment.ENTERPRISE],
            weights=[0.25, 0.50, 0.15, 0.10],
            k=1,
        )[0]

        # Subscription Amount in INR (proportional to segment)
        if segment == CustomerSegment.STARTER:
            amount = round(rng.uniform(499.0, 1999.0), 2)
        elif segment == CustomerSegment.SMB:
            amount = round(rng.uniform(2499.0, 7999.0), 2)
        elif segment == CustomerSegment.GROWTH:
            amount = round(rng.uniform(8999.0, 14999.0), 2)
        else:  # ENTERPRISE
            amount = round(rng.uniform(15000.0, 48000.0), 2)

        # Payment method distribution
        method = rng.choices(
            [PaymentMethod.CARD, PaymentMethod.UPI, PaymentMethod.NETBANKING, PaymentMethod.NACH],
            weights=[0.55, 0.30, 0.10, 0.05],
            k=1,
        )[0]

        prev_failures = rng.choices([1, 2, 3], weights=[0.65, 0.25, 0.10], k=1)[0]
        prev_contacts = rng.choices([0, 1, 2], weights=[0.70, 0.20, 0.10], k=1)[0]

        bank = rng.choice(BANKS)
        bank_degraded = (category in [FailureCategory.BANK_TIMEOUT, FailureCategory.NETWORK_FAILURE]) and (rng.random() < 0.65)
        opted_out = rng.random() < 0.02  # 2% opt-out rate

        err_code, err_reason = GATEWAY_ERRORS[category]

        hour_of_day = rng.randint(0, 23)
        day_of_week = rng.randint(0, 6)
        day_of_month = rng.randint(1, 28)
        salary_day_near = day_of_month in [1, 2, 3, 4, 5, 29, 30, 31]

        context = PaymentContext(
            payment_id=pay_id,
            subscription_id=sub_id,
            invoice_id=inv_id,
            customer_id=cust_id,
            customer_name=full_name,
            customer_email=email,
            customer_phone=phone,
            amount_inr=amount,
            currency="INR",
            failure_category=category,
            failure_code=err_code,
            failure_reason=err_reason,
            payment_method=method,
            customer_segment=segment,
            previous_failures=prev_failures,
            previous_contacts=prev_contacts,
            bank_name=bank,
            bank_degraded=bank_degraded,
            opted_out=opted_out,
            occurred_at=datetime(2026, 9, day_of_month, hour_of_day, 15, tzinfo=timezone.utc),
        )

        probs = compute_simulation_probabilities(
            category=category,
            amount_inr=amount,
            previous_contacts=prev_contacts,
            bank_degraded=bank_degraded,
            salary_day_near=salary_day_near,
            payment_method=method,
        )

        # Determine optimal action
        optimal_action = max(
            [a for a in RecoveryAction if a != RecoveryAction.STOP],
            key=lambda act: probs.get(act.value, 0.0),
        )

        # Expected safe interventions
        safe_actions: List[RecoveryAction] = []
        if category in [FailureCategory.BANK_TIMEOUT, FailureCategory.NETWORK_FAILURE]:
            safe_actions = [RecoveryAction.WAIT_FOR_RETRY, RecoveryAction.HUMAN_REVIEW]
        elif category == FailureCategory.EXPIRED_CARD:
            safe_actions = [RecoveryAction.REQUEST_METHOD_UPDATE, RecoveryAction.SEND_PAYMENT_LINK, RecoveryAction.HUMAN_REVIEW]
        elif category == FailureCategory.INSUFFICIENT_FUNDS:
            safe_actions = [RecoveryAction.WAIT_FOR_RETRY, RecoveryAction.SEND_PAYMENT_LINK, RecoveryAction.SEND_REMINDER, RecoveryAction.HUMAN_REVIEW]
        elif category == FailureCategory.UNKNOWN_FAILURE:
            safe_actions = [RecoveryAction.HUMAN_REVIEW]
        else:
            safe_actions = [RecoveryAction.SEND_PAYMENT_LINK, RecoveryAction.REQUEST_METHOD_UPDATE, RecoveryAction.HUMAN_REVIEW]

        scenario = SyntheticScenario(
            scenario_id=f"scn_{idx:04d}",
            context=context,
            expected_safe_actions=safe_actions,
            action_recovery_probabilities=probs,
            salary_day_near=salary_day_near,
            hour_of_day=hour_of_day,
            day_of_week=day_of_week,
            ground_truth_optimal_action=optimal_action,
            description=f"Synthetic scenario {idx}: {category.value} on {method.value} for {segment.value} customer.",
        )
        scenarios.append(scenario)

    return scenarios
