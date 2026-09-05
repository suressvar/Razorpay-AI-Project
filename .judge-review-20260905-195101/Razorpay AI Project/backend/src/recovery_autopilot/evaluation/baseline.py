"""Benchmark baseline strategies for recovery evaluation."""

import random

from recovery_autopilot.domain.enums import FailureCategory, RecoveryAction
from recovery_autopilot.synthetic.scenarios import SyntheticScenario


class FixedRuleBaseline:
    """Fixed-rule baseline: wait 24 hours -> send one reminder -> retry."""

    def __init__(self, contact_limit: int = 1):
        self.name = "Fixed Retry Baseline"
        self.contact_limit = contact_limit

    def decide_action(self, scenario: SyntheticScenario) -> RecoveryAction:
        ctx = scenario.context
        if ctx.opted_out or ctx.previous_contacts >= self.contact_limit:
            return RecoveryAction.STOP
        return RecoveryAction.SEND_REMINDER


class SimpleRuleBaseline:
    """Heuristic rule baseline: maps error category to standard static action."""

    def __init__(self, max_contacts: int = 2):
        self.name = "Simple Rule Baseline"
        self.max_contacts = max_contacts

    def decide_action(self, scenario: SyntheticScenario) -> RecoveryAction:
        ctx = scenario.context
        if ctx.opted_out or ctx.previous_contacts >= self.max_contacts:
            return RecoveryAction.STOP

        if ctx.failure_category == FailureCategory.EXPIRED_CARD:
            return RecoveryAction.SEND_PAYMENT_LINK
        elif ctx.failure_category == FailureCategory.BANK_DOWNTIME:
            return RecoveryAction.RETRY_PAYMENT
        elif ctx.failure_category == FailureCategory.INSUFFICIENT_FUNDS:
            return RecoveryAction.SEND_REMINDER
        elif ctx.failure_category == FailureCategory.MANDATE_DEGRADED:
            return RecoveryAction.SEND_PAYMENT_LINK
        return RecoveryAction.SEND_REMINDER


class RandomActionBaseline:
    """Random baseline: uniformly samples an action from allowed non-stop recovery actions."""

    def __init__(self, seed: int = 42, max_contacts: int = 2):
        self.name = "Random Action Baseline"
        self.rng = random.Random(seed)
        self.max_contacts = max_contacts

    def decide_action(self, scenario: SyntheticScenario) -> RecoveryAction:
        ctx = scenario.context
        if ctx.opted_out or ctx.previous_contacts >= self.max_contacts:
            return RecoveryAction.STOP

        actions = [
            RecoveryAction.SEND_REMINDER,
            RecoveryAction.RETRY_PAYMENT,
            RecoveryAction.SEND_PAYMENT_LINK,
            RecoveryAction.CHANGE_PAYMENT_METHOD,
        ]
        return self.rng.choice(actions)


class OracleUpperLimitBaseline:
    """Simulated theoretical maximum upper bound: executes true ground-truth optimal action."""

    def __init__(self):
        self.name = "Oracle Upper Bound"

    def decide_action(self, scenario: SyntheticScenario) -> RecoveryAction:
        ctx = scenario.context
        if ctx.opted_out or not scenario.true_state.recoverable:
            return RecoveryAction.STOP
        return scenario.true_state.optimal_action
