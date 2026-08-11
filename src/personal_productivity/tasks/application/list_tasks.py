"""Application use case for listing tasks."""

# Dataclass provides explicit dependency injection with minimal boilerplate.
from dataclasses import dataclass

# The use case depends on a port rather than a persistence implementation.
from personal_productivity.tasks.application.ports.task_repository import (
    TaskRepository,
)

# The application returns complete domain entities.
from personal_productivity.tasks.domain.task import Task


@dataclass(slots=True, kw_only=True)
class ListTasks:
    """Retrieve an immutable snapshot of every stored task."""

    # The caller injects any adapter satisfying the repository contract.
    repository: TaskRepository

    def execute(self) -> tuple[Task, ...]:
        """Return every task currently available in persistence."""

        # Collection loading belongs to the repository implementation.
        tasks = self.repository.list_all()

        # Return the immutable snapshot without duplicating domain behavior.
        return tasks