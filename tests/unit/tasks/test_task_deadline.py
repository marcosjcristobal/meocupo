"""Unit tests for task deadline values."""

# Date represents a calendar deadline without inventing a time.
from datetime import UTC, date, datetime

# Pytest provides readable assertions for invalid deadline combinations.
import pytest

# Import the domain value object through its absolute package path.
from personal_productivity.tasks.domain.task_deadline import TaskDeadline


def test_date_only_deadline_preserves_user_intent() -> None:
    """Verify that a calendar date remains distinct from an exact instant."""

    # Act: represent a deadline whose user supplied no time.
    deadline = TaskDeadline(due_on=date(2026, 8, 15))

    # Assert: the value object preserves the date-only meaning.
    assert deadline.due_on == date(2026, 8, 15)
    assert deadline.due_at is None

def test_exact_deadline_preserves_timezone_aware_instant() -> None:
    """Verify that a precise deadline retains its absolute instant."""

    # Arrange: create an explicit instant that can be compared globally.
    due_at = datetime(2026, 8, 15, 18, 0, tzinfo=UTC)

    # Act: represent the exact deadline.
    deadline = TaskDeadline(due_at=due_at)

    # Assert: exact and date-only variants remain mutually distinct.
    assert deadline.due_on is None
    assert deadline.due_at == due_at


def test_deadline_rejects_missing_value() -> None:
    """Ensure that an empty deadline cannot exist."""

    # Act and Assert: a value object must contain actual deadline information.
    with pytest.raises(
        ValueError,
        match="Deadline requires exactly one of due_on or due_at",
    ):
        TaskDeadline()


def test_deadline_rejects_date_and_instant_together() -> None:
    """Ensure that one deadline cannot express two competing meanings."""

    # Arrange: prepare both representations of a deadline.
    due_on = date(2026, 8, 15)
    due_at = datetime(2026, 8, 15, 18, 0, tzinfo=UTC)

    # Act and Assert: callers must choose exactly one representation.
    with pytest.raises(
        ValueError,
        match="Deadline requires exactly one of due_on or due_at",
    ):
        TaskDeadline(due_on=due_on, due_at=due_at)


def test_exact_deadline_rejects_naive_datetime() -> None:
    """Ensure that a precise deadline always identifies an absolute instant."""

    # Arrange: this datetime has no timezone or UTC offset.
    naive_due_at = datetime(2026, 8, 15, 18, 0)

    # Act and Assert: an ambiguous exact deadline is invalid.
    with pytest.raises(
        ValueError,
        match="Exact deadline must include a timezone",
    ):
        TaskDeadline(due_at=naive_due_at)

@pytest.mark.parametrize(
    "invalid_due_on",
    [
        datetime(2026, 8, 15, 18, 0, tzinfo=UTC),
        "2026-08-15",
    ],
)
def test_date_only_deadline_rejects_invalid_runtime_types(
    invalid_due_on: object,
) -> None:
    """Ensure that due_on contains a date without hidden time information."""

    # Act and Assert: datetime and text values violate date-only semantics.
    with pytest.raises(
        TypeError,
        match="due_on must be a date without time",
    ):
        TaskDeadline(due_on=invalid_due_on)


@pytest.mark.parametrize(
    "invalid_due_at",
    [
        date(2026, 8, 15),
        "2026-08-15T18:00:00Z",
    ],
)
def test_exact_deadline_rejects_invalid_runtime_types(
    invalid_due_at: object,
) -> None:
    """Ensure that due_at contains a real datetime object."""

    # Act and Assert: dates and text cannot represent exact instants here.
    with pytest.raises(
        TypeError,
        match="due_at must be a datetime",
    ):
        TaskDeadline(due_at=invalid_due_at)
