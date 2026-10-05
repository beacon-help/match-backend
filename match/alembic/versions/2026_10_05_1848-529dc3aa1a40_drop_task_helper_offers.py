"""drop_task_helper_offers

Revision ID: 529dc3aa1a40
Revises: 7331add87614
Create Date: 2026-10-05 18:48:56.377296

"""

import json
from collections import defaultdict
from datetime import timezone
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "529dc3aa1a40"
down_revision: Union[str, Sequence[str], None] = "7331add87614"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

tasks_table = sa.table("tasks", sa.column("id", sa.Integer), sa.column("helper_offers", sa.String))
task_events_table = sa.table(
    "task_events",
    sa.column("id", sa.Integer),
    sa.column("task_id", sa.Integer),
    sa.column("type", sa.String),
    sa.column("actor_id", sa.Integer),
    sa.column("message", sa.String),
    sa.column("occurred_at", sa.DateTime),
)


def _restore_helper_offers() -> None:
    connection = op.get_bind()
    offered = connection.execute(
        sa.select(task_events_table)
        .where(task_events_table.c.type == "offered")
        .order_by(task_events_table.c.occurred_at, task_events_table.c.id)
    )
    offers_by_task_id: dict[int, list[dict]] = defaultdict(list)
    for event in offered:
        offers_by_task_id[event.task_id].append(
            {
                "user_id": event.actor_id,
                "offered_at": event.occurred_at.replace(tzinfo=timezone.utc).isoformat(),
                "message": event.message or "",
            }
        )
    for task_id, offers in offers_by_task_id.items():
        connection.execute(
            tasks_table.update()
            .where(tasks_table.c.id == task_id)
            .values(helper_offers=json.dumps(offers))
        )


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_column("tasks", "helper_offers")


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column("tasks", sa.Column("helper_offers", sa.VARCHAR(), nullable=True))
    _restore_helper_offers()
