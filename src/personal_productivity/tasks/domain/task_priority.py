"""Priority levels available to a task."""

# StrEnum gives each priority a controlled name and a string representation.
from enum import StrEnum


class TaskPriority(StrEnum):
    """Represent the explicit importance assigned to a task."""

    # A critical task has exceptional consequences if it is not completed.
    CRITICAL = "critical"

    # A high-priority task has significant impact and deserves extra attention.
    HIGH = "high"

    # Normal is the default importance for tasks without exceptional impact.
    NORMAL = "normal"

    # A low-priority task has limited impact and may yield to more important work.
    LOW = "low"
