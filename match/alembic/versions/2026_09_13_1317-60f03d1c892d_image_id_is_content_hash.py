"""image_id_is_content_hash

Revision ID: 60f03d1c892d
Revises: abbd778f0ae0
Create Date: 2026-09-13 13:17:37.391803

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '60f03d1c892d'
down_revision: Union[str, Sequence[str], None] = 'abbd778f0ae0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("images") as batch_op:
        batch_op.alter_column(
            "id",
            existing_type=sa.INTEGER(),
            type_=sa.String(),
            existing_nullable=False,
        )
        batch_op.drop_index("ix_images_id")


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("images") as batch_op:
        batch_op.create_index("ix_images_id", ["id"], unique=False)
        batch_op.alter_column(
            "id",
            existing_type=sa.String(),
            type_=sa.INTEGER(),
            existing_nullable=False,
        )
