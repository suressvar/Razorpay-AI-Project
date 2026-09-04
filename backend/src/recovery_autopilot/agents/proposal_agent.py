"""Recovery proposal generation agent."""

from recovery_autopilot.domain.models import PaymentCase, RecoveryProposal
from recovery_autopilot.model_providers.base import ModelProvider


class ProposalAgent:
    """Agent responsible for formulating structured, policy-bounded recovery proposals."""

    def __init__(self, provider: ModelProvider):
        self.provider = provider

    async def propose(self, case: PaymentCase) -> RecoveryProposal:
        """Generate structured proposal strictly within allowed domain bounds."""
        return await self.provider.propose_recovery(case)
