"""Deterministic safety policy engine evaluating AI proposals."""

from typing import List

from recovery_autopilot.config import Settings
from recovery_autopilot.config import settings as global_settings
from recovery_autopilot.domain.enums import RecoveryAction
from recovery_autopilot.domain.models import PaymentCase, PolicyDecision, RecoveryProposal
from recovery_autopilot.policies.rules import (
    HighValueThresholdRule,
    LowConfidenceRule,
    MaxAttemptsRule,
    OptOutRule,
    ProhibitRetryOnExpiredCardRule,
    SafetyRule,
    UnknownFailureCategoryRule,
)


class SafetyPolicyEngine:
    """Evaluates an AI RecoveryProposal against deterministic business guardrails.

    Core Invariant:
    The AI proposes; this deterministic policy engine decides.
    """

    def __init__(self, settings: Settings = global_settings, custom_rules: List[SafetyRule] | None = None):
        self.settings = settings
        if custom_rules is not None:
            self.rules = custom_rules
        else:
            self.rules = [
                OptOutRule(),
                MaxAttemptsRule(max_attempts=settings.MAX_CONTACT_ATTEMPTS),
                HighValueThresholdRule(threshold_inr=settings.HUMAN_REVIEW_THRESHOLD_INR),
                UnknownFailureCategoryRule(),
                LowConfidenceRule(min_confidence=settings.MIN_CONFIDENCE_THRESHOLD),
                ProhibitRetryOnExpiredCardRule(),
            ]

    def evaluate(self, case: PaymentCase, proposal: RecoveryProposal) -> PolicyDecision:
        """Run all deterministic rules on proposal and produce an immutable PolicyDecision."""
        allowed = True
        approved_action = proposal.action
        modified_delay = proposal.delay_minutes
        requires_human_review = proposal.requires_human_approval
        collected_reason_codes: List[str] = list(proposal.reason_codes)
        block_reasons: List[str] = []

        for rule in self.rules:
            res = rule.evaluate(case, proposal)
            if not res.passed:
                allowed = False
                block_reasons.append(f"[{res.rule_code}] {res.message}")
                collected_reason_codes.append(res.rule_code)
                if res.override_action:
                    approved_action = res.override_action
            if res.mandate_human_review:
                requires_human_review = True
                collected_reason_codes.append(res.rule_code)
            if res.override_action and res.passed:
                approved_action = res.override_action

        # If human review is mandated, the effective action held is HUMAN_REVIEW
        if requires_human_review and approved_action != RecoveryAction.STOP:
            allowed = False  # Held pending human approval
            block_reasons.append("Mandatory human review triggered by safety policy threshold.")

        block_reason_str = " | ".join(block_reasons) if block_reasons else None

        return PolicyDecision(
            case_id=case.case_id,
            allowed=allowed,
            approved_action=approved_action,
            modified_delay_minutes=modified_delay,
            reason_codes=list(set(collected_reason_codes)),
            requires_human_review=requires_human_review,
            block_reason=block_reason_str,
        )
