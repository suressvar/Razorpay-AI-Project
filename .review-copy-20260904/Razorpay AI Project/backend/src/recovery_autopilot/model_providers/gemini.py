"""Gemini 3.7 Flash Model Provider with structured output and disabled automatic tool execution."""

import asyncio
import json
import logging
from typing import Any, Dict, Optional

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

logger = logging.getLogger("recovery_autopilot.model_providers.gemini")


class GeminiProvider(ModelProvider):
    """Google Gemini model provider with strict schema adherence and zero automatic tool privilege."""

    def __init__(
        self,
        api_key: str = "",
        model_name: str = "gemini-3.7-flash",
        temperature: float = 0.1,
        timeout_seconds: float = 15.0,
        max_retries: int = 2,
    ):
        self.provider_name = "gemini"
        self.model_identifier = model_name
        self.api_key = api_key
        self.temperature = temperature
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self._client = None

    def _get_client(self) -> Any:
        """Lazy client initialization."""
        if self._client is None:
            try:
                from google import genai
                self._client = genai.Client(api_key=self.api_key)
            except Exception as e:
                logger.warning("google-genai client initialization failed: %s", str(e))
                self._client = None
        return self._client

    async def _call_gemini(self, system_prompt: str, user_prompt: str, response_schema: Optional[type] = None) -> str:
        """Call Gemini API asynchronously with retry, backoff, and safety boundaries."""
        client = self._get_client()
        if not client or not self.api_key:
            raise ProviderError("Gemini API key is not configured", provider_name=self.provider_name, recoverable=False)

        last_error = None
        for attempt in range(self.max_retries + 1):
            try:
                # Synchronous client call executed in thread pool with timeout
                config: Dict[str, Any] = {
                    "temperature": self.temperature,
                    "system_instruction": system_prompt,
                }
                if response_schema:
                    config["response_mime_type"] = "application/json"
                    config["response_schema"] = response_schema

                # Explicitly verify NO function calling / automatic tool execution is registered
                config["tools"] = []

                loop = asyncio.get_running_loop()
                response = await asyncio.wait_for(
                    loop.run_in_executor(
                        None,
                        lambda: client.models.generate_content(
                            model=self.model_identifier,
                            contents=user_prompt,
                            config=config,
                        ),
                    ),
                    timeout=self.timeout_seconds,
                )
                if not response or not response.text:
                    raise ProviderError("Empty response returned by Gemini model", provider_name=self.provider_name)
                return response.text

            except asyncio.TimeoutError:
                last_error = ProviderError("Gemini API request timed out", provider_name=self.provider_name)
                logger.warning("Gemini timeout on attempt %d: %s", attempt + 1, str(last_error))
            except Exception as e:
                last_error = ProviderError(f"Gemini API invocation error: {str(e)}", provider_name=self.provider_name)
                logger.warning("Gemini error on attempt %d: %s", attempt + 1, str(e))

            if attempt < self.max_retries:
                await asyncio.sleep(2**attempt * 0.5)

        raise last_error or ProviderError("Unknown failure calling Gemini API", provider_name=self.provider_name)

    async def diagnose_failure(self, case: PaymentCase) -> DiagnosisResult:
        """Diagnose failure root cause via Gemini."""
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
            raw_json = await self._call_gemini(
                system_prompt=DIAGNOSIS_SYSTEM_INSTRUCTION,
                user_prompt=prompt,
                response_schema=DiagnosisResult,
            )
            data = json.loads(raw_json)
            return DiagnosisResult.model_validate(data)
        except Exception as e:
            logger.error("Gemini diagnosis failed; triggering safe human escalation: %s", str(e))
            # Safe deterministic fallback
            return DiagnosisResult(
                failure_category=ctx.failure_category,
                confidence=0.5,
                is_transient=False,
                evidence_signals=["PROVIDER_FALLBACK"],
                reasoning=f"AI diagnosis unavailable ({str(e)}). Fallback applied.",
                suggested_action=RecoveryAction.HUMAN_REVIEW,
            )

    async def propose_recovery(self, case: PaymentCase) -> RecoveryProposal:
        """Formulate structured RecoveryProposal via Gemini."""
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
            raw_json = await self._call_gemini(
                system_prompt=PROPOSAL_SYSTEM_INSTRUCTION,
                user_prompt=prompt,
                response_schema=RecoveryProposal,
            )
            data = json.loads(raw_json)
            # Ensure model metadata is attached
            data["model_name"] = self.model_identifier
            data["prompt_version"] = PROPOSAL_PROMPT_VERSION
            return RecoveryProposal.model_validate(data)
        except Exception as e:
            logger.error("Gemini proposal formulation failed; falling back to HUMAN_REVIEW: %s", str(e))
            return RecoveryProposal(
                action=RecoveryAction.HUMAN_REVIEW,
                confidence=0.5,
                delay_minutes=0,
                reason_codes=["MODEL_PROVIDER_ERROR_FALLBACK"],
                explanation=f"AI provider failed ({str(e)}). Safely escalating case for human operator review.",
                requires_human_approval=True,
                model_name=self.model_identifier,
                prompt_version=PROPOSAL_PROMPT_VERSION,
            )

    async def draft_customer_message(self, case: PaymentCase, action: RecoveryAction) -> Optional[str]:
        """Draft message via Gemini."""
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
            msg = await self._call_gemini(
                system_prompt=MESSAGE_SYSTEM_INSTRUCTION,
                user_prompt=prompt,
            )
            return msg.strip()
        except Exception as e:
            logger.warning("Message drafting failed: %s; using deterministic template", str(e))
            return f"Hello {ctx.customer_name}, your subscription payment of INR {ctx.amount_inr:,.2f} needs attention."
