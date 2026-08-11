"""Application use case for listing tasks."""

# Dataclass provides explicit dependency injection with minimal boilerplate.
from dataclasses import dataclass

# The use case depends on a port rather than a persistence implementation.
from personal_productivity.tasks.application.ports.task_repository import (
    TaskRepository,
)

# The application returns complete domain entities.
from personal_productivity.tasks.domain.task import Task

# TaskStatus defines the valid persisted lifecycle filters.
from personal_productivity.tasks.domain.task_status import TaskStatus

# TaskPriority defines the valid explicit importance filters.
from personal_productivity.tasks.domain.task_priority import TaskPriority


@dataclass(slots=True, kw_only=True)
class ListTasks:
    """Retrieve an immutable snapshot of every stored task."""

    # The caller injects any adapter satisfying the repository contract.
    repository: TaskRepository

    def execute(
        self,
        *,
        status: TaskStatus | None = None,
        priority: TaskPriority | None = None,
    ) -> tuple[Task, ...]:
        """Return tasks optionally filtered by status and priority."""

        # Runtime validation rejects malformed status before persistence.
        if status is not None and not isinstance(status, TaskStatus):
            raise TypeError(
                "Task status filter must be a TaskStatus."
            )

        # Runtime validation rejects malformed priority before persistence.
        if (
            priority is not None
            and not isinstance(priority, TaskPriority)
        ):
            raise TypeError(
                "Task priority filter must be a TaskPriority."
            )

        # Collection loading happens only after current validation succeeds.
        tasks = self.repository.list_all()

        # Missing filters preserve the complete repository snapshot.
        if status is None and priority is None:
            return tasks

        # Every supplied filter must match the resulting task.
        return tuple(
            task
            for task in tasks
            if (
                status is None
                or task.status is status
            )
            and (
                priority is None
                or task.priority is priority
            )
        )
