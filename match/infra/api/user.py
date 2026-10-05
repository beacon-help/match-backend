from dataclasses import asdict
from http import HTTPStatus

from fastapi import APIRouter, Depends, HTTPException, Response

from match.app.service import MatchService
from match.bootstrap import get_service
from match.domain.exceptions import EmailAlreadyRegistered, UserNotFound, UserVerificationError
from match.domain.user import User, UserType
from match.infra.api.auth import authenticated_user, verified_user
from match.infra.api.schemas import (
    HelpseekerCreationRequestSchema,
    UserCreationBaseSchema,
    UserSchema,
    VolunteerCreationRequestSchema,
)

router = APIRouter()


@router.get("/me", response_model=UserSchema)
def get_me(user: User = Depends(verified_user)) -> dict:
    return asdict(user)


@router.delete("/me", status_code=HTTPStatus.NO_CONTENT)
def delete_me(
    user: User = Depends(authenticated_user), service: MatchService = Depends(get_service)
) -> None:
    try:
        service.delete_user(user.id)
    except UserNotFound:
        raise HTTPException(status_code=HTTPStatus.UNAUTHORIZED)


@router.get("/{user_id}", response_model=UserSchema)
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
