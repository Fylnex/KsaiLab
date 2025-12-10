"""add_target_questions_to_tests

Revision ID: 0c8ee67e2491
Revises: rename_image_to_image_url
Create Date: 2025-10-03 08:14:44.237298

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0c8ee67e2491"
down_revision: Union[str, Sequence[str], None] = "rename_image_to_image_url"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add target_questions column to tests table
    op.add_column("tests", sa.Column("target_questions", sa.Integer(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    # Remove target_questions column from tests table
    op.drop_column("tests", "target_questions")
