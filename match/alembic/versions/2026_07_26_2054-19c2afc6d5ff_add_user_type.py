"""

Revision ID: 19c2afc6d5ff
Revises: e557cd96115f
Create Date: 2026-07-26 20:54:27.965092

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "19c2afc6d5ff"
down_revision: Union[str, Sequence[str], None] = "e557cd96115f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "user_type", sa.Enum("HELP_SEEKER", "VOLUNTEER", name="usertype"), nullable=False
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "user_type")
