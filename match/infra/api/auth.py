from http import HTTPStatus

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

from match.app.exceptions import AuthenticationFailed, SessionRevoked
from match.app.service import MatchService
from match.bootstrap import get_service
from match.domain.exceptions import UserNotFound
from match.domain.user import User
from match.infra.api.schemas import RefreshRequestSchema, TokenSchema
from match.infra.api.security import (
    ACCESS_TOKEN_TYPE,
    REFRESH_TOKEN_TYPE,
    TokenClaims,
    TokenError,
    create_access_token,
    create_refresh_token,
    decode_token,
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="user/login")


def get_access_token_claims(token: str = Depends(oauth2_scheme)) -> TokenClaims:
    try:
        return decode_token(token, ACCESS_TOKEN_TYPE)
    except TokenError:
        raise HTTPException(status_code=HTTPStatus.UNAUTHORIZED)


def authenticated_user(
    claims: TokenClaims = Depends(get_access_token_claims),
    service: MatchService = Depends(get_service),
) -> User:
    try:
        return service.get_session_user(claims.user_id, claims.issued_at)
    except (UserNotFound, SessionRevoked):
        raise HTTPException(status_code=HTTPStatus.UNAUTHORIZED)


def verified_user(user: User = Depends(authenticated_user)) -> User:
    if not user.is_verified:
        raise HTTPException(status_code=HTTPStatus.UNAUTHORIZED)
    return user


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
def refresh(
    params: RefreshRequestSchema, service: MatchService = Depends(get_service)
) -> TokenSchema:
    try:
        claims = decode_token(params.refresh_token, REFRESH_TOKEN_TYPE)
        user = service.get_session_user(claims.user_id, claims.issued_at)
    except (TokenError, UserNotFound, SessionRevoked):
        raise HTTPException(status_code=HTTPStatus.UNAUTHORIZED)
    return TokenSchema(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
    )
