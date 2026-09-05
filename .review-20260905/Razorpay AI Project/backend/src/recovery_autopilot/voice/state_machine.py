"""
Deterministic Multilingual Conversation State Machine.
Enforces strict lifecycle transitions and idempotency for Voice Recovery dialogue.
"""
from enum import Enum
from typing import Dict, List, Set, Optional


class VoiceConversationState(str, Enum):
    """Canonical states required for conversational recovery lifecycle."""
    CONSENT_REQUIRED = "consent_required"
    LISTENING = "listening"
    TRANSCRIBING = "transcribing"
    UNDERSTANDING = "understanding"
    CLARIFICATION_REQUIRED = "clarification_required"
    PROPOSING_ACTION = "proposing_action"
    CONFIRMATION_REQUIRED = "confirmation_required"
    EXECUTING = "executing"
    SPEAKING = "speaking"
    PROMISE_TO_PAY_CREATED = "promise_to_pay_created"
    HUMAN_ESCALATION = "human_escalation"
    STOPPED = "stopped"
    COMPLETED = "completed"
    FAILED_SAFELY = "failed_safely"


class InvalidStateTransitionError(Exception):
    """Raised when an illegal or out-of-order state transition is attempted."""
    def __init__(self, from_state: VoiceConversationState, to_state: VoiceConversationState, reason: str = ""):
        self.from_state = from_state
        self.to_state = to_state
        self.reason = reason
        super().__init__(f"Illegal state transition from '{from_state.value}' to '{to_state.value}': {reason}")


# Strict DAG of valid conversation transitions
VALID_TRANSITIONS: Dict[VoiceConversationState, Set[VoiceConversationState]] = {
    VoiceConversationState.CONSENT_REQUIRED: {
        VoiceConversationState.LISTENING,
        VoiceConversationState.SPEAKING,
        VoiceConversationState.STOPPED,
        VoiceConversationState.HUMAN_ESCALATION,
        VoiceConversationState.FAILED_SAFELY,
    },
    VoiceConversationState.LISTENING: {
        VoiceConversationState.TRANSCRIBING,
        VoiceConversationState.SPEAKING,
        VoiceConversationState.STOPPED,
        VoiceConversationState.HUMAN_ESCALATION,
        VoiceConversationState.FAILED_SAFELY,
    },
    VoiceConversationState.TRANSCRIBING: {
        VoiceConversationState.UNDERSTANDING,
        VoiceConversationState.CLARIFICATION_REQUIRED,
        VoiceConversationState.SPEAKING,
        VoiceConversationState.FAILED_SAFELY,
    },
    VoiceConversationState.UNDERSTANDING: {
        VoiceConversationState.PROPOSING_ACTION,
        VoiceConversationState.CONFIRMATION_REQUIRED,
        VoiceConversationState.CLARIFICATION_REQUIRED,
        VoiceConversationState.HUMAN_ESCALATION,
        VoiceConversationState.STOPPED,
        VoiceConversationState.SPEAKING,
        VoiceConversationState.FAILED_SAFELY,
    },
    VoiceConversationState.CLARIFICATION_REQUIRED: {
        VoiceConversationState.SPEAKING,
        VoiceConversationState.LISTENING,
        VoiceConversationState.HUMAN_ESCALATION,
        VoiceConversationState.STOPPED,
        VoiceConversationState.FAILED_SAFELY,
    },
    VoiceConversationState.PROPOSING_ACTION: {
        VoiceConversationState.CONFIRMATION_REQUIRED,
        VoiceConversationState.SPEAKING,
        VoiceConversationState.LISTENING,
        VoiceConversationState.HUMAN_ESCALATION,
        VoiceConversationState.STOPPED,
        VoiceConversationState.FAILED_SAFELY,
    },
    VoiceConversationState.CONFIRMATION_REQUIRED: {
        VoiceConversationState.EXECUTING,
        VoiceConversationState.PROMISE_TO_PAY_CREATED,
        VoiceConversationState.SPEAKING,
        VoiceConversationState.LISTENING,
        VoiceConversationState.PROPOSING_ACTION,
        VoiceConversationState.HUMAN_ESCALATION,
        VoiceConversationState.STOPPED,
        VoiceConversationState.FAILED_SAFELY,
    },
    VoiceConversationState.EXECUTING: {
        VoiceConversationState.COMPLETED,
        VoiceConversationState.PROMISE_TO_PAY_CREATED,
        VoiceConversationState.SPEAKING,
        VoiceConversationState.FAILED_SAFELY,
    },
    VoiceConversationState.SPEAKING: {
        VoiceConversationState.LISTENING,
        VoiceConversationState.CONFIRMATION_REQUIRED,
        VoiceConversationState.PROPOSING_ACTION,
        VoiceConversationState.COMPLETED,
        VoiceConversationState.STOPPED,
        VoiceConversationState.HUMAN_ESCALATION,
        VoiceConversationState.PROMISE_TO_PAY_CREATED,
        VoiceConversationState.FAILED_SAFELY,
    },
    # Terminal states
    VoiceConversationState.PROMISE_TO_PAY_CREATED: {
        VoiceConversationState.SPEAKING,
        VoiceConversationState.COMPLETED,
    },
    VoiceConversationState.HUMAN_ESCALATION: set(),
    VoiceConversationState.STOPPED: set(),
    VoiceConversationState.COMPLETED: set(),
    VoiceConversationState.FAILED_SAFELY: set(),
}


class VoiceStateMachine:
    """Encapsulates deterministic state progression, guardrail enforcement, and idempotency."""

    def __init__(self, initial_state: VoiceConversationState = VoiceConversationState.CONSENT_REQUIRED):
        self.current_state = initial_state
        self.transition_history: List[Dict[str, str]] = []
        self.executed_action_id: Optional[str] = None

    def can_transition_to(self, target_state: VoiceConversationState) -> bool:
        """Returns True if transition from current state to target state is allowed."""
        # Self transitions are idempotent
        if self.current_state == target_state:
            return True
        allowed = VALID_TRANSITIONS.get(self.current_state, set())
        return target_state in allowed

    def transition_to(self, target_state: VoiceConversationState, reason: str = "") -> VoiceConversationState:
        """Performs state transition or raises InvalidStateTransitionError."""
        if not self.can_transition_to(target_state):
            raise InvalidStateTransitionError(self.current_state, target_state, reason)

        prev = self.current_state
        self.current_state = target_state
        self.transition_history.append({
            "from": prev.value,
            "to": target_state.value,
            "reason": reason,
        })
        return self.current_state

    def is_terminal(self) -> bool:
        """Returns True if state is terminal."""
        return self.current_state in {
            VoiceConversationState.HUMAN_ESCALATION,
            VoiceConversationState.STOPPED,
            VoiceConversationState.COMPLETED,
            VoiceConversationState.FAILED_SAFELY,
        }

    def mark_action_executed(self, action_id: str) -> bool:
        """Guarantees idempotency: returns False if action was already executed."""
        if self.executed_action_id == action_id:
            return False
        self.executed_action_id = action_id
        return True
