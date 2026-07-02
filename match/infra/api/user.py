from dataclasses import asdict
from http import HTTPStatus

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.security import OAuth2PasswordRequestForm

from match.app.service import MatchService
from match.bootstrap import get_service
from match.domain.exceptions import AuthenticationFailed, UserVerificationError
from match.infra.api.auth import get_user_id
from match.infra.api.schemas import (
    HelpseekerCreationRequestSchema,
    RefreshRequestSchema,
    TokenSchema,
    UserSchema,
    VolunteerCreationRequestSchema,
)
from match.infra.api.security import (
    REFRESH_TOKEN_TYPE,
    TokenError,
    create_access_token,
    create_refresh_token,
    decode_token,
)

router = APIRouter()


@router.post("/login", response_model=TokenSchema)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    service: MatchService = Depends(get_service),
) -> TokenSchema:
    try:
        user = service.authenticate(form_data.username, form_data.password)
    except AuthenticationFailed:
        raise HTTPException(
            status_code=HTTPStatus.UNAUTHORIZED, detail="Incorrect username or password"
        )
    return TokenSchema(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
    )


@router.post("/refresh", response_model=TokenSchema)
def refresh(params: RefreshRequestSchema) -> TokenSchema:
    try:
        user_id = decode_token(params.refresh_token, REFRESH_TOKEN_TYPE)
    except TokenError:
        raise HTTPException(status_code=HTTPStatus.UNAUTHORIZED)
    return TokenSchema(
        access_token=create_access_token(user_id),
        refresh_token=create_refresh_token(user_id),
    )


@router.get("/me", response_model=UserSchema)
def get_me(
    user_id: int = Depends(get_user_id), service: MatchService = Depends(get_service)
) -> dict:
    user = service.get_user_by_id(user_id)
    if not user.is_verified:
        raise HTTPException(status_code=HTTPStatus.UNAUTHORIZED)
    return asdict(user)


@router.get("/{user_id}", response_model=UserSchema)
def get_user(user_id: int, service: MatchService = Depends(get_service)) -> dict:
    return asdict(service.get_user_by_id(user_id))


@router.post("/signup/helpseeker", response_model=UserSchema, status_code=HTTPStatus.CREATED)
def create_helpseeker_user(
    user_creation_params: HelpseekerCreationRequestSchema,
    service: MatchService = Depends(get_service),
) -> dict:
    user = service.create_user(**user_creation_params.model_dump())
    service.send_verification_request(user)
    return asdict(user)


@router.post("/signup/volunteer", response_model=UserSchema, status_code=HTTPStatus.CREATED)
def create_volunteer_user(
    user_creation_params: VolunteerCreationRequestSchema,
    service: MatchService = Depends(get_service),
) -> dict:
    user = service.create_user(**user_creation_params.model_dump())
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
