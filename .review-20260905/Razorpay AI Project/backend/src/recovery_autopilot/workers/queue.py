"""Durable Webhook Queue and Asynchronous Background Worker.

Provides:
1. Fast-path webhook ingestion (<50ms ack).
2. Durable database-backed queue table with safe row leasing.
3. Bounded retries with exponential backoff and jitter.
4. Dead-letter queue state for unrecoverable errors.
5. In-process asyncio worker lifecycle integration.
"""

import asyncio
import hashlib
import json
import logging
import random
from datetime import timedelta
from typing import Any, Dict, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from recovery_autopilot.persistence.database import async_session_factory
from recovery_autopilot.persistence.models import UnmatchedWebhookRecord, WebhookEventRecord, utc_now

logger = logging.getLogger("recovery_autopilot.workers.queue")


class DurableWebhookQueue:
    """Manages persistent webhook event queuing, leasing, and status transitions."""

    @staticmethod
    def compute_payload_hash(payload_str: str) -> str:
        """Compute SHA256 hex digest for payload idempotency."""
        return hashlib.sha256(payload_str.encode("utf-8")).hexdigest()

    async def enqueue(
        self,
        event_id: str,
        event_type: str,
        signature: str,
        payload_str: str,
        session: Optional[AsyncSession] = None,
    ) -> Dict[str, Any]:
        """Enqueue an incoming verified webhook for async processing.

        Returns immediately with queue status and idempotency indicators.
        """
        payload_hash = self.compute_payload_hash(payload_str)

        async def _do_enqueue(s: AsyncSession) -> Dict[str, Any]:
            # Check for existing record with same event_id
            existing = await s.get(WebhookEventRecord, event_id)
            if existing:
                return {
                    "event_id": event_id,
                    "status": existing.status,
                    "duplicate": True,
                    "message": "Webhook already received or processed",
                }

            record = WebhookEventRecord(
                event_id=event_id,
                event_type=event_type,
                signature=signature,
                payload_json=payload_str,
                payload_hash=payload_hash,
                status="queued",
                attempts=0,
                received_at=utc_now(),
            )
            s.add(record)
            await s.flush()
            return {
                "event_id": event_id,
                "status": "queued",
                "duplicate": False,
                "message": "Webhook successfully enqueued for processing",
            }

        if session:
            return await _do_enqueue(session)
        else:
            async with async_session_factory() as s:
                res = await _do_enqueue(s)
                await s.commit()
                return res

    async def lease_next_job(
        self,
        lease_seconds: int = 30,
        session: Optional[AsyncSession] = None,
    ) -> Optional[WebhookEventRecord]:
        """Atomically lease the oldest available job for processing."""
        now = utc_now()

        async def _do_lease(s: AsyncSession) -> Optional[WebhookEventRecord]:
            # Find candidate: status='queued' OR (status='processing' AND lease_expires_at < now)
            stmt = (
                select(WebhookEventRecord)
                .where(
                    (WebhookEventRecord.status == "queued")
                    | (
                        (WebhookEventRecord.status == "processing")
                        & WebhookEventRecord.lease_expires_at.is_not(None)
                        & (WebhookEventRecord.lease_expires_at < now)
                    )
                )
                .order_by(WebhookEventRecord.received_at.asc())
                .limit(1)
                .with_for_update(skip_locked=True)
            )

            result = await s.execute(stmt)
            job = result.scalar_one_or_none()

            if job:
                job.status = "processing"
                job.locked_at = now
                job.lease_expires_at = now + timedelta(seconds=lease_seconds)
                job.attempts = (job.attempts or 0) + 1
                await s.flush()
                return job
            return None

        if session:
            return await _do_lease(session)
        else:
            async with async_session_factory() as s:
                job = await _do_lease(s)
                await s.commit()
                return job

    async def mark_completed(
        self,
        event_id: str,
        session: Optional[AsyncSession] = None,
    ) -> None:
        """Mark a job as successfully processed."""
        now = utc_now()

        async def _do_complete(s: AsyncSession) -> None:
            job = await s.get(WebhookEventRecord, event_id)
            if job:
                job.status = "completed"
                job.processed = True
                job.processed_at = now
                job.locked_at = None
                job.lease_expires_at = None
                job.last_error = None
                await s.flush()

        if session:
            await _do_complete(session)
        else:
            async with async_session_factory() as s:
                await _do_complete(s)
                await s.commit()

    async def mark_unmatched(
        self,
        event_id: str,
        reason: str,
        session: Optional[AsyncSession] = None,
    ) -> None:
        """Mark a job as unmatched (no active case matched)."""
        now = utc_now()

        async def _do_unmatched(s: AsyncSession) -> None:
            job = await s.get(WebhookEventRecord, event_id)
            if job:
                job.status = "unmatched"
                job.processed = True
                job.processed_at = now
                job.locked_at = None
                job.lease_expires_at = None
                job.error_code = "UNMATCHED_EVENT"
                job.last_error = reason
                await s.flush()

        if session:
            await _do_unmatched(session)
        else:
            async with async_session_factory() as s:
                await _do_unmatched(s)
                await s.commit()

    async def mark_failed(
        self,
        event_id: str,
        error_msg: str,
        max_attempts: int = 5,
        retry_delay_seconds: Optional[float] = None,
        session: Optional[AsyncSession] = None,
    ) -> None:
        """Handle job failure with exponential backoff or dead-letter state."""
        now = utc_now()

        async def _do_fail(s: AsyncSession) -> None:
            job = await s.get(WebhookEventRecord, event_id)
            if not job:
                return

            job.last_error = error_msg[:1000]
            job.locked_at = None

            if job.attempts >= max_attempts:
                job.status = "dead_letter"
                job.lease_expires_at = None
                job.processed = False
                logger.error("Job %s moved to DEAD_LETTER queue after %s attempts. Error: %s", event_id, job.attempts, error_msg)
            else:
                job.status = "queued"
                # Exponential backoff with jitter or custom test delay
                if retry_delay_seconds is not None:
                    delay = retry_delay_seconds
                else:
                    delay = (2 ** (job.attempts - 1)) * 2 + random.uniform(0.1, 1.0)
                job.lease_expires_at = now + timedelta(seconds=delay)
                logger.warning("Job %s failed (attempt %s/%s). Retrying in %.2fs. Error: %s", event_id, job.attempts, max_attempts, delay, error_msg)

            await s.flush()

        if session:
            await _do_fail(session)
        else:
            async with async_session_factory() as s:
                await _do_fail(s)
                await s.commit()

    async def get_stats(self) -> Dict[str, Any]:
        """Fetch queue depth and status breakdown statistics."""
        async with async_session_factory() as s:
            stmt = select(WebhookEventRecord.status, func.count(WebhookEventRecord.event_id)).group_by(WebhookEventRecord.status)
            res = await s.execute(stmt)
            counts = {row[0]: row[1] for row in res.all()}

            unmatched_stmt = select(func.count(UnmatchedWebhookRecord.event_id))
            unmatched_res = await s.execute(unmatched_stmt)
            unmatched_count = unmatched_res.scalar_one_or_none() or 0

            return {
                "queued": counts.get("queued", 0),
                "processing": counts.get("processing", 0),
                "completed": counts.get("completed", 0),
                "failed": counts.get("failed", 0),
                "dead_letter": counts.get("dead_letter", 0),
                "unmatched": counts.get("unmatched", 0) + unmatched_count,
                "total_events": sum(counts.values()),
            }


class BackgroundWebhookWorker:
    """Async background worker daemon that consumes leased jobs from the durable queue."""

    def __init__(self, poll_interval_seconds: float = 0.5):
        self.queue = DurableWebhookQueue()
        self.poll_interval = poll_interval_seconds
        self.running = False
        self._task: Optional[asyncio.Task] = None

    def start(self) -> None:
        """Start the worker loop task."""
        if not self.running:
            self.running = True
            self._task = asyncio.create_task(self._worker_loop())
            logger.info("BackgroundWebhookWorker started.")

    async def stop(self) -> None:
        """Gracefully stop the worker loop."""
        self.running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            logger.info("BackgroundWebhookWorker stopped.")

    async def process_single_job(self) -> bool:
        """Lease and process one job from the queue. Returns True if a job was processed."""
        from recovery_autopilot.persistence.repository import SqlAlchemyRepository
        from recovery_autopilot.services.orchestrator import orchestrator

        job = await self.queue.lease_next_job(lease_seconds=30)
        if not job:
            return False

        event_id = job.event_id
        try:
            try:
                payload = json.loads(job.payload_json) if (job.payload_json and job.payload_json.strip()) else {}
            except (json.JSONDecodeError, ValueError) as json_err:
                logger.warning("Unparseable JSON payload for queued webhook %s: %s", event_id, json_err)
                await self.queue.mark_failed(event_id, f"Invalid JSON payload: {json_err}", max_attempts=1)
                return True

            async with async_session_factory() as session:
                repo = SqlAlchemyRepository(session)
                workflow = orchestrator.create_workflow(repo)

                # Process payload
                event_type = payload.get("event", "")
                if event_type == "payment.captured" or event_type == "payment_link.paid":
                    captured_ctx = orchestrator.event_mapper.map_payment_captured(payload)
                    res = await workflow.handle_payment_captured(captured_ctx)
                    await session.commit()

                    if res.get("status") == "unmatched":
                        await self.queue.mark_unmatched(event_id, res.get("message", "No matching case"))
                    else:
                        await self.queue.mark_completed(event_id)
                elif event_type in ("payment.failed", "subscription.charged"):
                    context = orchestrator.event_mapper.map_payment_failed(payload)
                    existing_case = await repo.get_case_by_exact_identifier(payment_id=context.payment_id)
                    if not existing_case:
                        await workflow.process_failed_payment(context)
                    await session.commit()
                    await self.queue.mark_completed(event_id)
                else:
                    await self.queue.mark_completed(event_id)

            return True

        except Exception as exc:
            logger.error("Error executing queued webhook %s: %s", event_id, str(exc), exc_info=True)
            await self.queue.mark_failed(event_id, str(exc))
            return True

    async def _worker_loop(self) -> None:
        """Main execution loop for background queue processing."""
        while self.running:
            try:
                processed = await self.process_single_job()
                if not processed:
                    await asyncio.sleep(self.poll_interval)
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error("Unexpected error in worker loop: %s", str(exc), exc_info=True)
                await asyncio.sleep(self.poll_interval * 2)


# Global worker and queue instances
webhook_queue = DurableWebhookQueue()
background_worker = BackgroundWebhookWorker()
