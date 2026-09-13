from match.app.service import MatchService
from match.config import get_config
from match.db import Session
from match.infra.image_repository import LocalImageRepository
from match.infra.message_client import FakeMessageClient
from match.infra.repositories import SQLiteRepository

"""
TODO: This is not a nice way of doing the dependency injections.
"""

config = get_config()

repository = SQLiteRepository(session=Session())
image_repository = LocalImageRepository()

match_service = MatchService(
    user_messaging_client=FakeMessageClient(config=config),
    repository=repository,
    image_repository=image_repository,
    _fe_host=config.FE_HOST,
    _backend_host=config.BACKEND_HOST,
)


def get_service() -> MatchService:
    return match_service
