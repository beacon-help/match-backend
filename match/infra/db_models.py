from datetime import datetime

from sqlalchemy import CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column

from match.db import Base


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
    status: Mapped[str] = mapped_column()
    category: Mapped[str] = mapped_column()
    owner_id: Mapped[int] = mapped_column()
    helper_id: Mapped[int | None] = mapped_column()
    updated_at: Mapped[datetime | None] = mapped_column()
    created_at: Mapped[datetime] = mapped_column()
    location_lat: Mapped[float | None] = mapped_column()
    location_lon: Mapped[float | None] = mapped_column()
    location_address: Mapped[str | None] = mapped_column()
