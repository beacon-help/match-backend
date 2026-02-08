from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.session import Session as SQLAlchemySession

SQLALCHEMY_DB_URL = "sqlite:////usr/src/app/data/app.db"

engine = create_engine(SQLALCHEMY_DB_URL, connect_args={"check_same_thread": False})

Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db() -> Generator[SQLAlchemySession]:
    try:
        db = Session()
        yield db
    finally:
        db.close()
