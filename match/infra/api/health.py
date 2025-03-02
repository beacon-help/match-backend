from fastapi import APIRouter

router = APIRouter()


@router.get("/")
def root() -> str:
    return "Match - don't conquer."


@router.get("/health")
def health_check() -> str:
    return "ok"


@router.get("/break")
def trigger_error() -> None:
    division_by_zero = 1 / 0
