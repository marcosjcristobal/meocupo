"""Domain entity for a task."""

# Dataclass removes constructor boilerplate while preserving a regular Python class.
from dataclasses import dataclass, field
# UUID provides portable identifiers without requiring a database round trip.
from uuid import UUID, uuid4

# Import the domain types that define valid task values.
from personal_productivity.tasks.domain.task_priority import TaskPriority
from personal_productivity.tasks.domain.task_status import TaskStatus


@dataclass(slots=True, kw_only=True, eq=False)
class Task:
    """Represent a task whose lifecycle is controlled by domain rules."""

    # Every task needs a human-readable purpose.
    title: str

    # The factory generates a fresh identifier for every new task instance.
    id: UUID = field(default_factory=uuid4)

    # A newly created task always starts pending.
    status: TaskStatus = field(default=TaskStatus.PENDING, init=False)

    # Normal is the safest default when no explicit importance is supplied.
    priority: TaskPriority = TaskPriority.NORMAL

    def __post_init__(self) -> None:
        """Validate invariants immediately after dataclass initialization."""

        # A title containing only whitespace communicates no actionable purpose.
        if not self.title.strip():
            raise ValueError("Task title cannot be empty.")
