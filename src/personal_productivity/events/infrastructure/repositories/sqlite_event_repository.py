"""SQLite structures for durable event persistence."""

# Datetime reconstructs exact instants from ISO 8601 text.
from datetime import datetime

# Connection represents an injected session and IntegrityError reports SQL conflicts.
from sqlite3 import Connection, IntegrityError

# UUID restores portable event identities from SQLite text.
from uuid import UUID

# CalendarTimeBlock validates restored interval boundaries.
from personal_productivity.calendar.domain.calendar_time_block import (
    CalendarTimeBlock,
)

# Duplicate identities use the same error as other repository adapters.
from personal_productivity.events.application.ports.event_repository import (
    EventAlreadyExistsError,
)

# Event is the domain entity stored by the adapter.
from personal_productivity.events.domain.event import Event

# Status detects lifecycle states during reconstruction.
from personal_productivity.events.domain.event_status import EventStatus


# Store all fields currently owned by the Event domain entity.
_CREATE_EVENTS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS events (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT,
    time_block_starts_at TEXT NOT NULL,
    time_block_ends_at TEXT NOT NULL,
    status TEXT NOT NULL
)
"""


def initialize_event_schema(connection: Connection) -> None:
    """Create the SQLite structures required by event persistence."""

    # Idempotent creation is safe to run whenever the application starts.
    connection.execute(_CREATE_EVENTS_TABLE_SQL)

    # Commit schema changes so later operations can see the table.
    connection.commit()


def _deserialize_event_record(record: tuple[object, ...]) -> Event:
    """Reconstruct one validated event from a complete SQLite row."""

    # Rehydration restores lifecycle without replaying cancellation.
    return Event.rehydrate(
        id=UUID(record[0]),
        title=record[1],
        description=record[2],
        time_block=CalendarTimeBlock(
            starts_at=datetime.fromisoformat(record[3]),
            ends_at=datetime.fromisoformat(record[4]),
        ),
        status=EventStatus(record[5]),
    )


class SqliteEventRepository:
    """Persist events using an injected SQLite connection."""

    def __init__(
        self,
        *,
        connection: Connection,
    ) -> None:
        """Keep the database session supplied by application setup."""

        # Connection ownership remains with the caller.
        self._connection = connection

    def add(self, event: Event) -> None:
        """Insert a newly created event into SQLite."""

        # Validate the domain type before reading attributes or writing SQL.
        if not isinstance(event, Event):
            raise TypeError("Event must be an Event.")

        try:
            # Store portable scalar values and exact interval boundaries.
            self._connection.execute(
                """
                INSERT INTO events (
                    id,
                    title,
                    description,
                    time_block_starts_at,
                    time_block_ends_at,
                    status
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    str(event.id),
                    event.title,
                    event.description,
                    event.time_block.starts_at.isoformat(),
                    event.time_block.ends_at.isoformat(),
                    event.status.value,
                ),
            )
        except IntegrityError as error:
            # Translate only conflicts caused by an occupied event identity.
            existing_record = self._connection.execute(
                "SELECT 1 FROM events WHERE id = ?",
                (str(event.id),),
            ).fetchone()
            if existing_record is not None:
                raise EventAlreadyExistsError(
                    f"Event '{event.id}' already exists."
                ) from error
            raise

        # Commit the insertion so later connections can read it.
        self._connection.commit()

    def get_by_id(self, event_id: UUID) -> Event | None:
        """Reconstruct one event by identity or return None when absent."""

        # Reject malformed identities before issuing a database query.
        if not isinstance(event_id, UUID):
            raise TypeError("Event identifier must be a UUID.")

        # Query complete stored state under the portable UUID value.
        record = self._connection.execute(
            """
            SELECT
                id,
                title,
                description,
                time_block_starts_at,
                time_block_ends_at,
                status
            FROM events
            WHERE id = ?
            """,
            (str(event_id),),
        ).fetchone()

        # Absence follows the optional repository result contract.
        if record is None:
            return None

        # Share the same validated mapping used by collection retrieval.
        return _deserialize_event_record(record)

    def list_all(self) -> tuple[Event, ...]:
        """Return an immutable snapshot of all stored events."""

        # Row order preserves the order in which events were inserted.
        records = self._connection.execute(
            """
            SELECT
                id,
                title,
                description,
                time_block_starts_at,
                time_block_ends_at,
                status
            FROM events
            ORDER BY rowid
            """
        ).fetchall()

        # Reconstruct independent domain entities without exposing SQL rows.
        return tuple(
            _deserialize_event_record(record)
            for record in records
        )
