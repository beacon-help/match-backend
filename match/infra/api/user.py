from dataclasses import asdict
from http import HTTPStatus

from fastapi import APIRouter, Depends, Request, Response

from match.app.service import MatchService
from match.bootstrap import get_service
from match.domain.exceptions import UserVerificationError
from match.infra.api.auth import get_user_id
from match.infra.api.schemas import UserCreationRequestSchema, UserSchema

router = APIRouter()


@router.get("/me", response_model=UserSchema)
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
    service.send_verification_request(user)
    return asdict(user)


@router.put("/verify/{verification_code}")
def verify_user(
    request: Request,
    response: Response,
    verification_code: str,
    service: MatchService = Depends(get_service),
) -> dict:
    user_id = get_user_id(request)
    try:
        service.verify_user_with_code(user_id, verification_code)
        response.status_code = HTTPStatus.OK
        out = {"status": "success"}
    except UserVerificationError:
        response.status_code = HTTPStatus.BAD_REQUEST
        out = {"success": "failed"}

    return out
