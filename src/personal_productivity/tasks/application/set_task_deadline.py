"""Application use case for assigning one task deadline."""

# Dataclass provides explicit dependency injection with minimal boilerplate.
from dataclasses import dataclass

# UUID represents the portable identity supplied by an external channel.
from uuid import UUID

# The use case depends only on the repository contract.
from personal_productivity.tasks.application.ports.task_repository import (
    TaskRepository,
)

# Shared lookup centralizes identity validation and absence handling.
from personal_productivity.tasks.application.task_lookup import (
    get_existing_task,
)

# Task contains the authoritative deadline operation.
from personal_productivity.tasks.domain.task import Task

# Deadline carries one validated temporal commitment.
from personal_productivity.tasks.domain.task_deadline import TaskDeadline


@dataclass(slots=True, kw_only=True)
class SetTaskDeadline:
    """Assign one task deadline and persist its newer planning state."""

    # Dependency injection keeps storage outside application logic.
    repository: TaskRepository

    def execute(
        self,
        *,
        task_id: UUID,
        deadline: TaskDeadline,
    ) -> Task:
        """Assign or replace one task completion deadline."""

        # Delegate shared validation and required retrieval.
        task = get_existing_task(
            repository=self.repository,
            task_id=task_id,
        )

        # Delegate type and editability rules to the domain entity.
        task.set_deadline(deadline)

        # Persist only after the domain operation succeeds.
        self.repository.save(task)

        # Return the updated entity to the calling interface.
        return task
