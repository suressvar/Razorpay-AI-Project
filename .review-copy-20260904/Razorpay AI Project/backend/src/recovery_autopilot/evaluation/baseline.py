"""Fixed-rule recovery strategy baseline for benchmark comparison."""

from recovery_autopilot.domain.enums import RecoveryAction
from recovery_autopilot.synthetic.scenarios import SyntheticScenario


class FixedRuleBaseline:
    """Fixed-rule baseline strategy:

    Wait 24 hours → send one generic reminder → stop after configured limit.
    Note: This represents a naive merchant default strategy, NOT Razorpay's production algorithms.
    """

    def __init__(self, contact_limit: int = 1):
        self.contact_limit = contact_limit

    def decide_action(self, scenario: SyntheticScenario) -> RecoveryAction:
        """Decide next intervention based strictly on fixed rules."""
        context = scenario.context

        # If customer already opted out, stop
        if context.opted_out:
            return RecoveryAction.STOP

        # If already sent the limit of reminders, stop
        if context.previous_contacts >= self.contact_limit:
            return RecoveryAction.STOP

        # Default action: send one generic reminder
        return RecoveryAction.SEND_REMINDER
