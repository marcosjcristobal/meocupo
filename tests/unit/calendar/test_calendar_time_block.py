"""Unit tests for reusable calendar time blocks."""

# Datetime provides deterministic and globally comparable schedule instants.
from datetime import UTC, date, datetime

# Pytest executes the same boundary rule against several invalid values.
import pytest

# Import the value object through its absolute domain package path.
from personal_productivity.calendar.domain.calendar_time_block import (
    CalendarTimeBlock,
)


def test_time_block_preserves_a_valid_interval() -> None:
    """Verify that a valid work interval retains both boundary instants."""

    # Arrange: define when planned work begins and ends.
    starts_at = datetime(2026, 8, 5, 18, 0, tzinfo=UTC)
    ends_at = datetime(2026, 8, 5, 19, 30, tzinfo=UTC)

    # Act: create one immutable calendar allocation.
    time_block = CalendarTimeBlock(
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
        CalendarTimeBlock(
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
        CalendarTimeBlock(
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
        CalendarTimeBlock(
            starts_at=starts_at,
            ends_at=ends_at,
        )


def test_partially_overlapping_time_blocks_overlap() -> None:
    """Verify that intervals sharing real elapsed time overlap symmetrically."""

    # Arrange: create two blocks that share thirty minutes.
    first_block = CalendarTimeBlock(
        starts_at=datetime(2026, 8, 5, 18, 0, tzinfo=UTC),
        ends_at=datetime(2026, 8, 5, 19, 0, tzinfo=UTC),
    )
    second_block = CalendarTimeBlock(
        starts_at=datetime(2026, 8, 5, 18, 30, tzinfo=UTC),
        ends_at=datetime(2026, 8, 5, 19, 30, tzinfo=UTC),
    )

    # Act and Assert: overlap cannot depend on comparison direction.
    assert first_block.overlaps(second_block) is True
    assert second_block.overlaps(first_block) is True


@pytest.mark.parametrize(
    ("other_starts_at", "other_ends_at", "expected"),
    [
        (
            datetime(2026, 8, 5, 16, 0, tzinfo=UTC),
            datetime(2026, 8, 5, 17, 0, tzinfo=UTC),
            False,
        ),
        (
            datetime(2026, 8, 5, 17, 0, tzinfo=UTC),
            datetime(2026, 8, 5, 18, 0, tzinfo=UTC),
            False,
        ),
        (
            datetime(2026, 8, 5, 19, 0, tzinfo=UTC),
            datetime(2026, 8, 5, 20, 0, tzinfo=UTC),
            False,
        ),
        (
            datetime(2026, 8, 5, 20, 0, tzinfo=UTC),
            datetime(2026, 8, 5, 21, 0, tzinfo=UTC),
            False,
        ),
        (
            datetime(2026, 8, 5, 18, 15, tzinfo=UTC),
            datetime(2026, 8, 5, 18, 45, tzinfo=UTC),
            True,
        ),
        (
            datetime(2026, 8, 5, 17, 30, tzinfo=UTC),
            datetime(2026, 8, 5, 19, 30, tzinfo=UTC),
            True,
        ),
        (
            datetime(2026, 8, 5, 18, 0, tzinfo=UTC),
            datetime(2026, 8, 5, 19, 0, tzinfo=UTC),
            True,
        ),
    ],
    ids=[
        "separate_before",
        "touches_start",
        "touches_end",
        "separate_after",
        "contained",
        "contains_reference",
        "identical",
    ],
)
def test_time_block_overlap_uses_half_open_boundaries(
    other_starts_at: datetime,
    other_ends_at: datetime,
    expected: bool,
) -> None:
    """Verify separation, contact, containment, and identical intervals."""

    # Arrange: use one fixed reference block for every boundary scenario.
    reference_block = CalendarTimeBlock(
        starts_at=datetime(2026, 8, 5, 18, 0, tzinfo=UTC),
        ends_at=datetime(2026, 8, 5, 19, 0, tzinfo=UTC),
    )
    other_block = CalendarTimeBlock(
        starts_at=other_starts_at,
        ends_at=other_ends_at,
    )

    # Act and Assert: only shared positive duration represents overlap.
    assert reference_block.overlaps(other_block) is expected

@pytest.mark.parametrize(
    "invalid_other",
    [
        None,
        "18:00/19:00",
        (
            datetime(2026, 8, 5, 18, 0, tzinfo=UTC),
            datetime(2026, 8, 5, 19, 0, tzinfo=UTC),
        ),
    ],
    ids=[
        "none",
        "text",
        "tuple",
    ],
)
def test_overlap_rejects_non_time_block_values(
    invalid_other: object,
) -> None:
    """Ensure that interval comparison cannot bypass the value object."""

    # Arrange: create one valid reference interval.
    reference_block = CalendarTimeBlock(
        starts_at=datetime(2026, 8, 5, 18, 0, tzinfo=UTC),
        ends_at=datetime(2026, 8, 5, 19, 0, tzinfo=UTC),
    )

    # Act and Assert: overlap requires another validated time block.
    with pytest.raises(
        TypeError,
        match="Other value must be a CalendarTimeBlock",
    ):
        reference_block.overlaps(invalid_other)

@pytest.mark.parametrize(
    ("instant", "expected_contains"),
    [
        (
            datetime(2026, 8, 5, 17, 59, tzinfo=UTC),
            False,
        ),
        (
            datetime(2026, 8, 5, 18, 0, tzinfo=UTC),
            True,
        ),
        (
            datetime(2026, 8, 5, 18, 30, tzinfo=UTC),
            True,
        ),
        (
            datetime(2026, 8, 5, 19, 0, tzinfo=UTC),
            False,
        ),
        (
            datetime(2026, 8, 5, 19, 1, tzinfo=UTC),
            False,
        ),
    ],
    ids=[
        "before_start",
        "at_start",
        "inside",
        "at_end",
        "after_end",
    ],
)
def test_time_block_contains_instants_using_half_open_boundaries(
    instant: datetime,
    expected_contains: bool,
) -> None:
    """Verify membership using an inclusive start and exclusive end."""

    # Arrange: reserve one exact hour in the calendar.
    time_block = CalendarTimeBlock(
        starts_at=datetime(2026, 8, 5, 18, 0, tzinfo=UTC),
        ends_at=datetime(2026, 8, 5, 19, 0, tzinfo=UTC),
    )

    # Act: ask the interval whether it contains the reference instant.
    actual_contains = time_block.contains(instant)

    # Assert: membership follows the shared half-open interval convention.
    assert actual_contains is expected_contains

@pytest.mark.parametrize(
    "invalid_instant",
    [
        None,
        date(2026, 8, 5),
        "2026-08-05T18:30:00Z",
    ],
    ids=[
        "none",
        "date",
        "text",
    ],
)
def test_contains_rejects_non_datetime_values(
    invalid_instant: object,
) -> None:
    """Ensure that interval membership requires an exact instant."""

    # Arrange: create one valid allocation for the attempted comparison.
    time_block = CalendarTimeBlock(
        starts_at=datetime(2026, 8, 5, 18, 0, tzinfo=UTC),
        ends_at=datetime(2026, 8, 5, 19, 0, tzinfo=UTC),
    )

    # Act and Assert: raw values cannot enter temporal comparisons.
    with pytest.raises(
        TypeError,
        match="Calendar instant must be a datetime",
    ):
        time_block.contains(invalid_instant)


def test_contains_rejects_timezone_free_instant() -> None:
    """Ensure that interval membership compares absolute moments."""

    # Arrange: create one valid allocation and one ambiguous local time.
    time_block = CalendarTimeBlock(
        starts_at=datetime(2026, 8, 5, 18, 0, tzinfo=UTC),
        ends_at=datetime(2026, 8, 5, 19, 0, tzinfo=UTC),
    )
    naive_instant = datetime(2026, 8, 5, 18, 30)

    # Act and Assert: a timezone-free value has no absolute meaning.
    with pytest.raises(
        ValueError,
        match="Calendar instant must include a timezone",
    ):
        time_block.contains(naive_instant)
