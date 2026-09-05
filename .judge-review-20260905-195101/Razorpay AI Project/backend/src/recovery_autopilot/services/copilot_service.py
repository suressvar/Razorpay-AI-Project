"""AI Copilot domain service for cross-referencing customer complaints with Razorpay records,
producing structured diagnoses, and executing bounded payment links with audit persistence.
"""

import json
import logging
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from recovery_autopilot.config import settings
from recovery_autopilot.domain.enums import ActorType, FailureCategory, RecoveryAction
from recovery_autopilot.domain.models import AuditEvent, utc_now
from recovery_autopilot.integrations.razorpay.payment_links import PaymentLinkAdapter
from recovery_autopilot.persistence.models import (
    PaymentCaseRecord,
    RecoveryActionRecord,
)
from recovery_autopilot.persistence.repository import SqlAlchemyRepository
from recovery_autopilot.policies.copilot_reasons import get_reason_detail

logger = logging.getLogger("recovery_autopilot.services.copilot")


def mask_phone(phone: Optional[str]) -> str:
    """Format phone as masked string e.g. +91 9944XXXX92."""
    if not phone:
        return "+91 9800XXXX00"
    clean = re.sub(r"[^\d+]", "", phone)
    if len(clean) >= 10:
        prefix = clean[:6] if clean.startswith("+") else clean[:4]
        suffix = clean[-2:]
        return f"{prefix}XXXX{suffix}"
    return f"{clean[:2]}XXXX{clean[-2:]}" if len(clean) > 4 else "+91 9800XXXX00"


class CopilotService:
    """Service orchestrating AI Copilot conversations, payment lookup, and action execution."""

    def __init__(self, payment_link_adapter: Optional[PaymentLinkAdapter] = None):
        self.link_adapter = payment_link_adapter or PaymentLinkAdapter(
            key_id=settings.RAZORPAY_KEY_ID,
            key_secret=settings.RAZORPAY_KEY_SECRET,
            test_mode=settings.SYNTHETIC_MODE,
        )

    def extract_entities(self, text: str) -> Dict[str, Any]:
        """Extract candidate payment IDs, emails, amounts, and names from text."""
        entities: Dict[str, Any] = {
            "payment_id": None,
            "case_id": None,
            "subscription_id": None,
            "email": None,
            "amount": None,
            "name_candidate": None,
        }

        # Payment ID pattern (e.g., pay_12345 or pay_syn_xxx)
        pay_match = re.search(r"\b(pay_[A-Za-z0-9_]+)\b", text, re.IGNORECASE)
        if pay_match:
            entities["payment_id"] = pay_match.group(1)

        # Case ID pattern (e.g., case_12345)
        case_match = re.search(r"\b(case_[A-Za-z0-9_]+)\b", text, re.IGNORECASE)
        if case_match:
            entities["case_id"] = case_match.group(1)

        # Sub ID pattern (e.g., sub_12345)
        sub_match = re.search(r"\b(sub_[A-Za-z0-9_]+)\b", text, re.IGNORECASE)
        if sub_match:
            entities["subscription_id"] = sub_match.group(1)

        # Email pattern
        email_match = re.search(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", text)
        if email_match:
            entities["email"] = email_match.group(0)

        # Amount pattern (e.g. ₹2000, Rs. 2,000, 2000 INR, 2000 rs)
        amt_match = re.search(r"(?:₹|rs\.?|inr)\s*([\d,]+(?:\.\d{1,2})?)", text, re.IGNORECASE)
        if not amt_match:
            amt_match = re.search(r"\b([\d,]+(?:\.\d{1,2})?)\s*(?:₹|rs\.?|inr|rupees)\b", text, re.IGNORECASE)
        if amt_match:
            try:
                amt_str = amt_match.group(1).replace(",", "")
                entities["amount"] = float(amt_str)
            except ValueError:
                pass

        # Name candidate heuristic (e.g. "for Rahul", "customer Rahul", "Rahul's")
        name_match = re.search(r"(?:for|customer|from|regarding|user)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)", text)
        if not name_match:
            name_match = re.search(r"([A-Z][a-z]+)'s\s+(?:payment|account|issue|card)", text)
        if name_match:
            entities["name_candidate"] = name_match.group(1).strip()

        return entities

    async def match_case(
        self,
        session: AsyncSession,
        entities: Dict[str, Any],
        raw_text: str,
    ) -> Optional[PaymentCaseRecord]:
        """Query database for the best matching failed payment record."""
        # 1. Exact ID matches
        if entities.get("case_id"):
            stmt = select(PaymentCaseRecord).where(PaymentCaseRecord.case_id == entities["case_id"])
            res = (await session.execute(stmt)).scalar_one_or_none()
            if res:
                return res

        if entities.get("payment_id"):
            stmt = select(PaymentCaseRecord).where(PaymentCaseRecord.payment_id == entities["payment_id"])
            res = (await session.execute(stmt)).scalar_one_or_none()
            if res:
                return res

        if entities.get("subscription_id"):
            stmt = select(PaymentCaseRecord).where(PaymentCaseRecord.subscription_id == entities["subscription_id"])
            res = (await session.execute(stmt)).scalars().first()
            if res:
                return res

        if entities.get("email"):
            stmt = select(PaymentCaseRecord).where(
                func.lower(PaymentCaseRecord.customer_email) == entities["email"].lower()
            ).order_by(desc(PaymentCaseRecord.created_at))
            res = (await session.execute(stmt)).scalars().first()
            if res:
                return res

        # 2. Match by candidate customer name
        if entities.get("name_candidate"):
            name = entities["name_candidate"].lower()
            stmt = select(PaymentCaseRecord).where(
                func.lower(PaymentCaseRecord.customer_name).contains(name)
            ).order_by(desc(PaymentCaseRecord.created_at))
            res = (await session.execute(stmt)).scalars().first()
            if res:
                return res

        # 3. Match any full word inside raw_text matching known customer names in DB
        # Fetch up to 20 recent cases to search in-memory
        recent_stmt = select(PaymentCaseRecord).order_by(desc(PaymentCaseRecord.created_at)).limit(25)
        recent_cases = (await session.execute(recent_stmt)).scalars().all()

        text_lower = raw_text.lower()
        for case in recent_cases:
            first_name = case.customer_name.split()[0].lower()
            if len(first_name) >= 3 and first_name in text_lower:
                return case
            if case.customer_email.lower() in text_lower:
                return case
            if case.payment_id.lower() in text_lower or case.case_id.lower() in text_lower:
                return case

        # 4. If amount is specified, match recent case with same amount
        if entities.get("amount"):
            amt = entities["amount"]
            for case in recent_cases:
                if abs(case.amount_inr - amt) < 1.0:
                    return case

        # 5. If query contains generic keywords like "failed", "customer", "issue", "payment" and we have cases,
        # return the latest active failure case as the representative record
        generic_keywords = ["customer", "payment", "failed", "issue", "complaint", "screenshot", "error", "help"]
        if any(kw in text_lower for kw in generic_keywords) and recent_cases:
            return recent_cases[0]

        return None

    async def process_chat(
        self,
        session: AsyncSession,
        query: str,
        image_base64: Optional[str] = None,
        image_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Process user support query / screenshot and return structured Copilot diagnosis."""
        entities = self.extract_entities(query)
        matched_record = await self.match_case(session, entities, query)

        # If no case is found anywhere in DB
        if not matched_record:
            return {
                "type": "fallback",
                "headline": None,
                "message": (
                    "I couldn't locate a matching payment record for this query. "
                    "Please provide a **Payment ID** (e.g., `pay_xxx`), **Customer Email**, "
                    "or **Customer Name** to diagnose the failure."
                ),
                "diagnosis": None,
                "suggestions": [
                    {"id": "s_1", "text": "Analyse all my failed payments", "action": "ANALYZE_ALL"},
                    {"id": "s_2", "text": "How do I create a payment link?", "action": "HELP_PAYMENT_LINK"},
                    {"id": "s_3", "text": "Search by Customer Email", "action": "SEARCH_EMAIL"},
                ],
            }

        # Build rich structured diagnosis
        category_enum = FailureCategory(matched_record.failure_category) if matched_record.failure_category in FailureCategory.__members__ else FailureCategory.UNKNOWN_FAILURE
        reason_detail = get_reason_detail(category_enum)

        formatted_amount = f"{matched_record.amount_inr:,.0f}" if matched_record.amount_inr.is_integer() else f"{matched_record.amount_inr:,.2f}"
        headline = reason_detail.headline_template.format(
            customer=matched_record.customer_name,
            amount=formatted_amount,
        )

        recommendation = reason_detail.recommendation.format(customer=matched_record.customer_name)
        followup_texts = [
            f.format(customer=matched_record.customer_name) for f in reason_detail.default_followups
        ]

        suggestions = [
            {
                "id": f"sug_{i+1}",
                "number": i + 1,
                "text": text,
                "action": "CREATE_PAYMENT_LINK" if i == 0 else "INFO_QUERY",
                "case_id": matched_record.case_id,
            }
            for i, text in enumerate(followup_texts)
        ]

        diagnosis_payload = {
            "case_id": matched_record.case_id,
            "payment_id": matched_record.payment_id,
            "customer_name": matched_record.customer_name,
            "customer_email": matched_record.customer_email,
            "customer_phone": matched_record.customer_phone,
            "masked_phone": mask_phone(matched_record.customer_phone),
            "amount_inr": matched_record.amount_inr,
            "currency": matched_record.currency or "INR",
            "failure_category": matched_record.failure_category,
            "failure_reason": matched_record.failure_reason,
            "headline": headline,
            "explanation": reason_detail.explanation,
            "auto_reversal_timeline": reason_detail.auto_reversal_timeline,
            "resolution_name": reason_detail.resolution_name,
            "resolution_instruction": reason_detail.resolution_instruction,
            "recommendation": recommendation,
        }

        return {
            "type": "diagnosis",
            "headline": headline,
            "diagnosis": diagnosis_payload,
            "suggestions": suggestions,
            "matched_case_id": matched_record.case_id,
        }

    async def create_payment_link(
        self,
        session: AsyncSession,
        case_id: str,
        amount_inr: float,
        customer_email: str,
        customer_phone: str,
        expiry_date: Optional[str] = None,
        note: Optional[str] = None,
        operator_name: str = "Support Agent",
    ) -> Dict[str, Any]:
        """Execute payment link creation via PaymentLinkAdapter and persist in audit & action records."""
        repo = SqlAlchemyRepository(session)
        case = await repo.get_case(case_id)
        if not case:
            raise ValueError(f"Case with ID {case_id} does not exist.")

        # Create updated context copy with operator supplied details if edited
        updated_context = case.context.model_copy(update={
            "amount_inr": amount_inr,
            "customer_email": customer_email,
            "customer_phone": customer_phone,
        })
        case.context = updated_context

        # Call adapter
        description = note or f"Payment for Subscription {case.context.subscription_id}"
        exec_result = await self.link_adapter.create_payment_link(case, description=description)


        if exec_result.status != "SUCCESS":
            raise RuntimeError(f"Payment Link API creation failed: {exec_result.error or 'Unknown error'}")

        plink_id = exec_result.external_id or f"plink_{uuid.uuid4().hex[:10]}"
        short_url = exec_result.metadata.get("short_url") or f"https://rzp.io/i/{plink_id}"

        # Persist recovery action record
        action_rec = RecoveryActionRecord(
            action_id=f"act_{uuid.uuid4().hex[:12]}",
            case_id=case.case_id,
            action=RecoveryAction.SEND_PAYMENT_LINK.value,
            external_id=plink_id,
            status="SUCCESS",
            idempotency_key=f"copilot_{case.case_id}_{uuid.uuid4().hex[:8]}",
            metadata_json=json.dumps({
                "source": "AI_COPILOT",
                "operator": operator_name,
                "amount_inr": amount_inr,
                "customer_email": customer_email,
                "customer_phone": customer_phone,
                "short_url": short_url,
                "expiry_date": expiry_date,
                "note": note,
            }),
            executed_at=utc_now(),
        )
        session.add(action_rec)

        # Persist audit trail event
        audit_event = AuditEvent(
            event_id=f"evt_{uuid.uuid4().hex[:12]}",
            case_id=case.case_id,
            timestamp=utc_now(),
            actor=ActorType.HUMAN,
            event_type="COPILOT_PAYMENT_LINK_CREATED",
            details={
                "operator": operator_name,
                "amount_inr": amount_inr,
                "short_url": short_url,
                "plink_id": plink_id,
                "customer_email": customer_email,
                "note": note,
                "expiry_date": expiry_date,
            },
        )
        await repo.record_audit(audit_event)

        # Update case status
        case.latest_action_result = exec_result
        case.contact_count += 1
        case.updated_at = utc_now()
        await repo.save_case(case)
        await session.commit()

        return {
            "status": "SUCCESS",
            "case_id": case_id,
            "payment_link_id": plink_id,
            "short_url": short_url,
            "amount_inr": amount_inr,
            "customer_email": customer_email,
            "customer_phone": mask_phone(customer_phone),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "note": note,
        }


copilot_service = CopilotService()
