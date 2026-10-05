import pytest
from sqlalchemy import text

from match.db import Session
from match.domain.task import Category, Task, TaskEventType
from match.domain.user import User, UserId, UserType
from match.infra.repositories import SQLiteRepository

OWNER = User(
    id=UserId(1), user_type=UserType.HELP_SEEKER, first_name="O", last_name="O", email="o@x.com"
)
HELPER = User(
    id=UserId(2), user_type=UserType.VOLUNTEER, first_name="H", last_name="H", email="h@x.com"
)


def _join(task):
    task.join(HELPER, "I can help")


def _approve(task):
    _join(task)
    task.approve_helper(OWNER, HELPER.id)


SCENARIOS = {
    TaskEventType.CREATED: lambda task: None,
    TaskEventType.OFFERED: _join,
    TaskEventType.APPROVED: _approve,
    TaskEventType.REJECTED: lambda task: (_join(task), task.reject_helper(OWNER, HELPER.id)),
    TaskEventType.WITHDRAWN: lambda task: (_approve(task), task.withdraw(HELPER)),
    TaskEventType.CLOSED: lambda task: task.close(OWNER),
    TaskEventType.SUCCEEDED: lambda task: (_approve(task), task.report_succeeded(OWNER)),
    TaskEventType.FAILED: lambda task: (_approve(task), task.report_failed(OWNER)),
}


@pytest.fixture
def repository():
    session = Session()
    yield SQLiteRepository(session)
    session.execute(
        text("DELETE FROM task_events WHERE task_id IN (SELECT id FROM tasks WHERE owner_id = 1)")
    )
    session.execute(text("DELETE FROM tasks WHERE owner_id = 1"))
    session.commit()
    session.close()


def test_every_event_type_has_a_scenario():
    assert set(SCENARIOS) == set(TaskEventType)


@pytest.mark.parametrize("event_type", SCENARIOS)
def test_stored_status_matches_domain_status(repository, event_type):
    task = repository.create_task(
        Task.create_task(
            owner=OWNER, title="t", description="d", category=Category.OTHER, location=None
        )
    )
    SCENARIOS[event_type](task)
    repository.task_update(task)

    stored = repository.get_task_by_id(task.id)

    assert task.events[-1].type == event_type
    assert stored.status == task.status
