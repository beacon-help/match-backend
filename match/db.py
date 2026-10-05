from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.session import Session as SQLAlchemySession

from match.config import get_config

engine = create_engine(
    f"sqlite:///{get_config().DB_PATH}", connect_args={"check_same_thread": False}
)

Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_session() -> Iterator[SQLAlchemySession]:
    with Session() as session:
        yield session
