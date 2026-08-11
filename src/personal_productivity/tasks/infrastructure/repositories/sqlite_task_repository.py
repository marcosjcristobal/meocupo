"""SQLite implementation of local task persistence."""

# Date and datetime convert deadline values to and from ISO 8601 text.
from datetime import date, datetime

# Connection represents an injected SQLite session and its integrity errors.
from sqlite3 import Connection, IntegrityError

# UUID converts portable text identities back into domain identifiers.
from uuid import UUID

# CalendarTimeBlock reconstructs exact scheduled work intervals.
from personal_productivity.calendar.domain.calendar_time_block import (
    CalendarTimeBlock,
)

# Repository conflicts use one storage-independent application exception.
from personal_productivity.tasks.application.ports.task_repository import (
    TaskAlreadyExistsError,
)

# SQLite rows are reconstructed as complete domain entities.
from personal_productivity.tasks.domain.task import Task

# TaskDeadline reconstructs the original temporal precision.
from personal_productivity.tasks.domain.task_deadline import TaskDeadline

# Priority converts its stable persisted string into the domain enum.
from personal_productivity.tasks.domain.task_priority import TaskPriority


# The initial schema preserves every field currently owned by Task.
_CREATE_TASKS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS tasks (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT,
    estimated_minutes INTEGER,
    deadline_due_on TEXT,
    deadline_due_at TEXT,
    time_block_starts_at TEXT,
    time_block_ends_at TEXT,
    priority TEXT NOT NULL,
    status TEXT NOT NULL,
    completed_at TEXT,
    postponement_count INTEGER NOT NULL
)
"""


def initialize_task_schema(connection: Connection) -> None:
    """Create the SQLite structures required by task persistence."""

    # Idempotent creation is safe to run whenever the application starts.
    connection.execute(_CREATE_TASKS_TABLE_SQL)

    # Commit schema changes so they become visible to later operations.
    connection.commit()


def _serialize_deadline(
    deadline: TaskDeadline | None,
) -> tuple[str | None, str | None]:
    """Convert an optional deadline into SQLite-compatible values."""

    # Missing deadlines occupy neither persistence column.
    if deadline is None:
        return (None, None)

    # Preserve date-only intent without inventing a clock time.
    due_on = (
        deadline.due_on.isoformat()
        if deadline.due_on is not None
        else None
    )

    # Preserve exact instants together with their UTC offset.
    due_at = (
        deadline.due_at.isoformat()
        if deadline.due_at is not None
        else None
    )

    return (due_on, due_at)


def _deserialize_deadline(
    due_on: str | None,
    due_at: str | None,
) -> TaskDeadline | None:
    """Reconstruct an optional deadline from SQLite values."""

    # Two absent columns represent a task without a deadline.
    if due_on is None and due_at is None:
        return None

    # TaskDeadline validates that exactly one precision is present.
    return TaskDeadline(
        due_on=(
            date.fromisoformat(due_on)
            if due_on is not None
            else None
        ),
        due_at=(
            datetime.fromisoformat(due_at)
            if due_at is not None
            else None
        ),
    )


def _serialize_time_block(
    time_block: CalendarTimeBlock | None,
) -> tuple[str | None, str | None]:
    """Convert an optional calendar block into SQLite values."""

    # Missing planning occupies neither boundary column.
    if time_block is None:
        return (None, None)

    # ISO text preserves both exact instants and their UTC offsets.
    return (
        time_block.starts_at.isoformat(),
        time_block.ends_at.isoformat(),
    )


def _deserialize_time_block(
    starts_at: str | None,
    ends_at: str | None,
) -> CalendarTimeBlock | None:
    """Reconstruct an optional calendar block from SQLite values."""

    # Two absent boundaries represent an unscheduled task.
    if starts_at is None and ends_at is None:
        return None

    # A partial interval indicates corrupted persistent data.
    if starts_at is None or ends_at is None:
        raise ValueError(
            "Stored time block must include both boundaries."
        )

    # CalendarTimeBlock revalidates timezone and interval invariants.
    return CalendarTimeBlock(
        starts_at=datetime.fromisoformat(starts_at),
        ends_at=datetime.fromisoformat(ends_at),
    )


def _deserialize_task_record(
    task_record: tuple[object, ...],
) -> Task:
    """Convert one SQLite row into a validated domain entity."""

    # Column positions follow the shared SELECT order used by repositories.
    return Task(
        id=UUID(task_record[0]),
        title=task_record[1],
        description=task_record[2],
        estimated_minutes=task_record[3],
        deadline=_deserialize_deadline(
            task_record[4],
            task_record[5],
        ),
        time_block=_deserialize_time_block(
            task_record[6],
            task_record[7],
        ),
        priority=TaskPriority(task_record[8]),
    )


class SqliteTaskRepository:
    """Persist tasks using an injected SQLite connection."""

    def __init__(
        self,
        *,
        connection: Connection,
    ) -> None:
        """Keep the database session supplied by the application bootstrap."""

        # Connection ownership remains outside the repository.
        self._connection = connection

    def add(self, task: Task) -> None:
        """Insert a newly created task into SQLite."""

        # Runtime validation protects SQL mapping from arbitrary values.
        if not isinstance(task, Task):
            raise TypeError("Stored value must be a Task.")

        # Convert the deadline without losing its original precision.
        deadline_due_on, deadline_due_at = _serialize_deadline(
            task.deadline,
        )

        # Convert optional planned work into two exact boundaries.
        time_block_starts_at, time_block_ends_at = (
            _serialize_time_block(task.time_block)
        )

        try:
            # Persist stable scalar values instead of Python-specific objects.
            self._connection.execute(
                """
                INSERT INTO tasks (
                    id,
                    title,
                    description,
                    estimated_minutes,
                    deadline_due_on,
                    deadline_due_at,
                    time_block_starts_at,
                    time_block_ends_at,
                    priority,
                    status,
                    postponement_count
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(task.id),
                    task.title,
                    task.description,
                    task.estimated_minutes,
                    deadline_due_on,
                    deadline_due_at,
                    time_block_starts_at,
                    time_block_ends_at,
                    task.priority.value,
                    task.status.value,
                    task.postponement_count,
                ),
            )
        except IntegrityError as error:
            # Clear the failed transaction before exposing a port-level error.
            self._connection.rollback()

            # Hide SQLite-specific exceptions from application use cases.
            raise TaskAlreadyExistsError(
                f"Task '{task.id}' already exists."
            ) from error

        # Make the inserted entity visible to later repository operations.
        self._connection.commit()

    def get_by_id(self, task_id: UUID) -> Task | None:
        """Reconstruct one stored task or return None when absent."""

        # Runtime validation keeps malformed identities outside SQL.
        if not isinstance(task_id, UUID):
            raise TypeError("Task identifier must be a UUID.")

        # Parameter binding avoids SQL injection and quoting mistakes.
        task_record = self._connection.execute(
            """
            SELECT
                id,
                title,
                description,
                estimated_minutes,
                deadline_due_on,
                deadline_due_at,
                time_block_starts_at,
                time_block_ends_at,
                priority
            FROM tasks
            WHERE id = ?
            """,
            (str(task_id),),
        ).fetchone()

        # Missing database rows implement the repository port's absence result.
        if task_record is None:
            return None

        # Reuse the authoritative row-to-domain conversion.
        return _deserialize_task_record(task_record)

    def list_all(self) -> tuple[Task, ...]:
        """Reconstruct an immutable snapshot of every stored task."""

        # Use the same column order required by the shared row mapper.
        task_records = self._connection.execute(
            """
            SELECT
                id,
                title,
                description,
                estimated_minutes,
                deadline_due_on,
                deadline_due_at,
                time_block_starts_at,
                time_block_ends_at,
                priority
            FROM tasks
            """
        ).fetchall()

        # Convert each independent row into a validated domain entity.
        return tuple(
            _deserialize_task_record(task_record)
            for task_record in task_records
        )
