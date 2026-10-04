from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    Column,
    ForeignKey,
    Index,
    Integer,
    MetaData,
    String,
    Table,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from match.db import Base
from match.domain.user import UserType


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        Index(
            "ix_users_email_active",
            "email",
            unique=True,
            sqlite_where=text("deleted_at IS NULL"),
        ),
        {"sqlite_autoincrement": True},
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement="auto")
    user_type: Mapped[UserType] = mapped_column()
    first_name: Mapped[str] = mapped_column()
    last_name: Mapped[str] = mapped_column()
    email: Mapped[str] = mapped_column()
    properties: Mapped[str] = mapped_column()
    is_verified: Mapped[bool] = mapped_column(default=False)
    verification_code: Mapped[str] = mapped_column()
    password_hash: Mapped[str | None] = mapped_column(default=None)
    created_at: Mapped[datetime] = mapped_column()
    deleted_at: Mapped[datetime | None] = mapped_column(default=None)


class Task(Base):
    __tablename__ = "tasks"

    __table_args__ = (
        CheckConstraint(
            "(location_lat IS NULL AND location_lon IS NULL AND location_address IS NULL) OR "
            "(location_lat IS NOT NULL AND location_lon IS NOT NULL AND location_address IS NOT NULL)",
            name="location_all_or_nothing",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement="auto")
    title: Mapped[str] = mapped_column()
    description: Mapped[str] = mapped_column()
    category: Mapped[str] = mapped_column()
    owner_id: Mapped[int] = mapped_column()
    helper_id: Mapped[int | None] = mapped_column()
    helper_offers: Mapped[str | None] = mapped_column()
    updated_at: Mapped[datetime | None] = mapped_column()
    created_at: Mapped[datetime] = mapped_column()
    location_lat: Mapped[float | None] = mapped_column()
    location_lon: Mapped[float | None] = mapped_column()
    location_address: Mapped[str | None] = mapped_column()
    deleted_at: Mapped[datetime | None] = mapped_column(default=None)


class Image(Base):
    __tablename__ = "images"

    id: Mapped[str] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id"), index=True)


class TaskEvent(Base):
    __tablename__ = "task_events"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement="auto")
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id"), index=True)
    type: Mapped[str] = mapped_column()
    actor_id: Mapped[int] = mapped_column()
    helper_id: Mapped[int | None] = mapped_column()
    message: Mapped[str | None] = mapped_column()
    occurred_at: Mapped[datetime] = mapped_column()


# View created by migration d56fce9e1540; kept off Base.metadata so create_all skips it.
tasks_with_status = Table(
    "tasks_with_status",
    MetaData(),
    Column("id", Integer, primary_key=True),
    Column("status", String),
)
