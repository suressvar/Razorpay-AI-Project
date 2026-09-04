"""Deterministic safety rules and check codes for payment recovery."""

from dataclasses import dataclass
from typing import Optional

from recovery_autopilot.domain.enums import FailureCategory, RecoveryAction
from recovery_autopilot.domain.models import PaymentCase, RecoveryProposal


@dataclass
class RuleEvaluationResult:
    """Outcome of evaluating a single safety rule."""

    passed: bool
    rule_code: str
    message: str
    mandate_human_review: bool = False
    override_action: Optional[RecoveryAction] = None
    override_delay_minutes: Optional[int] = None


class SafetyRule:
    """Abstract base class for deterministic safety rules."""

    def evaluate(self, case: PaymentCase, proposal: RecoveryProposal) -> RuleEvaluationResult:
        raise NotImplementedError


class OptOutRule(SafetyRule):
    """If customer opted out, forbid any communication or recovery action; force STOP."""

    def evaluate(self, case: PaymentCase, proposal: RecoveryProposal) -> RuleEvaluationResult:
        if case.context.opted_out:
            return RuleEvaluationResult(
                passed=False,
                rule_code="RULE_CUSTOMER_OPTED_OUT",
                message="Customer previously opted out of recovery interventions.",
                override_action=RecoveryAction.STOP,
            )
        return RuleEvaluationResult(passed=True, rule_code="RULE_CUSTOMER_OPTED_OUT", message="Customer has not opted out.")


class MaxAttemptsRule(SafetyRule):
    """Enforce absolute contact attempt limit."""

    def __init__(self, max_attempts: int = 3):
        self.max_attempts = max_attempts

    def evaluate(self, case: PaymentCase, proposal: RecoveryProposal) -> RuleEvaluationResult:
        contact_actions = {
            RecoveryAction.SEND_PAYMENT_LINK,
            RecoveryAction.REQUEST_METHOD_UPDATE,
            RecoveryAction.SEND_REMINDER,
        }
        if proposal.action in contact_actions and case.contact_count >= self.max_attempts:
            return RuleEvaluationResult(
                passed=False,
                rule_code="RULE_MAX_ATTEMPTS_EXCEEDED",
                message=f"Contact ceiling reached ({case.contact_count}/{self.max_attempts}). Further contact prohibited.",
                override_action=RecoveryAction.STOP,
            )
        return RuleEvaluationResult(passed=True, rule_code="RULE_MAX_ATTEMPTS_EXCEEDED", message="Within attempt ceiling.")


class HighValueThresholdRule(SafetyRule):
    """Mandate human operator approval for amounts exceeding the high-value ceiling."""

    def __init__(self, threshold_inr: float = 15000.0):
        self.threshold_inr = threshold_inr

    def evaluate(self, case: PaymentCase, proposal: RecoveryProposal) -> RuleEvaluationResult:
        if case.context.amount_inr >= self.threshold_inr:
            return RuleEvaluationResult(
                passed=True,
                rule_code="RULE_HIGH_VALUE_THRESHOLD",
                message=f"Amount INR {case.context.amount_inr:,.2f} >= threshold INR {self.threshold_inr:,.2f}; human review required.",
                mandate_human_review=True,
            )
        return RuleEvaluationResult(passed=True, rule_code="RULE_HIGH_VALUE_THRESHOLD", message="Amount below high-value ceiling.")


class UnknownFailureCategoryRule(SafetyRule):
    """Unknown failure categories must not execute automated customer interventions."""

    def evaluate(self, case: PaymentCase, proposal: RecoveryProposal) -> RuleEvaluationResult:
        if case.context.failure_category == FailureCategory.UNKNOWN_FAILURE:
            return RuleEvaluationResult(
                passed=True,
                rule_code="RULE_UNKNOWN_FAILURE_CATEGORY",
                message="Unknown failure category detected; human review required before any customer contact.",
                mandate_human_review=True,
                override_action=RecoveryAction.HUMAN_REVIEW,
            )
        return RuleEvaluationResult(passed=True, rule_code="RULE_UNKNOWN_FAILURE_CATEGORY", message="Category recognized.")


class LowConfidenceRule(SafetyRule):
    """Model proposals with confidence below threshold mandate human review."""

    def __init__(self, min_confidence: float = 0.70):
        self.min_confidence = min_confidence

    def evaluate(self, case: PaymentCase, proposal: RecoveryProposal) -> RuleEvaluationResult:
        if proposal.confidence < self.min_confidence:
            return RuleEvaluationResult(
                passed=True,
                rule_code="RULE_LOW_CONFIDENCE",
                message=f"Model confidence {proposal.confidence:.2f} < threshold {self.min_confidence:.2f}; human review mandated.",
                mandate_human_review=True,
            )
        return RuleEvaluationResult(passed=True, rule_code="RULE_LOW_CONFIDENCE", message="Confidence meets threshold.")


class ProhibitRetryOnExpiredCardRule(SafetyRule):
    """Retrying an expired card is mathematically invalid and creates friction."""

    def evaluate(self, case: PaymentCase, proposal: RecoveryProposal) -> RuleEvaluationResult:
        if case.context.failure_category == FailureCategory.EXPIRED_CARD and proposal.action == RecoveryAction.WAIT_FOR_RETRY:
            return RuleEvaluationResult(
                passed=False,
                rule_code="RULE_EXPIRED_CARD_NO_RETRY",
                message="Cannot retry an expired card. Overriding to REQUEST_METHOD_UPDATE.",
                override_action=RecoveryAction.REQUEST_METHOD_UPDATE,
            )
        return RuleEvaluationResult(passed=True, rule_code="RULE_EXPIRED_CARD_NO_RETRY", message="Card rule satisfied.")
