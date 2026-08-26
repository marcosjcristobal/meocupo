"""Application use case for retrieving one task."""

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

# Successful retrieval returns a complete domain entity.
from personal_productivity.tasks.domain.task import Task


@dataclass(slots=True, kw_only=True)
class GetTask:
    """Retrieve one task through its portable identifier."""

    # Dependency injection keeps storage outside the application logic.
    repository: TaskRepository

    def execute(
        self,
        *,
        task_id: UUID,
    ) -> Task:
        """Return the requested task or report that it is absent."""

        # Delegate shared validation and required retrieval.
        return get_existing_task(
            repository=self.repository,
            task_id=task_id,
        )
