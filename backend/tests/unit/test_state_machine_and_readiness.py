"""
Unit Tests for Multilingual Voice State Machine, Deterministic Transitions, and Demo Readiness Engine.
"""
import pytest
from recovery_autopilot.voice.state_machine import (
    InvalidStateTransitionError,
    VoiceConversationState,
    VoiceStateMachine,
)
from recovery_autopilot.voice.readiness import VoiceReadinessChecker


def test_valid_state_transitions():
    sm = VoiceStateMachine(initial_state=VoiceConversationState.CONSENT_REQUIRED)
    assert sm.current_state == VoiceConversationState.CONSENT_REQUIRED

    # Move to listening
    sm.transition_to(VoiceConversationState.LISTENING, "Customer started speaking")
    assert sm.current_state == VoiceConversationState.LISTENING

    # Move to transcribing
    sm.transition_to(VoiceConversationState.TRANSCRIBING, "Audio captured")
    assert sm.current_state == VoiceConversationState.TRANSCRIBING

    # Move to understanding
    sm.transition_to(VoiceConversationState.UNDERSTANDING, "STT complete")
    assert sm.current_state == VoiceConversationState.UNDERSTANDING

    # Move to proposing action
    sm.transition_to(VoiceConversationState.PROPOSING_ACTION, "Payment link determined")
    assert sm.current_state == VoiceConversationState.PROPOSING_ACTION

    # Move to confirmation required
    sm.transition_to(VoiceConversationState.CONFIRMATION_REQUIRED, "Asking customer confirmation")
    assert sm.current_state == VoiceConversationState.CONFIRMATION_REQUIRED

    # Move to executing
    sm.transition_to(VoiceConversationState.EXECUTING, "Customer confirmed with Haan")
    assert sm.current_state == VoiceConversationState.EXECUTING

    # Move to completed
    sm.transition_to(VoiceConversationState.COMPLETED, "Link sent successfully")
    assert sm.current_state == VoiceConversationState.COMPLETED
    assert sm.is_terminal()


def test_illegal_state_transition_rejected():
    sm = VoiceStateMachine(initial_state=VoiceConversationState.CONSENT_REQUIRED)
    with pytest.raises(InvalidStateTransitionError):
        # Cannot jump straight from consent_required to executing without understanding/confirmation
        sm.transition_to(VoiceConversationState.EXECUTING, "Illegal jump")


def test_terminal_state_rejection():
    sm = VoiceStateMachine(initial_state=VoiceConversationState.STOPPED)
    assert sm.is_terminal()
    with pytest.raises(InvalidStateTransitionError):
        # Cannot transition out of stopped
        sm.transition_to(VoiceConversationState.LISTENING, "Cannot resume stopped session")


def test_idempotency_action_protection():
    sm = VoiceStateMachine(initial_state=VoiceConversationState.CONFIRMATION_REQUIRED)
    action_id = "act_link_99281"

    # First execution succeeds
    assert sm.mark_action_executed(action_id) is True

    # Duplicate execution attempt blocked
    assert sm.mark_action_executed(action_id) is False


@pytest.mark.asyncio
async def test_readiness_checker_audit():
    checker = VoiceReadinessChecker()
    report = await checker.run_readiness_audit()

    assert "is_ready" in report
    assert "readiness_score" in report
    assert report["readiness_score"] >= 75.0
    assert len(report["checks"]) >= 4
    assert len(report["supported_languages"]) == 7
    # Verify all checks have passed status and metric
    for check in report["checks"]:
        assert "passed" in check
        assert "metric" in check
