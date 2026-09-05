"""Durable Webhook Queue and Asynchronous Background Worker.

Provides:
1. Fast-path webhook ingestion (<50ms ack).
2. Durable database-backed queue table with safe row leasing and worker lease tokens.
3. Bounded retries with exponential backoff and jitter, strictly honouring retry eligibility timestamps.
4. Dead-letter queue state for unrecoverable errors.
5. In-process asyncio worker lifecycle integration.
6. Unified event processing through UnifiedEventProcessor.
"""

import asyncio
import hashlib
import json
import logging
import random
import uuid
from datetime import timedelta
from typing import Any, Dict, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from recovery_autopilot.persistence.database import async_session_factory
from recovery_autopilot.persistence.models import UnmatchedWebhookRecord, WebhookEventRecord, utc_now
from recovery_autopilot.services.event_processor import event_processor

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
        worker_id: str = "default_worker",
        lease_seconds: int = 30,
        session: Optional[AsyncSession] = None,
    ) -> Optional[WebhookEventRecord]:
        """Atomically lease the oldest available job for processing, strictly honouring retry eligibility."""
        now = utc_now()
        lease_token = f"{worker_id}_{uuid.uuid4().hex[:8]}"

        async def _do_lease(s: AsyncSession) -> Optional[WebhookEventRecord]:
            # Find candidate:
            # 1. status='queued' AND (lease_expires_at is NULL OR lease_expires_at <= now)
            # 2. OR status='processing' AND lease_expires_at < now (expired lease recovery)
            stmt = (
                select(WebhookEventRecord)
                .where(
                    (
                        (WebhookEventRecord.status == "queued")
                        & (
                            WebhookEventRecord.lease_expires_at.is_(None)
                            | (WebhookEventRecord.lease_expires_at <= now)
                        )
                    )
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
                job.worker_lease_token = lease_token
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
        lease_token: Optional[str] = None,
        session: Optional[AsyncSession] = None,
    ) -> None:
        """Mark a job as successfully processed, verifying lease ownership."""
        now = utc_now()

        async def _do_complete(s: AsyncSession) -> None:
            job = await s.get(WebhookEventRecord, event_id)
            if not job:
                return

            if lease_token and job.worker_lease_token and job.worker_lease_token != lease_token:
                logger.warning(
                    "Stale worker lease rejected: lease_token %s != active %s for job %s",
                    lease_token,
                    job.worker_lease_token,
                    event_id,
                )
                return

            job.status = "completed"
            job.processed = True
            job.processed_at = now
            job.locked_at = None
            job.lease_expires_at = None
            job.worker_lease_token = None
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
        lease_token: Optional[str] = None,
        session: Optional[AsyncSession] = None,
    ) -> None:
        """Mark a job as unmatched (no active case matched)."""
        now = utc_now()

        async def _do_unmatched(s: AsyncSession) -> None:
            job = await s.get(WebhookEventRecord, event_id)
            if not job:
                return

            if lease_token and job.worker_lease_token and job.worker_lease_token != lease_token:
                logger.warning(
                    "Stale worker lease rejected for unmatched job %s: lease_token %s != active %s",
                    event_id,
                    lease_token,
                    job.worker_lease_token,
                )
                return

            job.status = "unmatched"
            job.processed = True
            job.processed_at = now
            job.locked_at = None
            job.lease_expires_at = None
            job.worker_lease_token = None
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
        lease_token: Optional[str] = None,
        session: Optional[AsyncSession] = None,
    ) -> None:
        """Handle job failure with exponential backoff or dead-letter state."""
        now = utc_now()

        async def _do_fail(s: AsyncSession) -> None:
            job = await s.get(WebhookEventRecord, event_id)
            if not job:
                return

            if lease_token and job.worker_lease_token and job.worker_lease_token != lease_token:
                logger.warning(
                    "Stale worker lease rejected for failed job %s: lease_token %s != active %s",
                    event_id,
                    lease_token,
                    job.worker_lease_token,
                )
                return

            job.last_error = error_msg[:1000]
            job.locked_at = None

            if job.attempts >= max_attempts:
                job.status = "dead_letter"
                job.lease_expires_at = None
                job.worker_lease_token = None
                job.processed = False
                logger.error(
                    "Job %s moved to DEAD_LETTER queue after %s attempts. Error: %s",
                    event_id,
                    job.attempts,
                    error_msg,
                )
            else:
                job.status = "queued"
                job.worker_lease_token = None
                # Exponential backoff with jitter or custom test delay
                if retry_delay_seconds is not None:
                    delay = retry_delay_seconds
                else:
                    delay = min((2 ** (job.attempts - 1)) * 2 + random.uniform(0.1, 1.0), 300.0)
                job.lease_expires_at = now + timedelta(seconds=delay)
                logger.warning(
                    "Job %s failed (attempt %s/%s). Retrying in %.2fs. Error: %s",
                    event_id,
                    job.attempts,
                    max_attempts,
                    delay,
                    error_msg,
                )

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
            stmt = (
                select(WebhookEventRecord.status, func.count(WebhookEventRecord.event_id))
                .group_by(WebhookEventRecord.status)
            )
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
        self.worker_id = f"worker_{uuid.uuid4().hex[:6]}"
        self.lease_seconds = 30
        self.poll_interval = poll_interval_seconds
        self.running = False
        self._task: Optional[asyncio.Task] = None

    def start(self) -> None:
        """Start the worker loop task."""
        if not self.running:
            self.running = True
            self._task = asyncio.create_task(self._worker_loop())
            logger.info("BackgroundWebhookWorker %s started.", self.worker_id)

    async def stop(self) -> None:
        """Gracefully stop the worker loop."""
        self.running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            logger.info("BackgroundWebhookWorker %s stopped.", self.worker_id)

    async def process_single_job(self) -> bool:
        """Lease and process one job from the queue via unified event processor. Returns True if a job was processed."""
        job = await self.queue.lease_next_job(worker_id=self.worker_id, lease_seconds=self.lease_seconds)
        if not job:
            return False

        event_id = job.event_id
        lease_token = job.worker_lease_token

        try:
            try:
                payload = json.loads(job.payload_json) if (job.payload_json and job.payload_json.strip()) else {}
            except (json.JSONDecodeError, ValueError) as json_err:
                logger.warning("Unparseable JSON payload for queued webhook %s: %s", event_id, json_err)
                await self.queue.mark_failed(event_id, f"Invalid JSON payload: {json_err}", max_attempts=1, lease_token=lease_token)
                return True

            # Process through unified event processor
            res = await event_processor.process_event(
                payload=payload,
                raw_body=job.payload_json.encode("utf-8") if job.payload_json else b"",
                signature=job.signature,
                event_id=event_id,
                source="worker",
            )

            status = res.get("status")
            if status in ("unmatched_stored", "ambiguous_subscription_stored"):
                await self.queue.mark_unmatched(
                    event_id,
                    res.get("reason", "No matching case or ambiguous obligation"),
                    lease_token=lease_token,
                )
            else:
                await self.queue.mark_completed(event_id, lease_token=lease_token)

            return True

        except Exception as exc:
            logger.error("Error executing queued webhook %s: %s", event_id, str(exc), exc_info=True)
            await self.queue.mark_failed(event_id, str(exc), lease_token=lease_token)
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
