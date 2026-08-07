"""In-memory implementation of the task repository port."""

# UUID provides the dictionary key used for task identity.
from uuid import UUID

# The adapter stores complete domain entities without modifying them.
from personal_productivity.tasks.domain.task import Task

# Repository conflicts use the storage-independent port exception.
from personal_productivity.tasks.application.ports.task_repository import (
    TaskAlreadyExistsError,
)


class InMemoryTaskRepository:
    """Store tasks inside the current Python process."""

    def __init__(self) -> None:
        """Initialize an empty identity-indexed collection."""

        # A dictionary provides direct lookup through the task UUID.
        self._tasks_by_id: dict[UUID, Task] = {}

    def add(self, task: Task) -> None:
        """Store a newly created task under its identity."""

        # Runtime validation protects storage from arbitrary external values.
        if not isinstance(task, Task):
            raise TypeError("Stored value must be a Task.")

        # Add semantics must never overwrite an existing identity.
        if task.id in self._tasks_by_id:
            raise TaskAlreadyExistsError(
                f"Task '{task.id}' already exists."
            )

        # Keep the authoritative domain entity available for later use cases.
        self._tasks_by_id[task.id] = task

    def get_by_id(self, task_id: UUID) -> Task | None:
        """Return a stored task or None when its identity is unknown."""

        # Runtime validation keeps repository keys inside the port contract.
        if not isinstance(task_id, UUID):
            raise TypeError("Task identifier must be a UUID.")

        # Dictionary lookup represents absence without raising a storage error.
        return self._tasks_by_id.get(task_id)
