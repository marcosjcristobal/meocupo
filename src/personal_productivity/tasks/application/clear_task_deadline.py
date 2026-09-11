"""Application use case for clearing one task deadline."""

# Dataclass provides concise dependency injection.
from dataclasses import dataclass

# UUID represents the task identity at the application boundary.
from uuid import UUID

# Repository keeps the use case independent from concrete storage.
from personal_productivity.tasks.application.ports.task_repository import (
    TaskRepository,
)

# Shared lookup centralizes identity validation and missing-task handling.
from personal_productivity.tasks.application.task_lookup import (
    get_existing_task,
)

# Task is the domain entity returned after the operation.
from personal_productivity.tasks.domain.task import Task


@dataclass(slots=True, kw_only=True)
class ClearTaskDeadline:
    """Clear one task deadline and persist its newer planning state."""

    # The application depends only on the repository abstraction.
    repository: TaskRepository

    def execute(
        self,
        *,
        task_id: UUID,
    ) -> Task:
        """Remove the task's current completion deadline."""

        # Retrieve one existing entity through the shared lookup policy.
        task = get_existing_task(
            repository=self.repository,
            task_id=task_id,
        )

        # Delegate editability rules and the actual change to the domain.
        task.clear_deadline()

        # Persist only after the domain operation succeeds.
        self.repository.save(task)

        # Return the updated entity to the caller.
        return task