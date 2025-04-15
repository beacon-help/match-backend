from dataclasses import dataclass

from match.domain.interfaces import MatchRepository
from match.domain.task import Task
from match.domain.user import User


@dataclass
class MatchService:
    repository: MatchRepository

    def create_user(self, first_name: str, last_name: str, email: str) -> User:
        user_data = {"first_name": first_name, "last_name": last_name, "email": email}
        user = self.repository.create_user(user_data=user_data)
        return user

    def get_user_by_id(self, user_id: int) -> User:
        return self.repository.get_user_by_id(user_id)

    def create_task(self, user_id: int, description: str, title: str) -> Task:
        user = self.repository.get_user_by_id(user_id)
        task = Task.create_task(owner=user, title=title, description=description)
        task = self.repository.create_task(task)
        return task

    def get_task_by_id(self, task_id: int) -> Task:
        return self.repository.get_task_by_id(task_id)

    def get_tasks(self) -> list[Task]:
        return self.repository.get_tasks()

    def task_join(self, task_id: int, user_id: int) -> Task:
        task = self.get_task_by_id(task_id)
        user = self.get_user_by_id(user_id)
        task.join(user)
        task = self.repository.task_update(task)
        return task

    def task_approve(self, task_id: int, owner_id: int, helper_id: int) -> Task:
        task = self.get_task_by_id(task_id)
        owner = self.get_user_by_id(owner_id)
        task.approve_helper(owner, helper_id=helper_id)
        task = self.repository.task_update(task)
        return task

    def task_reject(self, task_id: int, owner_id: int, helper_id: int) -> Task:
        task = self.get_task_by_id(task_id)
        owner = self.get_user_by_id(owner_id)
        task.reject_helper(owner, helper_id=helper_id)
        task = self.repository.task_update(task)
        return task
