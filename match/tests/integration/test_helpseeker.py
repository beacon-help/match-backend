import json
from http import HTTPStatus
from unittest.mock import patch

import pytest

from match.tests.conftest import build_headers


class TestCaseUserSignupPath:
    _USER_SIGNUP_URL = "/user/signup"
    _USER_ME_URL = "/user/me"

    @pytest.mark.parametrize(
        "signup_payload",
        (
            pytest.param(
                {
                    "first_name": "Maria",
                    "last_name": "De La Luz",
                    "email": "maria@example.com",
                },
                id="helpseeker",
            ),
            pytest.param(
                {
                    "first_name": "Maria",
                    "last_name": "De La Luz",
                    "email": "maria.volunteer@example.com",
                    "properties": ["HAS_CAR", "CAN_HOST"],
                },
                id="volunteer",
            ),
        ),
    )
    @patch("match.domain.user.uuid.uuid4")
    def test_user_signup_and_verify(self, mock_uuid4, test_client, signup_payload):
        verification_code = "2f75ccc7-9f7d-45f3-87bf-44345b0f2f06"
        mock_uuid4.return_value = verification_code

        user_created_response = test_client.post(
            self._USER_SIGNUP_URL, data=json.dumps(signup_payload)
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
