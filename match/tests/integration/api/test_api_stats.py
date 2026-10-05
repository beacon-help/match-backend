from http import HTTPStatus

from sqlalchemy import text

from match.db import Session
from match.tests.conftest import build_headers
from match.tests.integration.api.test_api_task import insert_events


def test_get_stats(test_client):
    response = test_client.get("/stats/")

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {
        "tasks": {"total": 1, "successful": 0, "in_progress": 0},
        "users": {"total_helpers": 2, "total_help_seekers": 2},
    }


def test_get_stats_counts_tasks_by_status(test_client):
    session = Session()
    statement = """
        INSERT OR REPLACE INTO tasks (id,title,description,category,owner_id,helper_id,updated_at,created_at,location_lat,location_lon,location_address)
        VALUES
            (101, 'Pending', 'pending', 'other', 101, 100, null, '2024-11-14T00:00:00Z', null, null, null),
            (102, 'Approved', 'approved', 'other', 101, 100, null, '2024-11-14T00:00:00Z', null, null, null),
            (103, 'Succeeded', 'succeeded', 'other', 101, 100, null, '2024-11-14T00:00:00Z', null, null, null),
            (104, 'Failed', 'failed', 'other', 101, 100, null, '2024-11-14T00:00:00Z', null, null, null),
            (105, 'Closed', 'closed', 'other', 101, null, null, '2024-11-14T00:00:00Z', null, null, null);
        """
    session.execute(text(statement))
    insert_events(
        session,
        (101, "created", 101, None),
        (101, "offered", 100, 100),
        (102, "created", 101, None),
        (102, "offered", 100, 100),
        (102, "approved", 101, 100),
        (103, "created", 101, None),
        (103, "offered", 100, 100),
        (103, "approved", 101, 100),
        (103, "succeeded", 101, 100),
        (104, "created", 101, None),
        (104, "offered", 100, 100),
        (104, "approved", 101, 100),
        (104, "failed", 101, 100),
        (105, "created", 101, None),
        (105, "closed", 101, None),
    )
    session.commit()

    response = test_client.get("/stats/")

    assert response.status_code == HTTPStatus.OK
    assert response.json()["tasks"] == {"total": 6, "successful": 1, "in_progress": 2}


def test_get_stats_excludes_deleted_user_and_their_tasks(test_client):
    test_client.delete("/user/me", headers=build_headers(100))

    response = test_client.get("/stats/")

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {
        "tasks": {"total": 0, "successful": 0, "in_progress": 0},
        "users": {"total_helpers": 1, "total_help_seekers": 2},
    }
