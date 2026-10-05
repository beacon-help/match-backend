from fastapi import Depends
from sqlalchemy.orm.session import Session as SQLAlchemySession

from match.app.service import MatchService
from match.config import get_config
from match.db import get_session
from match.infra.image_repository import LocalImageRepository
from match.infra.message_client import FakeMessageClient
from match.infra.password_hasher import PwdlibPasswordHasher
from match.infra.repositories import SQLiteRepository
from match.infra.unit_of_work import SqlAlchemyUnitOfWork

config = get_config()
image_repository = LocalImageRepository()
message_client = FakeMessageClient(config=config)
password_hasher = PwdlibPasswordHasher()


def build_service(session: SQLAlchemySession) -> MatchService:
    return MatchService(
        user_messaging_client=message_client,
        repository=SQLiteRepository(session=session),
        image_repository=image_repository,
        password_hasher=password_hasher,
        unit_of_work=SqlAlchemyUnitOfWork(session),
        _fe_host=config.FE_HOST,
    )


def get_service(session: SQLAlchemySession = Depends(get_session)) -> MatchService:
    return build_service(session)
