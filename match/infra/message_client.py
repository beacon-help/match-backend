from dataclasses import dataclass

from match.config import Config, Environment
from match.domain.interfaces import MessageClient
from match.domain.user import User


@dataclass
class FakeMessageClient(MessageClient):
    config: Config

    def send_message(self, message: str, user: User) -> None:
        if self.config.ENV == Environment.DEV:
            print(f"Sending message: {message} to user: {user}.")
