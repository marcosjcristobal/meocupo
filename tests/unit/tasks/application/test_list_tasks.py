"""Unit tests for the task listing application use case."""

# UUID keeps the test double compatible with the repository port.
from uuid import UUID

# Pytest verifies runtime validation of external filter values.
import pytest

# Import the use case that coordinates collection retrieval.
from personal_productivity.tasks.application.list_tasks import ListTasks

# TaskStatus provides the persisted lifecycle filter vocabulary.
from personal_productivity.tasks.domain.task_status import TaskStatus

# Listing tests use complete domain entities.
from personal_productivity.tasks.domain.task import Task

# TaskPriority provides the explicit importance filter vocabulary.
from personal_productivity.tasks.domain.task_priority import TaskPriority


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


def test_list_tasks_filters_by_exact_status() -> None:
    """Verify that callers may request one lifecycle state."""

    # Arrange: configure tasks in two different lifecycle states.
    pending_task = Task(title="Buy soil for the pitaya.")
    active_task = Task(title="Study Docker.")
    active_task.start()
    repository = ReturningTaskCollectionRepository(
        tasks=(
            pending_task,
            active_task,
        ),
    )
    use_case = ListTasks(repository=repository)

    # Act: request only tasks representing active work.
    listed_tasks = use_case.execute(
        status=TaskStatus.IN_PROGRESS,
    )

    # Assert: the result contains only the exact requested state.
    assert listed_tasks == (active_task,)

    # Assert: filtering needs only one repository snapshot.
    assert repository.list_call_count == 1


@pytest.mark.parametrize(
    "invalid_status",
    [
        "pending",
        1,
        True,
    ],
    ids=[
        "text",
        "integer",
        "boolean",
    ],
)
def test_list_tasks_rejects_non_status_filters(
    invalid_status: object,
) -> None:
    """Ensure that arbitrary values cannot become lifecycle filters."""

    # Arrange: configure a repository whose calls can be observed.
    repository = ReturningTaskCollectionRepository(tasks=())
    use_case = ListTasks(repository=repository)

    # Act and Assert: filters require the explicit domain enum.
    with pytest.raises(
        TypeError,
        match="Task status filter must be a TaskStatus",
    ):
        use_case.execute(status=invalid_status)

    # Assert: malformed input is rejected before querying persistence.
    assert repository.list_call_count == 0


def test_list_tasks_filters_by_exact_priority() -> None:
    """Verify that callers may request one importance level."""

    # Arrange: configure tasks with different explicit priorities.
    normal_task = Task(title="Study Docker.")
    critical_task = Task(
        title="Renew the insurance today.",
        priority=TaskPriority.CRITICAL,
    )
    repository = ReturningTaskCollectionRepository(
        tasks=(
            normal_task,
            critical_task,
        ),
    )
    use_case = ListTasks(repository=repository)

    # Act: request only tasks with critical importance.
    listed_tasks = use_case.execute(
        priority=TaskPriority.CRITICAL,
    )

    # Assert: the result contains only the requested priority.
    assert listed_tasks == (critical_task,)

    # Assert: filtering still requires one repository snapshot.
    assert repository.list_call_count == 1


@pytest.mark.parametrize(
    "invalid_priority",
    [
        "critical",
        1,
        True,
    ],
    ids=[
        "text",
        "integer",
        "boolean",
    ],
)
def test_list_tasks_rejects_non_priority_filters(
    invalid_priority: object,
) -> None:
    """Ensure that arbitrary values cannot become priority filters."""

    # Arrange: configure a repository whose calls can be observed.
    repository = ReturningTaskCollectionRepository(tasks=())
    use_case = ListTasks(repository=repository)

    # Act and Assert: filters require the explicit domain enum.
    with pytest.raises(
        TypeError,
        match="Task priority filter must be a TaskPriority",
    ):
        use_case.execute(priority=invalid_priority)

    # Assert: malformed input is rejected before querying persistence.
    assert repository.list_call_count == 0


def test_list_tasks_combines_status_and_priority_filters() -> None:
    """Verify that every supplied filter must match the result."""

    # Arrange: create tasks covering all relevant filter combinations.
    normal_pending_task = Task(
        title="Study Docker.",
    )
    critical_pending_task = Task(
        title="Renew the insurance.",
        priority=TaskPriority.CRITICAL,
    )
    critical_active_task = Task(
        title="Call the insurance company.",
        priority=TaskPriority.CRITICAL,
    )
    critical_active_task.start()
    repository = ReturningTaskCollectionRepository(
        tasks=(
            normal_pending_task,
            critical_pending_task,
            critical_active_task,
        ),
    )
    use_case = ListTasks(repository=repository)

    # Act: request tasks matching both lifecycle and importance.
    listed_tasks = use_case.execute(
        status=TaskStatus.PENDING,
        priority=TaskPriority.CRITICAL,
    )

    # Assert: partial matches are excluded from the final snapshot.
    assert listed_tasks == (critical_pending_task,)
    assert repository.list_call_count == 1
