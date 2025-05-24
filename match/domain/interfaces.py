import abc

from match.domain.task import Task
from match.domain.user import User


class MatchRepository(abc.ABC):
    @abc.abstractmethod
    def create_user(self, user_data: dict) -> User: ...

    @abc.abstractmethod
    def get_user_by_id(self, user_id: int) -> User: ...

    @abc.abstractmethod
    def user_update(self, user: User) -> User: ...

    @abc.abstractmethod
    def create_task(self, task: Task) -> Task: ...

    @abc.abstractmethod
    def get_task_by_id(self, task_id: int) -> Task: ...

    @abc.abstractmethod
    def get_tasks(self) -> list[Task]: ...

    @abc.abstractmethod
    def task_update(self, task: Task) -> Task: ...


class MessageClient(abc.ABC):
    @abc.abstractmethod
    def send_message(self, message: str, user: User) -> None: ...
