"""Unit tests for the task listing application use case."""

# UUID keeps the test double compatible with the repository port.
from uuid import UUID

# Import the use case that coordinates collection retrieval.
from personal_productivity.tasks.application.list_tasks import ListTasks

# Listing tests use complete domain entities.
from personal_productivity.tasks.domain.task import Task


class ReturningTaskCollectionRepository:
    """Return a configured immutable collection of tasks."""

    def __init__(self, tasks: tuple[Task, ...]) -> None:
        """Configure the snapshot returned by the repository."""

        # The test controls the exact collection available to the use case.
        self.tasks = tasks

        # A counter makes repeated or missing repository calls observable.
        self.list_call_count = 0

    def add(self, task: Task) -> None:
        """Reject writes because this test repository is read-only."""

        # A listing use case must never perform persistence writes.
        raise AssertionError("ListTasks must not add tasks.")

    def get_by_id(self, task_id: UUID) -> Task | None:
        """Reject identity queries because listing does not retrieve one task."""

        # The test fails immediately if the wrong repository operation is used.
        raise AssertionError("ListTasks must not query one task by ID.")

    def list_all(self) -> tuple[Task, ...]:
        """Return the configured collection and record the interaction."""

        # Count the exact number of collection queries.
        self.list_call_count += 1

        # Return the immutable repository snapshot.
        return self.tasks


def test_list_tasks_returns_repository_snapshot() -> None:
    """Verify that listing returns every entity supplied by persistence."""

    # Arrange: configure two existing tasks in one repository snapshot.
    first_task = Task(title="Study Docker.")
    second_task = Task(title="Buy soil for the pitaya.")
    expected_tasks = (
        first_task,
        second_task,
    )
    repository = ReturningTaskCollectionRepository(
        tasks=expected_tasks,
    )
    use_case = ListTasks(repository=repository)

    # Act: retrieve the complete task collection.
    listed_tasks = use_case.execute()

    # Assert: the application returns the same immutable snapshot.
    assert listed_tasks is expected_tasks

    # Assert: the repository was queried exactly once.
    assert repository.list_call_count == 1
