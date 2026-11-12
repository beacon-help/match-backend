from dataclasses import asdict
from http import HTTPStatus
from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException, Response
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError

from match.app.exceptions import CurrentPasswordIncorrect
from match.app.service import MatchService
from match.bootstrap import get_service
from match.domain.exceptions import (
    EmailAlreadyRegistered,
    HelpSeekerCannotHaveProperties,
    UserNotFound,
    UserVerificationError,
)
from match.domain.user import User, UserType
from match.infra.api.auth import authenticated_user, verified_user
from match.infra.api.routing import AuthBeforeBodyRoute
from match.infra.api.schemas import (
    HelpseekerCreationRequestSchema,
    HelpseekerUpdateRequestSchema,
    PasswordChangeRequestSchema,
    ProfileUpdateBody,
    PublicUserSchema,
    UserCreationBaseSchema,
    UserSchema,
    VolunteerCreationRequestSchema,
    VolunteerUpdateRequestSchema,
)

router = APIRouter(route_class=AuthBeforeBodyRoute)


@router.get("/me", response_model=UserSchema)
def get_me(user: User = Depends(verified_user)) -> dict:
    return asdict(user)


def profile_update_params(
    body: Annotated[ProfileUpdateBody, Body()],
    user: User = Depends(verified_user),
) -> HelpseekerUpdateRequestSchema | VolunteerUpdateRequestSchema:
    schema = (
        VolunteerUpdateRequestSchema
        if user.user_type == UserType.VOLUNTEER
        else HelpseekerUpdateRequestSchema
    )
    try:
        return schema.model_validate(body)
    except ValidationError as e:
        raise RequestValidationError(
            [{**error, "loc": ("body", *error["loc"])} for error in e.errors(include_url=False)],
            body=body,
        )


@router.put("/me", response_model=UserSchema)
def update_me(
    params: HelpseekerUpdateRequestSchema = Depends(profile_update_params),
    user: User = Depends(verified_user),
    service: MatchService = Depends(get_service),
) -> dict:
    properties = params.properties if isinstance(params, VolunteerUpdateRequestSchema) else []
    try:
        updated_user = service.update_profile(
            user.id,
            first_name=params.first_name,
            last_name=params.last_name,
            properties=properties,
        )
    except UserNotFound:
        raise HTTPException(status_code=HTTPStatus.UNAUTHORIZED)
    except HelpSeekerCannotHaveProperties:
        raise RequestValidationError(
            [
                {
                    "type": "extra_forbidden",
                    "loc": ("body", "properties"),
                    "msg": "Extra inputs are not permitted",
                    "input": properties,
                }
            ]
        )
    return asdict(updated_user)


@router.put("/me/password", status_code=HTTPStatus.NO_CONTENT)
def change_my_password(
    params: PasswordChangeRequestSchema,
    user: User = Depends(verified_user),
    service: MatchService = Depends(get_service),
) -> None:
    try:
        service.change_password(
            user.id,
            current_password=params.current_password,
            new_password=params.new_password,
        )
    except UserNotFound:
        raise HTTPException(status_code=HTTPStatus.UNAUTHORIZED)
    except CurrentPasswordIncorrect:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST, detail="Current password is incorrect."
        )


@router.delete("/me", status_code=HTTPStatus.NO_CONTENT)
def delete_me(
    user: User = Depends(authenticated_user), service: MatchService = Depends(get_service)
) -> None:
    try:
        service.delete_user(user.id)
    except UserNotFound:
        raise HTTPException(status_code=HTTPStatus.UNAUTHORIZED)


@router.get("/{user_id}", response_model=PublicUserSchema)
def get_user(
    user_id: int, _: User = Depends(verified_user), service: MatchService = Depends(get_service)
) -> dict:
    try:
        return asdict(service.get_user_by_id(user_id))
    except UserNotFound:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND)


def _sign_up(service: MatchService, user_type: UserType, params: UserCreationBaseSchema) -> dict:
    try:
        user = service.create_user(**params.model_dump(), user_type=user_type)
    except EmailAlreadyRegistered:
        raise HTTPException(status_code=HTTPStatus.CONFLICT, detail="Email already registered.")
    service.send_verification_request(user)
    return asdict(user)


@router.post("/signup/helpseeker", response_model=UserSchema, status_code=HTTPStatus.CREATED)
def create_helpseeker_user(
    user_creation_params: HelpseekerCreationRequestSchema,
    service: MatchService = Depends(get_service),
) -> dict:
    return _sign_up(service, UserType.HELP_SEEKER, user_creation_params)


@router.post("/signup/volunteer", response_model=UserSchema, status_code=HTTPStatus.CREATED)
def create_volunteer_user(
    user_creation_params: VolunteerCreationRequestSchema,
    service: MatchService = Depends(get_service),
) -> dict:
    return _sign_up(service, UserType.VOLUNTEER, user_creation_params)


@router.put("/verify/{verification_code}")
def verify_user(
    response: Response,
    verification_code: str,
    service: MatchService = Depends(get_service),
) -> dict:
    try:
        service.verify_user_with_code(verification_code)
        response.status_code = HTTPStatus.OK
        out = {"status": "success"}
    except UserVerificationError:
        response.status_code = HTTPStatus.BAD_REQUEST
        out = {"success": "failed"}

    return out
