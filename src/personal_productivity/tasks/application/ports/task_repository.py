"""Persistence boundary required by task application use cases."""

# Protocol describes required behavior without choosing an implementation.
from typing import Protocol

# UUID identifies tasks without exposing database-specific keys.
from uuid import UUID

# The application layer persists complete domain entities.
from personal_productivity.tasks.domain.task import Task


class TaskRepository(Protocol):
    """Define how task use cases communicate with persistent storage."""

    def add(self, task: Task) -> None:
        """Persist a newly created task."""

        # Concrete adapters will implement this operation.
        ...

    def get_by_id(self, task_id: UUID) -> Task | None:
        """Return one task by identity or report that it is absent."""

        # Concrete adapters decide how stored entities are located.
        ...
