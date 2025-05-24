from match.app.service import MatchService
from match.infra.message_client import FakeMessageClient
from match.infra.repositories import InMemoryMatchRepository

"""
TODO: This is not a nice way of doing the dependency injections.
"""


match_service = MatchService(
    user_messaging_client=FakeMessageClient(), repository=InMemoryMatchRepository()
)


def get_service() -> MatchService:
    return match_service
