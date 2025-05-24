from match.app.service import MatchService
from match.config import get_config
from match.infra.message_client import FakeMessageClient
from match.infra.repositories import InMemoryMatchRepository

"""
TODO: This is not a nice way of doing the dependency injections.
"""

config = get_config()

match_service = MatchService(
    user_messaging_client=FakeMessageClient(config=config), repository=InMemoryMatchRepository()
)


def get_service() -> MatchService:
    return match_service
