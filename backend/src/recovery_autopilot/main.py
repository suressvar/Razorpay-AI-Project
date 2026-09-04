"""Main FastAPI application entry point for Recovery Autopilot."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from recovery_autopilot.api import (
    admin_router,
    cases_router,
    copilot_router,
    demo_router,
    metrics_router,
    voice_router,
    webhooks_router,
)
from recovery_autopilot.config import settings
from recovery_autopilot.persistence.database import init_db
from recovery_autopilot.workers.queue import background_worker

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("recovery_autopilot.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context for initialization and teardown."""
    logger.info("Starting up %s (Environment: %s, Model: %s, Mode: %s)", settings.APP_NAME, settings.ENVIRONMENT, settings.MODEL_PROVIDER, settings.PAYMENT_EXECUTION_MODE)
    await init_db()

    if settings.USE_IN_PROCESS_WORKER:
        background_worker.start()
        logger.info("In-process background webhook worker started.")

    yield

    if settings.USE_IN_PROCESS_WORKER:
        await background_worker.stop()
        logger.info("In-process background webhook worker stopped.")

    logger.info("Shutting down %s", settings.APP_NAME)


app = FastAPI(
    title=settings.APP_NAME,
    description="Autonomous, safety-bounded subscription payment recovery agent for Razorpay.",
    version="0.1.0",
    lifespan=lifespan,
)

# Configure CORS for Vite / React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Root info endpoint directing users to UI and API docs."""
    return {
        "message": "Razorpay AI Revenue Recovery Autopilot API",
        "frontend_ui_url": "http://localhost:5175/",
        "copilot_ui_url": "http://localhost:5175/copilot",
        "api_docs_swagger": "/docs",
        "health_check": "/health",
    }


@app.get("/health")
async def health_check():
    """Service health check endpoint reporting operational parameters."""
    return {
        "status": "healthy",
        "app_name": settings.APP_NAME,
        "version": "0.1.0",
        "environment": settings.ENVIRONMENT,
        "model_provider": settings.MODEL_PROVIDER,
        "synthetic_mode": settings.SYNTHETIC_MODE,
        "human_review_threshold_inr": settings.HUMAN_REVIEW_THRESHOLD_INR,
    }



# Register feature routers
app.include_router(webhooks_router)
app.include_router(cases_router)
app.include_router(copilot_router)
app.include_router(metrics_router)
app.include_router(demo_router)
app.include_router(admin_router)
app.include_router(voice_router)



