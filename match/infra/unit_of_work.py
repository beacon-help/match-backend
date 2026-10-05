from sqlalchemy.orm.session import Session as SQLAlchemySession

from match.domain.interfaces import UnitOfWork


class SqlAlchemyUnitOfWork(UnitOfWork):
    def __init__(self, session: SQLAlchemySession) -> None:
        self.session = session

    def commit(self) -> None:
        self.session.commit()
