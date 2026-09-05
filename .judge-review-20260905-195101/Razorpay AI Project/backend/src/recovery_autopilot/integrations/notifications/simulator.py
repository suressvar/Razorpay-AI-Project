"""Simulated notification dispatcher and unified action executor."""

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, List, Optional

from pydantic import BaseModel, Field

from recovery_autopilot.domain.enums import RecoveryAction
from recovery_autopilot.domain.models import ExecutionResult, PaymentCase
from recovery_autopilot.integrations.razorpay.payment_links import PaymentLinkAdapter
from recovery_autopilot.workflows.protocols import ActionExecutorProtocol

logger = logging.getLogger("recovery_autopilot.integrations.notifications")


class NotificationPreview(BaseModel):
    """In-memory recorded notification for UI preview."""

    notification_id: str = Field(default_factory=lambda: f"notif_{uuid.uuid4().hex[:10]}")
    case_id: str
    channel: str  # "WHATSAPP", "EMAIL", "SMS"
    recipient_masked: str
    content: str
    sent_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    status: str = "SIMULATED_DELIVERED"


class UnifiedActionExecutor(ActionExecutorProtocol):
    """Unified test-mode action executor implementing ActionExecutorProtocol.

    Handles:
    - WAIT_FOR_RETRY: schedules wait timer, sends no customer contact.
    - SEND_PAYMENT_LINK: creates test payment link and sends preview notification.
    - REQUEST_METHOD_UPDATE: drafts update mandate prompt and stores preview.
    - SEND_REMINDER: stores reminder preview.
    - HUMAN_REVIEW: tags case for human ops.
    - STOP: records termination.
    """

    def __init__(self, payment_link_adapter: PaymentLinkAdapter, simulate_notifications: bool = True):
        self.payment_link_adapter = payment_link_adapter
        self.simulate_notifications = simulate_notifications
        self.recorded_notifications: List[NotificationPreview] = []

    def get_notifications_for_case(self, case_id: str) -> List[NotificationPreview]:
        """Retrieve simulated notification previews for UI inspection."""
        return [n for n in self.recorded_notifications if n.case_id == case_id]

    async def execute_action(
        self,
        case: PaymentCase,
        action: RecoveryAction,
        customer_message: Optional[str] = None,
        session: Optional[Any] = None,
    ) -> ExecutionResult:
        """Execute action in safe sandbox mode with immediate emergency kill-switch verification."""
        from recovery_autopilot.config import settings

        if settings.KILL_SWITCH_ACTIVE:
            logger.warning("Emergency Kill Switch is ACTIVE. Halting execution for case %s.", case.case_id)
            return ExecutionResult(
                action=action,
                status="BLOCKED_BY_KILL_SWITCH",
                error="Emergency Kill Switch is active. All recovery side effects halted.",
            )

        ctx = case.context

        if action == RecoveryAction.WAIT_FOR_RETRY:
            return ExecutionResult(
                action=action,
                status="SCHEDULED",
                executed_at=datetime.now(timezone.utc),
                metadata={"delay_minutes": case.latest_decision.modified_delay_minutes or 120, "mode": "WAIT_FOR_RETRY"},
            )

        elif action == RecoveryAction.SEND_PAYMENT_LINK:
            # 1. Create payment link
            result = await self.payment_link_adapter.create_payment_link(case, description=customer_message, session=session)
            link_url = result.metadata.get("short_url", "https://rzp.io/test")

            # 2. Store simulated WhatsApp/Email preview
            msg = customer_message or f"Hello {ctx.customer_name}, please complete your subscription payment here: {link_url}"
            self.recorded_notifications.append(
                NotificationPreview(
                    case_id=case.case_id,
                    channel="WHATSAPP",
                    recipient_masked=f"{ctx.customer_phone[:4]}***{ctx.customer_phone[-2:]}",
                    content=msg,
                )
            )
            return result

        elif action == RecoveryAction.REQUEST_METHOD_UPDATE:
            msg = customer_message or f"Hello {ctx.customer_name}, your subscription card has expired. Please update payment method."
            self.recorded_notifications.append(
                NotificationPreview(
                    case_id=case.case_id,
                    channel="EMAIL",
                    recipient_masked=f"{ctx.customer_email[:3]}***@{ctx.customer_email.split('@')[-1]}",
                    content=msg,
                )
            )
            return ExecutionResult(
                action=action,
                external_id=f"req_{uuid.uuid4().hex[:8]}",
                status="SIMULATED",
                executed_at=datetime.now(timezone.utc),
                metadata={"channel": "EMAIL", "message_length": len(msg)},
            )

        elif action == RecoveryAction.SEND_REMINDER:
            msg = customer_message or f"Hello {ctx.customer_name}, reminder regarding your pending subscription payment."
            self.recorded_notifications.append(
                NotificationPreview(
                    case_id=case.case_id,
                    channel="WHATSAPP",
                    recipient_masked=f"{ctx.customer_phone[:4]}***{ctx.customer_phone[-2:]}",
                    content=msg,
                )
            )
            return ExecutionResult(
                action=action,
                external_id=f"rem_{uuid.uuid4().hex[:8]}",
                status="SIMULATED",
                executed_at=datetime.now(timezone.utc),
                metadata={"channel": "WHATSAPP"},
            )

        elif action == RecoveryAction.HUMAN_REVIEW:
            return ExecutionResult(
                action=action,
                status="HELD_FOR_HUMAN_REVIEW",
                executed_at=datetime.now(timezone.utc),
                metadata={"reason": case.latest_decision.block_reason if case.latest_decision else "Manual review mandated"},
            )

        elif action == RecoveryAction.STOP:
            return ExecutionResult(
                action=action,
                status="STOPPED",
                executed_at=datetime.now(timezone.utc),
                metadata={"reason": "Recovery terminated"},
            )

        return ExecutionResult(
            action=action,
            status="UNKNOWN",
            executed_at=datetime.now(timezone.utc),
        )
