"""Celery worker tasks for asynchronous recovery processing."""

import asyncio
import logging

from recovery_autopilot.services.orchestrator import orchestrator
from recovery_autopilot.workers.celery_app import celery_app

logger = logging.getLogger("recovery_autopilot.workers.tasks")


@celery_app.task(name="recovery_autopilot.process_webhook")
def process_webhook_task(raw_body_str: str, signature: str):
    """Background task to process webhook payload asynchronously."""
    raw_bytes = raw_body_str.encode("utf-8")
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(orchestrator.handle_webhook(raw_bytes, signature))
    finally:
        loop.close()


@celery_app.task(name="recovery_autopilot.seed_demo")
def seed_demo_task(count: int = 50, seed: int = 42):
    """Background task to seed demo dataset."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(orchestrator.seed_demo_data(count, seed))
    finally:
        loop.close()
