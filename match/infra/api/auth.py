from http import HTTPStatus

from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer

from match.app.service import MatchService
from match.bootstrap import get_service
from match.domain.exceptions import UserNotFound
from match.domain.user import User
from match.infra.api.security import ACCESS_TOKEN_TYPE, TokenError, decode_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="user/login")


def get_user_id(token: str = Depends(oauth2_scheme)) -> int:
    try:
        return decode_token(token, ACCESS_TOKEN_TYPE)
    except TokenError:
        raise HTTPException(status_code=HTTPStatus.UNAUTHORIZED)


def authenticated_user(
    user_id: int = Depends(get_user_id),
    service: MatchService = Depends(get_service),
) -> User:
    try:
        return service.get_user_by_id(user_id)
    except UserNotFound:
        raise HTTPException(status_code=HTTPStatus.UNAUTHORIZED)


def verified_user(user: User = Depends(authenticated_user)) -> User:
    if not user.is_verified:
        raise HTTPException(status_code=HTTPStatus.UNAUTHORIZED)
    return user
