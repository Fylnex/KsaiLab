"""Rename image to image_url in questions table

Revision ID: rename_image_to_image_url
Revises: add_group_topics_table
Create Date: 2025-01-22 13:45:00.000000

"""

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "rename_image_to_image_url"
down_revision: str = "add_group_topics_table"
branch_labels: None = None
depends_on: None = None


def upgrade() -> None:
    # Rename the column from 'image' to 'image_url'
    op.alter_column("questions", "image", new_column_name="image_url")


def downgrade() -> None:
    # Rename the column back from 'image_url' to 'image'
    op.alter_column("questions", "image_url", new_column_name="image")
