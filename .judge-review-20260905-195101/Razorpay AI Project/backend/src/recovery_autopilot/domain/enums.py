"""Controlled domain enumerations for Recovery Autopilot."""

from enum import Enum


class FailureCategory(str, Enum):
    """Categorization of payment failures."""

    INSUFFICIENT_FUNDS = "INSUFFICIENT_FUNDS"
    BANK_TIMEOUT = "BANK_TIMEOUT"
    EXPIRED_CARD = "EXPIRED_CARD"
    MANDATE_REVOKED = "MANDATE_REVOKED"
    LIMIT_EXCEEDED = "LIMIT_EXCEEDED"
    NETWORK_FAILURE = "NETWORK_FAILURE"
    CUSTOMER_ACTION_REQUIRED = "CUSTOMER_ACTION_REQUIRED"
    UNKNOWN_FAILURE = "UNKNOWN_FAILURE"


class CaseStatus(str, Enum):
    """State machine lifecycle statuses for a payment recovery case."""

    NEW = "NEW"
    DIAGNOSING = "DIAGNOSING"
    AWAITING_POLICY = "AWAITING_POLICY"
    SCHEDULED = "SCHEDULED"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    ACTION_IN_PROGRESS = "ACTION_IN_PROGRESS"
    MONITORING = "MONITORING"
    PROMISED_TO_PAY = "PROMISED_TO_PAY"
    RECOVERED = "RECOVERED"
    EXHAUSTED = "EXHAUSTED"
    OPTED_OUT = "OPTED_OUT"
    STOPPED = "STOPPED"
    ERROR = "ERROR"


class RecoveryAction(str, Enum):
    """Controlled set of permitted recovery actions. Arbitrary actions are forbidden."""

    WAIT_FOR_RETRY = "WAIT_FOR_RETRY"
    SEND_PAYMENT_LINK = "SEND_PAYMENT_LINK"
    REQUEST_METHOD_UPDATE = "REQUEST_METHOD_UPDATE"
    SEND_REMINDER = "SEND_REMINDER"
    HUMAN_REVIEW = "HUMAN_REVIEW"
    STOP = "STOP"


class CustomerSegment(str, Enum):
    """Customer value tiers."""

    ENTERPRISE = "ENTERPRISE"
    GROWTH = "GROWTH"
    SMB = "SMB"
    STARTER = "STARTER"


class PaymentMethod(str, Enum):
    """Payment methods used for subscriptions."""

    CARD = "CARD"
    UPI = "UPI"
    NETBANKING = "NETBANKING"
    NACH = "NACH"


class ActorType(str, Enum):
    """Source of an action or audit event."""

    AI = "AI"
    POLICY = "POLICY"
    EXECUTOR = "EXECUTOR"
    HUMAN = "HUMAN"
    WEBHOOK = "WEBHOOK"
    SIMULATOR = "SIMULATOR"
    SYSTEM = "SYSTEM"
