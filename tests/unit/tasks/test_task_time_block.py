"""Unit tests for calendar time blocks assigned to tasks."""

# Datetime provides deterministic and globally comparable schedule instants.
from datetime import UTC, date, datetime

# Pytest executes the same boundary rule against several invalid values.
import pytest

# Import the value object through its absolute domain package path.
from personal_productivity.tasks.domain.task_time_block import TaskTimeBlock


def test_time_block_preserves_a_valid_interval() -> None:
    """Verify that a valid work interval retains both boundary instants."""

    # Arrange: define when planned work begins and ends.
    starts_at = datetime(2026, 8, 5, 18, 0, tzinfo=UTC)
    ends_at = datetime(2026, 8, 5, 19, 30, tzinfo=UTC)

    # Act: create one immutable calendar allocation.
    time_block = TaskTimeBlock(
        starts_at=starts_at,
        ends_at=ends_at,
    )

    # Assert: the value object preserves the complete interval.
    assert time_block.starts_at == starts_at
    assert time_block.ends_at == ends_at

@pytest.mark.parametrize(
    ("starts_at", "ends_at"),
    [
        (
            date(2026, 8, 5),
            datetime(2026, 8, 5, 19, 30, tzinfo=UTC),
        ),
        (
            datetime(2026, 8, 5, 18, 0, tzinfo=UTC),
            date(2026, 8, 5),
        ),
        (
            "2026-08-05T18:00:00Z",
            datetime(2026, 8, 5, 19, 30, tzinfo=UTC),
        ),
        (
            datetime(2026, 8, 5, 18, 0, tzinfo=UTC),
            "2026-08-05T19:30:00Z",
        ),
    ],
    ids=[
        "date_as_start",
        "date_as_end",
        "text_as_start",
        "text_as_end",
    ],
)
def test_time_block_rejects_non_datetime_boundaries(
    starts_at: object,
    ends_at: object,
) -> None:
    """Ensure that raw values cannot bypass exact scheduling semantics."""

    # Act and Assert: both interval boundaries require datetime instances.
    with pytest.raises(
        TypeError,
        match="Time block boundaries must be datetimes",
    ):
        TaskTimeBlock(
            starts_at=starts_at,
            ends_at=ends_at,
        )

@pytest.mark.parametrize(
    ("starts_at", "ends_at"),
    [
        (
            datetime(2026, 8, 5, 18, 0),
            datetime(2026, 8, 5, 19, 30, tzinfo=UTC),
        ),
        (
            datetime(2026, 8, 5, 18, 0, tzinfo=UTC),
            datetime(2026, 8, 5, 19, 30),
        ),
    ],
    ids=[
        "naive_start",
        "naive_end",
    ],
)
def test_time_block_rejects_timezone_free_boundaries(
    starts_at: datetime,
    ends_at: datetime,
) -> None:
    """Ensure that every schedule boundary identifies an absolute instant."""

    # Act and Assert: ambiguous local clock values cannot form a time block.
    with pytest.raises(
        ValueError,
        match="Time block boundaries must include a timezone",
    ):
        TaskTimeBlock(
            starts_at=starts_at,
            ends_at=ends_at,
        )

@pytest.mark.parametrize(
    "ends_at",
    [
        datetime(2026, 8, 5, 18, 0, tzinfo=UTC),
        datetime(2026, 8, 5, 17, 59, tzinfo=UTC),
    ],
    ids=[
        "zero_duration",
        "ends_before_start",
    ],
)
def test_time_block_requires_end_after_start(
    ends_at: datetime,
) -> None:
    """Ensure that a planned interval has a positive duration."""

    # Arrange: use one fixed starting instant for both invalid boundaries.
    starts_at = datetime(2026, 8, 5, 18, 0, tzinfo=UTC)

    # Act and Assert: zero or negative durations cannot reserve calendar time.
    with pytest.raises(
        ValueError,
        match="Time block end must be later than its start",
    ):
        TaskTimeBlock(
            starts_at=starts_at,
            ends_at=ends_at,
        )