from dataclasses import asdict
from http import HTTPStatus

from fastapi import APIRouter, Depends, Request

from match.app.service import MatchService
from match.bootstrap import get_service
from match.infra.api.auth import get_user_id
from match.infra.api.schemas import UserCreationRequestSchema, UserSchema
from match.infra.repositories import InMemoryMatchRepository

router = APIRouter()


@router.get("/me")  # response_model=UserSchema)
def get_me(request: Request, service: MatchService = Depends(get_service)) -> dict:
    user_id = get_user_id(request)
    user = service.get_user_by_id(user_id)
    return asdict(user)


@router.get("/{user_id}", response_model=UserSchema)
def get_user(user_id: int, service: MatchService = Depends(get_service)) -> dict:
    return asdict(service.get_user_by_id(user_id))


@router.post("/signup", response_model=UserSchema, status_code=HTTPStatus.CREATED)
def create_user(
    user_creation_params: UserCreationRequestSchema, service: MatchService = Depends(get_service)
) -> dict:
    user_data = user_creation_params.model_dump()
    user = service.create_user(**user_creation_params.dict())
    return asdict(user)
