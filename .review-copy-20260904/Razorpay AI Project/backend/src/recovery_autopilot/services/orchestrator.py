"""Core orchestrator service coordinating webhooks, AI workflow, and execution."""

import json
import logging
from typing import Any, Dict

from recovery_autopilot.config import settings
from recovery_autopilot.integrations.notifications.simulator import UnifiedActionExecutor
from recovery_autopilot.integrations.razorpay.event_mapper import RazorpayEventMapper
from recovery_autopilot.integrations.razorpay.payment_links import PaymentLinkAdapter
from recovery_autopilot.integrations.razorpay.webhook_verifier import RazorpayWebhookVerifier
from recovery_autopilot.model_providers.factory import get_model_provider
from recovery_autopilot.persistence.database import async_session_factory
from recovery_autopilot.persistence.repository import SqlAlchemyRepository
from recovery_autopilot.policies.guardrails import SafetyPolicyEngine
from recovery_autopilot.synthetic.generator import generate_synthetic_dataset
from recovery_autopilot.workflows.recovery_workflow import RecoveryWorkflow

logger = logging.getLogger("recovery_autopilot.services.orchestrator")


class RecoveryOrchestrator:
    """Singleton service facade managing recovery operations."""

    def __init__(self):
        self.webhook_verifier = RazorpayWebhookVerifier(settings.RAZORPAY_WEBHOOK_SECRET)
        self.payment_link_adapter = PaymentLinkAdapter(
            key_id=settings.RAZORPAY_KEY_ID,
            key_secret=settings.RAZORPAY_KEY_SECRET,
            test_mode=settings.SYNTHETIC_MODE,
        )
        self.unified_executor = UnifiedActionExecutor(
            payment_link_adapter=self.payment_link_adapter,
            simulate_notifications=settings.SIMULATE_NOTIFICATIONS,
        )
        self.policy_engine = SafetyPolicyEngine(settings)
        self.model_provider = get_model_provider(settings)

    def create_workflow(self, repository: SqlAlchemyRepository) -> RecoveryWorkflow:
        """Create a RecoveryWorkflow bound to the given repository."""
        return RecoveryWorkflow(
            provider=self.model_provider,
            policy_engine=self.policy_engine,
            executor=self.unified_executor,
            repository=repository,
        )

    async def handle_webhook(self, raw_body: bytes, signature: str) -> Dict[str, Any]:
        """Validate, store, and process incoming Razorpay webhook."""
        # 1. Verify HMAC Signature
        self.webhook_verifier.verify(raw_body, signature)

        # 2. Parse JSON
        payload = json.loads(raw_body.decode("utf-8"))
        event_name = payload.get("event", "unknown")
        event_id = payload.get("id") or f"evt_{hash(raw_body)}"

        async with async_session_factory() as session:
            repo = SqlAlchemyRepository(session)

            # 3. Idempotent Deduplication Check
            is_new = await repo.save_webhook_event(
                event_id=event_id,
                event_type=event_name,
                signature=signature,
                payload_json=raw_body.decode("utf-8"),
            )
            if not is_new:
                logger.info("Ignoring duplicate webhook event %s", event_id)
                return {"status": "duplicate_ignored", "event_id": event_id}

            await session.commit()

        # 4. Dispatch Processing
        if event_name == "payment.failed":
            ctx = RazorpayEventMapper.map_payment_failed(payload)
            async with async_session_factory() as session:
                repo = SqlAlchemyRepository(session)
                workflow = self.create_workflow(repo)
                await workflow.process_failed_payment(ctx)
                await session.commit()

        elif event_name in ["payment.captured", "order.paid"]:
            pay_id, amount = RazorpayEventMapper.map_payment_captured(payload)
            # Find matching active case by payment_id or customer/amount
            async with async_session_factory() as session:
                repo = SqlAlchemyRepository(session)
                cases = await repo.list_cases(limit=10)
                for case in cases:
                    if case.context.payment_id == pay_id or case.status.value in ["MONITORING", "SCHEDULED", "AWAITING_APPROVAL"]:
                        workflow = self.create_workflow(repo)
                        await workflow.handle_payment_success(case, pay_id, amount)
                        await session.commit()
                        break

        return {"status": "accepted", "event_id": event_id, "event": event_name}

    async def seed_demo_data(self, count: int = 50, seed: int = 42) -> int:
        """Seed database with synthetic failure cases and run through initial recovery workflow."""
        scenarios = generate_synthetic_dataset(count=count, seed=seed)
        seeded = 0

        for s in scenarios:
            async with async_session_factory() as session:
                repo = SqlAlchemyRepository(session)
                workflow = self.create_workflow(repo)
                await workflow.process_failed_payment(s.context)
                await session.commit()
                seeded += 1

        logger.info("Successfully seeded %d synthetic demo cases into database", seeded)
        return seeded


# Global orchestrator instance
orchestrator = RecoveryOrchestrator()
