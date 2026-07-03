import json
from http import HTTPStatus
from uuid import uuid4

import pytest

from match.tests.conftest import build_headers
from match.tests.unit.infra.api.conftest import SEED_PASSWORD, VALID_VERIF_CODE


def build_user_response(user_id=100):
    return {
        "id": user_id,
        "first_name": "John",
        "last_name": "Johnson",
        "email": "john@johnson.com",
        "is_verified": True,
    }


def test_health(test_client):
    response = test_client.get("/health")

    assert response.status_code == HTTPStatus.OK


def test_get_user_me(test_client):
    expected = build_user_response()
    response = test_client.get("/user/me", headers=build_headers(100))

    assert response.status_code == HTTPStatus.OK
    assert response.json() == expected


def test_get_user_by_id(test_client):
    expected = build_user_response(100)
    response = test_client.get("/user/100")

    assert response.status_code == HTTPStatus.OK
    assert response.json() == expected


def test_login_happy_path(test_client):
    response = test_client.post(
        "/user/login",
        data={"username": "john@johnson.com", "password": SEED_PASSWORD},
    )

    assert response.status_code == HTTPStatus.OK
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["refresh_token"]

    token = body["access_token"]
    me_response = test_client.get("/user/me", headers={"Authorization": f"Bearer {token}"})
    assert me_response.status_code == HTTPStatus.OK


@pytest.mark.parametrize(
    "username,password",
    (
        pytest.param("john@johnson.com", "wrong-password", id="wrong-password"),
        pytest.param("nobody@nowhere.com", SEED_PASSWORD, id="unknown-user"),
        pytest.param("gary@move.out", SEED_PASSWORD, id="unverified-user"),
    ),
)
def test_login_rejected(test_client, username, password):
    response = test_client.post(
        "/user/login",
        data={"username": username, "password": password},
    )

    assert response.status_code == HTTPStatus.UNAUTHORIZED


def test_refresh_happy_path(test_client):
    login_response = test_client.post(
        "/user/login",
        data={"username": "john@johnson.com", "password": SEED_PASSWORD},
    )
    refresh_token = login_response.json()["refresh_token"]

    response = test_client.post("/user/refresh", json={"refresh_token": refresh_token})

    assert response.status_code == HTTPStatus.OK
    new_access_token = response.json()["access_token"]
    me_response = test_client.get(
        "/user/me", headers={"Authorization": f"Bearer {new_access_token}"}
    )
    assert me_response.status_code == HTTPStatus.OK


def test_access_token_rejected_on_refresh(test_client):
    login_response = test_client.post(
        "/user/login",
        data={"username": "john@johnson.com", "password": SEED_PASSWORD},
    )
    access_token = login_response.json()["access_token"]

    response = test_client.post("/user/refresh", json={"refresh_token": access_token})

    assert response.status_code == HTTPStatus.UNAUTHORIZED


def test_refresh_token_rejected_on_protected_endpoint(test_client):
    login_response = test_client.post(
        "/user/login",
        data={"username": "john@johnson.com", "password": SEED_PASSWORD},
    )
    refresh_token = login_response.json()["refresh_token"]

    response = test_client.get("/task", headers={"Authorization": f"Bearer {refresh_token}"})

    assert response.status_code == HTTPStatus.UNAUTHORIZED


def test_create_helpseeker_user_rejects_properties(test_client):
    payload = {
        "first_name": "Arnold",
        "last_name": "Adams",
        "email": "email@example.com",
        "properties": ["HAS_CAR"],
    }

    response = test_client.post("/user/signup/helpseeker", data=json.dumps(payload))

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


@pytest.mark.parametrize(
    "endpoint,payload",
    (
        pytest.param(
            "/user/signup/helpseeker",
            {
                "first_name": "Arnold",
                "last_name": "Adams",
                "email": "email@example.com",
                "password": "s3cr3t-password",
            },
            id="helpseeker",
        ),
        pytest.param(
            "/user/signup/volunteer",
            {
                "first_name": "John",
                "last_name": "Johnson",
                "email": "john@johnson.com",
                "password": "s3cr3t-password",
                "properties": ["HAS_CAR"],
            },
            id="volunteer",
        ),
    ),
)
def test_create_user_happy_path(test_client, endpoint, payload):
    response = test_client.post(endpoint, data=json.dumps(payload))

    assert response.status_code == HTTPStatus.CREATED


def test_verify_user_happy_path(test_client):
    response = test_client.put(f"/user/verify/{VALID_VERIF_CODE}")
    assert response.status_code == HTTPStatus.OK


@pytest.mark.parametrize(
    "verification_code",
    (
        pytest.param("verif-code-100", id="user already verified"),
        pytest.param(str(uuid4()), id="unknown verification code"),
    ),
)
def test_verify_user_failed(verification_code, test_client):
    response = test_client.put(f"/user/verify/{verification_code}")
    assert response.status_code == HTTPStatus.BAD_REQUEST
