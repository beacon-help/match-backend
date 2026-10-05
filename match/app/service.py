from dataclasses import dataclass
from datetime import datetime
from typing import Any, Iterable

from match.app.exceptions import AuthenticationFailed, ImageNotFound, MatchServiceException
from match.domain.exceptions import UserNotFound, UserVerificationCodeInvalid
from match.domain.interfaces import (
    ImageRepository,
    MessageClient,
    PasswordHasher,
    TaskFilter,
    TaskRepository,
    UnitOfWork,
    UserRepository,
)
from match.domain.task import Category, ImageId, Location, Task, TaskStatus
from match.domain.user import User, UserId, UserType, create_user_verification_message

VERIFICATION_URL = "localhost:8000/user/verify/"


@dataclass
class MatchService:
    user_messaging_client: MessageClient
    user_repository: UserRepository
    task_repository: TaskRepository
    image_repository: ImageRepository
    password_hasher: PasswordHasher
    unit_of_work: UnitOfWork
    _fe_host: str

    def _construct_verification_url(self, code: str) -> str:
        return f"{self._fe_host}/verify/{code}"

    def _create_user(
        self,
        user_type: UserType,
        first_name: str,
        last_name: str,
        email: str,
        password: str,
        properties: Iterable[Any],
    ) -> User:
        user_data = {
            "user_type": user_type,
            "first_name": first_name,
            "last_name": last_name,
            "email": email,
            "is_verified": False,
            "properties": [getattr(property_, "value", property_) for property_ in properties],
            "password_hash": self.password_hasher.hash(password),
        }
        user = self.user_repository.create_user(user_data=user_data)
        self.unit_of_work.commit()
        return user

    def create_user(
        self,
        user_type: UserType,
        first_name: str,
        last_name: str,
        email: str,
        password: str,
        properties: Iterable[Any] = (),
    ) -> User:
        return self._create_user(
            user_type, first_name, last_name, email, password, properties=properties
        )

    def authenticate(self, email: str, password: str) -> User:
        try:
            user = self.user_repository.get_user_by_email(email)
        except UserNotFound:
            raise AuthenticationFailed
        if user.password_hash is None or not self.password_hasher.verify(
            password, user.password_hash
        ):
            raise AuthenticationFailed
        if not user.is_verified:
            raise AuthenticationFailed
        return user

    def send_verification_request(self, user: User) -> None:
        if not user.verification_code:
            raise Exception
        verification_url = VERIFICATION_URL + user.verification_code
        message = create_user_verification_message(user, verification_url)
        print("FE verification link:", self._construct_verification_url(user.verification_code))
        self.user_messaging_client.send_message(message, user)

    def verify_user_with_code(self, verification_code: str) -> None:
        try:
            user = self.user_repository.get_user_by_verification_code(verification_code)
        except UserNotFound:
            raise UserVerificationCodeInvalid
        user = user.verify(verification_code)
        self.user_repository.user_update(user)
        self.unit_of_work.commit()

    def get_user_by_id(self, user_id: int) -> User:
        return self.user_repository.get_user_by_id(user_id)

    def delete_user(self, user_id: int) -> None:
        user = self.get_user_by_id(user_id)
        deleted_at = user.delete()
        self.user_repository.user_update(user)
        self.task_repository.tasks_delete_owned_by(user.id, deleted_at)
        self.unit_of_work.commit()

    def purge_deleted_users(self, deleted_before: datetime) -> int:
        user_ids = self.user_repository.get_user_ids_deleted_before(deleted_before)
        image_ids = self.task_repository.tasks_purge_owned_by(user_ids)
        self.user_repository.users_purge(user_ids)
        self.unit_of_work.commit()
        for image_id in image_ids:
            self.image_repository.delete(image_id)
        return len(user_ids)

    def create_task(
        self,
        user_id: int,
        description: str,
        title: str,
        category: str,
        location_lon: float | None = None,
        location_lat: float | None = None,
        location_address: str | None = None,
    ) -> Task:
        user = self.get_user_by_id(user_id)
        if location_lat is not None and location_lon is not None and location_address is not None:
            location = Location(lon=location_lon, lat=location_lat, address=location_address)
        elif location_lat is None and location_lon is None and location_address is None:
            location = None
        else:
            raise Exception("Incorrect location.")

        try:
            category_enum = Category(category.lower())
        except ValueError:
            raise MatchServiceException(f"Incorrect category {category}.")
        task = Task.create_task(
            owner=user,
            title=title,
            description=description,
            category=category_enum,
            location=location,
        )
        task = self.task_repository.create_task(task)
        self.unit_of_work.commit()
        return task

    def get_task_by_id(self, task_id: int) -> Task:
        return self.task_repository.get_task_by_id(task_id)

    def get_tasks(self, filters: TaskFilter | None = None) -> list[Task]:
        return self.task_repository.get_tasks(filters=filters)

    def get_users_referenced_by(self, tasks: Iterable[Task]) -> dict[UserId, User]:
        return self.user_repository.get_users_by_ids(
            {user_id for task in tasks for user_id in task.participant_ids}
        )

    def task_join(self, task_id: int, user_id: int, message: str) -> Task:
        task = self.get_task_by_id(task_id)
        user = self.get_user_by_id(user_id)
        task.join(user, message)
        task = self.task_repository.task_update(task)
        self.unit_of_work.commit()
        return task

    def task_approve(self, task_id: int, owner_id: int, helper_id: int) -> Task:
        task = self.get_task_by_id(task_id)
        owner = self.get_user_by_id(owner_id)
        task.approve_helper(owner, helper_id=UserId(helper_id))
        task = self.task_repository.task_update(task)
        self.unit_of_work.commit()
        return task

    def task_reject(self, task_id: int, owner_id: int, helper_id: int) -> Task:
        task = self.get_task_by_id(task_id)
        owner = self.get_user_by_id(owner_id)
        task.reject_helper(owner, helper_id=UserId(helper_id))
        task = self.task_repository.task_update(task)
        self.unit_of_work.commit()
        return task

    def task_withdraw(self, task_id: int, helper_id: int) -> Task:
        task = self.get_task_by_id(task_id)
        helper = self.get_user_by_id(helper_id)
        task.withdraw(helper)
        task = self.task_repository.task_update(task)
        self.unit_of_work.commit()
        return task

    def task_edit(
        self,
        task_id: int,
        owner_id: int,
        title: str | None = None,
        description: str | None = None,
        category: str | None = None,
        location_lon: float | None = None,
        location_lat: float | None = None,
        location_address: str | None = None,
    ) -> Task:
        task = self.get_task_by_id(task_id)
        owner = self.get_user_by_id(owner_id)

        category_enum = None
        if category is not None:
            try:
                category_enum = Category(category.lower())
            except ValueError:
                raise MatchServiceException(f"Incorrect category {category}.")

        location = None
        if location_lat is not None and location_lon is not None and location_address is not None:
            location = Location(lon=location_lon, lat=location_lat, address=location_address)
        elif location_lat is not None or location_lon is not None or location_address is not None:
            raise MatchServiceException("Incorrect location.")

        task.edit(
            owner,
            title=title,
            description=description,
            category=category_enum,
            location=location,
        )
        task = self.task_repository.task_update(task)
        self.unit_of_work.commit()
        return task

    def get_task_image(self, image_id: str) -> bytes:
        if not self.task_repository.image_exists(ImageId(image_id)):
            raise ImageNotFound
        return self.image_repository.read([image_id])[image_id]

    def task_add_images(self, task_id: int, owner_id: int, images: list[bytes]) -> Task:
        task = self.get_task_by_id(task_id)
        owner = self.get_user_by_id(owner_id)
        task.validate_editable_by(owner)
        image_ids = [ImageId(self.image_repository.upload(image)) for image in images]
        task.add_images(owner, image_ids)
        task = self.task_repository.task_update(task)
        self.unit_of_work.commit()
        return task

    def task_remove_image(self, task_id: int, owner_id: int, image_id: str) -> Task:
        task = self.get_task_by_id(task_id)
        owner = self.get_user_by_id(owner_id)
        task.remove_image(owner, ImageId(image_id))
        task = self.task_repository.task_update(task)
        self.task_repository.images_delete([ImageId(image_id)])
        self.unit_of_work.commit()
        self.image_repository.delete(image_id)
        return task

    def task_close(self, task_id: int, owner_id: int) -> Task:
        task = self.get_task_by_id(task_id)
        owner = self.get_user_by_id(owner_id)
        task.close(owner)
        task = self.task_repository.task_update(task)
        self.unit_of_work.commit()
        return task

    def task_report_success(self, task_id: int, owner_id: int) -> Task:
        task = self.get_task_by_id(task_id)
        owner = self.get_user_by_id(owner_id)
        task.report_succeeded(owner)
        task = self.task_repository.task_update(task)
        self.unit_of_work.commit()
        return task

    def task_report_failed(self, task_id: int, owner_id: int) -> Task:
        task = self.get_task_by_id(task_id)
        owner = self.get_user_by_id(owner_id)
        task.report_failed(owner)
        task = self.task_repository.task_update(task)
        self.unit_of_work.commit()
        return task

    def _get_task_stats(self) -> dict[str, int]:
        counts = self.task_repository.count_tasks_by_status()
        return {
            "total": sum(counts.values()),
            "successful": counts.get(TaskStatus.SUCCEEDED, 0),
            "in_progress": counts.get(TaskStatus.PENDING, 0) + counts.get(TaskStatus.APPROVED, 0),
        }

    def _get_user_stats(self) -> dict[str, int]:
        counts = self.user_repository.count_users_by_type()
        return {
            "total_helpers": counts.get(UserType.VOLUNTEER, 0),
            "total_help_seekers": counts.get(UserType.HELP_SEEKER, 0),
        }

    def get_stats(self) -> tuple[dict[str, int], dict[str, int]]:
        return self._get_task_stats(), self._get_user_stats()
