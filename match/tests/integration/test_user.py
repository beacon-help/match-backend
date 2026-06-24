import json
from http import HTTPStatus
from unittest.mock import patch

import pytest
from sqlalchemy import text

from match.db import Session
from match.tests.conftest import build_headers


class TestCaseUserSignupPath:
    _USER_SIGNUP_BASE_URL = "/user/signup"
    _USER_ME_URL = "/user/me"

    @pytest.mark.parametrize(
        "signup_payload,url_suffix",
        (
            pytest.param(
                {
                    "first_name": "Maria",
                    "last_name": "De La Luz",
                    "email": "maria@example.com",
                },
                "/helpseeker",
                id="helpseeker",
            ),
            pytest.param(
                {
                    "first_name": "Maria",
                    "last_name": "De La Luz",
                    "email": "maria.volunteer@example.com",
                    "properties": ["HAS_CAR", "CAN_HOST"],
                },
                "/volunteer",
                id="volunteer",
            ),
        ),
    )
    @patch("match.domain.user.uuid.uuid4")
    def test_user_signup_and_verify(self, mock_uuid4, test_client, signup_payload, url_suffix):
        verification_code = "2f75ccc7-9f7d-45f3-87bf-44345b0f2f06"
        mock_uuid4.return_value = verification_code

        user_created_response = test_client.post(
            self._USER_SIGNUP_BASE_URL + url_suffix, data=json.dumps(signup_payload)
        )

        assert user_created_response.status_code == HTTPStatus.CREATED
        user_id = user_created_response.json()["id"]
        assert isinstance(user_id, int)

        headers = build_headers(user_id)

        me_response = test_client.get(self._USER_ME_URL, headers=headers)
        assert me_response.status_code == HTTPStatus.UNAUTHORIZED

        verify_response = test_client.put(f"/user/verify/{verification_code}", headers=headers)
        assert verify_response.status_code == HTTPStatus.OK

        me_response_2 = test_client.get(self._USER_ME_URL, headers=headers)
        assert me_response_2.status_code == HTTPStatus.OK


class TestUserTaskInteractions:
    @pytest.fixture()
    def populate_db(self):
        session = Session()
        clear_users_statement = "DELETE FROM users;"
        clear_statement = "DELETE FROM tasks;"
        user_stmt = """
        INSERT OR REPLACE INTO users (
            id, first_name, last_name, email, properties, is_verified, verification_code, created_at
        ) VALUES
            (1, 'John', 'Johnson', 'john@johnson.com', '[]', 1, '2f75ccc7-9f7d-45f3-87bf-44345b0f2f06', '2024-11-14T00:00:00Z'),
            (2, 'Adam', 'Adamson', 'adam@adamson.com', '[]', 1, '2f75ccc7-9f7d-45f3-87bf-44345b0f2f06', '2024-11-14T00:00:00Z');
        """
        session.execute(text(clear_users_statement))
        session.execute(text(clear_statement))
        session.execute(text(user_stmt))
        session.commit()
        return session

    @staticmethod
    def _add_task(session: Session, task_id=1, owner_id=1, helper_id="null"):
        session.execute(
            text(
                f"""
                INSERT OR REPLACE INTO tasks (
                    id, title, description, status, category, owner_id, helper_id,
                    updated_at, created_at, location_lat, location_lon, location_address
                ) VALUES (
                    {task_id}, 'Help', 'please help me', 'open', 'other', {owner_id}, {helper_id},
                    null, '2024-11-14T00:00:00Z', 39.4738, 0.3756, 'My address'
                );
                """
            )
        )
        session.commit()

    def test_user_views_tasks(self, test_client, populate_db):
        session = populate_db

        response = test_client.get("/task/my-tasks", headers=build_headers(1))

        assert response.status_code == HTTPStatus.OK
        assert response.json() == []

        self._add_task(session)

        response = test_client.get("/task/my-tasks", headers=build_headers(1))

        assert response.status_code == HTTPStatus.OK
        actual = response.json()
        assert len(actual) == 1
        assert actual == [
            {
                "id": 1,
                "title": "Help",
                "created_at": "2024-11-14T00:00:00Z",
                "updated_at": None,
                "status": "open",
                "owner": {"id": 1, "first_name": "John"},
                "helper": None,
                "description": "please help me",
                "location": {
                    "lat": 39.4738,
                    "lon": 0.3756,
                    "address": "My address",
                },
                "category": "other",
            }
        ]

    def test_users_complete_task_together(self, test_client, populate_db):
        session = populate_db
        task_id = 123
        user_1_id = 1
        user_2_id = 2

        self._add_task(session, task_id=task_id)

        join_response = test_client.put(
            f"/task/{task_id}", params={"action": "join"}, headers=build_headers(user_2_id)
        )

        assert join_response.status_code == HTTPStatus.OK
        task = join_response.json()
        assert task["status"] == "pending"
        assert task["helper"] == {"id": user_2_id, "first_name": "Adam"}

        approve_response = test_client.put(
            f"/task/{task_id}",
            params={"action": "approve", "helper_id": user_2_id},
            headers=build_headers(user_1_id),
        )

        assert approve_response.status_code == HTTPStatus.OK
        task = approve_response.json()
        assert task["status"] == "approved"
        assert task["helper"] == {"id": user_2_id, "first_name": "Adam"}

        success_response = test_client.put(
            f"/task/{task_id}",
            params={"action": "report_success"},
            headers=build_headers(user_1_id),
        )

        assert success_response.status_code == HTTPStatus.OK
        task = success_response.json()
        assert task["status"] == "succeeded"
        assert task["owner"] == {"id": user_1_id, "first_name": "John"}
        assert task["helper"] == {"id": user_2_id, "first_name": "Adam"}

    def test_user_rejects_helper_and_closes_task(self, test_client, populate_db):
        session = populate_db
        task_id = 123
        user_1_id = 1
        user_2_id = 2

        self._add_task(session, task_id=task_id)

        join_response = test_client.put(
            f"/task/{task_id}", params={"action": "join"}, headers=build_headers(user_2_id)
        )

        assert join_response.status_code == HTTPStatus.OK
        task = join_response.json()
        assert task["status"] == "pending"
        assert task["helper"] == {"id": user_2_id, "first_name": "Adam"}

        reject_response = test_client.put(
            f"/task/{task_id}",
            params={"action": "reject", "helper_id": user_2_id},
            headers=build_headers(user_1_id),
        )

        assert reject_response.status_code == HTTPStatus.OK
        task = reject_response.json()
        assert task["status"] == "open"
        assert task["helper"] is None

        close_response = test_client.put(
            f"/task/{task_id}", params={"action": "close"}, headers=build_headers(user_1_id)
        )

        assert close_response.status_code == HTTPStatus.OK
        task = close_response.json()
        assert task["status"] == "cancelled"
        assert task["owner"] == {"id": user_1_id, "first_name": "John"}
        assert task["helper"] is None
