from recovery_autopilot.api.routes_admin import router as admin_router
from recovery_autopilot.api.routes_cases import router as cases_router
from recovery_autopilot.api.routes_copilot import router as copilot_router
from recovery_autopilot.api.routes_copilot_v2 import router as copilot_v2_router
from recovery_autopilot.api.routes_demo import router as demo_router
from recovery_autopilot.api.routes_metrics import router as metrics_router
from recovery_autopilot.api.routes_voice import router as voice_router
from recovery_autopilot.api.routes_webhooks import router as webhooks_router

__all__ = [
    "admin_router",
    "cases_router",
    "copilot_router",
    "copilot_v2_router",
    "demo_router",
    "metrics_router",
    "voice_router",
    "webhooks_router",
]


