from datetime import datetime

from sqlalchemy.orm import Mapped, mapped_column

from match.db import Base


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement="auto")
    title: Mapped[str] = mapped_column()
    description: Mapped[str] = mapped_column()
    status: Mapped[str] = mapped_column()
    owner_id: Mapped[int] = mapped_column()
    helper_id: Mapped[int | None] = mapped_column()
    updated_at: Mapped[datetime | None] = mapped_column()
    created_at: Mapped[datetime] = mapped_column()
