"""Deterministic outcome simulator for recovery interventions."""

import hashlib
from typing import Optional

from pydantic import BaseModel

from recovery_autopilot.domain.enums import FailureCategory, RecoveryAction
from recovery_autopilot.synthetic.scenarios import SyntheticScenario


class SimulationResult(BaseModel):
    """Result of simulating an intervention on a synthetic payment failure scenario."""

    scenario_id: str
    action_attempted: RecoveryAction
    recovered: bool
    recovered_amount: float
    time_to_recovery_hours: float
    customer_contact_count: int
    human_review_needed: bool
    safety_violation_occurred: bool
    violation_reason: Optional[str] = None
    probability_applied: float


class OutcomeSimulator:
    """Deterministic, assumption-transparent outcome simulator."""

    def __init__(self, human_review_threshold_inr: float = 15000.0, max_contacts_limit: int = 3):
        self.human_review_threshold_inr = human_review_threshold_inr
        self.max_contacts_limit = max_contacts_limit

    def simulate(self, scenario: SyntheticScenario, action: RecoveryAction) -> SimulationResult:
        """Simulate the resolution of a scenario given an intervention action."""
        context = scenario.context

        # 1. Safety Violation Checks (Prioritized)
        safety_violation = False
        violation_reason: Optional[str] = None

        contact_actions = {
            RecoveryAction.SEND_PAYMENT_LINK,
            RecoveryAction.REQUEST_METHOD_UPDATE,
            RecoveryAction.SEND_REMINDER,
        }

        if action in contact_actions:
            if context.opted_out:
                safety_violation = True
                violation_reason = "VIOLATION_CONTACTED_OPTED_OUT_CUSTOMER"
            elif context.previous_contacts >= self.max_contacts_limit:
                safety_violation = True
                violation_reason = "VIOLATION_EXCEEDED_MAX_CONTACT_ATTEMPTS"
            elif context.amount_inr >= self.human_review_threshold_inr:
                safety_violation = True
                violation_reason = "VIOLATION_HIGH_VALUE_WITHOUT_HUMAN_APPROVAL"
            elif context.failure_category == FailureCategory.UNKNOWN_FAILURE:
                safety_violation = True
                violation_reason = "VIOLATION_AUTOMATED_ACTION_ON_UNKNOWN_FAILURE"

        # 2. Contact Count Increment
        contacts_added = 1 if action in contact_actions else 0
        total_contacts = context.previous_contacts + contacts_added

        # 3. Determine Recovery Probability
        raw_prob = scenario.action_recovery_probabilities.get(action.value, 0.0)

        # If safety violation occurred, recovery fails due to customer friction/rejection
        if safety_violation:
            raw_prob = 0.0

        # If opted out, recovery is 0 unless resolved organically via retry
        if context.opted_out and action != RecoveryAction.WAIT_FOR_RETRY:
            raw_prob = 0.0

        # Deterministic pseudo-random resolution based on hash of (scenario_id + action.value)
        hash_digest = hashlib.sha256(f"{scenario.scenario_id}:{action.value}".encode()).hexdigest()
        normalized_rand = int(hash_digest[:8], 16) / 0xFFFFFFFF

        recovered = normalized_rand < raw_prob
        recovered_amount = context.amount_inr if recovered else 0.0

        # 4. Time to recovery estimation
        time_to_recovery = 0.0
        if recovered:
            if action == RecoveryAction.WAIT_FOR_RETRY:
                time_to_recovery = 4.0
            elif action == RecoveryAction.SEND_PAYMENT_LINK:
                time_to_recovery = 8.5
            elif action == RecoveryAction.REQUEST_METHOD_UPDATE:
                time_to_recovery = 18.0
            elif action == RecoveryAction.SEND_REMINDER:
                time_to_recovery = 22.0
            elif action == RecoveryAction.HUMAN_REVIEW:
                time_to_recovery = 12.0
        else:
            time_to_recovery = 72.0  # Terminal failure after 72h window

        human_review_needed = (
            action == RecoveryAction.HUMAN_REVIEW
            or context.amount_inr >= self.human_review_threshold_inr
            or context.failure_category == FailureCategory.UNKNOWN_FAILURE
        )

        return SimulationResult(
            scenario_id=scenario.scenario_id,
            action_attempted=action,
            recovered=recovered,
            recovered_amount=recovered_amount,
            time_to_recovery_hours=round(time_to_recovery, 1),
            customer_contact_count=total_contacts,
            human_review_needed=human_review_needed,
            safety_violation_occurred=safety_violation,
            violation_reason=violation_reason,
            probability_applied=round(raw_prob, 4),
        )
