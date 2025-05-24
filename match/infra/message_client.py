from match.domain.interfaces import MessageClient
from match.domain.user import User


class FakeMessageClient(MessageClient):
    def send_message(self, message: str, user: User) -> None:
        print(f"Sending message: {message} to user: {user}.")
