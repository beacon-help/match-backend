"""soft_delete_users

Revision ID: 7331add87614
Revises: d56fce9e1540
Create Date: 2026-10-04 23:50:35.856734

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "7331add87614"
down_revision: Union[str, Sequence[str], None] = "d56fce9e1540"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Not batch mode: recreating tasks fails on SQLite because view tasks_with_status depends on it.
    op.add_column("tasks", sa.Column("deleted_at", sa.DateTime(), nullable=True))
    # AUTOINCREMENT stops SQLite from reusing ids of purged users still referenced by other tasks.
    # The naming convention gives the reflected unnamed UNIQUE(email) a name so it can be dropped.
    with op.batch_alter_table(
        "users",
        recreate="always",
        table_kwargs={"sqlite_autoincrement": True},
        naming_convention={"uq": "uq_%(table_name)s_%(column_0_name)s"},
    ) as batch_op:
        batch_op.add_column(sa.Column("deleted_at", sa.DateTime(), nullable=True))
        batch_op.drop_constraint("uq_users_email", type_="unique")
    op.create_index(
        "ix_users_email_active",
        "users",
        ["email"],
        unique=True,
        sqlite_where=sa.text("deleted_at IS NULL"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    shared_emails = op.get_bind().scalar(
        sa.text("SELECT COUNT(*) FROM (SELECT email FROM users GROUP BY email HAVING COUNT(*) > 1)")
    )
    if shared_emails:
        raise RuntimeError(
            f"{shared_emails} emails belong to several accounts; "
            "purge soft-deleted users before downgrading."
        )
    op.drop_index("ix_users_email_active", table_name="users")
    with op.batch_alter_table("users", recreate="always") as batch_op:
        batch_op.drop_column("deleted_at")
        batch_op.create_unique_constraint("uq_users_email", ["email"])
    op.drop_column("tasks", "deleted_at")
