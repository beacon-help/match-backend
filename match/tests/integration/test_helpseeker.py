import json
from http import HTTPStatus
from unittest.mock import patch

import pytest
from sqlalchemy import text

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


# class TestUserTaskInteractions:
#     def test_user_views_tasks(self, test_client, database):
#         response = test_client.get("/task/my-tasks", headers=build_headers(1))
#
#         assert response.status_code == HTTPStatus.OK
#         assert response.json() == []
#
#         database.execute(
#             text(
#                 """
#                 INSERT OR REPLACE INTO tasks (
#                     id, title, description, status, category, owner_id, helper_id,
#                     updated_at, created_at, location_lat, location_lon, location_address
#                 ) VALUES (
#                     1, 'Help', 'please help me', 'open', 'other', 1, null,
#                     null, '2024-11-14T00:00:00Z', 39.4738, 0.3756, 'My address'
#                 );
#                 """
#             )
#         )
#         database.commit()
#
#         response = test_client.get("/task/my-tasks", headers=build_headers(1))
#
#         assert response.status_code == HTTPStatus.OK
#         assert response.json() == [
#             {
#                 "id": 1,
#                 "title": "Help",
#                 "created_at": "2024-11-14T00:00:00Z",
#                 "updated_at": None,
#                 "status": "open",
#                 "owner": {"id": 1, "first_name": "Alice"},
#                 "helper": None,
#                 "description": "please help me",
#                 "location": {
#                     "lat": 39.4738,
#                     "lon": 0.3756,
#                     "address": "My address",
#                 },
#                 "category": "other",
#             }
#         ]
