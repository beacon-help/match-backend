from dataclasses import asdict
from http import HTTPStatus
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request

from match.app.service import MatchService
from match.bootstrap import get_service
from match.domain.exceptions import PermissionDenied
from match.domain.task import Task
from match.infra.api.auth import get_user_id
from match.infra.api.schemas import TaskCreationRequestSchema, TaskSchema

router = APIRouter()


def task_to_dict(task: Task) -> dict[str, Any]:

    task_dict = asdict(task)
    # task_dict["owner_id"] = task.owner_id
    # task_dict["helper_id"] = task.helper_id

    return task_dict


@router.post("/", response_model=TaskSchema, status_code=HTTPStatus.CREATED)
def create_task(
    request: Request,
    task_creation_params: TaskCreationRequestSchema,
    service: MatchService = Depends(get_service),
) -> dict:
    user_id = get_user_id(request)
    try:
        task = service.create_task(
            user_id, description=task_creation_params.description, title=task_creation_params.title
        )
        return task_to_dict(task)
    except PermissionDenied:
        raise HTTPException(status_code=HTTPStatus.FORBIDDEN)


@router.get("/{task_id}", response_model=TaskSchema)
def get_task(task_id: int, service: MatchService = Depends(get_service)) -> dict:
    task = service.get_task_by_id(task_id)
    return task_to_dict(task)


@router.put("/{task_id}", response_model=TaskSchema)
def manage_task(
    request: Request,
    task_id: int,
    action: str,
    helper_id: int | None = None,
    service: MatchService = Depends(get_service),
) -> dict:
    user_id = get_user_id(request)

    try:
        match action:
            case "join":
                task = service.task_join(task_id, user_id)
            case "approve":
                if helper_id is None:
                    raise HTTPException(
                        status_code=HTTPStatus.BAD_REQUEST, detail="Helper id not provided."
                    )
                task = service.task_approve(task_id, owner_id=user_id, helper_id=helper_id)
            case "reject":
                if helper_id is None:
                    raise HTTPException(
                        status_code=HTTPStatus.BAD_REQUEST, detail="Helper id not provided."
                    )
                task = service.task_reject(task_id, owner_id=user_id, helper_id=helper_id)
            case "close":
                task = service.task_close(task_id, owner_id=user_id)
            case "report_success":
                task = service.task_report_success(task_id, owner_id=user_id)
            case "report_failure":
                task = service.task_report_failed(task_id, owner_id=user_id)

            case _:
                raise HTTPException(status_code=HTTPStatus.BAD_REQUEST)
    except PermissionDenied as e:
        raise HTTPException(
            status_code=HTTPStatus.FORBIDDEN,
            detail=f"Permission denied for user {user_id}.{str(e)}",
        )

    return task_to_dict(task)


@router.get("/", response_model=list[TaskSchema])
def list_tasks(service: MatchService = Depends(get_service)) -> list:
    tasks = service.get_tasks()
    return [task_to_dict(t) for t in tasks]
