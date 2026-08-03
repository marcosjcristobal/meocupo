"""Unit tests for the urgency levels derived from task deadlines."""

# Date and datetime provide deterministic temporal references.
from datetime import UTC, date, datetime
# Pytest executes the same business rule at each urgency boundary.
import pytest

# Import the domain type through its absolute application package path.
from personal_productivity.tasks.domain.task_urgency import TaskUrgency

# Import the entity and deadline value object used by urgency calculations.
from personal_productivity.tasks.domain.task import Task
from personal_productivity.tasks.domain.task_deadline import TaskDeadline


def test_overdue_urgency_has_stable_serializable_value() -> None:
    """Verify that overdue urgency keeps its external representation stable."""

    # The value may cross JSON and database boundaries, so it must remain stable.
    assert TaskUrgency.OVERDUE.value == "overdue"


def test_enum_contains_only_derived_urgency_levels() -> None:
    """Ensure that urgency remains distinct from user-assigned priority."""

    # Arrange: define every urgency category produced by domain calculations.
    expected_values = {
        "not_urgent",
        "upcoming",
        "imminent",
        "overdue",
    }

    # Act: extract the external value of every declared urgency level.
    actual_values = {urgency.value for urgency in TaskUrgency}

    # Assert: no manual-priority or lifecycle values may enter this vocabulary.
    assert actual_values == expected_values


def test_undated_task_is_not_urgent() -> None:
    """Verify that missing deadlines do not create artificial urgency."""

    # Arrange: create a task without any temporal commitment.
    task = Task(title="Study Docker.")

    # Act: calculate urgency using deterministic temporal references.
    urgency = task.calculate_urgency(
        today=date(2026, 8, 15),
        now=datetime(2026, 8, 15, 12, 0, tzinfo=UTC),
    )

    # Assert: an undated task has no deadline-driven pressure.
    assert urgency is TaskUrgency.NOT_URGENT


def test_overdue_task_has_overdue_urgency() -> None:
    """Verify that a missed deadline produces the strongest temporal signal."""

    # Arrange: create an unfinished task whose calendar deadline has passed.
    task = Task(
        title="Renew the insurance.",
        deadline=TaskDeadline(due_on=date(2026, 8, 15)),
    )

    # Act: evaluate the task on the following local calendar day.
    urgency = task.calculate_urgency(
        today=date(2026, 8, 16),
        now=datetime(2026, 8, 16, 12, 0, tzinfo=UTC),
    )

    # Assert: delay is represented explicitly instead of as a lifecycle state.
    assert urgency is TaskUrgency.OVERDUE


@pytest.mark.parametrize(
    ("due_on", "expected_urgency"),
    [
        (date(2026, 8, 15), TaskUrgency.IMMINENT),
        (date(2026, 8, 16), TaskUrgency.UPCOMING),
        (date(2026, 8, 18), TaskUrgency.UPCOMING),
        (date(2026, 8, 19), TaskUrgency.NOT_URGENT),
    ],
    ids=[
        "due_today",
        "due_tomorrow",
        "last_upcoming_day",
        "outside_upcoming_window",
    ],
)
def test_date_only_deadline_uses_calendar_urgency_windows(
    due_on: date,
    expected_urgency: TaskUrgency,
) -> None:
    """Verify urgency boundaries without inventing a deadline time."""

    # Arrange: create a task whose deadline represents a calendar day.
    task = Task(
        title="Renew the insurance.",
        deadline=TaskDeadline(due_on=due_on),
    )

    # Act: calculate urgency from the user's current local date.
    actual_urgency = task.calculate_urgency(
        today=date(2026, 8, 15),
        now=datetime(2026, 8, 15, 12, 0, tzinfo=UTC),
    )

    # Assert: the calendar distance selects the expected urgency category.
    assert actual_urgency is expected_urgency


@pytest.mark.parametrize(
    ("due_at", "expected_urgency"),
    [
        (
            datetime(2026, 8, 15, 11, 59, tzinfo=UTC),
            TaskUrgency.OVERDUE,
        ),
        (
            datetime(2026, 8, 15, 12, 0, tzinfo=UTC),
            TaskUrgency.IMMINENT,
        ),
        (
            datetime(2026, 8, 16, 12, 0, tzinfo=UTC),
            TaskUrgency.IMMINENT,
        ),
        (
            datetime(2026, 8, 16, 12, 1, tzinfo=UTC),
            TaskUrgency.UPCOMING,
        ),
        (
            datetime(2026, 8, 18, 12, 0, tzinfo=UTC),
            TaskUrgency.UPCOMING,
        ),
        (
            datetime(2026, 8, 18, 12, 1, tzinfo=UTC),
            TaskUrgency.NOT_URGENT,
        ),
    ],
    ids=[
        "overdue",
        "due_now",
        "last_imminent_minute",
        "first_upcoming_minute",
        "last_upcoming_minute",
        "outside_upcoming_window",
    ],
)
def test_exact_deadline_uses_elapsed_time_urgency_windows(
    due_at: datetime,
    expected_urgency: TaskUrgency,
) -> None:
    """Verify urgency boundaries using absolute elapsed time."""

    # Arrange: create a task with an unambiguous deadline instant.
    task = Task(
        title="Submit the report.",
        deadline=TaskDeadline(due_at=due_at),
    )
    now = datetime(2026, 8, 15, 12, 0, tzinfo=UTC)

    # Act: calculate urgency from one deterministic absolute instant.
    actual_urgency = task.calculate_urgency(
        today=date(2026, 8, 15),
        now=now,
    )

    # Assert: the remaining duration selects the expected urgency category.
    assert actual_urgency is expected_urgency


def test_completed_task_is_not_urgent() -> None:
    """Ensure that completed work no longer demands operational attention."""

    # Arrange: complete a task before evaluating it after its deadline.
    task = Task(
        title="Submit the report.",
        deadline=TaskDeadline(due_on=date(2026, 8, 15)),
    )
    task.complete(
        completed_at=datetime(2026, 8, 14, 18, 0, tzinfo=UTC),
    )

    # Act: calculate urgency after the original deadline has passed.
    urgency = task.calculate_urgency(
        today=date(2026, 8, 16),
        now=datetime(2026, 8, 16, 12, 0, tzinfo=UTC),
    )

    # Assert: historical success must not appear in the attention queue.
    assert urgency is TaskUrgency.NOT_URGENT


def test_cancelled_task_is_not_urgent() -> None:
    """Ensure that abandoned work no longer demands operational attention."""

    # Arrange: cancel a task before evaluating it after its deadline.
    task = Task(
        title="Submit the report.",
        deadline=TaskDeadline(due_on=date(2026, 8, 15)),
    )
    task.cancel()

    # Act: calculate urgency after the original deadline has passed.
    urgency = task.calculate_urgency(
        today=date(2026, 8, 16),
        now=datetime(2026, 8, 16, 12, 0, tzinfo=UTC),
    )

    # Assert: cancelled work must not appear in the attention queue.
    assert urgency is TaskUrgency.NOT_URGENT


def test_exact_urgency_rejects_naive_current_time() -> None:
    """Ensure that exact urgency calculations use an absolute current instant."""

    # Arrange: the deadline is absolute but the supplied current time is ambiguous.
    task = Task(
        title="Submit the report.",
        deadline=TaskDeadline(
            due_at=datetime(2026, 8, 15, 18, 0, tzinfo=UTC),
        ),
    )
    naive_now = datetime(2026, 8, 15, 12, 0)

    # Act and Assert: timezone-free instants cannot be compared reliably.
    with pytest.raises(
        ValueError,
        match="Current time must include a timezone",
    ):
        task.calculate_urgency(
            today=date(2026, 8, 15),
            now=naive_now,
        )

