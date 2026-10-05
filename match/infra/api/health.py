from fastapi import APIRouter

router = APIRouter()


@router.get("/")
def root() -> str:
    return "Match - don't conquer."


@router.get("/health")
def health_check() -> str:
    return "ok"
