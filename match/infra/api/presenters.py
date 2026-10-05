from dataclasses import asdict
from typing import Any

from match.domain.task import ImageId, Task
from match.domain.user import User, UserId

DELETED_USER_FIRST_NAME = "Deleted user"


class TaskPresenter:
    def __init__(self, backend_host: str) -> None:
        self.backend_host = backend_host

    def image_url(self, image_id: ImageId) -> str:
        return f"{self.backend_host}/task/images/{image_id}"

    @staticmethod
    def user_summary(
        user_id: UserId | None, users_by_id: dict[UserId, User]
    ) -> dict[str, Any] | None:
        if user_id is None:
            return None
        user = users_by_id.get(user_id)
        first_name = user.first_name if user is not None else DELETED_USER_FIRST_NAME
        return {"id": user_id, "first_name": first_name}

    def task(self, task: Task, users_by_id: dict[UserId, User]) -> dict[str, Any]:
        task_dict = asdict(task)
        task_dict.pop("owner_id")
        task_dict.pop("helper_id")
        task_dict["owner"] = self.user_summary(task.owner_id, users_by_id)
        task_dict["helper"] = self.user_summary(task.helper_id, users_by_id)
        task_dict["images"] = [
            {"id": image_id, "path": self.image_url(image_id)} for image_id in task.images
        ]
        task_dict["events"] = [
            {
                "id": event.id,
                "type": event.type,
                "actor": self.user_summary(event.actor_id, users_by_id),
                "helper": self.user_summary(event.helper_id, users_by_id),
                "message": event.message,
                "occurred_at": event.occurred_at,
            }
            for event in task.events
        ]
        return task_dict

    def tasks(self, tasks: list[Task], users_by_id: dict[UserId, User]) -> list[dict[str, Any]]:
        return [self.task(task, users_by_id) for task in tasks]

    @staticmethod
    def locations(tasks: list[Task]) -> list[dict[str, Any]]:
        return [
            {"id": task.id, "location": task.location}
            for task in tasks
            if task.location is not None
        ]
