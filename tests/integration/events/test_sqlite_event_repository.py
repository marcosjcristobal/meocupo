"""Integration tests for durable SQLite event persistence."""

# Datetime builds one deterministic calendar allocation.
from datetime import UTC, datetime

# Path types the temporary database location supplied by pytest.
from pathlib import Path

# SQLite ships with Python and needs no external database service.
import sqlite3

# Pytest verifies explicit validation failures at the SQLite boundary.
import pytest

# CalendarTimeBlock represents the interval occupied by an event.
from personal_productivity.calendar.domain.calendar_time_block import (
    CalendarTimeBlock,
)

# Application use cases collaborate without knowing the database adapter.
from personal_productivity.events.application.create_event import CreateEvent
from personal_productivity.events.application.get_event import GetEvent
from personal_productivity.events.application.list_events import ListEvents

# Duplicate creation uses one storage-independent repository outcome.
from personal_productivity.events.application.ports.event_repository import (
    EventAlreadyExistsError,
)

# Persistence tests cross the boundary with complete domain entities.
from personal_productivity.events.domain.event import Event

# Status verifies that lifecycle state survives the database round trip.
from personal_productivity.events.domain.event_status import EventStatus

# The schema initializer creates storage for event entities.
from personal_productivity.events.infrastructure.repositories.sqlite_event_repository import (
    SqliteEventRepository,
    initialize_event_schema,
)


def test_schema_initialization_creates_events_table() -> None:
    """Verify that local initialization creates event storage."""

    # Arrange: open an isolated SQLite database for this test.
    connection = sqlite3.connect(":memory:")

    try:
        # Act: initialize the structures required by event persistence.
        initialize_event_schema(connection)

        # Inspect SQLite metadata to confirm the table really exists.
        table_record = connection.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
              AND name = 'events'
            """
        ).fetchone()
    finally:
        # Always release the native database connection.
        connection.close()

    # Assert: initialization created the expected event table.
    assert table_record == ("events",)


def test_added_event_can_be_retrieved_by_identity() -> None:
    """Verify that a stored event can be reconstructed from SQLite."""

    # Arrange: create one event with its full calendar allocation.
    connection = sqlite3.connect(":memory:")
    original_event = Event(
        title="Boxing training.",
        time_block=CalendarTimeBlock(
            starts_at=datetime(2026, 9, 25, 18, 0, tzinfo=UTC),
            ends_at=datetime(2026, 9, 25, 19, 30, tzinfo=UTC),
        ),
    )

    try:
        initialize_event_schema(connection)
        repository = SqliteEventRepository(connection=connection)

        # Act: persist the entity, then reconstruct it from its UUID.
        repository.add(original_event)
        retrieved_event = repository.get_by_id(original_event.id)
    finally:
        # Always release the native database connection.
        connection.close()

    # Assert: retrieval created a separate entity with the same domain data.
    assert retrieved_event is not original_event
    assert retrieved_event is not None
    assert retrieved_event.id == original_event.id
    assert retrieved_event.title == original_event.title
    assert retrieved_event.time_block == original_event.time_block
    assert retrieved_event.description is None
    assert retrieved_event.status is EventStatus.SCHEDULED


def test_sqlite_preserves_cancelled_event_lifecycle() -> None:
    """Verify that cancellation remains visible after reconstruction."""

    # Arrange: cancel one event before storing its historical state.
    connection = sqlite3.connect(":memory:")
    original_event = Event(
        title="Boxing training.",
        time_block=CalendarTimeBlock(
            starts_at=datetime(2026, 9, 25, 18, 0, tzinfo=UTC),
            ends_at=datetime(2026, 9, 25, 19, 30, tzinfo=UTC),
        ),
    )
    original_event.cancel()

    try:
        initialize_event_schema(connection)
        repository = SqliteEventRepository(connection=connection)

        # Act: store and reconstruct the cancelled event.
        repository.add(original_event)
        retrieved_event = repository.get_by_id(original_event.id)
    finally:
        # Always release the native database connection.
        connection.close()

    # Assert: identity, interval, and terminal lifecycle survive storage.
    assert retrieved_event is not None
    assert retrieved_event.id == original_event.id
    assert retrieved_event.time_block == original_event.time_block
    assert retrieved_event.status is EventStatus.CANCELLED


def test_sqlite_list_all_returns_event_snapshot() -> None:
    """Verify that listing reconstructs every stored event in order."""

    # Arrange: prepare two events with different lifecycle states.
    connection = sqlite3.connect(":memory:")
    first_event = Event(
        title="Boxing training.",
        time_block=CalendarTimeBlock(
            starts_at=datetime(2026, 9, 25, 18, 0, tzinfo=UTC),
            ends_at=datetime(2026, 9, 25, 19, 30, tzinfo=UTC),
        ),
    )
    second_event = Event(
        title="Dentist appointment.",
        description="Bring the insurance card.",
        time_block=CalendarTimeBlock(
            starts_at=datetime(2026, 9, 26, 9, 0, tzinfo=UTC),
            ends_at=datetime(2026, 9, 26, 9, 30, tzinfo=UTC),
        ),
    )
    second_event.cancel()

    try:
        initialize_event_schema(connection)
        repository = SqliteEventRepository(connection=connection)
        repository.add(first_event)
        repository.add(second_event)

        # Act: request a complete snapshot from durable storage.
        event_snapshot = repository.list_all()
    finally:
        # Always release the native database connection.
        connection.close()

    # Assert: the collection is immutable and preserves insertion order.
    assert isinstance(event_snapshot, tuple)
    assert tuple(event.id for event in event_snapshot) == (
        first_event.id,
        second_event.id,
    )

    # Assert: reconstruction retains optional details and lifecycle.
    assert event_snapshot[0].status is EventStatus.SCHEDULED
    assert event_snapshot[1].status is EventStatus.CANCELLED
    assert event_snapshot[1].description == "Bring the insurance card."


def test_event_use_cases_collaborate_through_sqlite() -> None:
    """Verify that creation, lookup, and listing share durable storage."""

    # Arrange: inject one SQLite repository into independent use cases.
    connection = sqlite3.connect(":memory:")
    time_block = CalendarTimeBlock(
        starts_at=datetime(2026, 9, 25, 18, 0, tzinfo=UTC),
        ends_at=datetime(2026, 9, 25, 19, 30, tzinfo=UTC),
    )

    try:
        initialize_event_schema(connection)
        repository = SqliteEventRepository(connection=connection)
        create_event = CreateEvent(repository=repository)
        get_event = GetEvent(repository=repository)
        list_events = ListEvents(repository=repository)

        # Act: create one event and query it in two independent ways.
        created_event = create_event.execute(
            title="Boxing training.",
            time_block=time_block,
            description="Bring the red gloves.",
        )
        retrieved_event = get_event.execute(event_id=created_event.id)
        listed_events = list_events.execute()
    finally:
        # Always release the native database connection.
        connection.close()

    # Assert: each application operation refers to the same event.
    assert retrieved_event.id == created_event.id
    assert retrieved_event.time_block == time_block
    assert retrieved_event.description == "Bring the red gloves."
    assert tuple(event.id for event in listed_events) == (
        created_event.id,
    )


def test_sqlite_file_preserves_event_across_connections(
    tmp_path: Path,
) -> None:
    """Verify that an event survives database connection shutdown."""

    # Arrange: use one isolated database file supplied by pytest.
    database_path = tmp_path / "meocupo.db"
    original_event = Event(
        title="Dentist appointment.",
        description="Bring the insurance card.",
        time_block=CalendarTimeBlock(
            starts_at=datetime(2026, 9, 26, 9, 0, tzinfo=UTC),
            ends_at=datetime(2026, 9, 26, 9, 30, tzinfo=UTC),
        ),
    )
    original_event.cancel()

    # Act: initialize and persist through the first connection.
    first_connection = sqlite3.connect(database_path)
    try:
        initialize_event_schema(first_connection)
        first_repository = SqliteEventRepository(
            connection=first_connection,
        )
        first_repository.add(original_event)
    finally:
        # Closing the connection simulates application shutdown.
        first_connection.close()

    # Act: open the same file through a new database connection.
    second_connection = sqlite3.connect(database_path)
    try:
        second_repository = SqliteEventRepository(
            connection=second_connection,
        )
        retrieved_event = second_repository.get_by_id(original_event.id)
    finally:
        # Release the reopened connection after verification.
        second_connection.close()

    # Assert: committed event data survived both connection lifecycles.
    assert retrieved_event is not None
    assert retrieved_event.id == original_event.id
    assert retrieved_event.title == original_event.title
    assert retrieved_event.description == original_event.description
    assert retrieved_event.time_block == original_event.time_block
    assert retrieved_event.status is EventStatus.CANCELLED


@pytest.mark.parametrize(
    "invalid_event_id",
    [
        None,
        42,
        "not-a-uuid",
    ],
    ids=[
        "none",
        "integer",
        "text",
    ],
)
def test_sqlite_get_by_id_rejects_non_uuid_values(
    invalid_event_id: object,
) -> None:
    """Ensure that malformed identities cannot enter SQLite lookup."""

    # Arrange: prepare an empty but initialized event database.
    connection = sqlite3.connect(":memory:")
    try:
        initialize_event_schema(connection)
        repository = SqliteEventRepository(connection=connection)

        # Act and Assert: storage keys must be portable UUID objects.
        with pytest.raises(
            TypeError,
            match="Event identifier must be a UUID",
        ):
            repository.get_by_id(invalid_event_id)
    finally:
        # Always release the native database connection.
        connection.close()


@pytest.mark.parametrize(
    "invalid_event",
    [
        None,
        42,
        "not-an-event",
    ],
    ids=[
        "none",
        "integer",
        "text",
    ],
)
def test_sqlite_add_rejects_non_event_values(
    invalid_event: object,
) -> None:
    """Ensure that only domain events can enter SQLite storage."""

    # Arrange: prepare isolated event storage.
    connection = sqlite3.connect(":memory:")
    try:
        initialize_event_schema(connection)
        repository = SqliteEventRepository(connection=connection)

        # Act and Assert: reject arbitrary values before serialization.
        with pytest.raises(
            TypeError,
            match="Event must be an Event",
        ):
            repository.add(invalid_event)
    finally:
        # Always release the native database connection.
        connection.close()


def test_sqlite_add_rejects_duplicate_event_identity() -> None:
    """Ensure that creation cannot replace an existing SQLite event."""

    # Arrange: prepare two different entities under the same identity.
    connection = sqlite3.connect(":memory:")
    existing_event = Event(
        title="Boxing training.",
        time_block=CalendarTimeBlock(
            starts_at=datetime(2026, 9, 25, 18, 0, tzinfo=UTC),
            ends_at=datetime(2026, 9, 25, 19, 30, tzinfo=UTC),
        ),
    )
    duplicate_event = Event(
        id=existing_event.id,
        title="Replacement event.",
        time_block=CalendarTimeBlock(
            starts_at=datetime(2026, 9, 26, 18, 0, tzinfo=UTC),
            ends_at=datetime(2026, 9, 26, 19, 30, tzinfo=UTC),
        ),
    )

    try:
        initialize_event_schema(connection)
        repository = SqliteEventRepository(connection=connection)
        repository.add(existing_event)

        # Act and Assert: duplicate creation has a portable error.
        with pytest.raises(
            EventAlreadyExistsError,
            match=f"Event '{existing_event.id}' already exists",
        ):
            repository.add(duplicate_event)

        # Verify that the failed insert did not replace the original.
        retrieved_event = repository.get_by_id(existing_event.id)
    finally:
        # Always release the native database connection.
        connection.close()

    assert retrieved_event is not None
    assert retrieved_event.title == existing_event.title
