from fastapi import APIRouter, Depends

from match.app.service import MatchService
from match.bootstrap import get_service
from match.infra.api.schemas import Stats as StatsSchema

router = APIRouter()


@router.get("/", response_model=StatsSchema)
def get_stats(service: MatchService = Depends(get_service)) -> dict:
    task_stats, user_stats = service.get_stats()
    return {"tasks": task_stats, "users": user_stats}
