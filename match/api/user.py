from http import HTTPStatus

from fastapi import APIRouter, HTTPException

from match.api.schemas import UserCreationRequestSchema, UserSchema

router = APIRouter()


@router.get("/me", response_model=UserSchema)
def get_me() -> dict:
    return {
        "id": 1,
        "first_name": "Arnold",
        "last_name": "Adams",
        "email": "email@example.com",
    }


@router.get("/{user_id}", response_model=UserSchema)
def get_user(user_id: int) -> dict:
    return {
        "id": user_id,
        "first_name": "Arnold",
        "last_name": "Adams",
        "email": "email@example.com",
    }


@router.post("/signup", response_model=UserSchema, status_code=HTTPStatus.CREATED)
def create_user(user_creation_params: UserCreationRequestSchema) -> dict:
    user_data = user_creation_params.model_dump()
    user_data["id"] = 1
    return user_data
