"""Domain entity for a task."""

# Dataclass removes constructor boilerplate while preserving a regular Python class.
from dataclasses import dataclass, field
# UUID provides portable identifiers without requiring a database round trip.
from uuid import UUID, uuid4

# Import the domain types that define valid task values.
from personal_productivity.tasks.domain.task_priority import TaskPriority
from personal_productivity.tasks.domain.task_status import TaskStatus


class InvalidTaskTransitionError(ValueError):
    """Raised when a requested task lifecycle transition is not allowed."""


@dataclass(slots=True, kw_only=True, eq=False)
class Task:
    """Represent a task whose lifecycle is controlled by domain rules."""

    # Every task needs a human-readable purpose.
    title: str

    # The factory generates a fresh identifier for every new task instance.
    id: UUID = field(default_factory=uuid4)

    # Private storage prevents callers from bypassing lifecycle methods.
    _status: TaskStatus = field(
        default=TaskStatus.PENDING,
        init=False,
        repr=False,
    )

    # Normal is the safest default when no explicit importance is supplied.
    priority: TaskPriority = TaskPriority.NORMAL

    @property
    def status(self) -> TaskStatus:
        """Expose the current lifecycle state without allowing direct replacement."""

        # Domain methods remain the only writers of the private state.
        return self._status

    def __post_init__(self) -> None:
        """Validate invariants immediately after dataclass initialization."""

        # A title containing only whitespace communicates no actionable purpose.
        if not self.title.strip():
            raise ValueError("Task title cannot be empty.")

    def start(self) -> None:
        """Move a pending task into active work."""

        # Starting is valid only before active work has begun.
        if self._status is not TaskStatus.PENDING:
            raise InvalidTaskTransitionError(
                f"Cannot start a task from '{self._status.value}'."
            )

        # Mutate the entity only after every transition rule has passed.
        self._status = TaskStatus.IN_PROGRESS
