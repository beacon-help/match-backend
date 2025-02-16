from match.domain import exceptions
from match.domain.interfaces import UserRepository
from match.domain.user import User


class InMemoryUserRepository(UserRepository):
    def __init__(self) -> None:
        self.users: dict[int, User] = {}

    def create_user(self, user_data: dict) -> User:
        user_id = 1
        while user_id in self.users:
            user_id += 1
        user = User(id=user_id, **user_data)
        self.users[user.id] = user
        return user

    def get_user_by_id(self, user_id: int) -> User:
        try:
            return self.users[user_id]
        except KeyError:
            raise exceptions.UserNotFound
