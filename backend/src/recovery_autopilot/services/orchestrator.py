"""Core orchestrator service coordinating webhooks, AI workflow, and execution."""

import json
import logging
from typing import Any, Dict, Optional

from recovery_autopilot.config import settings
from recovery_autopilot.domain.enums import CaseStatus, RecoveryAction
from recovery_autopilot.evaluation.simulator import OutcomeSimulator
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
        # 1. Verify HMAC Signature
        self.webhook_verifier.verify(raw_body, signature)

        # 2. Parse event payload
        payload = json.loads(raw_body.decode("utf-8"))

        # 3. Delegate to Unified Event Processor
        from recovery_autopilot.services.event_processor import event_processor

        return await event_processor.process_event(
            payload=payload,
            raw_body=raw_body,
            signature=signature,
            event_id=event_id_header,
            source="webhook",
        )

    async def seed_demo_data(self, count: int = 50, seed: int = 42) -> int:
        """Seed database with synthetic failure cases and run through initial recovery workflow with simulated outcomes."""
        await init_db()
        scenarios = generate_synthetic_dataset(count=count, seed=seed)
        simulator = OutcomeSimulator()
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
                case = await workflow.process_failed_payment(s.context)
                seeded += 1

                # If the case is not blocked or held for human review, simulate recovery outcome
                if case.status not in (CaseStatus.AWAITING_APPROVAL, CaseStatus.STOPPED, CaseStatus.OPTED_OUT):
                    action = (
                        case.current_proposal.action
                        if case.current_proposal and case.current_proposal.action != RecoveryAction.HUMAN_REVIEW
                        else RecoveryAction.SEND_PAYMENT_LINK
                    )
                    sim_res = simulator.simulate(s, action)
                    if sim_res.recovered and not sim_res.safety_violation_occurred and not sim_res.human_review_needed:
                        await workflow.handle_payment_success(
                            case=case,
                            payment_id=f"pay_rec_{s.context.payment_id[-12:]}",
                            amount_inr=s.context.amount_inr,
                            currency=s.context.currency,
                            matched_field="payment_id",
                            matched_value=s.context.payment_id,
                        )

            # Seed demo customer issues for the Copilot customer issue tracker
            from recovery_autopilot.domain.issue_models import (
                CustomerIssue,
                IssueCategory,
                IssueSeverity,
                IssueStatus,
                IssueEvidence,
                IssueCause,
                ConfidenceLevel,
            )
            from recovery_autopilot.persistence.issue_repository import IssueRepository

            issue_repo = IssueRepository(session)
            demo_issues = [
                CustomerIssue(
                    issue_id="iss_demo_001",
                    title="Card declined — Insufficient funds for Priya Sharma",
                    category=IssueCategory.PAYMENT_FAILURE,
                    severity=IssueSeverity.HIGH,
                    status=IssueStatus.INVESTIGATING,
                    customer_name="Priya Sharma",
                    customer_email="priya.sharma@example.com",
                    payment_id="pay_demo_fail_001",
                    reported_symptoms="Customer reported recurring SaaS subscription payment failed at 02:00 AM.",
                    evidence=[
                        IssueEvidence(
                            source="payment_record",
                            description="Payment transaction declined with Razorpay error code BAD_REQUEST_PAYMENT_FAILED",
                            confidence=ConfidenceLevel.HIGH,
                        ),
                        IssueEvidence(
                            source="gateway_response",
                            description="Issuing bank responded with decline code 51 (insufficient funds)",
                            confidence=ConfidenceLevel.HIGH,
                        ),
                    ],
                    possible_causes=[
                        IssueCause(
                            description="Customer account has insufficient balance on salary cycle renewal date",
                            confidence=ConfidenceLevel.HIGH,
                            is_confirmed=True,
                            recommended_action="Send smart retry link via WhatsApp and email allowing payment via alternate card or UPI.",
                        ),
                    ],
                ),
                CustomerIssue(
                    issue_id="iss_demo_002",
                    title="Amount debited but subscription inactive for Rahul Verma",
                    category=IssueCategory.DEBIT_WITHOUT_CONFIRMATION,
                    severity=IssueSeverity.CRITICAL,
                    status=IssueStatus.ACTION_IN_PROGRESS,
                    customer_name="Rahul Verma",
                    customer_email="rahul.verma@example.com",
                    payment_id="pay_demo_debit_002",
                    order_id="order_demo_002",
                    reported_symptoms="Customer states bank deducted ₹4,999 but the app dashboard still indicates subscription expired.",
                    evidence=[
                        IssueEvidence(
                            source="webhook_event",
                            description="Webhook payment.captured was delivered with a 45-minute delay due to merchant server latency",
                            confidence=ConfidenceLevel.HIGH,
                        ),
                        IssueEvidence(
                            source="database_record",
                            description="Order status in application table order_demo_002 was not updated from pending to paid",
                            confidence=ConfidenceLevel.HIGH,
                        ),
                    ],
                    possible_causes=[
                        IssueCause(
                            description="Webhook event timeout resulted in order status desynchronization between Razorpay and merchant database",
                            confidence=ConfidenceLevel.HIGH,
                            is_confirmed=True,
                            recommended_action="Run reconciliation sync to update order status to paid and send confirmation email.",
                        ),
                    ],
                ),
                CustomerIssue(
                    issue_id="iss_demo_003",
                    title="Refund delay follow-up for Sunita Patel",
                    category=IssueCategory.REFUND_DELAY,
                    severity=IssueSeverity.MEDIUM,
                    status=IssueStatus.RESOLVED,
                    customer_name="Sunita Patel",
                    customer_email="sunita.patel@example.com",
                    payment_id="pay_demo_refund_003",
                    refund_id="rfnd_demo_003",
                    reported_symptoms="Customer asked why refund of ₹1,499 initiated 3 days ago is not in bank statement.",
                    resolution_summary="Explained 5-7 business day banking turnaround SLA for NEFT/IMPS refunds. Verified refund status is PROCESSING in gateway.",
                    resolution_verified=True,
                    resolution_evidence="Razorpay gateway reference ARN 409281729482 verified with issuing bank.",
                ),
            ]
            for iss in demo_issues:
                existing = await issue_repo.get_issue(iss.issue_id)
                if not existing:
                    await issue_repo.save_issue(iss)

            await session.commit()

        logger.info("Successfully seeded %d synthetic demo cases and %d customer issues into database", seeded, len(demo_issues))
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


