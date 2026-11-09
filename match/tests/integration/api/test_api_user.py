import dataclasses
import json
import time
from http import HTTPStatus
from uuid import uuid4

import pytest
from sqlalchemy import text

from match import bootstrap
from match.app.service import MatchService
from match.db import Session
from match.domain.exceptions import UserNotFound
from match.infra.api.schemas import VolunteerUpdateRequestSchema
from match.infra.api.user import profile_update_params
from match.infra.password_hasher import PwdlibPasswordHasher
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
@pytest.mark.parametrize(
    "password,expected_status",
    (
        pytest.param("7-chars", HTTPStatus.UNPROCESSABLE_ENTITY, id="seven-characters"),
        pytest.param("8-chars!", HTTPStatus.CREATED, id="eight-characters"),
        pytest.param("p" * 128, HTTPStatus.CREATED, id="128-characters"),
        pytest.param("p" * 129, HTTPStatus.UNPROCESSABLE_ENTITY, id="129-characters"),
    ),
)
def test_create_user_password_length(test_client, endpoint, password, expected_status):
    payload = {
        "first_name": "Nina",
        "last_name": "New",
        "email": "nina@example.com",
        "password": password,
    }
    if endpoint.endswith("volunteer"):
        payload["properties"] = []

    response = test_client.post(endpoint, json=payload)

    assert response.status_code == expected_status


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
    payload = {"first_name": "Jane", "last_name": "Doe", "properties": ["has_car", "can_host"]}

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


def test_help_seeker_properties_rejected_by_domain_answer_like_schema(test_client):
    headers = build_headers(101)
    payload = {"first_name": "Adrian", "last_name": "Adams", "properties": ["has_car"]}
    schema_response = test_client.put("/user/me", json=payload, headers=headers)
    test_client.app.dependency_overrides[profile_update_params] = (
        lambda: VolunteerUpdateRequestSchema.model_validate(payload)
    )

    try:
        response = test_client.put("/user/me", json=payload, headers=headers)
    finally:
        del test_client.app.dependency_overrides[profile_update_params]

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert response.json() == schema_response.json()
    assert _error_types_and_locs(response) == [("extra_forbidden", ["body", "properties"])]
    assert test_client.get("/user/me", headers=headers).json()["first_name"] == "Adam"


@pytest.mark.parametrize(
    "payload,expected_error",
    (
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


JSON_CONTENT_TYPE = {"Content-Type": "application/json"}
INVALID_BODIES = (
    pytest.param({"content": b'{"first_name": '}, id="malformed-json"),
    pytest.param({"content": b'{"first_name": "\xff"}'}, id="invalid-utf8"),
    pytest.param({}, id="no-body"),
    pytest.param({"content": b'["Jane", "Doe"]'}, id="not-an-object"),
    pytest.param({"content": b"{}"}, id="missing-fields"),
)
UNAUTHORIZED_USERS = (pytest.param(None, id="anonymous"), pytest.param(102, id="unverified"))


@pytest.mark.parametrize("user_id", UNAUTHORIZED_USERS)
@pytest.mark.parametrize(
    "body",
    (
        pytest.param({"json": {"first_name": "Jane", "last_name": "Doe"}}, id="valid"),
        *INVALID_BODIES,
    ),
)
def test_update_me_requires_verified_user(test_client, user_id, body):
    headers = {**JSON_CONTENT_TYPE, **(build_headers(user_id) if user_id else {})}

    response = test_client.put("/user/me", headers=headers, **body)

    assert response.status_code == HTTPStatus.UNAUTHORIZED


@pytest.mark.parametrize("path", ("/user/me", "/user/me/password"))
def test_malformed_json_from_verified_user_is_rejected(test_client, path):
    response = test_client.put(
        path, content=b'{"first_name": ', headers={**JSON_CONTENT_TYPE, **build_headers(100)}
    )

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert response.json() == {
        "detail": [
            {
                "type": "json_invalid",
                "loc": ["body", 15],
                "msg": "JSON decode error",
                "input": {},
                "ctx": {"error": "Expecting value"},
            }
        ]
    }


@pytest.mark.parametrize("path", ("/user/me", "/user/me/password"))
def test_undecodable_body_from_verified_user_is_rejected(test_client, path):
    response = test_client.put(
        path,
        content=b'{"first_name": "\xff"}',
        headers={**JSON_CONTENT_TYPE, **build_headers(100)},
    )

    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert response.json() == {"detail": "There was an error parsing the body"}


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


NEW_PASSWORD = "n3w-pass"


def _login(test_client, password):
    return test_client.post(
        "/user/login", data={"username": "john@johnson.com", "password": password}
    )


def test_change_password(test_client):
    payload = {"current_password": SEED_PASSWORD, "new_password": NEW_PASSWORD}

    response = test_client.put("/user/me/password", json=payload, headers=build_headers(100))

    assert response.status_code == HTTPStatus.NO_CONTENT
    assert response.content == b""
    assert _login(test_client, NEW_PASSWORD).status_code == HTTPStatus.OK
    assert _login(test_client, SEED_PASSWORD).status_code == HTTPStatus.UNAUTHORIZED


def test_change_password_accepts_128_character_password(test_client):
    payload = {"current_password": SEED_PASSWORD, "new_password": "p" * 128}

    response = test_client.put("/user/me/password", json=payload, headers=build_headers(100))

    assert response.status_code == HTTPStatus.NO_CONTENT
    assert _login(test_client, "p" * 128).status_code == HTTPStatus.OK


def test_password_set_before_length_limit_still_logs_in_and_changes(test_client):
    long_password = "p" * 200
    with Session() as session:
        session.execute(
            text("UPDATE users SET password_hash = :pw WHERE id = 100"),
            {"pw": PwdlibPasswordHasher().hash(long_password)},
        )
        session.commit()
    payload = {"current_password": long_password, "new_password": NEW_PASSWORD}

    assert _login(test_client, long_password).status_code == HTTPStatus.OK
    response = test_client.put("/user/me/password", json=payload, headers=build_headers(100))

    assert response.status_code == HTTPStatus.NO_CONTENT
    assert _login(test_client, NEW_PASSWORD).status_code == HTTPStatus.OK


def test_change_password_rejects_wrong_current_password(test_client):
    payload = {"current_password": "wrong-password", "new_password": NEW_PASSWORD}

    response = test_client.put("/user/me/password", json=payload, headers=build_headers(100))

    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert response.json() == {"detail": "Current password is incorrect."}
    assert _login(test_client, SEED_PASSWORD).status_code == HTTPStatus.OK
    assert _login(test_client, NEW_PASSWORD).status_code == HTTPStatus.UNAUTHORIZED


@pytest.mark.parametrize(
    "payload",
    (
        pytest.param(
            {"current_password": SEED_PASSWORD, "new_password": NEW_PASSWORD[:-1]},
            id="new-password-too-short",
        ),
        pytest.param(
            {"current_password": SEED_PASSWORD, "new_password": "p" * 129},
            id="new-password-too-long",
        ),
        pytest.param(
            {"current_password": SEED_PASSWORD, "new_password": SEED_PASSWORD},
            id="new-password-unchanged",
        ),
        pytest.param({"new_password": NEW_PASSWORD}, id="missing-current-password"),
        pytest.param({"current_password": SEED_PASSWORD}, id="missing-new-password"),
        pytest.param(
            {
                "current_password": SEED_PASSWORD,
                "new_password": NEW_PASSWORD,
                "email": "john@johnson.com",
            },
            id="extra-field",
        ),
    ),
)
def test_change_password_rejects_invalid_payload(test_client, payload):
    response = test_client.put("/user/me/password", json=payload, headers=build_headers(100))

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert _login(test_client, SEED_PASSWORD).status_code == HTTPStatus.OK


@pytest.mark.parametrize("user_id", UNAUTHORIZED_USERS)
@pytest.mark.parametrize(
    "body",
    (
        pytest.param(
            {"json": {"current_password": SEED_PASSWORD, "new_password": NEW_PASSWORD}},
            id="valid",
        ),
        *INVALID_BODIES,
    ),
)
def test_change_password_requires_verified_user(test_client, user_id, body):
    headers = {**JSON_CONTENT_TYPE, **(build_headers(user_id) if user_id else {})}

    response = test_client.put("/user/me/password", headers=headers, **body)

    assert response.status_code == HTTPStatus.UNAUTHORIZED
    assert _login(test_client, SEED_PASSWORD).status_code == HTTPStatus.OK


def test_deleted_user_cannot_change_password(test_client, deleted_user):
    payload = {"current_password": SEED_PASSWORD, "new_password": NEW_PASSWORD}

    response = test_client.put("/user/me/password", json=payload, headers=build_headers(100))

    assert response.status_code == HTTPStatus.UNAUTHORIZED


def test_change_password_answers_like_unknown_user_when_already_gone(test_client, monkeypatch):
    def raise_error(service, user_id, **kwargs):
        raise UserNotFound

    monkeypatch.setattr(MatchService, "change_password", raise_error)
    payload = {"current_password": SEED_PASSWORD, "new_password": NEW_PASSWORD}

    response = test_client.put("/user/me/password", json=payload, headers=build_headers(100))

    assert response.status_code == HTTPStatus.UNAUTHORIZED
    assert (
        response.json()
        == test_client.put("/user/me/password", json=payload, headers=build_headers(9999)).json()
    )


def _bearer(token):
    return {"Authorization": f"Bearer {token}"}


def _change_password_after_login(test_client):
    tokens = _login(test_client, SEED_PASSWORD).json()
    response = test_client.put(
        "/user/me/password",
        json={"current_password": SEED_PASSWORD, "new_password": NEW_PASSWORD},
        headers=_bearer(tokens["access_token"]),
    )
    assert response.status_code == HTTPStatus.NO_CONTENT
    return tokens


@pytest.mark.parametrize("path", ("/user/me", "/task/my-tasks"))
def test_password_change_revokes_access_tokens(test_client, path):
    tokens = _change_password_after_login(test_client)

    response = test_client.get(path, headers=_bearer(tokens["access_token"]))

    assert response.status_code == HTTPStatus.UNAUTHORIZED
    assert response.json() == test_client.get(path, headers=_bearer("not-a-token")).json()


def test_password_change_revokes_refresh_tokens(test_client):
    tokens = _change_password_after_login(test_client)

    response = test_client.post("/user/refresh", json={"refresh_token": tokens["refresh_token"]})

    assert response.status_code == HTTPStatus.UNAUTHORIZED
    assert (
        response.json()
        == test_client.post("/user/refresh", json={"refresh_token": "not-a-token"}).json()
    )


def test_login_after_password_change_starts_a_valid_session(test_client):
    _change_password_after_login(test_client)
    # Tokens carry whole-second issue times, and those from the second of the change are revoked.
    time.sleep(1 - time.time() % 1)

    tokens = _login(test_client, NEW_PASSWORD).json()

    assert test_client.get("/user/me", headers=_bearer(tokens["access_token"])).status_code == (
        HTTPStatus.OK
    )
    refresh_response = test_client.post(
        "/user/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert refresh_response.status_code == HTTPStatus.OK


def test_password_change_keeps_sessions_when_revocation_is_off(test_client, monkeypatch):
    monkeypatch.setattr(
        bootstrap,
        "config",
        dataclasses.replace(bootstrap.config, REVOKE_SESSIONS_ON_PASSWORD_CHANGE=False),
    )
    tokens = _change_password_after_login(test_client)

    me_response = test_client.get("/user/me", headers=_bearer(tokens["access_token"]))
    refresh_response = test_client.post(
        "/user/refresh", json={"refresh_token": tokens["refresh_token"]}
    )

    assert me_response.status_code == HTTPStatus.OK
    assert refresh_response.status_code == HTTPStatus.OK
