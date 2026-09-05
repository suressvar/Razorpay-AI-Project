"""Unit tests for AI proposal and diagnosis schema validation using fixtures."""

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from recovery_autopilot.domain.enums import FailureCategory, RecoveryAction
from recovery_autopilot.domain.models import RecoveryProposal
from recovery_autopilot.model_providers.base import DiagnosisResult

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures" / "model_responses"


def test_valid_proposal_fixture():
    """Valid proposal fixture should load and pass schema validation."""
    with open(FIXTURES_DIR / "valid_proposal.json", "r") as f:
        data = json.load(f)
    proposal = RecoveryProposal.model_validate(data)
    assert proposal.action == RecoveryAction.SEND_PAYMENT_LINK
    assert proposal.confidence == 0.86
    assert proposal.delay_minutes == 120
    assert proposal.requires_human_approval is False


def test_prohibited_action_fixture():
    """Arbitrary/prohibited actions must be rejected by RecoveryProposal enum validation."""
    with open(FIXTURES_DIR / "prohibited_action.json", "r") as f:
        data = json.load(f)
    with pytest.raises(ValidationError) as exc_info:
        RecoveryProposal.model_validate(data)
    assert "Input should be 'WAIT_FOR_RETRY', 'SEND_PAYMENT_LINK'" in str(exc_info.value)


def test_missing_fields_fixture():
    """Missing required schema fields must raise ValidationError."""
    with open(FIXTURES_DIR / "missing_fields.json", "r") as f:
        data = json.load(f)
    with pytest.raises(ValidationError):
        RecoveryProposal.model_validate(data)


def test_diagnosis_schema_validation():
    """DiagnosisResult correctly validates structured diagnosis outputs."""
    valid_data = {
        "failure_category": "BANK_TIMEOUT",
        "confidence": 0.91,
        "is_transient": True,
        "evidence_signals": ["SWITCH_TIMEOUT"],
        "reasoning": "Bank response delayed by over 30 seconds.",
        "suggested_action": "WAIT_FOR_RETRY",
    }
    diag = DiagnosisResult.model_validate(valid_data)
    assert diag.failure_category == FailureCategory.BANK_TIMEOUT
    assert diag.suggested_action == RecoveryAction.WAIT_FOR_RETRY
    assert diag.is_transient is True
