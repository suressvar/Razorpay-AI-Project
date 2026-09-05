"""Synthetic scenario data structures."""

from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from recovery_autopilot.domain.enums import (
    RecoveryAction,
)
from recovery_autopilot.domain.models import PaymentContext


class SyntheticScenario(BaseModel):
    """A synthetic test scenario representing a failed recurring payment with simulation ground truth."""

    scenario_id: str = Field(..., description="Unique deterministic scenario ID, e.g. scn_0001")
    context: PaymentContext = Field(..., description="The payment context")
    expected_safe_actions: List[RecoveryAction] = Field(..., description="Domain-expert approved recovery interventions")
    action_recovery_probabilities: Dict[str, float] = Field(
        ...,
        description="Simulated probability of recovery [0.0 - 1.0] for each RecoveryAction enum",
    )
    salary_day_near: bool = Field(False, description="Whether the event is near typical salary settlement (1st-5th of month)")
    hour_of_day: int = Field(10, ge=0, le=23, description="Hour of failure event")
    day_of_week: int = Field(1, ge=0, le=6, description="Day of week (0=Mon, 6=Sun)")
    ground_truth_optimal_action: RecoveryAction = Field(..., description="Statistically optimal intervention")
    description: Optional[str] = Field(None, description="Scenario narrative")
