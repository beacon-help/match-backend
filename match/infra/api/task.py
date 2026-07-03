from dataclasses import asdict
from http import HTTPStatus

from fastapi import APIRouter, Depends, HTTPException, Request

from match.app.service import MatchService
from match.bootstrap import get_service
from match.domain.exceptions import PermissionDenied
from match.domain.interfaces import TaskFilter
from match.domain.task import Category, Location, LocationRadius, Task, TaskStatus
from match.domain.user import User
from match.infra.api.auth import get_user_id, verified_user
from match.infra.api.schemas import (
    PublicTaskSchema,
    TaskCreationRequestSchema,
    TaskLocationSchema,
    TaskSchema,
)

router = APIRouter()


def _task_filters_from_request(request: Request) -> TaskFilter:
    query_params = request.query_params
    filters: TaskFilter = {}
    location_filter_keys = {"lat", "lon", "radius_km"}

    try:
        if "status" in query_params:
            filters["status"] = TaskStatus(query_params["status"])
        if "category" in query_params:
            filters["category"] = Category(query_params["category"])
        if "owner_id" in query_params:
            filters["owner_id"] = int(query_params["owner_id"])
        if "helper_id" in query_params:
            helper_id = query_params["helper_id"]
            filters["helper_id"] = None if helper_id == "null" else int(helper_id)
        if location_filter_keys & query_params.keys():
            if not location_filter_keys <= query_params.keys():
                raise ValueError
            location_radius = LocationRadius(
                lat=float(query_params["lat"]),
                lon=float(query_params["lon"]),
                radius_km=float(query_params["radius_km"]),
            )
            if not -90 <= location_radius.lat <= 90:
                raise ValueError
            if not -180 <= location_radius.lon <= 180:
                raise ValueError
            if location_radius.radius_km <= 0:
                raise ValueError
            filters["location_radius"] = location_radius
    except ValueError as exc:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST, detail="Invalid task filter."
        ) from exc

    return filters


def public_task_to_dict(task: Task) -> dict:
    task_dict = asdict(task)
    task_dict.pop("owner_id")
    task_dict.pop("helper_id")
    task_dict.pop("created_at")
    task_dict.pop("updated_at")
    task_dict.pop("description")
    return task_dict


@router.post("/", response_model=TaskSchema, status_code=HTTPStatus.CREATED)
def create_task(
    task_creation_params: TaskCreationRequestSchema,
    user_id: int = Depends(get_user_id),
    service: MatchService = Depends(get_service),
) -> dict:
    try:
        task = service.create_task(
            user_id,
            description=task_creation_params.description,
            title=task_creation_params.title,
            category=task_creation_params.category,
            location_lon=task_creation_params.location.lon,
            location_lat=task_creation_params.location.lat,
            location_address=task_creation_params.location.address,
        )
        return service.format_task_response(task)
    except PermissionDenied:
        raise HTTPException(status_code=HTTPStatus.FORBIDDEN)


@router.put("/{task_id}", response_model=TaskSchema)
def manage_task(
    task_id: int,
    action: str,
    helper_id: int | None = None,
    user: User = Depends(verified_user),
    service: MatchService = Depends(get_service),
) -> dict:
    try:
        match action:
            case "join":
                task = service.task_join(task_id, user.id)
            case "approve":
                if helper_id is None:
                    raise HTTPException(
                        status_code=HTTPStatus.BAD_REQUEST, detail="Helper id not provided."
                    )
                task = service.task_approve(task_id, owner_id=user.id, helper_id=helper_id)
            case "reject":
                if helper_id is None:
                    raise HTTPException(
                        status_code=HTTPStatus.BAD_REQUEST, detail="Helper id not provided."
                    )
                task = service.task_reject(task_id, owner_id=user.id, helper_id=helper_id)
            case "close":
                task = service.task_close(task_id, owner_id=user.id)
            case "report_success":
                task = service.task_report_success(task_id, owner_id=user.id)
            case "report_failure":
                task = service.task_report_failed(task_id, owner_id=user.id)

            case _:
                raise HTTPException(status_code=HTTPStatus.BAD_REQUEST)
    except PermissionDenied as e:
        raise HTTPException(
            status_code=HTTPStatus.FORBIDDEN,
            detail=f"Permission denied for user {user}.{str(e)}",
        )

    return service.format_task_response(task)


@router.get("/", response_model=list[TaskSchema])
def list_tasks(
    request: Request,
    service: MatchService = Depends(get_service),
    _: User = Depends(verified_user),
) -> list:
    return service.get_tasks_response(filters=_task_filters_from_request(request))


@router.get("/locations", response_model=list[TaskLocationSchema])
def list_task_locations(
    request: Request,
    service: MatchService = Depends(get_service),
) -> list:
    return service.get_task_locations(filters=_task_filters_from_request(request))


@router.get("/public", response_model=list[PublicTaskSchema])
def list_tasks_public() -> list:
    test_location = Location(lat=40.7128, lon=-74.0060, address="New York, NY")
    tasks = [
        Task(
            id=1,
            title="Help with groceries",
            description="Need help carrying groceries upstairs.",
            status=TaskStatus.OPEN,
            owner_id=1,
            helper_id=None,
            category=Category.FOOD,
            location=test_location,
        ),
        Task(
            id=2,
            title="Dog walking",
            description="Looking for someone to walk my dog in the evenings.",
            status=TaskStatus.PENDING,
            owner_id=2,
            helper_id=3,
            category=Category.OTHER,
            location=test_location,
        ),
    ]
    return [public_task_to_dict(task) for task in tasks]


@router.get("/my-tasks", response_model=list[TaskSchema])
def get_my_tasks(
    user_id: int = Depends(get_user_id), service: MatchService = Depends(get_service)
) -> list[dict]:
    return service.get_tasks_response(filters={"owner_id": user_id})


@router.get("/{task_id}", response_model=TaskSchema)
def get_task(task_id: int, service: MatchService = Depends(get_service)) -> dict:
    return service.get_task_response(task_id)
