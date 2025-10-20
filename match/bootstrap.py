from match.app.service import MatchService
from match.config import get_config
from match.db import Session
from match.infra.message_client import FakeMessageClient
from match.infra.repositories import InMemoryMatchRepository, SQLiteRepository

"""
TODO: This is not a nice way of doing the dependency injections.
"""

config = get_config()

repository = SQLiteRepository(session=Session())
match_service = MatchService(
    user_messaging_client=FakeMessageClient(config=config), repository=repository
)


def get_service() -> MatchService:
    return match_service
