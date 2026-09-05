"""Ollama (Qwen3 8B) Model Provider for local, private model execution."""

import json
import logging
from typing import Optional

import httpx

from recovery_autopilot.agents.prompts import (
    DIAGNOSIS_SYSTEM_INSTRUCTION,
    DIAGNOSIS_USER_TEMPLATE,
    MESSAGE_SYSTEM_INSTRUCTION,
    MESSAGE_USER_TEMPLATE,
    PROPOSAL_PROMPT_VERSION,
    PROPOSAL_SYSTEM_INSTRUCTION,
    PROPOSAL_USER_TEMPLATE,
)
from recovery_autopilot.domain.enums import RecoveryAction
from recovery_autopilot.domain.models import PaymentCase, RecoveryProposal
from recovery_autopilot.model_providers.base import DiagnosisResult, ModelProvider, ProviderError

logger = logging.getLogger("recovery_autopilot.model_providers.ollama")


class OllamaProvider(ModelProvider):
    """Local Ollama provider targeting models like Qwen3 8B."""

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model_name: str = "qwen3:8b",
        timeout_seconds: float = 30.0,
    ):
        self.provider_name = "ollama"
        self.model_identifier = model_name
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    async def _query_ollama(self, system_prompt: str, user_prompt: str, json_format: bool = True) -> str:
        """Call Ollama /api/chat endpoint."""
        endpoint = f"{self.base_url}/api/chat"
        payload = {
            "model": self.model_identifier,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "stream": False,
            "options": {"temperature": 0.1},
        }
        if json_format:
            payload["format"] = "json"

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(endpoint, json=payload)
                if response.status_code != 200:
                    raise ProviderError(
                        f"Ollama returned HTTP {response.status_code}: {response.text}",
                        provider_name=self.provider_name,
                    )
                data = response.json()
                content = data.get("message", {}).get("content", "")
                if not content:
                    raise ProviderError("Empty response returned by Ollama", provider_name=self.provider_name)
                return content
        except httpx.RequestError as exc:
            raise ProviderError(f"Network error contacting Ollama: {str(exc)}", provider_name=self.provider_name)

    async def diagnose_failure(self, case: PaymentCase) -> DiagnosisResult:
        """Execute local failure diagnosis."""
        ctx = case.context
        prompt = DIAGNOSIS_USER_TEMPLATE.format(
            payment_id=ctx.payment_id,
            subscription_id=ctx.subscription_id,
            amount_inr=ctx.amount_inr,
            failure_code=ctx.failure_code,
            failure_reason=ctx.failure_reason,
            payment_method=ctx.payment_method.value,
            customer_segment=ctx.customer_segment.value,
            previous_failures=ctx.previous_failures,
            bank_name=ctx.bank_name or "Unknown",
            bank_degraded=ctx.bank_degraded,
            opted_out=ctx.opted_out,
        )

        try:
            content = await self._query_ollama(DIAGNOSIS_SYSTEM_INSTRUCTION, prompt, json_format=True)
            data = json.loads(content)
            return DiagnosisResult.model_validate(data)
        except Exception as e:
            logger.error("Ollama diagnosis failed; triggering safe fallback: %s", str(e))
            return DiagnosisResult(
                failure_category=ctx.failure_category,
                confidence=0.5,
                is_transient=False,
                evidence_signals=["OLLAMA_FALLBACK"],
                reasoning=f"Local model diagnosis unavailable: {str(e)}",
                suggested_action=RecoveryAction.HUMAN_REVIEW,
            )

    async def propose_recovery(self, case: PaymentCase) -> RecoveryProposal:
        """Generate structured proposal via local Ollama."""
        ctx = case.context
        prompt = PROPOSAL_USER_TEMPLATE.format(
            payment_id=ctx.payment_id,
            amount_inr=ctx.amount_inr,
            failure_category=ctx.failure_category.value,
            failure_reason=ctx.failure_reason,
            payment_method=ctx.payment_method.value,
            customer_segment=ctx.customer_segment.value,
            previous_contacts=ctx.previous_contacts,
            bank_name=ctx.bank_name or "Unknown",
            bank_degraded=ctx.bank_degraded,
            opted_out=ctx.opted_out,
        )

        try:
            content = await self._query_ollama(PROPOSAL_SYSTEM_INSTRUCTION, prompt, json_format=True)
            data = json.loads(content)
            data["model_name"] = self.model_identifier
            data["prompt_version"] = PROPOSAL_PROMPT_VERSION
            return RecoveryProposal.model_validate(data)
        except Exception as e:
            logger.error("Ollama proposal failed; falling back to HUMAN_REVIEW: %s", str(e))
            return RecoveryProposal(
                action=RecoveryAction.HUMAN_REVIEW,
                confidence=0.5,
                delay_minutes=0,
                reason_codes=["OLLAMA_FALLBACK_TO_HUMAN"],
                explanation=f"Local model inference failed ({str(e)}). Escalating to human operator.",
                requires_human_approval=True,
                model_name=self.model_identifier,
                prompt_version=PROPOSAL_PROMPT_VERSION,
            )

    async def draft_customer_message(self, case: PaymentCase, action: RecoveryAction) -> Optional[str]:
        """Draft communication message."""
        if action in [RecoveryAction.WAIT_FOR_RETRY, RecoveryAction.STOP]:
            return None

        ctx = case.context
        prompt = MESSAGE_USER_TEMPLATE.format(
            customer_name=ctx.customer_name,
            amount_inr=ctx.amount_inr,
            action=action.value,
            failure_reason=ctx.failure_reason,
        )

        try:
            msg = await self._query_ollama(MESSAGE_SYSTEM_INSTRUCTION, prompt, json_format=False)
            return msg.strip()
        except Exception:
            return f"Hello {ctx.customer_name}, please check your subscription status for INR {ctx.amount_inr:,.2f}."
