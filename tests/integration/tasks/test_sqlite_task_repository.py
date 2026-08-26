"""Integration tests for SQLite task persistence."""

# Temporal values verify reversible ISO 8601 persistence.
from datetime import UTC, date, datetime

# Path types the temporary database location supplied by pytest.
from pathlib import Path

# SQLite is included in Python and requires no external service.
import sqlite3

# UUID creates valid identities that are absent from storage.
from uuid import uuid4

# Pytest verifies runtime validation at the SQLite boundary.
import pytest

# CalendarTimeBlock represents exact planned work intervals.
from personal_productivity.calendar.domain.calendar_time_block import (
    CalendarTimeBlock,
)

# Application use cases must work without knowing that SQLite is used.
from personal_productivity.tasks.application.cancel_task import CancelTask
from personal_productivity.tasks.application.complete_task import CompleteTask
from personal_productivity.tasks.application.create_task import CreateTask
from personal_productivity.tasks.application.get_task import GetTask
from personal_productivity.tasks.application.list_tasks import ListTasks
from personal_productivity.tasks.application.pause_task import PauseTask
from personal_productivity.tasks.application.postpone_task import PostponeTask
from personal_productivity.tasks.application.resume_task import ResumeTask
from personal_productivity.tasks.application.schedule_task import ScheduleTask
from personal_productivity.tasks.application.start_task import StartTask

# Repository outcomes remain independent from concrete storage.
from personal_productivity.tasks.application.ports.task_repository import (
    TaskAlreadyExistsError,
    TaskNotFoundError,
)

# Persistence tests cross the boundary using real domain entities.
from personal_productivity.tasks.domain.task import Task

# TaskDeadline preserves the user's date-only or exact-time intent.
from personal_productivity.tasks.domain.task_deadline import TaskDeadline

# Priority verifies stable enum serialization through SQLite text.
from personal_productivity.tasks.domain.task_priority import TaskPriority

# Status verifies that lifecycle values survive serialization.
from personal_productivity.tasks.domain.task_status import TaskStatus

# Import the local SQLite adapter and its schema initializer.
from personal_productivity.tasks.infrastructure.repositories.sqlite_task_repository import (
    SqliteTaskRepository,
    initialize_task_schema,
)


def test_schema_initialization_creates_tasks_table() -> None:
    """Verify that local database initialization creates task storage."""

    # Arrange: open a real SQLite database that exists only in memory.
    connection = sqlite3.connect(":memory:")

    try:
        # Act: initialize the schema required by task persistence.
        initialize_task_schema(connection)

        # Query SQLite metadata instead of relying on implementation details.
        table_record = connection.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
              AND name = 'tasks'
            """
        ).fetchone()
    finally:
        # Always release the native database connection after the test.
        connection.close()

    # Assert: initialization created the expected table.
    assert table_record == ("tasks",)


def test_added_task_can_be_retrieved_by_identity() -> None:
    """Verify that SQLite persists and reconstructs a basic task."""

    # Arrange: initialize isolated real SQLite storage.
    connection = sqlite3.connect(":memory:")

    try:
        initialize_task_schema(connection)
        repository = SqliteTaskRepository(connection=connection)
        original_task = Task(
            title="Study Docker.",
        )

        # Act: cross the persistence boundary in both directions.
        repository.add(original_task)
        retrieved_task = repository.get_by_id(original_task.id)
    finally:
        # Always release the native database connection.
        connection.close()

    # Assert: retrieval reconstructs a new domain entity.
    assert retrieved_task is not original_task
    assert isinstance(retrieved_task, Task)

    # Assert: identity and basic domain state survive persistence.
    assert retrieved_task.id == original_task.id
    assert retrieved_task.title == "Study Docker."
    assert retrieved_task.status is TaskStatus.PENDING


def test_sqlite_preserves_optional_scalar_task_fields() -> None:
    """Verify that ordinary planning data survives a database round trip."""

    # Arrange: create isolated SQLite storage and a configured task.
    connection = sqlite3.connect(":memory:")

    try:
        initialize_task_schema(connection)
        repository = SqliteTaskRepository(connection=connection)
        original_task = Task(
            title="Prepare the investor presentation.",
            description="   Include the financial forecast.   ",
            estimated_minutes=90,
            priority=TaskPriority.HIGH,
        )

        # Act: persist and reconstruct the configured entity.
        repository.add(original_task)
        retrieved_task = repository.get_by_id(original_task.id)
    finally:
        # Always release the native database connection.
        connection.close()

    # Assert: retrieval produced one existing domain entity.
    assert retrieved_task is not None

    # Assert: normalized optional values survive serialization.
    assert retrieved_task.description == "Include the financial forecast."
    assert retrieved_task.estimated_minutes == 90
    assert retrieved_task.priority is TaskPriority.HIGH


def test_sqlite_preserves_both_deadline_precisions() -> None:
    """Verify that date-only and exact deadlines survive persistence."""

    # Arrange: create isolated storage and both deadline variants.
    connection = sqlite3.connect(":memory:")

    try:
        initialize_task_schema(connection)
        repository = SqliteTaskRepository(connection=connection)
        date_deadline_task = Task(
            title="Renew the insurance.",
            deadline=TaskDeadline(
                due_on=date(2026, 8, 20),
            ),
        )
        exact_deadline_task = Task(
            title="Submit the report.",
            deadline=TaskDeadline(
                due_at=datetime(
                    2026,
                    8,
                    21,
                    18,
                    30,
                    tzinfo=UTC,
                ),
            ),
        )

        # Act: persist and reconstruct both temporal representations.
        repository.add(date_deadline_task)
        repository.add(exact_deadline_task)
        retrieved_date_task = repository.get_by_id(
            date_deadline_task.id,
        )
        retrieved_exact_task = repository.get_by_id(
            exact_deadline_task.id,
        )
    finally:
        # Always release the native database connection.
        connection.close()

    # Assert: both stored rows were reconstructed.
    assert retrieved_date_task is not None
    assert retrieved_exact_task is not None

    # Assert: persistence preserves deadline precision and value.
    assert retrieved_date_task.deadline == date_deadline_task.deadline
    assert retrieved_exact_task.deadline == exact_deadline_task.deadline


def test_sqlite_preserves_optional_calendar_time_block() -> None:
    """Verify that planned work intervals survive persistence."""

    # Arrange: create isolated storage and one scheduled task.
    connection = sqlite3.connect(":memory:")

    try:
        initialize_task_schema(connection)
        repository = SqliteTaskRepository(connection=connection)
        original_task = Task(
            title="Study Docker.",
            time_block=CalendarTimeBlock(
                starts_at=datetime(
                    2026,
                    8,
                    15,
                    18,
                    0,
                    tzinfo=UTC,
                ),
                ends_at=datetime(
                    2026,
                    8,
                    15,
                    19,
                    30,
                    tzinfo=UTC,
                ),
            ),
        )

        # Act: persist and reconstruct the scheduled task.
        repository.add(original_task)
        retrieved_task = repository.get_by_id(original_task.id)
    finally:
        # Always release the native database connection.
        connection.close()

    # Assert: the stored row produced one domain entity.
    assert retrieved_task is not None

    # Assert: both exact interval boundaries remain unchanged.
    assert retrieved_task.time_block == original_task.time_block


def test_sqlite_returns_none_for_unknown_task_identity() -> None:
    """Verify that an absent valid UUID follows the repository contract."""

    # Arrange: initialize empty isolated SQLite storage.
    connection = sqlite3.connect(":memory:")

    try:
        initialize_task_schema(connection)
        repository = SqliteTaskRepository(connection=connection)

        # Act: request a valid identity that was never persisted.
        retrieved_task = repository.get_by_id(uuid4())
    finally:
        # Always release the native database connection.
        connection.close()

    # Assert: database absence is represented explicitly.
    assert retrieved_task is None


@pytest.mark.parametrize(
    "invalid_task_id",
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
    invalid_task_id: object,
) -> None:
    """Ensure that malformed identities never become SQL parameters."""

    # Arrange: initialize empty isolated SQLite storage.
    connection = sqlite3.connect(":memory:")

    try:
        initialize_task_schema(connection)
        repository = SqliteTaskRepository(connection=connection)

        # Act and Assert: the adapter enforces the repository contract.
        with pytest.raises(
            TypeError,
            match="Task identifier must be a UUID",
        ):
            repository.get_by_id(invalid_task_id)
    finally:
        # Always release the native database connection.
        connection.close()


@pytest.mark.parametrize(
    "invalid_task",
    [
        None,
        42,
        "not-a-task",
    ],
    ids=[
        "none",
        "integer",
        "text",
    ],
)
def test_sqlite_add_rejects_non_task_values(
    invalid_task: object,
) -> None:
    """Ensure that arbitrary values cannot enter SQLite task storage."""

    # Arrange: initialize empty isolated SQLite storage.
    connection = sqlite3.connect(":memory:")

    try:
        initialize_task_schema(connection)
        repository = SqliteTaskRepository(connection=connection)

        # Act and Assert: persistence accepts complete Task entities only.
        with pytest.raises(
            TypeError,
            match="Stored value must be a Task",
        ):
            repository.add(invalid_task)
    finally:
        # Always release the native database connection.
        connection.close()


def test_sqlite_add_rejects_duplicate_task_identity() -> None:
    """Ensure that SQLite add semantics never overwrite an entity."""

    # Arrange: create two tasks sharing one portable identity.
    connection = sqlite3.connect(":memory:")

    try:
        initialize_task_schema(connection)
        repository = SqliteTaskRepository(connection=connection)
        existing_task = Task(title="Study Docker.")
        replacement_task = Task(
            title="Replace the original task.",
            id=existing_task.id,
        )
        repository.add(existing_task)

        # Act and Assert: database uniqueness becomes a port-level error.
        with pytest.raises(
            TaskAlreadyExistsError,
            match=f"Task '{existing_task.id}' already exists",
        ):
            repository.add(replacement_task)

        # Assert: rejection preserves the original stored entity.
        retrieved_task = repository.get_by_id(existing_task.id)
    finally:
        # Always release the native database connection.
        connection.close()

    assert retrieved_task is not None
    assert retrieved_task.title == "Study Docker."


def test_sqlite_list_all_returns_immutable_task_snapshot() -> None:
    """Verify that SQLite reconstructs every stored task."""

    # Arrange: persist two independent tasks in isolated storage.
    connection = sqlite3.connect(":memory:")

    try:
        initialize_task_schema(connection)
        repository = SqliteTaskRepository(connection=connection)
        first_task = Task(title="Study Docker.")
        second_task = Task(
            title="Renew the insurance.",
            priority=TaskPriority.HIGH,
        )
        repository.add(first_task)
        repository.add(second_task)

        # Act: retrieve the complete persistence snapshot.
        task_snapshot = repository.list_all()
    finally:
        # Always release the native database connection.
        connection.close()

    # Assert: the adapter follows the immutable port contract.
    assert isinstance(task_snapshot, tuple)
    assert len(task_snapshot) == 2

    # Assert: every identity was reconstructed exactly once.
    retrieved_ids = {
        task.id
        for task in task_snapshot
    }
    assert retrieved_ids == {
        first_task.id,
        second_task.id,
    }


def test_task_use_cases_collaborate_through_sqlite() -> None:
    """Verify that SQLite can replace memory behind the same port."""

    # Arrange: inject one SQLite adapter into three application use cases.
    connection = sqlite3.connect(":memory:")

    try:
        initialize_task_schema(connection)
        repository = SqliteTaskRepository(connection=connection)
        create_task = CreateTask(repository=repository)
        get_task = GetTask(repository=repository)
        list_tasks = ListTasks(repository=repository)

        # Act: create, retrieve, and filter through application boundaries.
        created_task = create_task.execute(
            title="Prepare the investor presentation.",
            description="Include the financial forecast.",
            estimated_minutes=90,
            priority=TaskPriority.HIGH,
        )
        retrieved_task = get_task.execute(
            task_id=created_task.id,
        )
        listed_tasks = list_tasks.execute(
            priority=TaskPriority.HIGH,
        )
    finally:
        # Always release the native database connection.
        connection.close()

    # Assert: retrieval reconstructs the persisted domain identity.
    assert retrieved_task.id == created_task.id
    assert retrieved_task.description == created_task.description

    # Assert: application filtering also works with SQLite snapshots.
    assert len(listed_tasks) == 1
    assert listed_tasks[0].id == created_task.id


def test_sqlite_file_preserves_task_across_connections(
    tmp_path: Path,
) -> None:
    """Verify that local persistence survives connection shutdown."""

    # Arrange: let pytest provide an isolated temporary directory.
    database_path = tmp_path / "meocupo.db"
    original_task = Task(
        title="Renew the insurance.",
        description="Review the annual policy.",
    )

    # Act: create the database and persist through the first connection.
    first_connection = sqlite3.connect(database_path)

    try:
        initialize_task_schema(first_connection)
        first_repository = SqliteTaskRepository(
            connection=first_connection,
        )
        first_repository.add(original_task)
    finally:
        # Closing the first connection simulates application shutdown.
        first_connection.close()

    # Act: reopen the same file through a completely new connection.
    second_connection = sqlite3.connect(database_path)

    try:
        second_repository = SqliteTaskRepository(
            connection=second_connection,
        )
        retrieved_task = second_repository.get_by_id(
            original_task.id,
        )
    finally:
        # Release the reopened connection after verification.
        second_connection.close()

    # Assert: committed task data survived both connection lifecycles.
    assert retrieved_task is not None
    assert retrieved_task.id == original_task.id
    assert retrieved_task.title == original_task.title
    assert retrieved_task.description == original_task.description


def test_sqlite_preserves_completed_task_lifecycle() -> None:
    """Verify that completion state and history survive persistence."""

    # Arrange: complete one task at an authoritative fixed instant.
    connection = sqlite3.connect(":memory:")
    completed_at = datetime(
        2026,
        8,
        14,
        18,
        30,
        tzinfo=UTC,
    )
    original_task = Task(
        title="Prepare the investor presentation.",
    )
    original_task.complete(completed_at=completed_at)

    try:
        initialize_task_schema(connection)
        repository = SqliteTaskRepository(connection=connection)

        # Act: persist and reconstruct the completed entity.
        repository.add(original_task)
        retrieved_task = repository.get_by_id(original_task.id)
    finally:
        # Always release the native database connection.
        connection.close()

    # Assert: the stored task was reconstructed successfully.
    assert retrieved_task is not None

    # Assert: lifecycle state and its historical instant remain coupled.
    assert retrieved_task.status is TaskStatus.COMPLETED
    assert retrieved_task.completed_at == completed_at


def test_sqlite_preserves_task_postponement_history() -> None:
    """Verify that deadline postponement history survives persistence."""

    # Arrange: postpone one calendar deadline twice.
    connection = sqlite3.connect(":memory:")
    original_task = Task(
        title="Renew the insurance.",
        deadline=TaskDeadline(
            due_on=date(2026, 8, 15),
        ),
    )
    original_task.postpone(
        deadline=TaskDeadline(
            due_on=date(2026, 8, 20),
        ),
    )
    original_task.postpone(
        deadline=TaskDeadline(
            due_on=date(2026, 8, 25),
        ),
    )

    try:
        initialize_task_schema(connection)
        repository = SqliteTaskRepository(connection=connection)

        # Act: persist and reconstruct the task history.
        repository.add(original_task)
        retrieved_task = repository.get_by_id(original_task.id)
    finally:
        # Always release the native database connection.
        connection.close()

    # Assert: the stored task was reconstructed successfully.
    assert retrieved_task is not None

    # Assert: both current planning and its history remain unchanged.
    assert retrieved_task.deadline == original_task.deadline
    assert retrieved_task.postponement_count == 2
    assert retrieved_task.status is TaskStatus.PENDING


def test_sqlite_preserves_non_completed_lifecycle_states() -> None:
    """Verify that active and terminal states survive reconstruction."""

    # Arrange: create tasks in three distinct non-completed states.
    in_progress_task = Task(title="Study Docker.")
    in_progress_task.start()

    paused_task = Task(title="Prepare the investor presentation.")
    paused_task.start()
    paused_task.pause()

    cancelled_task = Task(title="Buy soil for the pitaya.")
    cancelled_task.cancel()

    connection = sqlite3.connect(":memory:")

    try:
        initialize_task_schema(connection)
        repository = SqliteTaskRepository(connection=connection)

        # Persist every lifecycle variant through the same adapter.
        repository.add(in_progress_task)
        repository.add(paused_task)
        repository.add(cancelled_task)

        # Act: reconstruct the complete immutable snapshot.
        retrieved_tasks = repository.list_all()
    finally:
        # Always release the native database connection.
        connection.close()

    # Assert: each identity retains its exact persisted lifecycle state.
    retrieved_statuses = {
        task.id: task.status
        for task in retrieved_tasks
    }
    assert retrieved_statuses == {
        in_progress_task.id: TaskStatus.IN_PROGRESS,
        paused_task.id: TaskStatus.PAUSED,
        cancelled_task.id: TaskStatus.CANCELLED,
    }

    # Assert: non-completed tasks never invent completion history.
    assert all(
        task.completed_at is None
        for task in retrieved_tasks
    )


def test_sqlite_save_persists_existing_task_state() -> None:
    """Verify that saving updates an existing SQLite task row."""

    # Arrange: persist a task in its initial pending state.
    connection = sqlite3.connect(":memory:")
    task = Task(title="Study Docker.")

    try:
        initialize_task_schema(connection)
        repository = SqliteTaskRepository(connection=connection)
        repository.add(task)

        # Change the authoritative entity after its initial insertion.
        task.start()

        # Act: persist the newer lifecycle state.
        repository.save(task)
        retrieved_task = repository.get_by_id(task.id)
    finally:
        # Always release the native database connection.
        connection.close()

    # Assert: the existing row was reconstructed with its newer state.
    assert retrieved_task is not None
    assert retrieved_task.id == task.id
    assert retrieved_task.status is TaskStatus.IN_PROGRESS
    assert retrieved_task.completed_at is None


@pytest.mark.parametrize(
    "invalid_task",
    [
        None,
        42,
        "not-a-task",
    ],
    ids=[
        "none",
        "integer",
        "text",
    ],
)
def test_sqlite_save_rejects_non_task_values(
    invalid_task: object,
) -> None:
    """Ensure that arbitrary values cannot enter SQLite updates."""

    # Arrange: initialize isolated SQLite storage.
    connection = sqlite3.connect(":memory:")

    try:
        initialize_task_schema(connection)
        repository = SqliteTaskRepository(connection=connection)

        # Act and Assert: save accepts complete Task entities only.
        with pytest.raises(
            TypeError,
            match="Stored value must be a Task",
        ):
            repository.save(invalid_task)
    finally:
        # Always release the native database connection.
        connection.close()


def test_sqlite_save_rejects_unknown_task_identity() -> None:
    """Ensure that saving cannot create a missing SQLite task."""

    # Arrange: create an entity whose identity is absent from storage.
    connection = sqlite3.connect(":memory:")
    missing_task = Task(title="Study Docker.")

    try:
        initialize_task_schema(connection)
        repository = SqliteTaskRepository(connection=connection)

        # Act and Assert: creation must use add instead of save.
        with pytest.raises(
            TaskNotFoundError,
            match=f"Task '{missing_task.id}' was not found",
        ):
            repository.save(missing_task)

        # Assert: the rejected update did not create a database row.
        assert repository.get_by_id(missing_task.id) is None
    finally:
        # Always release the native database connection.
        connection.close()


def test_start_task_persists_transition_through_sqlite() -> None:
    """Verify that starting work survives a complete SQLite round trip."""

    # Arrange: inject one SQLite repository into the collaborating use cases.
    connection = sqlite3.connect(":memory:")

    try:
        initialize_task_schema(connection)
        repository = SqliteTaskRepository(connection=connection)
        create_task = CreateTask(repository=repository)
        start_task = StartTask(repository=repository)
        get_task = GetTask(repository=repository)

        # Create the task through the application boundary.
        created_task = create_task.execute(
            title="Study Docker.",
        )

        # Act: retrieve, transition, and save through StartTask.
        started_task = start_task.execute(
            task_id=created_task.id,
        )

        # Re-read the entity instead of trusting the in-memory result.
        retrieved_task = get_task.execute(
            task_id=created_task.id,
        )
    finally:
        # Always release the native database connection.
        connection.close()

    # Assert: both application results retain the same identity.
    assert started_task.id == created_task.id
    assert retrieved_task.id == created_task.id

    # Assert: the lifecycle transition survived SQLite persistence.
    assert started_task.status is TaskStatus.IN_PROGRESS
    assert retrieved_task.status is TaskStatus.IN_PROGRESS


def test_pause_task_persists_transition_through_sqlite() -> None:
    """Verify that pausing work survives a complete SQLite round trip."""

    # Arrange: inject one SQLite repository into all collaborating use cases.
    connection = sqlite3.connect(":memory:")

    try:
        initialize_task_schema(connection)
        repository = SqliteTaskRepository(connection=connection)
        create_task = CreateTask(repository=repository)
        start_task = StartTask(repository=repository)
        pause_task = PauseTask(repository=repository)
        get_task = GetTask(repository=repository)

        # Create and start the task through application boundaries.
        created_task = create_task.execute(
            title="Study Docker.",
        )
        start_task.execute(
            task_id=created_task.id,
        )

        # Act: retrieve, pause, and save through PauseTask.
        paused_task = pause_task.execute(
            task_id=created_task.id,
        )

        # Re-read the entity from SQLite after the transition.
        retrieved_task = get_task.execute(
            task_id=created_task.id,
        )
    finally:
        # Always release the native database connection.
        connection.close()

    # Assert: both application results retain the original identity.
    assert paused_task.id == created_task.id
    assert retrieved_task.id == created_task.id

    # Assert: the paused state survived SQLite persistence.
    assert paused_task.status is TaskStatus.PAUSED
    assert retrieved_task.status is TaskStatus.PAUSED


def test_resume_task_persists_transition_through_sqlite() -> None:
    """Verify that resumed work survives a complete SQLite round trip."""

    # Arrange: inject one SQLite repository into all collaborating use cases.
    connection = sqlite3.connect(":memory:")

    try:
        initialize_task_schema(connection)
        repository = SqliteTaskRepository(connection=connection)
        create_task = CreateTask(repository=repository)
        start_task = StartTask(repository=repository)
        pause_task = PauseTask(repository=repository)
        resume_task = ResumeTask(repository=repository)
        get_task = GetTask(repository=repository)

        # Create, start, and pause through application boundaries.
        created_task = create_task.execute(
            title="Study Docker.",
        )
        start_task.execute(
            task_id=created_task.id,
        )
        pause_task.execute(
            task_id=created_task.id,
        )

        # Act: retrieve, resume, and save through ResumeTask.
        resumed_task = resume_task.execute(
            task_id=created_task.id,
        )

        # Re-read the entity from SQLite after the transition.
        retrieved_task = get_task.execute(
            task_id=created_task.id,
        )
    finally:
        # Always release the native database connection.
        connection.close()

    # Assert: both application results retain the original identity.
    assert resumed_task.id == created_task.id
    assert retrieved_task.id == created_task.id

    # Assert: active work survived SQLite persistence.
    assert resumed_task.status is TaskStatus.IN_PROGRESS
    assert retrieved_task.status is TaskStatus.IN_PROGRESS


def test_complete_task_persists_transition_through_sqlite() -> None:
    """Verify that completion history survives a complete SQLite round trip."""

    # Arrange: inject one SQLite repository into collaborating use cases.
    connection = sqlite3.connect(":memory:")
    completed_at = datetime(
        2026,
        8,
        26,
        18,
        30,
        tzinfo=UTC,
    )

    try:
        initialize_task_schema(connection)
        repository = SqliteTaskRepository(connection=connection)
        create_task = CreateTask(repository=repository)
        complete_task = CompleteTask(repository=repository)
        get_task = GetTask(repository=repository)

        # Create the task through the application boundary.
        created_task = create_task.execute(
            title="Prepare the investor presentation.",
        )

        # Act: retrieve, complete, and save through CompleteTask.
        completed_task = complete_task.execute(
            task_id=created_task.id,
            completed_at=completed_at,
        )

        # Re-read the entity from SQLite after the transition.
        retrieved_task = get_task.execute(
            task_id=created_task.id,
        )
    finally:
        # Always release the native database connection.
        connection.close()

    # Assert: both application results retain the original identity.
    assert completed_task.id == created_task.id
    assert retrieved_task.id == created_task.id

    # Assert: lifecycle and completion history survived persistence.
    assert completed_task.status is TaskStatus.COMPLETED
    assert retrieved_task.status is TaskStatus.COMPLETED
    assert completed_task.completed_at == completed_at
    assert retrieved_task.completed_at == completed_at


def test_cancel_task_persists_transition_through_sqlite() -> None:
    """Verify that cancellation survives a complete SQLite round trip."""

    # Arrange: inject one SQLite repository into collaborating use cases.
    connection = sqlite3.connect(":memory:")

    try:
        initialize_task_schema(connection)
        repository = SqliteTaskRepository(connection=connection)
        create_task = CreateTask(repository=repository)
        cancel_task = CancelTask(repository=repository)
        get_task = GetTask(repository=repository)

        # Create the task through the application boundary.
        created_task = create_task.execute(
            title="Buy soil for the pitaya.",
        )

        # Act: retrieve, cancel, and save through CancelTask.
        cancelled_task = cancel_task.execute(
            task_id=created_task.id,
        )

        # Re-read the entity from SQLite after the transition.
        retrieved_task = get_task.execute(
            task_id=created_task.id,
        )
    finally:
        # Always release the native database connection.
        connection.close()

    # Assert: both application results retain the original identity.
    assert cancelled_task.id == created_task.id
    assert retrieved_task.id == created_task.id

    # Assert: cancellation survived without inventing completion history.
    assert cancelled_task.status is TaskStatus.CANCELLED
    assert retrieved_task.status is TaskStatus.CANCELLED
    assert cancelled_task.completed_at is None
    assert retrieved_task.completed_at is None


def test_postpone_task_persists_planning_through_sqlite() -> None:
    """Verify that postponement history survives a SQLite round trip."""

    # Arrange: define the original and later calendar commitments.
    connection = sqlite3.connect(":memory:")
    original_deadline = TaskDeadline(
        due_on=date(2026, 8, 26),
    )
    postponed_deadline = TaskDeadline(
        due_on=date(2026, 8, 30),
    )

    try:
        initialize_task_schema(connection)
        repository = SqliteTaskRepository(connection=connection)
        create_task = CreateTask(repository=repository)
        postpone_task = PostponeTask(repository=repository)
        get_task = GetTask(repository=repository)

        # Create the task with its initial temporal commitment.
        created_task = create_task.execute(
            title="Renew the insurance.",
            deadline=original_deadline,
        )

        # Act: retrieve, postpone, and save through PostponeTask.
        postponed_task = postpone_task.execute(
            task_id=created_task.id,
            deadline=postponed_deadline,
        )

        # Re-read the entity from SQLite after the planning change.
        retrieved_task = get_task.execute(
            task_id=created_task.id,
        )
    finally:
        # Always release the native database connection.
        connection.close()

    # Assert: both application results retain the original identity.
    assert postponed_task.id == created_task.id
    assert retrieved_task.id == created_task.id

    # Assert: current planning and its history survived persistence.
    assert postponed_task.deadline == postponed_deadline
    assert retrieved_task.deadline == postponed_deadline
    assert postponed_task.postponement_count == 1
    assert retrieved_task.postponement_count == 1

    # Assert: postponement does not alter lifecycle.
    assert postponed_task.status is TaskStatus.PENDING
    assert retrieved_task.status is TaskStatus.PENDING


def test_schedule_task_persists_allocation_through_sqlite() -> None:
    """Verify that task calendar allocation survives a SQLite round trip."""

    # Arrange: define one exact interval for planned work.
    connection = sqlite3.connect(":memory:")
    time_block = CalendarTimeBlock(
        starts_at=datetime(2026, 8, 27, 18, 0, tzinfo=UTC),
        ends_at=datetime(2026, 8, 27, 19, 30, tzinfo=UTC),
    )

    try:
        initialize_task_schema(connection)
        repository = SqliteTaskRepository(connection=connection)
        create_task = CreateTask(repository=repository)
        schedule_task = ScheduleTask(repository=repository)
        get_task = GetTask(repository=repository)

        # Create the task without an initial calendar allocation.
        created_task = create_task.execute(
            title="Study Docker.",
        )

        # Act: retrieve, schedule, and save through ScheduleTask.
        scheduled_task = schedule_task.execute(
            task_id=created_task.id,
            time_block=time_block,
        )

        # Re-read the entity from SQLite after the planning change.
        retrieved_task = get_task.execute(
            task_id=created_task.id,
        )
    finally:
        # Always release the native database connection.
        connection.close()

    # Assert: both application results retain the original identity.
    assert scheduled_task.id == created_task.id
    assert retrieved_task.id == created_task.id

    # Assert: the exact allocation survived SQLite persistence.
    assert scheduled_task.time_block == time_block
    assert retrieved_task.time_block == time_block

    # Assert: scheduling does not alter lifecycle.
    assert scheduled_task.status is TaskStatus.PENDING
    assert retrieved_task.status is TaskStatus.PENDING
