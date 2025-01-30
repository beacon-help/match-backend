from datetime import datetime, timezone
from http import HTTPStatus

from fastapi import APIRouter

from match.api.schemas import TaskCreationRequestSchema, TaskSchema, TaskStatus, TaskType

router = APIRouter()


@router.post("/", response_model=TaskSchema, status_code=HTTPStatus.CREATED)
def create_task(task_creation_params: TaskCreationRequestSchema) -> dict:
    task_data = task_creation_params.model_dump()

    return TaskSchema(
        **task_data,
        id=1,
        created_at=datetime.now(timezone.utc),
        status=TaskStatus.OPEN,
        requester_id=1,
    ).model_dump()


@router.get("/{task_id}", response_model=TaskSchema)
def get_task(task_id: int) -> dict:
    return TaskSchema(
        id=task_id,
        name="Task 1",
        created_at=datetime(year=2024, month=11, day=14, tzinfo=timezone.utc),
        status=TaskStatus.OPEN,
        requester_id=3,
        helper_id=None,
        type=TaskType.TASK_TYPE_1,
        description="This is a description.",
        location="This will be a location",
    ).model_dump()


@router.put("/manage/{task_id}", response_model=TaskSchema)
def update_task(task_id: int, task_update_params: TaskCreationRequestSchema) -> dict:

    task_data = task_update_params.model_dump()

    return TaskSchema(
        **task_data,
        id=task_id,
        created_at=datetime.now(timezone.utc),
        status=TaskStatus.OPEN,
        requester_id=1,
    ).model_dump()


@router.put("/{task_id}", response_model=TaskSchema)
def manage_task(task_id: int, action: str) -> dict:
    task_schema = TaskSchema(
        id=task_id,
        name="Task 1",
        created_at=datetime(year=2024, month=11, day=14, tzinfo=timezone.utc),
        status=TaskStatus.OPEN,
        requester_id=3,
        helper_id=None,
        type=TaskType.TASK_TYPE_1,
        description="This is a description.",
        location="This will be a location",
    )
    match action:
        case "sign":
            task_schema.helper_id = 4
            task_schema.status = TaskStatus.PENDING_APPROVAL
        case "approve":
            task_schema.helper_id = 4
            task_schema.status = TaskStatus.IN_PROGRESS
        case "close":
            task_schema.helper_id = 4
            task_schema.status = TaskStatus.DONE
        case "cancel":
            task_schema.helper_id = 4
            task_schema.status = TaskStatus.CANCELLED
        case _:
            raise Exception

    return task_schema.model_dump()


@router.get("/", response_model=list[TaskSchema])
def list_tasks() -> list:
    return [
        TaskSchema(
            id=1,
            name="Task 1",
            created_at=datetime(year=2024, month=11, day=14, tzinfo=timezone.utc),
            status=TaskStatus.OPEN,
            requester_id=3,
            helper_id=None,
            type=TaskType.TASK_TYPE_1,
            description="This is a description.",
            location="This will be a location",
        ).model_dump(),
        TaskSchema(
            id=2,
            name="Task 2",
            created_at=datetime(year=2024, month=12, day=14, tzinfo=timezone.utc),
            status=TaskStatus.IN_PROGRESS,
            requester_id=3,
            helper_id=5,
            type=TaskType.TASK_TYPE_1,
            description="This is a description.",
            location="This will be a location",
        ).model_dump(),
    ]
