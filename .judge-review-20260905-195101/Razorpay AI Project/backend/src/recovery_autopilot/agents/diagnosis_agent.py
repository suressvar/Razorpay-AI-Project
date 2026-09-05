"""Payment failure root-cause diagnosis agent."""

from recovery_autopilot.domain.models import PaymentCase
from recovery_autopilot.model_providers.base import DiagnosisResult, ModelProvider


class DiagnosisAgent:
    """Agent responsible for analyzing payment failures and producing a root-cause diagnosis."""

    def __init__(self, provider: ModelProvider):
        self.provider = provider

    async def diagnose(self, case: PaymentCase) -> DiagnosisResult:
        """Diagnose failure cause using configured model provider."""
        return await self.provider.diagnose_failure(case)
