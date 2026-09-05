"""Deterministic Fake Model Provider for testing, fallback, and offline demonstration."""

from typing import Optional

from recovery_autopilot.agents.prompts import (
    PROPOSAL_PROMPT_VERSION,
)
from recovery_autopilot.domain.enums import FailureCategory, RecoveryAction
from recovery_autopilot.domain.models import PaymentCase, RecoveryProposal
from recovery_autopilot.model_providers.base import DiagnosisResult, ModelProvider


class FakeModelProvider(ModelProvider):
    """Deterministic model provider implementing domain heuristics.

    Supports injection modes for testing edge cases (e.g. malformed JSON, timeouts).
    """

    def __init__(
        self,
        provider_name: str = "fake",
        model_identifier: str = "heuristic-mock-v1",
        simulate_error: Optional[str] = None,
        force_low_confidence: bool = False,
    ):
        self.provider_name = provider_name
        self.model_identifier = model_identifier
        self.simulate_error = simulate_error
        self.force_low_confidence = force_low_confidence

    async def diagnose_failure(self, case: PaymentCase) -> DiagnosisResult:
        """Heuristic diagnosis matching payment context attributes."""
        if self.simulate_error == "timeout":
            raise TimeoutError("Simulated model timeout during diagnosis")
        elif self.simulate_error == "provider_down":
            raise ConnectionError("Simulated provider connection failure")

        ctx = case.context
        confidence = 0.45 if self.force_low_confidence else 0.92

        if ctx.failure_category in [FailureCategory.BANK_TIMEOUT, FailureCategory.NETWORK_FAILURE]:
            is_transient = True
            suggested = RecoveryAction.WAIT_FOR_RETRY
            reasoning = f"Transient gateway switch issue detected on {ctx.bank_name or 'issuing bank'}. Retry expected to resolve."
            signals = ["BANK_LATENCY_SPIKE", "INFRASTRUCTURE_GLITCH"]
        elif ctx.failure_category == FailureCategory.EXPIRED_CARD:
            is_transient = False
            suggested = RecoveryAction.REQUEST_METHOD_UPDATE
            reasoning = "Card instrument expiration date has passed. Automated retry will fail; customer update required."
            signals = ["EXPIRED_INSTRUMENT", "NON_RETRYABLE"]
        elif ctx.failure_category == FailureCategory.INSUFFICIENT_FUNDS:
            is_transient = False
            suggested = RecoveryAction.SEND_PAYMENT_LINK
            reasoning = "Account balance insufficient. Direct payment link offers highest recovery rate."
            signals = ["INSUFFICIENT_BALANCE", "CUSTOMER_SETTLEMENT_PREFERRED"]
        elif ctx.failure_category == FailureCategory.UNKNOWN_FAILURE:
            is_transient = False
            suggested = RecoveryAction.HUMAN_REVIEW
            confidence = 0.50
            reasoning = "Unrecognized upstream gateway code. Escalation to human review required."
            signals = ["UNRECOGNIZED_ERROR", "SAFE_ESCALATION"]
        else:
            is_transient = False
            suggested = RecoveryAction.SEND_PAYMENT_LINK
            reasoning = f"Failure category {ctx.failure_category.value} mapped to standard intervention."
            signals = ["STANDARD_ACTION"]

        return DiagnosisResult(
            failure_category=ctx.failure_category,
            confidence=confidence,
            is_transient=is_transient,
            evidence_signals=signals,
            reasoning=reasoning,
            suggested_action=suggested,
        )

    async def propose_recovery(self, case: PaymentCase) -> RecoveryProposal:
        """Heuristic recovery proposal generation."""
        if self.simulate_error == "timeout":
            raise TimeoutError("Simulated model timeout during proposal")
        elif self.simulate_error == "invalid_json":
            raise ValueError("Malformed model JSON output")

        ctx = case.context

        # Opted out -> STOP
        if ctx.opted_out:
            return RecoveryProposal(
                action=RecoveryAction.STOP,
                confidence=1.0,
                delay_minutes=0,
                reason_codes=["CUSTOMER_OPTED_OUT"],
                explanation="Customer previously opted out of recovery communications.",
                requires_human_approval=False,
                model_name=self.model_identifier,
                prompt_version=PROPOSAL_PROMPT_VERSION,
            )

        # High value or Unknown -> HUMAN_REVIEW
        if ctx.amount_inr >= 15000.0 or ctx.failure_category == FailureCategory.UNKNOWN_FAILURE:
            return RecoveryProposal(
                action=RecoveryAction.HUMAN_REVIEW,
                confidence=0.85,
                delay_minutes=0,
                reason_codes=["HIGH_VALUE_THRESHOLD" if ctx.amount_inr >= 15000.0 else "UNKNOWN_FAILURE_ESCALATION"],
                explanation="High-value subscription charge or unrecognized error requires human operations sign-off.",
                requires_human_approval=True,
                model_name=self.model_identifier,
                prompt_version=PROPOSAL_PROMPT_VERSION,
            )

        # Bank timeout or Network failure -> WAIT_FOR_RETRY
        if ctx.failure_category in [FailureCategory.BANK_TIMEOUT, FailureCategory.NETWORK_FAILURE]:
            return RecoveryProposal(
                action=RecoveryAction.WAIT_FOR_RETRY,
                confidence=0.45 if self.force_low_confidence else 0.90,
                delay_minutes=180,  # 3 hours wait
                reason_codes=["TRANSIENT_BANK_TIMEOUT", "ORGANIC_RETRY_RECOMMENDED"],
                explanation="Bank network downtime is transient; scheduled retry avoids unnecessary customer friction.",
                customer_message=None,
                requires_human_approval=False,
                model_name=self.model_identifier,
                prompt_version=PROPOSAL_PROMPT_VERSION,
            )

        # Expired card -> REQUEST_METHOD_UPDATE
        if ctx.failure_category == FailureCategory.EXPIRED_CARD:
            return RecoveryProposal(
                action=RecoveryAction.REQUEST_METHOD_UPDATE,
                confidence=0.45 if self.force_low_confidence else 0.88,
                delay_minutes=30,
                reason_codes=["EXPIRED_CARD_DETECTED", "UPDATE_MANDATE_INSTRUMENT"],
                explanation="Card validity lapsed. Requesting alternate card or UPI mandate.",
                customer_message="Hi! Your subscription card has expired. Please tap here to securely update your payment method.",
                requires_human_approval=False,
                model_name=self.model_identifier,
                prompt_version=PROPOSAL_PROMPT_VERSION,
            )

        # Insufficient funds -> SEND_PAYMENT_LINK
        if ctx.failure_category == FailureCategory.INSUFFICIENT_FUNDS:
            return RecoveryProposal(
                action=RecoveryAction.SEND_PAYMENT_LINK,
                confidence=0.45 if self.force_low_confidence else 0.82,
                delay_minutes=120,
                reason_codes=["INSUFFICIENT_FUNDS", "ON_DEMAND_SETTLEMENT"],
                explanation="Sending an on-demand payment link allows customer to complete payment with any valid instrument.",
                customer_message="Your subscription payment could not be processed. Use this link to complete the payment.",
                requires_human_approval=False,
                model_name=self.model_identifier,
                prompt_version=PROPOSAL_PROMPT_VERSION,
            )

        # Default fallback
        return RecoveryProposal(
            action=RecoveryAction.SEND_PAYMENT_LINK,
            confidence=0.75,
            delay_minutes=60,
            reason_codes=["DEFAULT_RECOVERY_POLICY"],
            explanation="Standard payment link intervention proposed.",
            requires_human_approval=False,
            model_name=self.model_identifier,
            prompt_version=PROPOSAL_PROMPT_VERSION,
        )

    async def draft_customer_message(self, case: PaymentCase, action: RecoveryAction) -> Optional[str]:
        """Generate compliant customer draft message."""
        ctx = case.context
        if action == RecoveryAction.WAIT_FOR_RETRY or action == RecoveryAction.STOP:
            return None
        elif action == RecoveryAction.REQUEST_METHOD_UPDATE:
            return f"Hello {ctx.customer_name}, your subscription card has expired. Please update your payment method to maintain uninterrupted service."
        elif action == RecoveryAction.SEND_PAYMENT_LINK:
            return f"Hello {ctx.customer_name}, your subscription charge of INR {ctx.amount_inr:,.2f} could not be processed. Please complete payment using your secure link."
        elif action == RecoveryAction.SEND_REMINDER:
            return f"Hello {ctx.customer_name}, this is a gentle reminder regarding your subscription payment of INR {ctx.amount_inr:,.2f}."
        return None
