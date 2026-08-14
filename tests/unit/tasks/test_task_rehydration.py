"""Unit tests for controlled task reconstruction from persistence."""

# Datetime provides deterministic completion metadata.
from datetime import UTC, datetime

# Pytest verifies invalid persisted state combinations.
import pytest

# UUID verifies that persisted identity is preserved.
from uuid import UUID, uuid4

# Rehydration must produce a regular domain entity.
from personal_productivity.tasks.domain.task import Task

# Persisted lifecycle values use the domain enum.
from personal_productivity.tasks.domain.task_status import TaskStatus


def test_completed_task_can_be_rehydrated() -> None:
    """Verify restoration of identity, lifecycle, and historical metadata."""

    # Arrange: represent trusted values previously stored by a repository.
    task_id = uuid4()
    completed_at = datetime(
        2026,
        8,
        14,
        18,
        30,
        tzinfo=UTC,
    )

    # Act: reconstruct the entity without replaying historical commands.
    task = Task.rehydrate(
        id=task_id,
        title="Prepare the investor presentation.",
        status=TaskStatus.COMPLETED,
        completed_at=completed_at,
        postponement_count=2,
    )

    # Assert: reconstruction returns a normal domain entity.
    assert isinstance(task, Task)
    assert isinstance(task.id, UUID)

    # Assert: persisted identity and lifecycle remain authoritative.
    assert task.id == task_id
    assert task.status is TaskStatus.COMPLETED
    assert task.completed_at == completed_at
    assert task.postponement_count == 2


@pytest.mark.parametrize(
    "invalid_status",
    [
        None,
        "completed",
        1,
    ],
    ids=[
        "none",
        "text",
        "integer",
    ],
)
def test_rehydration_rejects_non_status_values(
    invalid_status: object,
) -> None:
    """Ensure that raw persistence values cannot replace the status enum."""

    # Act and Assert: rehydration accepts the domain lifecycle vocabulary only.
    with pytest.raises(
        TypeError,
        match="Rehydrated status must be a TaskStatus",
    ):
        Task.rehydrate(
            id=uuid4(),
            title="Study Docker.",
            status=invalid_status,
            completed_at=None,
            postponement_count=0,
        )


def test_completed_rehydration_requires_completion_time() -> None:
    """Ensure that completed state always has historical metadata."""

    # Act and Assert: completed without an instant is an impossible state.
    with pytest.raises(
        ValueError,
        match="Completed task must include completion time",
    ):
        Task.rehydrate(
            id=uuid4(),
            title="Study Docker.",
            status=TaskStatus.COMPLETED,
            completed_at=None,
            postponement_count=0,
        )


@pytest.mark.parametrize(
    "status",
    [
        TaskStatus.PENDING,
        TaskStatus.IN_PROGRESS,
        TaskStatus.PAUSED,
        TaskStatus.CANCELLED,
    ],
    ids=[
        "pending",
        "in_progress",
        "paused",
        "cancelled",
    ],
)
def test_non_completed_rehydration_rejects_completion_time(
    status: TaskStatus,
) -> None:
    """Ensure that unfinished or cancelled tasks have no completion instant."""

    # Arrange: create one valid absolute instant that should not be present.
    completed_at = datetime(
        2026,
        8,
        14,
        18,
        30,
        tzinfo=UTC,
    )

    # Act and Assert: completion metadata belongs to completed state only.
    with pytest.raises(
        ValueError,
        match="Only completed tasks may include completion time",
    ):
        Task.rehydrate(
            id=uuid4(),
            title="Study Docker.",
            status=status,
            completed_at=completed_at,
            postponement_count=0,
        )


def test_completed_rehydration_rejects_naive_completion_time() -> None:
    """Ensure that restored completion metadata is an absolute instant."""

    # Arrange: create an ambiguous timestamp without timezone information.
    naive_completed_at = datetime(
        2026,
        8,
        14,
        18,
        30,
    )

    # Act and Assert: ambiguous historical instants cannot be restored.
    with pytest.raises(
        ValueError,
        match="Completion time must include a timezone",
    ):
        Task.rehydrate(
            id=uuid4(),
            title="Study Docker.",
            status=TaskStatus.COMPLETED,
            completed_at=naive_completed_at,
            postponement_count=0,
        )


@pytest.mark.parametrize(
    "invalid_completed_at",
    [
        "2026-08-14T18:30:00+00:00",
        42,
        True,
    ],
    ids=[
        "text",
        "integer",
        "boolean",
    ],
)
def test_completed_rehydration_rejects_non_datetime_completion_time(
    invalid_completed_at: object,
) -> None:
    """Ensure that completion history uses an actual datetime value."""

    # Act and Assert: serialized or arbitrary values cannot bypass the domain.
    with pytest.raises(
        TypeError,
        match="Completion time must be a datetime",
    ):
        Task.rehydrate(
            id=uuid4(),
            title="Prepare the investor presentation.",
            status=TaskStatus.COMPLETED,
            completed_at=invalid_completed_at,
            postponement_count=0,
        )


@pytest.mark.parametrize(
    "invalid_task_id",
    [
        None,
        "not-a-uuid",
        42,
    ],
    ids=[
        "none",
        "text",
        "integer",
    ],
)
def test_rehydration_rejects_non_uuid_identifiers(
    invalid_task_id: object,
) -> None:
    """Ensure that persisted identity uses the domain identifier type."""

    # Act and Assert: malformed storage values cannot become task identities.
    with pytest.raises(
        TypeError,
        match="Rehydrated task identifier must be a UUID",
    ):
        Task.rehydrate(
            id=invalid_task_id,
            title="Prepare the investor presentation.",
            status=TaskStatus.PENDING,
            completed_at=None,
            postponement_count=0,
        )

@pytest.mark.parametrize(
    "invalid_postponement_count",
    [
        True,
        1.5,
        "2",
    ],
    ids=[
        "boolean",
        "float",
        "text",
    ],
)
def test_rehydration_rejects_non_integer_postponement_count(
    invalid_postponement_count: object,
) -> None:
    """Ensure that persisted postponement history uses whole numbers."""

    # Act and Assert: malformed storage values cannot become history.
    with pytest.raises(
        TypeError,
        match="Postponement count must be an integer",
    ):
        Task.rehydrate(
            id=uuid4(),
            title="Prepare the investor presentation.",
            status=TaskStatus.PENDING,
            completed_at=None,
            postponement_count=invalid_postponement_count,
        )


def test_rehydration_rejects_negative_postponement_count() -> None:
    """Ensure that postponement history cannot move below zero."""

    # Act and Assert: a count cannot represent negative history.
    with pytest.raises(
        ValueError,
        match="Postponement count cannot be negative",
    ):
        Task.rehydrate(
            id=uuid4(),
            title="Prepare the investor presentation.",
            status=TaskStatus.PENDING,
            completed_at=None,
            postponement_count=-1,
        )


@pytest.mark.parametrize(
    "persisted_status",
    [
        TaskStatus.PENDING,
        TaskStatus.IN_PROGRESS,
        TaskStatus.PAUSED,
        TaskStatus.CANCELLED,
    ],
    ids=[
        "pending",
        "in_progress",
        "paused",
        "cancelled",
    ],
)
def test_non_completed_task_status_can_be_rehydrated(
    persisted_status: TaskStatus,
) -> None:
    """Verify restoration of every lifecycle state without completion history."""

    # Arrange: preserve one explicit identity across reconstruction.
    task_id = uuid4()

    # Act: rebuild the entity directly from valid persistent state.
    task = Task.rehydrate(
        id=task_id,
        title="Prepare the investor presentation.",
        status=persisted_status,
        completed_at=None,
        postponement_count=0,
    )

    # Assert: restoration keeps identity and lifecycle unchanged.
    assert task.id == task_id
    assert task.status is persisted_status
    assert task.completed_at is None
    assert task.postponement_count == 0
