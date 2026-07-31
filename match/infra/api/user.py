from dataclasses import asdict
from http import HTTPStatus

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.security import OAuth2PasswordRequestForm

from match.app.service import MatchService
from match.bootstrap import get_service
from match.domain.exceptions import UserVerificationError
from match.domain.user import User, UserType
from match.infra.api.auth import verified_user
from match.infra.api.schemas import (
    HelpseekerCreationRequestSchema,
    UserSchema,
    VolunteerCreationRequestSchema,
)


router = APIRouter()


@router.get("/me", response_model=UserSchema)
def get_me(user: User = Depends(verified_user)) -> dict:
    return asdict(user)


@router.get("/{user_id}", response_model=UserSchema)
def get_user(
    user_id: int, _: User = Depends(verified_user), service: MatchService = Depends(get_service)
) -> dict:
    return asdict(service.get_user_by_id(user_id))


@router.post("/signup/helpseeker", response_model=UserSchema, status_code=HTTPStatus.CREATED)
def create_helpseeker_user(
    user_creation_params: HelpseekerCreationRequestSchema,
    service: MatchService = Depends(get_service),
) -> dict:
    user = service.create_user(**user_creation_params.model_dump(), user_type=UserType.HELP_SEEKER)
    service.send_verification_request(user)
    return asdict(user)


@router.post("/signup/volunteer", response_model=UserSchema, status_code=HTTPStatus.CREATED)
def create_volunteer_user(
    user_creation_params: VolunteerCreationRequestSchema,
    service: MatchService = Depends(get_service),
) -> dict:
    user = service.create_user(**user_creation_params.model_dump(), user_type=UserType.VOLUNTEER)
    service.send_verification_request(user)
    return asdict(user)


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
