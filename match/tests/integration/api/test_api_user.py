import json
from http import HTTPStatus
from uuid import uuid4

import pytest

from match.app.service import MatchService
from match.domain.exceptions import UserNotFound
from match.tests.conftest import build_headers
from match.tests.integration.api.conftest import SEED_PASSWORD, VALID_VERIF_CODE


def build_user_response(user_id=100):
    return {
        "id": user_id,
        "user_type": "volunteer",
        "first_name": "John",
        "last_name": "Johnson",
        "email": "john@johnson.com",
        "is_verified": True,
        "properties": [],
    }


def test_health(test_client):
    response = test_client.get("/health")

    assert response.status_code == HTTPStatus.OK


def test_get_user_me(test_client):
    expected = build_user_response()
    response = test_client.get("/user/me", headers=build_headers(100))

    assert response.status_code == HTTPStatus.OK
    assert response.json() == expected


def test_get_user_by_id_returns_public_profile(test_client):
    response = test_client.get("/user/100", headers=build_headers(101))

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {"id": 100, "user_type": "volunteer", "first_name": "John"}


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
        "properties": ["has_car"],
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
                "first_name": "Vera",
                "last_name": "Volunteer",
                "email": "vera@example.com",
                "password": "s3cr3t-password",
                "properties": ["has_car"],
            },
            id="volunteer",
        ),
    ),
)
def test_create_user_happy_path(test_client, endpoint, payload):
    response = test_client.post(endpoint, data=json.dumps(payload))

    assert response.status_code == HTTPStatus.CREATED
    assert response.json()["properties"] == payload.get("properties", [])


@pytest.mark.parametrize("endpoint", ("/user/signup/helpseeker", "/user/signup/volunteer"))
def test_create_user_with_registered_email_conflicts(test_client, endpoint):
    payload = {
        "first_name": "Someone",
        "last_name": "Else",
        "email": "john@johnson.com",
        "password": "s3cr3t-password",
    }
    if endpoint.endswith("volunteer"):
        payload["properties"] = []

    response = test_client.post(endpoint, json=payload)

    assert response.status_code == HTTPStatus.CONFLICT
    assert "John" not in response.text


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


def test_delete_me(test_client):
    headers = build_headers(100)

    response = test_client.delete("/user/me", headers=headers)

    assert response.status_code == HTTPStatus.NO_CONTENT
    assert response.content == b""
    assert test_client.get("/user/me", headers=headers).status_code == HTTPStatus.UNAUTHORIZED


@pytest.fixture
def deleted_user(test_client):
    test_client.delete("/user/me", headers=build_headers(100))


def test_deleted_user_cannot_log_in(test_client, deleted_user):
    response = test_client.post(
        "/user/login",
        data={"username": "john@johnson.com", "password": SEED_PASSWORD},
    )

    assert response.status_code == HTTPStatus.UNAUTHORIZED


def test_deleted_user_cannot_refresh_token(test_client):
    login_response = test_client.post(
        "/user/login",
        data={"username": "john@johnson.com", "password": SEED_PASSWORD},
    )
    test_client.delete("/user/me", headers=build_headers(100))

    response = test_client.post(
        "/user/refresh", json={"refresh_token": login_response.json()["refresh_token"]}
    )

    assert response.status_code == HTTPStatus.UNAUTHORIZED


def test_get_deleted_user_answers_like_unknown_user(test_client, deleted_user):
    response = test_client.get("/user/100", headers=build_headers(101))

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json() == test_client.get("/user/9999", headers=build_headers(101)).json()


def test_delete_me_answers_like_unknown_user_when_already_gone(test_client, monkeypatch):
    def raise_error(service, user_id):
        raise UserNotFound

    monkeypatch.setattr(MatchService, "delete_user", raise_error)

    response = test_client.delete("/user/me", headers=build_headers(100))

    assert response.status_code == HTTPStatus.UNAUTHORIZED
    assert response.json() == test_client.delete("/user/me", headers=build_headers(9999)).json()


def test_update_me_replaces_profile(test_client):
    headers = build_headers(100)
    payload = {"first_name": "  Jane ", "last_name": "Doe", "properties": ["has_car", "can_host"]}

    response = test_client.put("/user/me", json=payload, headers=headers)

    expected = {
        **build_user_response(),
        "first_name": "Jane",
        "last_name": "Doe",
        "properties": ["has_car", "can_host"],
    }
    assert response.status_code == HTTPStatus.OK
    assert response.json() == expected
    assert test_client.get("/user/me", headers=headers).json() == expected


def test_update_me_with_empty_properties_clears_them(test_client):
    headers = build_headers(100)
    test_client.put(
        "/user/me",
        json={"first_name": "John", "last_name": "Johnson", "properties": ["has_car"]},
        headers=headers,
    )

    response = test_client.put(
        "/user/me",
        json={"first_name": "John", "last_name": "Johnson", "properties": []},
        headers=headers,
    )

    assert response.status_code == HTTPStatus.OK
    assert response.json() == build_user_response()
    assert test_client.get("/user/me", headers=headers).json() == build_user_response()


def _error_types_and_locs(response):
    return [(error["type"], error["loc"]) for error in response.json()["detail"]]


def test_volunteer_must_send_properties(test_client):
    response = test_client.put(
        "/user/me", json={"first_name": "Jane", "last_name": "Doe"}, headers=build_headers(100)
    )

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert _error_types_and_locs(response) == [("missing", ["body", "properties"])]


def test_help_seeker_updates_name(test_client):
    headers = build_headers(101)

    response = test_client.put(
        "/user/me", json={"first_name": "Adrian", "last_name": "Adams"}, headers=headers
    )

    assert response.status_code == HTTPStatus.OK
    assert response.json()["first_name"] == "Adrian"
    assert response.json()["last_name"] == "Adams"
    assert response.json()["properties"] == []
    assert test_client.get("/user/me", headers=headers).json() == response.json()


@pytest.mark.parametrize(
    "properties",
    (pytest.param([], id="empty-properties"), pytest.param(["has_car"], id="properties")),
)
def test_help_seeker_cannot_send_properties(test_client, properties):
    headers = build_headers(101)

    response = test_client.put(
        "/user/me",
        json={"first_name": "Adrian", "last_name": "Adams", "properties": properties},
        headers=headers,
    )

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert _error_types_and_locs(response) == [("extra_forbidden", ["body", "properties"])]
    assert test_client.get("/user/me", headers=headers).json()["first_name"] == "Adam"


@pytest.mark.parametrize(
    "payload,expected_error",
    (
        pytest.param(
            {"first_name": "", "last_name": "Doe", "properties": []},
            ("string_too_short", ["body", "first_name"]),
            id="empty-first-name",
        ),
        pytest.param(
            {"first_name": "Jane", "last_name": "   ", "properties": []},
            ("string_too_short", ["body", "last_name"]),
            id="blank-last-name",
        ),
        pytest.param(
            {"last_name": "Doe", "properties": []},
            ("missing", ["body", "first_name"]),
            id="missing-first-name",
        ),
        pytest.param(
            {"first_name": "Jane", "last_name": "Doe", "properties": ["can_fly"]},
            ("enum", ["body", "properties", 0]),
            id="unknown-property",
        ),
        pytest.param(
            {"first_name": "Jane", "last_name": "Doe", "properties": [], "email": "j@doe.com"},
            ("extra_forbidden", ["body", "email"]),
            id="extra-field",
        ),
        pytest.param(["Jane", "Doe"], ("model_type", ["body"]), id="not-an-object"),
        pytest.param(None, ("missing", ["body"]), id="no-body"),
    ),
)
def test_update_me_rejects_invalid_payload(test_client, payload, expected_error):
    headers = build_headers(100)

    response = test_client.put("/user/me", json=payload, headers=headers)

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert _error_types_and_locs(response) == [expected_error]
    assert test_client.get("/user/me", headers=headers).json() == build_user_response()


@pytest.mark.parametrize(
    "user_id", (pytest.param(None, id="anonymous"), pytest.param(102, id="unverified"))
)
def test_update_me_requires_verified_user(test_client, user_id):
    headers = build_headers(user_id) if user_id else {}

    response = test_client.put(
        "/user/me", json={"first_name": "Jane", "last_name": "Doe"}, headers=headers
    )

    assert response.status_code == HTTPStatus.UNAUTHORIZED


def test_deleted_user_cannot_update_profile(test_client, deleted_user):
    response = test_client.put(
        "/user/me", json={"first_name": "Jane", "last_name": "Doe"}, headers=build_headers(100)
    )

    assert response.status_code == HTTPStatus.UNAUTHORIZED


def test_update_me_answers_like_unknown_user_when_already_gone(test_client, monkeypatch):
    def raise_error(service, user_id, **kwargs):
        raise UserNotFound

    monkeypatch.setattr(MatchService, "update_profile", raise_error)
    payload = {"first_name": "Jane", "last_name": "Doe", "properties": []}

    response = test_client.put("/user/me", json=payload, headers=build_headers(100))

    assert response.status_code == HTTPStatus.UNAUTHORIZED
    assert (
        response.json()
        == test_client.put("/user/me", json=payload, headers=build_headers(9999)).json()
    )
