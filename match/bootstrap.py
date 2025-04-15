from match.app.service import MatchService
from match.infra.repositories import InMemoryMatchRepository

"""
TODO: This is not a nice way of doing the dependency injections.
"""


match_service = MatchService(repository=InMemoryMatchRepository())


def get_service() -> MatchService:
    return match_service
