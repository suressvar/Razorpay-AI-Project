"""OpenAI Model Provider (GPT-4o, GPT-4o-mini, etc.) for autonomous diagnosis and proposals."""

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

logger = logging.getLogger("recovery_autopilot.model_providers.openai")


class OpenAIProvider(ModelProvider):
    """OpenAI API provider targeting models like gpt-4o, gpt-4o-mini, gpt-4-turbo."""

    def __init__(
        self,
        api_key: str = "",
        model_name: str = "gpt-4o-mini",
        base_url: str = "https://api.openai.com/v1",
        temperature: float = 0.1,
        timeout_seconds: float = 30.0,
    ):
        self.provider_name = "openai"
        self.model_identifier = model_name
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.temperature = temperature
        self.timeout_seconds = timeout_seconds

    async def _query_openai(self, system_prompt: str, user_prompt: str, json_format: bool = True) -> str:
        """Call OpenAI /chat/completions endpoint."""
        if not self.api_key:
            raise ProviderError("OPENAI_API_KEY is not set in configuration or .env", provider_name=self.provider_name)

        endpoint = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model_identifier,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": self.temperature,
        }
        if json_format:
            payload["response_format"] = {"type": "json_object"}

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(endpoint, json=payload, headers=headers)
                if response.status_code != 200:
                    raise ProviderError(
                        f"OpenAI returned HTTP {response.status_code}: {response.text}",
                        provider_name=self.provider_name,
                    )
                data = response.json()
                choices = data.get("choices", [])
                if not choices:
                    raise ProviderError("No completion choices returned by OpenAI", provider_name=self.provider_name)
                content = choices[0].get("message", {}).get("content", "")
                if not content:
                    raise ProviderError("Empty response content returned by OpenAI", provider_name=self.provider_name)
                return content
        except httpx.RequestError as exc:
            raise ProviderError(f"Network error contacting OpenAI: {str(exc)}", provider_name=self.provider_name)

    async def diagnose_failure(self, case: PaymentCase) -> DiagnosisResult:
        """Execute failure diagnosis via OpenAI."""
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
            content = await self._query_openai(DIAGNOSIS_SYSTEM_INSTRUCTION, prompt, json_format=True)
            data = json.loads(content)
            return DiagnosisResult.model_validate(data)
        except Exception as e:
            logger.error("OpenAI diagnosis failed; falling back to safe defaults: %s", str(e))
            return DiagnosisResult(
                failure_category=ctx.failure_category,
                confidence=0.5,
                is_transient=False,
                evidence_signals=["OPENAI_FALLBACK"],
                reasoning=f"OpenAI diagnosis error: {str(e)}",
                suggested_action=RecoveryAction.HUMAN_REVIEW,
            )

    async def propose_recovery(self, case: PaymentCase) -> RecoveryProposal:
        """Generate structured proposal via OpenAI."""
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
            content = await self._query_openai(PROPOSAL_SYSTEM_INSTRUCTION, prompt, json_format=True)
            data = json.loads(content)
            data["model_name"] = self.model_identifier
            data["prompt_version"] = PROPOSAL_PROMPT_VERSION
            return RecoveryProposal.model_validate(data)
        except Exception as e:
            logger.error("OpenAI proposal failed; falling back to HUMAN_REVIEW: %s", str(e))
            return RecoveryProposal(
                action=RecoveryAction.HUMAN_REVIEW,
                confidence=0.5,
                delay_minutes=0,
                reason_codes=["OPENAI_FALLBACK_TO_HUMAN"],
                explanation=f"OpenAI inference error ({str(e)}). Escalating to human review.",
                requires_human_approval=True,
                model_name=self.model_identifier,
                prompt_version=PROPOSAL_PROMPT_VERSION,
            )

    async def draft_customer_message(self, case: PaymentCase, action: RecoveryAction) -> Optional[str]:
        """Draft communication message via OpenAI."""
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
            msg = await self._query_openai(MESSAGE_SYSTEM_INSTRUCTION, prompt, json_format=False)
            return msg.strip()
        except Exception:
            return f"Hello {ctx.customer_name}, please check your subscription payment status for INR {ctx.amount_inr:,.2f}."
