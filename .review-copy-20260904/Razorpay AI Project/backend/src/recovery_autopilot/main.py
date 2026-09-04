"""Main FastAPI application entry point for Recovery Autopilot."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from recovery_autopilot.api import (
    cases_router,
    demo_router,
    metrics_router,
    webhooks_router,
)
from recovery_autopilot.config import settings
from recovery_autopilot.persistence.database import init_db

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("recovery_autopilot.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context for initialization and teardown."""
    logger.info("Starting up %s (Environment: %s, Model: %s)", settings.APP_NAME, settings.ENVIRONMENT, settings.MODEL_PROVIDER)
    await init_db()
    yield
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
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
app.include_router(metrics_router)
app.include_router(demo_router)
