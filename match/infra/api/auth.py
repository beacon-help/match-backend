from http import HTTPStatus

from fastapi import Depends, HTTPException, Request

from match.app.service import MatchService
from match.bootstrap import get_service
from match.domain.exceptions import UserNotFound
from match.domain.user import User


def get_user_id(request: Request) -> int:
    user_id = request.headers.get("X-User")
    if not user_id:
        raise HTTPException(status_code=HTTPStatus.UNAUTHORIZED)
    try:
        return int(user_id)
    except ValueError:
        raise HTTPException(status_code=HTTPStatus.UNAUTHORIZED)


def authenticated_user(
    request: Request,
    service: MatchService = Depends(get_service),
) -> User:
    user_id = get_user_id(request)
    try:
        return service.get_user_by_id(user_id)
    except UserNotFound:
        raise HTTPException(status_code=HTTPStatus.UNAUTHORIZED)


def verified_user(user: User = Depends(authenticated_user)) -> User:
    if not user.is_verified:
        raise HTTPException(status_code=HTTPStatus.UNAUTHORIZED)
    return user
