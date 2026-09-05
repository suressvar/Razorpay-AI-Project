"""Email drafting, simulated sending, and delivery tracking service.

Uses template-based generation. Integrates with issue tracking for
provenance and duplicate prevention.
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from recovery_autopilot.config import settings
from recovery_autopilot.domain.issue_models import (
    CommunicationChannel,
    CommunicationStatus,
    IssueCommunication,
    utc_now,
)
from recovery_autopilot.persistence.issue_repository import IssueRepository

logger = logging.getLogger("recovery_autopilot.services.email_service")


# --- Email Templates ---

EMAIL_TEMPLATES = {
    "payment_failure": {
        "subject": "Regarding your payment of ₹{amount} — {business_name}",
        "body_text": (
            "Dear {customer_name},\n\n"
            "We noticed that your recent payment of ₹{amount} was not successful.\n\n"
            "Reason: {failure_reason}\n\n"
            "{resolution_instruction}\n\n"
            "{payment_link_section}"
            "If you have any questions, please don't hesitate to reach out to us.\n\n"
            "Best regards,\n"
            "{business_name} Support Team"
        ),
        "body_html": (
            "<p>Dear {customer_name},</p>"
            "<p>We noticed that your recent payment of <strong>₹{amount}</strong> was not successful.</p>"
            "<p><strong>Reason:</strong> {failure_reason}</p>"
            "<p>{resolution_instruction}</p>"
            "{payment_link_section_html}"
            "<p>If you have any questions, please don't hesitate to reach out to us.</p>"
            "<p>Best regards,<br/>{business_name} Support Team</p>"
        ),
    },
    "payment_link": {
        "subject": "Complete your payment of ₹{amount} — {business_name}",
        "body_text": (
            "Dear {customer_name},\n\n"
            "Please complete your pending payment of ₹{amount} using the secure link below:\n\n"
            "{payment_link_url}\n\n"
            "This link is valid until {expiry_info}.\n\n"
            "If you have already made this payment, please disregard this message.\n\n"
            "Best regards,\n"
            "{business_name} Support Team"
        ),
        "body_html": (
            "<p>Dear {customer_name},</p>"
            "<p>Please complete your pending payment of <strong>₹{amount}</strong> using the secure link below:</p>"
            "<p><a href='{payment_link_url}' style='padding:10px 20px;background:#0052cc;color:white;text-decoration:none;border-radius:4px;'>Pay Now — ₹{amount}</a></p>"
            "<p>This link is valid until {expiry_info}.</p>"
            "<p>If you have already made this payment, please disregard this message.</p>"
            "<p>Best regards,<br/>{business_name} Support Team</p>"
        ),
    },
    "refund_update": {
        "subject": "Refund update for your payment — {business_name}",
        "body_text": (
            "Dear {customer_name},\n\n"
            "We wanted to update you on the refund for your payment of ₹{amount}.\n\n"
            "Refund Status: {refund_status}\n"
            "{refund_details}\n\n"
            "Please allow 5-7 business days for the refund to reflect in your account.\n\n"
            "Best regards,\n"
            "{business_name} Support Team"
        ),
        "body_html": (
            "<p>Dear {customer_name},</p>"
            "<p>We wanted to update you on the refund for your payment of <strong>₹{amount}</strong>.</p>"
            "<p><strong>Refund Status:</strong> {refund_status}</p>"
            "<p>{refund_details}</p>"
            "<p>Please allow 5-7 business days for the refund to reflect in your account.</p>"
            "<p>Best regards,<br/>{business_name} Support Team</p>"
        ),
    },
    "resolution": {
        "subject": "Your issue has been resolved — {business_name}",
        "body_text": (
            "Dear {customer_name},\n\n"
            "We're pleased to inform you that the issue regarding your payment of ₹{amount} "
            "has been resolved.\n\n"
            "Resolution: {resolution_summary}\n\n"
            "If you experience any further issues, please don't hesitate to contact us.\n\n"
            "Best regards,\n"
            "{business_name} Support Team"
        ),
        "body_html": (
            "<p>Dear {customer_name},</p>"
            "<p>We're pleased to inform you that the issue regarding your payment of "
            "<strong>₹{amount}</strong> has been resolved.</p>"
            "<p><strong>Resolution:</strong> {resolution_summary}</p>"
            "<p>If you experience any further issues, please don't hesitate to contact us.</p>"
            "<p>Best regards,<br/>{business_name} Support Team</p>"
        ),
    },
    "escalation": {
        "subject": "Update on your support request — {business_name}",
        "body_text": (
            "Dear {customer_name},\n\n"
            "Your support request regarding the payment of ₹{amount} has been escalated "
            "to our senior team for priority resolution.\n\n"
            "A specialist will review your case and reach out to you within 24 hours.\n\n"
            "Your reference number: {issue_id}\n\n"
            "Best regards,\n"
            "{business_name} Support Team"
        ),
        "body_html": (
            "<p>Dear {customer_name},</p>"
            "<p>Your support request regarding the payment of <strong>₹{amount}</strong> has been escalated "
            "to our senior team for priority resolution.</p>"
            "<p>A specialist will review your case and reach out to you within 24 hours.</p>"
            "<p><strong>Your reference number:</strong> {issue_id}</p>"
            "<p>Best regards,<br/>{business_name} Support Team</p>"
        ),
    },
}


class EmailService:
    """Service for drafting, storing, and simulating email sends."""

    def __init__(self):
        self.business_name = "Recovery Autopilot"

    async def generate_draft(
        self,
        session: AsyncSession,
        template_id: str,
        recipient_email: str,
        recipient_name: str,
        template_vars: Dict[str, Any],
        issue_id: Optional[str] = None,
        case_id: Optional[str] = None,
        created_by: str = "copilot",
    ) -> Dict[str, Any]:
        """Generate and persist an email draft from a template.

        Returns the draft record dict including draft_id for later retrieval.
        """
        issue_repo = IssueRepository(session)

        template = EMAIL_TEMPLATES.get(template_id)
        if not template:
            raise ValueError(f"Unknown email template: {template_id}. Available: {list(EMAIL_TEMPLATES.keys())}")

        # Ensure business_name and basic vars
        vars_with_defaults = {
            "business_name": self.business_name,
            "customer_name": recipient_name,
            "payment_link_section": "",
            "payment_link_section_html": "",
            "payment_link_url": "",
            "expiry_info": "the specified expiry date",
            "refund_status": "Processing",
            "refund_details": "",
            "resolution_summary": "",
            "issue_id": issue_id or "",
            **template_vars,
        }

        # Safely format template with available vars
        try:
            subject = template["subject"].format(**vars_with_defaults)
            body_text = template["body_text"].format(**vars_with_defaults)
            body_html = template["body_html"].format(**vars_with_defaults)
        except KeyError as e:
            logger.warning("Missing template variable: %s", e)
            subject = template["subject"].format_map({**vars_with_defaults, **{str(e).strip("'"): f"[{e}]"}})
            body_text = template["body_text"].format_map({**vars_with_defaults, **{str(e).strip("'"): f"[{e}]"}})
            body_html = template["body_html"].format_map({**vars_with_defaults, **{str(e).strip("'"): f"[{e}]"}})

        # Sanitize: no secrets, internal logs, or unsupported claims
        for sensitive in ["api_key", "key_secret", "webhook_secret", "rzp_test_", "rzp_live_"]:
            if sensitive in body_text.lower():
                raise ValueError(f"Email body contains sensitive content: {sensitive}")

        draft_id = f"draft_{uuid.uuid4().hex[:12]}"
        idempotency_key = f"email_{case_id or issue_id or 'generic'}_{template_id}_{uuid.uuid4().hex[:6]}"

        # Check for duplicate draft
        existing = await issue_repo.find_draft_by_idempotency_key(idempotency_key)
        if existing:
            logger.info("Returning existing draft %s for idempotency key %s", existing["draft_id"], idempotency_key)
            return existing

        draft = {
            "draft_id": draft_id,
            "issue_id": issue_id,
            "case_id": case_id,
            "template_id": template_id,
            "recipient_email": recipient_email,
            "recipient_name": recipient_name,
            "subject": subject,
            "body_html": body_html,
            "body_text": body_text,
            "status": "DRAFT",
            "idempotency_key": idempotency_key,
            "created_by": created_by,
        }

        await issue_repo.save_email_draft(draft)
        logger.info("Email draft %s created for %s (template: %s)", draft_id, recipient_email, template_id)

        return draft

    async def send_email(
        self,
        session: AsyncSession,
        draft_id: str,
        operator_id: str = "copilot",
    ) -> Dict[str, Any]:
        """Send an email draft. In synthetic mode, simulates the send.

        Returns status and provider_message_id.
        """
        issue_repo = IssueRepository(session)

        draft = await issue_repo.get_email_draft(draft_id)
        if not draft:
            raise ValueError(f"Email draft {draft_id} not found")

        # Prevent duplicate sends
        if draft["status"] in ("ACCEPTED", "DELIVERED"):
            logger.warning("Draft %s already sent (status: %s). Preventing duplicate.", draft_id, draft["status"])
            return {
                "status": draft["status"],
                "draft_id": draft_id,
                "provider_message_id": draft.get("provider_message_id"),
                "message": "Email was already sent. Duplicate send prevented.",
                "is_duplicate": True,
            }

        if draft["status"] == "QUEUED":
            return {
                "status": "QUEUED",
                "draft_id": draft_id,
                "message": "Email is already queued for delivery.",
                "is_duplicate": True,
            }

        # Validate recipient
        if not draft["recipient_email"] or "@" not in draft["recipient_email"]:
            await issue_repo.update_draft_status(draft_id, "FAILED", error_message="Invalid recipient email")
            raise ValueError(f"Invalid recipient email: {draft['recipient_email']}")

        # Simulated send (safe for development/testing)
        provider_message_id = f"sim_msg_{uuid.uuid4().hex[:12]}"

        if settings.SYNTHETIC_MODE or settings.SIMULATE_NOTIFICATIONS:
            # Simulated delivery
            await issue_repo.update_draft_status(
                draft_id,
                status="ACCEPTED",
                provider_message_id=provider_message_id,
            )
            logger.info(
                "SIMULATED email send: draft=%s, to=%s, subject=%s, provider_id=%s",
                draft_id, draft["recipient_email"], draft["subject"], provider_message_id,
            )

            # Update associated issue if exists
            if draft.get("issue_id"):
                issue = await issue_repo.get_issue(draft["issue_id"])
                if issue:
                    comm = IssueCommunication(
                        channel=CommunicationChannel.EMAIL,
                        direction="outbound",
                        recipient=draft["recipient_email"],
                        subject=draft["subject"],
                        body=draft["body_text"],
                        template_used=draft.get("template_id"),
                        provider_message_id=provider_message_id,
                        status=CommunicationStatus.ACCEPTED,
                        idempotency_key=draft.get("idempotency_key"),
                        sent_at=utc_now(),
                    )
                    issue.add_communication(comm)
                    await issue_repo.save_issue(issue)

            return {
                "status": "ACCEPTED",
                "draft_id": draft_id,
                "provider_message_id": provider_message_id,
                "recipient": draft["recipient_email"],
                "subject": draft["subject"],
                "message": "Email accepted for delivery (simulated mode).",
                "is_simulated": True,
                "is_duplicate": False,
            }
        else:
            # Real email send would go here — document what's needed
            await issue_repo.update_draft_status(draft_id, "FAILED", error_message="No email provider configured")
            return {
                "status": "FAILED",
                "draft_id": draft_id,
                "message": "No email provider is configured. Configure an email provider (SendGrid, SES, Resend) in settings to enable real email sends.",
                "is_simulated": False,
                "is_duplicate": False,
            }


# Singleton
email_service = EmailService()
