from dataclasses import asdict
from http import HTTPStatus
from typing import Any

from fastapi import APIRouter, Depends, Request

from match.app.service import MatchService
from match.bootstrap import get_service
from match.domain.task import Task
from match.infra.api.auth import get_user_id
from match.infra.api.schemas import TaskCreationRequestSchema, TaskSchema

router = APIRouter()


def task_to_dict(task: Task) -> dict[str, Any]:

    task_dict = asdict(task)
    task_dict["owner_id"] = task.owner.id if task.owner else None
    task_dict["helper_id"] = task.helper.id if task.helper else None

    return task_dict


@router.post("/", response_model=TaskSchema, status_code=HTTPStatus.CREATED)
def create_task(
    request: Request,
    task_creation_params: TaskCreationRequestSchema,
    service: MatchService = Depends(get_service),
) -> dict:
    print("ELOELO")
    user_id = get_user_id(request)
    task = service.create_task(
        user_id, description=task_creation_params.description, title=task_creation_params.title
    )
    return task_to_dict(task)


@router.get("/{task_id}", response_model=TaskSchema)
def get_task(task_id: int, service: MatchService = Depends(get_service)) -> dict:
    task = service.get_task_by_id(task_id)
    print(asdict(task))
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

    match action:
        case "join":
            task = service.task_join(task_id, user_id)
        case "approve":
            if helper_id is None:
                raise Exception("Helper id not provided.")
            task = service.task_approve(task_id, owner_id=user_id, helper_id=helper_id)
        case "reject":
            if helper_id is None:
                raise Exception("Helper id not provided.")
            task = service.task_reject(task_id, owner_id=user_id, helper_id=helper_id)
        case "close":
            task = service.task_close(task_id, owner_id=user_id)
        case "report_success":
            task = service.task_report_success(task_id, owner_id=user_id)
        case "report_failure":
            task = service.task_report_failed(task_id, owner_id=user_id)

        case _:
            raise Exception

    return task_to_dict(task)


@router.get("/", response_model=list[TaskSchema])
def list_tasks(service: MatchService = Depends(get_service)) -> list:
    tasks = service.get_tasks()
    return [task_to_dict(t) for t in tasks]
