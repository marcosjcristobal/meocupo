"""Domain entity for a task."""

# Dataclass removes constructor boilerplate while preserving a regular Python class.
from dataclasses import dataclass, field
# Datetime represents lifecycle instants without coupling the entity to a clock.
from datetime import date, datetime
# UUID provides portable identifiers without requiring a database round trip.
from uuid import UUID, uuid4

# Import the domain types that define valid task values.
from personal_productivity.tasks.domain.task_priority import TaskPriority
from personal_productivity.tasks.domain.task_status import TaskStatus
from personal_productivity.tasks.domain.task_deadline import TaskDeadline


class InvalidTaskTransitionError(ValueError):
    """Raised when a requested task lifecycle transition is not allowed."""


class TaskNotEditableError(ValueError):
    """Raised when a terminal task receives a planning modification."""

@dataclass(slots=True, kw_only=True, eq=False)
class Task:
    """Represent a task whose lifecycle is controlled by domain rules."""

    # Every task needs a human-readable purpose.
    title: str

    # Optional context may explain the task without becoming its identity.
    description: str | None = None

    # Exact minutes preserve more information than a broad effort category.
    estimated_minutes: int | None = None

    # A validated value object preserves either date-only or exact-time intent.
    deadline: TaskDeadline | None = None

    # The factory generates a fresh identifier for every new task instance.
    id: UUID = field(default_factory=uuid4)

    # Private storage prevents callers from bypassing lifecycle methods.
    _status: TaskStatus = field(
        default=TaskStatus.PENDING,
        init=False,
        repr=False,
    )

    # Unfinished tasks have no completion instant.
    _completed_at: datetime | None = field(
        default=None,
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

    @property
    def completed_at(self) -> datetime | None:
        """Expose when the task was completed, if completion has occurred."""

        # External layers may read but cannot directly replace this value.
        return self._completed_at

    def is_overdue(
        self,
        *,
        today: date,
        now: datetime,
    ) -> bool:
        """Calculate delay from explicit local and absolute references."""

        # Terminal outcomes no longer represent outstanding work.
        if self._status in (
            TaskStatus.COMPLETED,
            TaskStatus.CANCELLED,
        ):
            return False

        # Without a deadline there is no temporal promise to violate.
        if self.deadline is None:
            return False

        # Date-only deadlines use the user's local calendar boundary.
        if self.deadline.due_on is not None:
            return today > self.deadline.due_on

        # Exact comparisons require an unambiguous reference instant.
        if now.tzinfo is None or now.utcoffset() is None:
            raise ValueError("Current time must include a timezone.")

        # TaskDeadline guarantees that the remaining variant contains due_at.
        assert self.deadline.due_at is not None
        return now > self.deadline.due_at

    def __post_init__(self) -> None:
        """Validate and normalize invariants after dataclass initialization."""

        # Remove accidental whitespace once and reuse the normalized result.
        normalized_title = self.title.strip()

        # Normalize optional text so blank and absent descriptions are equivalent.
        if self.description is not None:
            normalized_description = self.description.strip()
            self.description = normalized_description or None

        # A title containing only whitespace communicates no actionable purpose.
        if not normalized_title:
            raise ValueError("Task title cannot be empty.")

        # Persist the canonical representation used by every external channel.
        self.title = normalized_title

        # Validate runtime type because annotations alone do not enforce it.
        if self.estimated_minutes is not None:
            if isinstance(self.estimated_minutes, bool) or not isinstance(
                self.estimated_minutes,
                int,
            ):
                raise TypeError("Estimated minutes must be an integer.")

            # An explicit estimate must represent a positive amount of work.
            if self.estimated_minutes <= 0:
                raise ValueError("Estimated minutes must be greater than zero.")

        # Deadline rules belong to TaskDeadline, so Task only enforces the boundary.
        if self.deadline is not None and not isinstance(
            self.deadline,
            TaskDeadline,
        ):
            raise TypeError("Task deadline must be a TaskDeadline.")

    def start(self) -> None:
        """Move a pending task into active work."""

        # Starting is valid only before active work has begun.
        if self._status is not TaskStatus.PENDING:
            raise InvalidTaskTransitionError(
                f"Cannot start a task from '{self._status.value}'."
            )

        # Mutate the entity only after every transition rule has passed.
        self._status = TaskStatus.IN_PROGRESS

    def pause(self) -> None:
        """Temporarily stop work on an in-progress task."""

        # Pausing requires work to be actively underway.
        if self._status is not TaskStatus.IN_PROGRESS:
            raise InvalidTaskTransitionError(
                f"Cannot pause a task from '{self._status.value}'."
            )

        # Apply the transition only after validating its origin.
        self._status = TaskStatus.PAUSED

    def resume(self) -> None:
        """Continue work on a paused task."""

        # Resuming is meaningful only when work was previously paused.
        if self._status is not TaskStatus.PAUSED:
            raise InvalidTaskTransitionError(
                f"Cannot resume a task from '{self._status.value}'."
            )

        # Return the task to active work after validating its origin.
        self._status = TaskStatus.IN_PROGRESS

    def complete(self, *, completed_at: datetime) -> None:
        """Mark an unfinished task as completed at an explicit instant."""

        # Pending, active, and paused tasks are all unfinished and completable.
        if self._status not in (
            TaskStatus.PENDING,
            TaskStatus.IN_PROGRESS,
            TaskStatus.PAUSED,
        ):
            raise InvalidTaskTransitionError(
                f"Cannot complete a task from '{self._status.value}'."
            )

        # A timezone-aware datetime maps completion to one absolute instant.
        if completed_at.tzinfo is None or completed_at.utcoffset() is None:
            raise ValueError("Completion time must include a timezone.")

        # Update state and completion metadata only after transition validation.
        self._status = TaskStatus.COMPLETED
        self._completed_at = completed_at

    def cancel(self) -> None:
        """Abandon an unfinished task without recording completion."""

        # Only unfinished lifecycle states may transition to cancelled.
        if self._status not in (
            TaskStatus.PENDING,
            TaskStatus.IN_PROGRESS,
            TaskStatus.PAUSED,
        ):
            raise InvalidTaskTransitionError(
                f"Cannot cancel a task from '{self._status.value}'."
            )

        # Cancellation changes lifecycle state but never completion metadata.
        self._status = TaskStatus.CANCELLED

    def set_deadline(self, deadline: TaskDeadline) -> None:
        """Assign or replace the deadline of an unfinished task."""

        # Terminal tasks retain the planning data that produced their outcome.
        self._ensure_editable(action="change deadline")

        # Reuse the value object boundary instead of duplicating its rules.
        if not isinstance(deadline, TaskDeadline):
            raise TypeError("Task deadline must be a TaskDeadline.")

        # Replacing an immutable value keeps the update conceptually atomic.
        self.deadline = deadline

    def clear_deadline(self) -> None:
        """Remove the deadline from an unfinished task."""

        # Terminal tasks retain their historical temporal context.
        self._ensure_editable(action="clear deadline")

        # None is the canonical representation for a task without a deadline.
        self.deadline = None

    def _ensure_editable(self, *, action: str) -> None:
        """Reject planning changes after the task reaches a terminal state."""

        # Completed and cancelled tasks represent immutable historical outcomes.
        if self._status in (
            TaskStatus.COMPLETED,
            TaskStatus.CANCELLED,
        ):
            raise TaskNotEditableError(
                f"Cannot {action} for a task in '{self._status.value}'."
            )
