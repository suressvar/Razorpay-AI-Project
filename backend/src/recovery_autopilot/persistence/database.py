"""Asynchronous database connection and session management."""

import logging
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from recovery_autopilot.config import settings
from recovery_autopilot.persistence.models import Base

logger = logging.getLogger("recovery_autopilot.persistence.database")

# Configure database engine
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    future=True,
)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def init_db() -> None:
    """Initialize database schema tables and ensure incremental schema migrations."""
    from sqlalchemy import text

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

        # Lightweight safe migrations for newly added columns
        migration_statements = [
            "ALTER TABLE payment_cases ADD COLUMN order_id VARCHAR(64)",
            "ALTER TABLE payment_cases ADD COLUMN payment_link_id VARCHAR(128)",
            "ALTER TABLE webhook_events ADD COLUMN status VARCHAR(32) DEFAULT 'received'",
            "ALTER TABLE webhook_events ADD COLUMN attempts INTEGER DEFAULT 0",
            "ALTER TABLE webhook_events ADD COLUMN error_code VARCHAR(64)",
            "ALTER TABLE webhook_events ADD COLUMN processed_at TIMESTAMP",
            "ALTER TABLE payment_cases ADD COLUMN promise_to_pay_json TEXT",
            "ALTER TABLE webhook_events ADD COLUMN payload_hash VARCHAR(64)",
            "ALTER TABLE webhook_events ADD COLUMN last_error TEXT",
            "ALTER TABLE webhook_events ADD COLUMN locked_at TIMESTAMP",
            "ALTER TABLE webhook_events ADD COLUMN lease_expires_at TIMESTAMP",
        ]
        for stmt in migration_statements:
            try:
                await conn.execute(text(stmt))
            except Exception:
                # Column already exists
                pass

    logger.info("Database schema initialized successfully against %s", settings.DATABASE_URL.split("@")[-1])



async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for providing database session to FastAPI endpoints."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
