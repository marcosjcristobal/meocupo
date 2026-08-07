"""Persistence boundary required by task application use cases."""

# Protocol describes required behavior without choosing an implementation.
from typing import Protocol

# The application layer persists complete domain entities.
from personal_productivity.tasks.domain.task import Task


class TaskRepository(Protocol):
    """Define how task use cases communicate with persistent storage."""

    def add(self, task: Task) -> None:
        """Persist a newly created task."""

        # Concrete adapters will implement this operation.
        ...