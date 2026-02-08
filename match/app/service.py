from dataclasses import dataclass

from match.domain.interfaces import MatchRepository, MessageClient
from match.domain.task import Category, Location, Task
from match.domain.user import User, create_user_verification_message

VERIFICATION_URL = "localhost:8000/user/verify/"


@dataclass
class MatchService:
    user_messaging_client: MessageClient
    repository: MatchRepository

    def create_user(self, first_name: str, last_name: str, email: str) -> User:
        user_data = {
            "first_name": first_name,
            "last_name": last_name,
            "email": email,
            "is_verified": False,
        }
        user = self.repository.create_user(user_data=user_data)
        return user

    def send_verification_request(self, user: User) -> None:
        if not user.verification_code:
            raise Exception
        verification_url = VERIFICATION_URL + user.verification_code
        message = create_user_verification_message(user, verification_url)
        self.user_messaging_client.send_message(message, user)

    def verify_user_with_code(self, user_id: int, verification_code: str) -> None:
        user = self.get_user_by_id(user_id)
        user = user.verify(verification_code)
        self.repository.user_update(user)

    def get_user_by_id(self, user_id: int) -> User:
        return self.repository.get_user_by_id(user_id)

    def create_task(
            self,
            user_id: int,
            description: str,
            title: str,
            category: str,
            location_lon: float | None = None,
            location_lat: float | None = None,
            location_address: str | None = None
    ) -> Task:
        user = self.get_user_by_id(user_id)
        if location_lat is not None and location_lon is not None and location_address is not None:
            location = Location(
                lon=location_lon,
                lat=location_lat,
                address=location_address
            )
        elif location_lat is None and location_lon is None and location_address is None:
            location = None
        else:
            raise Exception("Incorrect location.")

        try:
            category_enum = Category(category)
        except ValueError:
            raise Exception("Incorrect category")
        task = Task.create_task(owner=user, title=title, description=description, category=category_enum, location=location)
        task = self.repository.create_task(task)
        return task

    def get_task_by_id(self, task_id: int) -> Task:
        return self.repository.get_task_by_id(task_id)

    def get_tasks(self) -> list[Task]:
        return self.repository.get_tasks()

    def task_join(self, task_id: int, user_id: int) -> Task:
        task = self.get_task_by_id(task_id)
        user = self.get_user_by_id(user_id)
        if user_id != user.id:
            print("WFTFFF")
            raise Exception("lol")
        task.join(user.id)
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

    def task_close(self, task_id: int, owner_id: int) -> Task:
        task = self.get_task_by_id(task_id)
        owner = self.get_user_by_id(owner_id)
        task.close(owner)
        task = self.repository.task_update(task)
        return task

    def task_report_success(self, task_id: int, owner_id: int) -> Task:
        task = self.get_task_by_id(task_id)
        owner = self.get_user_by_id(owner_id)
        task.report_succeeded(owner)
        task = self.repository.task_update(task)
        return task

    def task_report_failed(self, task_id: int, owner_id: int) -> Task:
        task = self.get_task_by_id(task_id)
        owner = self.get_user_by_id(owner_id)
        task.report_failed(owner)
        task = self.repository.task_update(task)
        return task
