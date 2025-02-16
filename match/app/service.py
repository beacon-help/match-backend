from dataclasses import dataclass

from match.domain.interfaces import UserRepository


@dataclass
class MatchService:
    user_repository: UserRepository
