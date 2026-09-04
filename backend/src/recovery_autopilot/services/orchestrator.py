"""Core orchestrator service coordinating webhooks, AI workflow, and execution."""

import json
import logging
from typing import Any, Dict, Optional

from recovery_autopilot.config import settings
from recovery_autopilot.integrations.notifications.simulator import UnifiedActionExecutor
from recovery_autopilot.integrations.razorpay.event_mapper import RazorpayEventMapper
from recovery_autopilot.integrations.razorpay.payment_links import PaymentLinkAdapter
from recovery_autopilot.integrations.razorpay.webhook_verifier import RazorpayWebhookVerifier
from recovery_autopilot.model_providers.fake import FakeModelProvider
from recovery_autopilot.persistence.database import async_session_factory, init_db
from recovery_autopilot.persistence.repository import SqlAlchemyRepository
from recovery_autopilot.policies.guardrails import SafetyPolicyEngine
from recovery_autopilot.synthetic.generator import generate_synthetic_dataset
from recovery_autopilot.workflows.recovery_workflow import RecoveryWorkflow

logger = logging.getLogger("recovery_autopilot.services.orchestrator")


class RecoveryOrchestrator:
    """Singleton service facade managing recovery operations."""

    def __init__(self):
        self.webhook_verifier = RazorpayWebhookVerifier(settings.RAZORPAY_WEBHOOK_SECRET)
        self.event_mapper = RazorpayEventMapper()
        self.payment_link_adapter = PaymentLinkAdapter(
            key_id=settings.RAZORPAY_KEY_ID,
            key_secret=settings.RAZORPAY_KEY_SECRET,
            mode=settings.PAYMENT_EXECUTION_MODE,
        )
        self.unified_executor = UnifiedActionExecutor(
            payment_link_adapter=self.payment_link_adapter,
            simulate_notifications=settings.SIMULATE_NOTIFICATIONS,
        )
        self.policy_engine = SafetyPolicyEngine(settings)
        # Note: Depending on global state, might need import factory if not using fake default
        from recovery_autopilot.model_providers.factory import get_model_provider
        self.model_provider = get_model_provider(settings)

    def create_workflow(self, repository: SqlAlchemyRepository) -> RecoveryWorkflow:
        """Create a RecoveryWorkflow bound to the given repository."""
        return RecoveryWorkflow(
            provider=self.model_provider,
            policy_engine=self.policy_engine,
            executor=self.unified_executor,
            repository=repository,
        )

    async def handle_webhook(
        self,
        raw_body: bytes,
        signature: str,
        event_id_header: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Validate, store, and process incoming Razorpay webhook with strict financial correlation."""
        import hashlib

        # 1. Verify HMAC Signature
        self.webhook_verifier.verify(raw_body, signature)

        # 2. Parse event payload
        payload = json.loads(raw_body.decode("utf-8"))
        event_name = payload.get("event", "unknown")
        event_id = event_id_header or payload.get("id") or f"evt_{hashlib.sha256(raw_body).hexdigest()[:16]}"
        payload_str = raw_body.decode("utf-8")

        # 3. Idempotent Deduplication Check
        async with async_session_factory() as session:
            repo = SqlAlchemyRepository(session)
            is_new = await repo.save_webhook_event(
                event_id=event_id,
                event_type=event_name,
                signature=signature,
                payload_json=payload_str,
                status="received",
            )
            if not is_new:
                logger.info("Ignoring duplicate webhook event %s", event_id)
                return {"status": "duplicate_ignored", "event_id": event_id}
            await session.commit()

        # 4. Handle PAYMENT FAILURE events
        if event_name in ("payment.failed", "order.paid.failed", "subscription.charged.failed"):
            context = RazorpayEventMapper.map_payment_failed(payload)

            async with async_session_factory() as session:
                repo = SqlAlchemyRepository(session)
                workflow = self.create_workflow(repo)
                case = await workflow.process_failed_payment(context)
                await repo.update_webhook_status(event_id, status="completed")
                await session.commit()

                return {
                    "status": "processed",
                    "event_id": event_id,
                    "case_id": case.case_id,
                    "case_status": case.status.value,
                    "action": case.latest_action_result.action.value if case.latest_action_result else None,
                }

        # 5. Handle PAYMENT SUCCESS / RECOVERY CAPTURE events
        if event_name in ("payment.captured", "order.paid", "subscription.charged", "payment.authorized"):
            captured_ctx = RazorpayEventMapper.map_payment_captured(payload)

            async with async_session_factory() as session:
                repo = SqlAlchemyRepository(session)
                match_result = await repo.get_case_by_exact_identifier(
                    payment_id=captured_ctx.payment_id,
                    payment_link_id=captured_ctx.payment_link_id,
                    invoice_id=captured_ctx.invoice_id,
                    order_id=captured_ctx.order_id,
                    subscription_id=captured_ctx.subscription_id,
                )

                if not match_result:
                    reason_msg = (
                        f"Uncorrelatable success event: payment_id={captured_ctx.payment_id}, "
                        f"order_id={captured_ctx.order_id}, sub_id={captured_ctx.subscription_id}, "
                        f"plink_id={captured_ctx.payment_link_id}"
                    )
                    await repo.save_unmatched_event(
                        event_id=event_id,
                        event_type=event_name,
                        payload_json=raw_body.decode("utf-8"),
                        reason=reason_msg,
                        signature=signature,
                    )
                    await repo.update_webhook_status(event_id, status="unmatched")
                    await session.commit()
                    return {"status": "unmatched_stored", "event_id": event_id, "reason": reason_msg}

                case, matched_field, matched_value = match_result
                workflow = self.create_workflow(repo)
                outcome = await workflow.handle_payment_success(
                    case=case,
                    payment_id=captured_ctx.payment_id,
                    amount_inr=captured_ctx.amount_inr,
                    currency=captured_ctx.currency,
                    matched_field=matched_field,
                    matched_value=matched_value,
                )
                await repo.update_webhook_status(event_id, status="completed")
                await session.commit()

                return {
                    "status": "recovered" if outcome.recovered else "held_for_review",
                    "event_id": event_id,
                    "case_id": case.case_id,
                    "matched_by": matched_field,
                    "matched_value": matched_value,
                    "recovered_amount": outcome.recovered_amount,
                }

        return {"status": "accepted", "event_id": event_id, "event": event_name}

    async def seed_demo_data(self, count: int = 50, seed: int = 42) -> int:
        """Seed database with synthetic failure cases and run through initial recovery workflow."""
        await init_db()
        scenarios = generate_synthetic_dataset(count=count, seed=seed)
        seeded = 0

        # Use fast deterministic provider for rapid, zero-rate-limit demo seeding
        fast_provider = FakeModelProvider(
            provider_name="synthetic-seed-engine",
            model_identifier="heuristic-deterministic-v1",
        )

        async with async_session_factory() as session:
            repo = SqlAlchemyRepository(session)
            workflow = RecoveryWorkflow(
                provider=fast_provider,
                policy_engine=self.policy_engine,
                executor=self.unified_executor,
                repository=repo,
            )
            for s in scenarios:
                await workflow.process_failed_payment(s.context)
                seeded += 1
            await session.commit()

        logger.info("Successfully seeded %d synthetic demo cases into database", seeded)
        return seeded

    async def clear_all_data(self) -> dict:
        """Completely wipe all records from database in synthetic / sandbox mode."""
        await init_db()
        async with async_session_factory() as session:
            repo = SqlAlchemyRepository(session)
            counts = await repo.clear_all_data()
            await session.commit()
            logger.info("Successfully wiped all data from database: %s", counts)
            return counts


# Global orchestrator instance
orchestrator = RecoveryOrchestrator()

