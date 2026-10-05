from http import HTTPStatus

from fastapi import APIRouter, Depends, File, HTTPException, Request, Response, UploadFile

from match.app.exceptions import ImageNotFound
from match.app.service import MatchService
from match.bootstrap import get_service
from match.config import get_config
from match.domain.exceptions import (
    DomainException,
    InvalidLocation,
    InvalidTaskAction,
    TaskNotFound,
)
from match.domain.interfaces import TaskFilter
from match.domain.task import Category, Location, LocationRadius, Task, TaskStatus
from match.domain.user import User
from match.infra.api.auth import get_user_id, verified_user
from match.infra.api.presenters import TaskPresenter
from match.infra.api.schemas import Location as LocationSchema
from match.infra.api.schemas import (
    PublicTaskSchema,
    TaskAction,
    TaskCreationRequestSchema,
    TaskEditRequestSchema,
    TaskLocationSchema,
    TaskSchema,
)

router = APIRouter()


def get_task_presenter() -> TaskPresenter:
    return TaskPresenter(get_config().BACKEND_HOST)


def _to_location(location: LocationSchema | None) -> Location | None:
    if location is None:
        return None
    return Location(lat=location.lat, lon=location.lon, address=location.address)


def _task_response(task: Task, service: MatchService, presenter: TaskPresenter) -> dict:
    return presenter.task(task, service.get_users_referenced_by([task]))


def _tasks_response(tasks: list[Task], service: MatchService, presenter: TaskPresenter) -> list:
    return presenter.tasks(tasks, service.get_users_referenced_by(tasks))


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
            filters["location_radius"] = LocationRadius(
                lat=float(query_params["lat"]),
                lon=float(query_params["lon"]),
                radius_km=float(query_params["radius_km"]),
            )
    except (ValueError, InvalidLocation) as exc:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST, detail="Invalid task filter."
        ) from exc

    return filters


@router.post("/", response_model=TaskSchema, status_code=HTTPStatus.CREATED)
def create_task(
    task_creation_params: TaskCreationRequestSchema,
    user: User = Depends(verified_user),
    service: MatchService = Depends(get_service),
    presenter: TaskPresenter = Depends(get_task_presenter),
) -> dict:
    try:
        task = service.create_task(
            user.id,
            title=task_creation_params.title,
            description=task_creation_params.description,
            category=task_creation_params.category,
            location=_to_location(task_creation_params.location),
        )
        return _task_response(task, service, presenter)
    except InvalidLocation as e:
        raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail=str(e))


@router.get("/images/{image_id}")
def get_task_image(image_id: str, service: MatchService = Depends(get_service)) -> Response:
    try:
        content = service.get_task_image(image_id)
    except (ImageNotFound, FileNotFoundError):
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND)
    return Response(content=content, media_type="application/octet-stream")


@router.post("/{task_id}/images", response_model=TaskSchema, status_code=HTTPStatus.CREATED)
def add_task_images(
    task_id: int,
    images: list[UploadFile] = File(...),
    user: User = Depends(verified_user),
    service: MatchService = Depends(get_service),
    presenter: TaskPresenter = Depends(get_task_presenter),
) -> dict:
    try:
        task = service.task_add_images(
            task_id, owner_id=user.id, images=[image.file.read() for image in images]
        )
    except TaskNotFound:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND)
    except InvalidTaskAction as e:
        raise HTTPException(status_code=HTTPStatus.FORBIDDEN, detail=str(e))
    return _task_response(task, service, presenter)


@router.delete("/{task_id}/images/{image_id}", response_model=TaskSchema)
def remove_task_image(
    task_id: int,
    image_id: str,
    user: User = Depends(verified_user),
    service: MatchService = Depends(get_service),
    presenter: TaskPresenter = Depends(get_task_presenter),
) -> dict:
    try:
        task = service.task_remove_image(task_id, owner_id=user.id, image_id=image_id)
    except TaskNotFound:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND)
    except InvalidTaskAction as e:
        raise HTTPException(status_code=HTTPStatus.FORBIDDEN, detail=str(e))
    except DomainException:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND)
    return _task_response(task, service, presenter)


@router.put("/{task_id}/edit", response_model=TaskSchema)
def edit_task(
    task_id: int,
    task_edit_params: TaskEditRequestSchema,
    user: User = Depends(verified_user),
    service: MatchService = Depends(get_service),
    presenter: TaskPresenter = Depends(get_task_presenter),
) -> dict:
    try:
        task = service.task_edit(
            task_id,
            owner_id=user.id,
            title=task_edit_params.title,
            description=task_edit_params.description,
            category=task_edit_params.category,
            location=_to_location(task_edit_params.location),
        )
    except TaskNotFound:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND)
    except InvalidTaskAction as e:
        raise HTTPException(status_code=HTTPStatus.FORBIDDEN, detail=str(e))
    except InvalidLocation as e:
        raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail=str(e))

    return _task_response(task, service, presenter)


@router.put("/{task_id}/manage", response_model=TaskSchema)
def manage_task(
    task_id: int,
    action: TaskAction,
    message: str | None = None,
    helper_id: int | None = None,
    user: User = Depends(verified_user),
    service: MatchService = Depends(get_service),
    presenter: TaskPresenter = Depends(get_task_presenter),
) -> dict:
    try:
        match action:
            case TaskAction.JOIN:
                if message is None:
                    raise HTTPException(
                        status_code=HTTPStatus.BAD_REQUEST,
                        detail="Message is required to join a task.",
                    )
                task = service.task_join(task_id, user.id, message)
            case TaskAction.APPROVE:
                if helper_id is None:
                    raise HTTPException(
                        status_code=HTTPStatus.BAD_REQUEST, detail="Helper id not provided."
                    )
                task = service.task_approve(task_id, owner_id=user.id, helper_id=helper_id)
            case TaskAction.REJECT:
                if helper_id is None:
                    raise HTTPException(
                        status_code=HTTPStatus.BAD_REQUEST, detail="Helper id not provided."
                    )
                task = service.task_reject(task_id, owner_id=user.id, helper_id=helper_id)
            case TaskAction.WITHDRAW:
                task = service.task_withdraw(task_id, helper_id=user.id)
            case TaskAction.CLOSE:
                task = service.task_close(task_id, owner_id=user.id)
            case TaskAction.REPORT_SUCCESS:
                task = service.task_report_success(task_id, owner_id=user.id)
            case TaskAction.REPORT_FAILURE:
                task = service.task_report_failed(task_id, owner_id=user.id)
    except TaskNotFound:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND)
    except InvalidTaskAction as e:
        raise HTTPException(status_code=HTTPStatus.FORBIDDEN, detail=str(e))

    return _task_response(task, service, presenter)


@router.get("/", response_model=list[TaskSchema])
def list_tasks(
    request: Request,
    service: MatchService = Depends(get_service),
    presenter: TaskPresenter = Depends(get_task_presenter),
    _: User = Depends(verified_user),
) -> list:
    return _tasks_response(
        service.get_tasks(_task_filters_from_request(request)), service, presenter
    )


@router.get("/locations", response_model=list[TaskLocationSchema])
def list_task_locations(
    request: Request,
    service: MatchService = Depends(get_service),
) -> list:
    return TaskPresenter.locations(service.get_tasks(_task_filters_from_request(request)))


@router.get("/public", response_model=list[PublicTaskSchema])
def list_tasks_public(
    request: Request,
    service: MatchService = Depends(get_service),
    presenter: TaskPresenter = Depends(get_task_presenter),
) -> list:
    return _tasks_response(
        service.get_tasks(_task_filters_from_request(request)), service, presenter
    )


@router.get("/my-tasks", response_model=list[TaskSchema])
def get_my_tasks(
    user_id: int = Depends(get_user_id),
    service: MatchService = Depends(get_service),
    presenter: TaskPresenter = Depends(get_task_presenter),
) -> list[dict]:
    return _tasks_response(service.get_tasks({"owner_id": user_id}), service, presenter)


@router.get("/{task_id}", response_model=TaskSchema)
def get_task(
    task_id: int,
    _: User = Depends(verified_user),
    service: MatchService = Depends(get_service),
    presenter: TaskPresenter = Depends(get_task_presenter),
) -> dict:
    try:
        return _task_response(service.get_task_by_id(task_id), service, presenter)
    except TaskNotFound:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND)
