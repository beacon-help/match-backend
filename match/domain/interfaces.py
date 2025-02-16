import abc

from match.domain.user import User


class UserRepository(abc.ABC):
    @abc.abstractmethod
    def create_user(self, user_data: dict) -> User: ...

    @abc.abstractmethod
    def get_user_by_id(self, user_id: int) -> User: ...
