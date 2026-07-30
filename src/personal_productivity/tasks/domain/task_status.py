"""Lifecycle states available to a task."""

# StrEnum lets enum members behave like strings at serialization boundaries.
from enum import StrEnum


class TaskStatus(StrEnum):
    """Represent the mutually exclusive lifecycle state persisted for a task."""

    # A pending task exists but active work has not started yet.
    PENDING = "pending"

    # An in-progress task has active work currently underway.
    IN_PROGRESS = "in_progress"

    # A paused task was started but is temporarily not being worked on.
    PAUSED = "paused"

    # A completed task successfully reached its intended outcome.
    COMPLETED = "completed"

    # A cancelled task was intentionally abandoned without being completed.
    CANCELLED = "cancelled"