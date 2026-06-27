"""Application-wide enums and constants."""

from enum import Enum


class DraftStatus(str, Enum):
    """Post draft status values."""

    PENDING = "pending"  # Added for agent compatibility
    DRAFTED = "drafted"
    APPROVED = "approved"
    POSTED = "posted"
    FAILED = "failed"


class EngagementStatus(str, Enum):
    """Pending engagement status values."""

    PENDING = "pending"
    APPROVED = "approved"
    SKIPPED = "skipped"
    POSTED = "posted"
    COMPLETED = "completed"  # Added for monitoring agent
    FAILED = "failed"


class GraphStatus(str, Enum):
    """Graph run status values."""

    RUNNING = "running"
    WAITING_HUMAN = "waiting_human"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ActionType(str, Enum):
    """LinkedIn engagement action types."""

    LIKE = "like"
    CELEBRATE = "celebrate"
    SUPPORT = "support"
    INSIGHTFUL = "insightful"
    COMMENT = "comment"


# Alias for monitoring agent compatibility
EngagementType = ActionType


class BrowserProvider(str, Enum):
    """Browser control provider options."""

    KIMI_WEBBRIDGE = "kimi_webbridge"
    PLAYWRIGHT = "playwright"


class BrowserSessionStatus(str, Enum):
    """Browser session connection status."""

    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"


# Valid status transitions
DRAFT_STATUS_TRANSITIONS = {
    DraftStatus.PENDING: [DraftStatus.DRAFTED, DraftStatus.APPROVED, DraftStatus.FAILED],
    DraftStatus.DRAFTED: [DraftStatus.APPROVED, DraftStatus.FAILED],
    DraftStatus.APPROVED: [DraftStatus.POSTED, DraftStatus.FAILED],
    DraftStatus.POSTED: [],  # Terminal state
    DraftStatus.FAILED: [],  # Terminal state
}

ENGAGEMENT_STATUS_TRANSITIONS = {
    EngagementStatus.PENDING: [
        EngagementStatus.APPROVED,
        EngagementStatus.SKIPPED,
    ],
    EngagementStatus.APPROVED: [
        EngagementStatus.POSTED,
        EngagementStatus.COMPLETED,
        EngagementStatus.FAILED,
    ],
    EngagementStatus.SKIPPED: [],  # Terminal state
    EngagementStatus.POSTED: [],  # Terminal state
    EngagementStatus.COMPLETED: [],  # Terminal state
    EngagementStatus.FAILED: [],  # Terminal state
}


def validate_status_transition(
    current_status: str, new_status: str, transitions: dict[str, list[str]]
) -> bool:
    """Validate if a status transition is allowed.

    Args:
        current_status: Current status value
        new_status: Desired new status value
        transitions: Dictionary of valid transitions

    Returns:
        True if transition is valid, False otherwise
    """
    allowed_transitions = transitions.get(current_status, [])
    return new_status in allowed_transitions
