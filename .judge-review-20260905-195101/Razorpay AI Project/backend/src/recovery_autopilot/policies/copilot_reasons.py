"""Configurable mapping of Razorpay payment failure reasons to plain-language explanations,
reversal timelines, resolution paths, and recommendations for AI Copilot.
"""

from typing import Dict, List, Optional

from recovery_autopilot.domain.enums import FailureCategory


class FailureReasonDetail:
    """Config item for a specific failure type."""

    def __init__(
        self,
        headline_template: str,
        explanation: str,
        auto_reversal_timeline: Optional[str],
        resolution_name: str,
        resolution_instruction: str,
        recommendation: str,
        default_followups: List[str],
    ):
        self.headline_template = headline_template
        self.explanation = explanation
        self.auto_reversal_timeline = auto_reversal_timeline
        self.resolution_name = resolution_name
        self.resolution_instruction = resolution_instruction
        self.recommendation = recommendation
        self.default_followups = default_followups


# Comprehensive mapping by FailureCategory
COPILOT_REASON_CATALOG: Dict[FailureCategory, FailureReasonDetail] = {
    FailureCategory.BANK_TIMEOUT: FailureReasonDetail(
        headline_template="{customer}'s ₹{amount} payment didn't go through due to a bank connection timeout.",
        explanation="The issuing bank's gateway took too long to acknowledge the transaction, resulting in a network timeout. The subscription mandate could not be executed.",
        auto_reversal_timeline="If the amount was debited from the customer's account, it will be automatically reversed by their bank within 2 business days.",
        resolution_name="Ask for a Retry or Payment Link",
        resolution_instruction="Ask the customer to retry with a different network or payment method, or generate an instant payment link.",
        recommendation="Create a fresh payment link and share it directly with the customer to complete the payment.",
        default_followups=[
            "Create a payment link for {customer}",
            "What happens to the failed amount?",
            "Analyse all my failed payments",
        ],
    ),
    FailureCategory.INSUFFICIENT_FUNDS: FailureReasonDetail(
        headline_template="{customer}'s ₹{amount} payment failed due to insufficient account balance.",
        explanation="The transaction was declined because the customer's linked bank account or card did not have enough available balance at the time of charge.",
        auto_reversal_timeline=None,
        resolution_name="Payment Link or Scheduled Retry",
        resolution_instruction="Send a direct payment link or wait for the customer's typical salary deposit window to trigger an automated retry.",
        recommendation="Create and send a payment link with flexible payment methods (UPI, Cards, NetBanking).",
        default_followups=[
            "Create a payment link for {customer}",
            "When is the best time to retry?",
            "View customer retry history",
        ],
    ),
    FailureCategory.EXPIRED_CARD: FailureReasonDetail(
        headline_template="{customer}'s ₹{amount} payment failed because their registered card has expired.",
        explanation="The card expiry date registered with the recurring subscription has passed. Razorpay safety policy blocks automatic retries on expired cards to prevent charge penalties.",
        auto_reversal_timeline=None,
        resolution_name="Request Updated Payment Method",
        resolution_instruction="Send a payment link that allows the customer to pay and update their card details for future billing cycles.",
        recommendation="Create a payment link so {customer} can securely authenticate a fresh card or switch to UPI.",
        default_followups=[
            "Create a payment link for {customer}",
            "How do I update customer card details?",
            "Analyse all my failed payments",
        ],
    ),
    FailureCategory.MANDATE_REVOKED: FailureReasonDetail(
        headline_template="{customer}'s ₹{amount} recurring mandate was cancelled or paused.",
        explanation="The customer or their bank revoked the auto-debit standing instruction. Automated recurring charges will no longer succeed for this subscription.",
        auto_reversal_timeline=None,
        resolution_name="New Mandate or Manual Payment Link",
        resolution_instruction="Contact the customer to re-authorize the mandate or send an ad-hoc payment link to cover this billing period.",
        recommendation="Send a payment link for immediate dues and prompt the customer to authorize a new e-mandate.",
        default_followups=[
            "Create a payment link for {customer}",
            "Why was the mandate revoked?",
            "Analyse all my failed payments",
        ],
    ),
    FailureCategory.LIMIT_EXCEEDED: FailureReasonDetail(
        headline_template="{customer}'s ₹{amount} payment failed due to card velocity or transaction limits.",
        explanation="The card issuer declined the payment because it exceeded the customer's daily online transaction limit or card velocity restriction.",
        auto_reversal_timeline="No funds were deducted from the customer's account.",
        resolution_name="Alternative Payment Mode or Retry",
        resolution_instruction="Ask customer to temporarily raise their card limit in their banking app or pay via UPI/Netbanking.",
        recommendation="Create a payment link offering alternative payment methods like UPI or NetBanking.",
        default_followups=[
            "Create a payment link for {customer}",
            "What payment methods are supported?",
            "Analyse all my failed payments",
        ],
    ),
    FailureCategory.NETWORK_FAILURE: FailureReasonDetail(
        headline_template="{customer}'s ₹{amount} payment encountered a banking switch communication failure.",
        explanation="A temporary communication breakdown occurred between the payment gateway and the card network (Visa/Mastercard/NPCI).",
        auto_reversal_timeline="If debited, funds will be auto-refunded to the customer within 3-5 business days according to RBI guidelines.",
        resolution_name="Instant Payment Link",
        resolution_instruction="Generate an on-demand payment link with multi-gateway fallback.",
        recommendation="Create a fresh payment link for {customer} to ensure uninterrupted subscription access.",
        default_followups=[
            "Create a payment link for {customer}",
            "What happens to the failed amount?",
            "Analyse all my failed payments",
        ],
    ),
    FailureCategory.CUSTOMER_ACTION_REQUIRED: FailureReasonDetail(
        headline_template="{customer}'s ₹{amount} payment requires 3D Secure / OTP authentication.",
        explanation="The customer's bank required two-factor authentication (OTP/biometrics) which could not be completed autonomously in headless subscription mode.",
        auto_reversal_timeline=None,
        resolution_name="Interactive Payment Link",
        resolution_instruction="Share an interactive payment link where the customer can manually enter the OTP.",
        recommendation="Create a payment link and send it to {customer} via WhatsApp/SMS for quick OTP approval.",
        default_followups=[
            "Create a payment link for {customer}",
            "Can we send the link via WhatsApp?",
            "Analyse all my failed payments",
        ],
    ),
    FailureCategory.UNKNOWN_FAILURE: FailureReasonDetail(
        headline_template="{customer}'s ₹{amount} payment was declined by the gateway.",
        explanation="The issuing institution declined the transaction with generic response code. Further diagnostic signals indicate manual verification is advised.",
        auto_reversal_timeline="If debited, the transaction will auto-reconcile within 5 business days.",
        resolution_name="Manual Verification / Payment Link",
        resolution_instruction="Verify customer status and generate an on-demand payment link.",
        recommendation="Create a fresh payment link for the customer.",
        default_followups=[
            "Create a payment link for {customer}",
            "What happens to the failed amount?",
            "Analyse all my failed payments",
        ],
    ),
}


def get_reason_detail(category: FailureCategory) -> FailureReasonDetail:
    """Retrieve failure reason detail by category with fallback."""
    return COPILOT_REASON_CATALOG.get(category, COPILOT_REASON_CATALOG[FailureCategory.UNKNOWN_FAILURE])
